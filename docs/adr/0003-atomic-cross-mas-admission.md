# ADR-0003: Atomic cross-MAS message admission

- Status: Proposed; W6 is blocked until independent design and implementation reviews pass.
- Date: 2026-10-08
- Predecessor: frozen W1 contract and independent W4/W5 gates, integration `eb1d256`.

## Reproduced contract gap

`FinancialMASDispatcher.link_runs` performs source-run CAS and stores a relation/event. It does not reserve the authoritative `FinancialRun.budget.hops/followups`, serialize correlation-wide graph admission, or fence a recipient becoming terminal. `RuntimeContext.consume_budget` requires an executing driver's claim. A thin router cannot safely compose these operations from snapshot reads. W6 reported this block before implementing production communication. Envelope counters alone are not a budget authority.

## Additive decision

Add one public dispatcher method without changing requests, artifacts, checkpoints, existing lifecycle methods, default registries or table schemas:

```python
dispatcher.admit_cross_message(source_run_id: str, target_run_id: str,
    *, expected_source_version: int, expected_target_version: int,
    envelope: CrossMASEnvelope) -> dict
```

The returned relation snapshot identifies a reserved `relation_type='cross_admitted'`. Only this method may create that relation type; legacy `link_runs` remains a diagnostic compatibility seam and rejects the newly reserved type. W6 consumes only admitted envelopes. It never treats a historical diagnostic relation as executable authorization.

Admission is one transaction:

1. Load both runs, require the same conversation, correlation, aware `as_of`, opposite kinds and correct envelope ownership/direction/key. Acquire a canonical conversation-row write lock by updating `updated_at` to itself. This leaves its value unchanged, serializes financial admissions on PostgreSQL and SQLite, and requires no migration. Financial admissions in one conversation are deliberately serialized; General execution does not use this lock. Every writer of cross counters, including existing `RuntimeContext.consume_budget('hops'/'followups')`, must acquire this same conversation lock BEFORE any run CAS and apply the same correlation totals/ceilings. Its public signature and claim requirements stay unchanged; round reservations retain their existing single-run path.
2. Financial creation/retry also acquires that conversation lock before inserting membership or checking retry authority. Joining runs, including retries, enter correlation membership at commit; later charged admissions/reservations apply the lowest current member ceiling. A lower-ceiling join does not rewrite historical counters or revoke a valid existing request's zero-cost resolution, but prevents further charged work if totals already exceed its ceiling. No conversation lock is ever acquired after holding a run CAS lock.
3. After locking, look up the conversation idempotency key. An exact existing source/target/envelope AND reserved relation type returns unchanged before version, terminal or TTL checks, consuming no counters and appending no events. A changed payload or a legacy diagnostic key collision conflicts. Require message IDs to be nonblank and unique within the conversation under this lock, including IDs present on diagnostic envelopes, so causation cannot resolve ambiguously. Replaying an expired relation is historical retrieval only; consumers must recheck its TTL.
4. CAS both AgentRun rows in stable run-ID order using caller versions. Reload metadata/status under these locks. A stale version or terminal recipient rejects the whole transaction. New requests require a nonterminal sender; completed producers may transfer their immutable final evidence. Unavailable diagnostics may come from a terminal producer. No admission changes either business status, checkpoint, claim token or lease.
5. Validate absolute creation/deadline, schema, source artifact ownership/timepoint, and a Market recipient's symbol. W6 additionally validates Portfolio holdings scope through its trusted immutable snapshot loader before admission and again before consumption.
6. Use persisted RunBudget counters and ceilings, not caller envelope counters. Across all financial runs sharing conversation/correlation, sum authoritative hop/follow-up counters and apply the lowest participant ceiling. A new initiating message consumes one hop on its sender; a `MARKET_EVIDENCE_REQUEST` also consumes one follow-up. Thus initial M→P evidence plus P→M further-evidence request uses two logical hops and one follow-up. A causally matched reverse evidence response to that admitted request consumes no new initiating hop. `SYSTEM_UNAVAILABLE` is a non-work diagnostic with no artifact and zero new-work cost. Every other envelope must have internally valid counters and cannot advertise cross ceilings higher than the source/target ceilings.
7. A resolving READY or UNAVAILABLE must identify exactly one admitted unresolved `MARKET_EVIDENCE_REQUEST` in the same conversation/correlation, reverse its exact run endpoints, have `created_at >= request.created_at` and `deadline_at <= request.deadline_at`, and be the only resolution of that request. READY requires the producer's Market artifact. A causation ID cannot reference a diagnostic, evidence transfer, other correlation or other request type. Initial READY has no causation and charges one hop. Unavailable without causation remains a non-work diagnostic and resolves no waiting edge. `PORTFOLIO_IMPACT_REQUEST` is explicitly unsupported by this MVP admission API (the frozen enum has no positive Portfolio response type); reject it without mutation, while preserving the reserved enum for future reviewed extensions.
8. Reject cycles in the outstanding REQUEST wait graph. Only unresolved requests between nonterminal runs create waiting edges; a matching reverse response/diagnostic resolves an edge. Persisted relations and current statuses are checked inside the canonical admission lock. Ordinary evidence transfer never creates waiting edges. The supported MVP request direction is P→M; the generic graph check still rejects malformed/pre-existing outstanding paths and future unsafe reuse.
9. Persist source budget reservations, the immutable relation, and source/recipient audit events together. Allocate each event sequence under that run's CAS lock. Any validation, budget, graph, version or uniqueness failure rolls back counters, versions and events.

The response rule bounds logical requests rather than charging a third hop for the reply to the single allowed follow-up. It does not permit another request or recursive waiting. Per-run counters and correlation totals remain observable. A new follow-up Market run retains its own state/model/tool budget; cross ancestry uses relations, never General retry parent semantics.

## Compatibility, rollback and validation

No migration, new coordinator, queue, persistence authority or LangGraph is introduced. Existing `link_runs` behavior is preserved except for a previously unused reserved relation type. Existing financial cross-counter reservations become correlation-aware under the same lock; this intentional behavioral tightening is confined to the cross counters and documented before implementation. Only the new API accepts stale-version exact replay as a no-op; legacy link CAS semantics stay frozen. Disable W6 router registration to roll back application usage; existing runs/artifacts and General behavior remain readable. No production database downgrade is involved.

Independent tests must cover competing/opposing admissions, a third participant's `consume_budget` race, joining/retry membership and lowered ceilings, duplicate replay after sender/recipient completion and TTL expiry, diagnostic-key/duplicate-message collisions, changed payload rejection, lowered zero/one budgets, exactly one follow-up/reply, READY-versus-UNAVAILABLE resolution races, causation/type/creation/deadline forgery, unsupported message types, outstanding wait cycles, terminal-recipient and cancellation races, source/target independent monotonic events, complete rollback, and unchanged General/default tools. Disposable SQLite concurrency proves the local adapter; PostgreSQL lock SQL is inspected/compiled, not presented as live infrastructure recovery evidence.

The implementation is gated before W6 resumes. Frozen-contract changes beyond this additive seam require another reported decision and review.
