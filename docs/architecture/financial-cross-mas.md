# Cross-MAS integration admission gate

Status: W6 blocked before production implementation at baseline
`eb1d25678f16b3c43bd70c9aa3ec1a0d4a97c388`. W4 and W5 remain independent
workflows; this document does not declare W6 implemented or accepted.

## Frozen public API limitation

The frozen dispatcher exposes `create`, `start`, `snapshot`, `link_runs` and
`relations` to the router. `link_runs` atomically fences the source run version,
checks immutable ownership/timepoint metadata and persists a relation plus its
source event. It does not check or reserve persisted `RunBudget.hops` or
`RunBudget.followups`. Its transaction does not admit a correlation-wide graph
transition or fence the target run's lifecycle.

Only `RuntimeContext.consume_budget` currently reserves these counters. That
operation requires an executing driver's claim token; it is not a public router
operation. Reserving separately would also separate budget consumption from
relation insertion and break crash-safe idempotency.

A router cannot replace this with `snapshot`/`relations` reads followed by
`link_runs`: the reads and admission are separate transactions. Opposing sources
have independent CAS versions, so both may pass a previously observed graph.
Canonicalizing admission on one source can serialize relation changes but still
cannot reserve actual W1 counters through the allowed API. Envelope counters
alone would leave authoritative run counters unchanged and silently bypass the
frozen budget contract. Process locks would not survive restart or protect
multiple workers.

Consequently implementing W6-T4, lowered user budgets and concurrent admission
under the assigned public-only restriction requires an additive reviewed runtime
contract. No integration code should use private `_mutation`, runtime tables or
synthetic driver claims to work around this limitation.

## Required coordinator decision

Before implementation, the runtime owner must define an additive public atomic
cross-message admission operation and document its compatibility/rollback in an
ADR. The operation must combine:

- Durable exact-payload idempotency, checked before new-request terminal rules
  so an accepted historical request can be replayed without creating new work.
- Correlation-wide serialization or a canonical admission owner, with a graph
  rule that prevents cyclic waiting across concurrent opposing requests.
- The configured run hop/follow-up ceilings, including zero, authoritative
  counter reservation, and immutable logical hop/follow-up metadata in the
  persisted envelope/relation. Define which run pays each logical operation.
- Source and target lifecycle checks, aware UTC deadline validation, immutable
  artifact ownership/schema/timepoint checks and one transactional relation/event
  write. Terminal evidence producers may transfer an existing artifact; terminal
  Portfolio consumers cannot initiate new follow-up work.

Normal combined creation still requires separate Market and Portfolio run IDs,
shared correlation and independent state/budgets/events. `parent_run_id` keeps
retry-only semantics. Admission must support one bounded additional Market run
without changing completed producer history. No third business Coordinator is
needed.

After that contract is reviewed, W6 will implement the typed thin router and
scoped Portfolio artifact resolver using only public APIs and ArtifactStore,
with trusted saved-holdings scope and consumption-time TTL checks. Full W6 tests
must assemble the real W4/W5 drivers and W2/W3 tools on SQLite, including restart,
duplicate/concurrent admission, lowered budgets, peer failure, immutable history
and all three modes. PostgreSQL/worker/provider acceptance remains a separate
deployment gate.
