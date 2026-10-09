# ADR-0005: durable cross-work origin and guarded execution

Status: PROPOSED; implementation blocked pending independent DESIGN PASS.
Date: 2026-10-09. Supersedes no accepted ADR. Additive to ADR-0002/0003/0004.

## Reported blocking evidence

Independent W6 review at 866f7df reproduced two P1 failures using actual drivers
and deterministic tools. A failed follow-up admission leaves a queued Market
run. `advance(restore(orphan))` treats it as independent and executes five models
and three tools without any admitted relation or hop/follow-up charge. A REQUEST
can expire after router preflight but before dispatcher claim; its target still
executes. Ordinary queue entry also executes these targets. Router-only filtering,
post-failure compensating cancellation and worker-only preflight cannot close
creation/admission crash windows or preflight/claim races.

The frozen snapshot has no durable origin discriminator. Explicit correlation
does not mean follow-up: router Market-only and Portfolio-only legitimately have
explicit correlations without relations. Initial Portfolio must remain available
even if an optional follow-up leaves an orphan. No inference from run goal,
symbols, keys, membership counts or current source status is acceptable.

W6 Gate remains NEEDS_WORK. W7 dependent work stays blocked. Reviewer evidence
is retained in the W6 worktree logs/financial-mas/w6-independent-*.

## Proposed additive contract

Introduce exported typed `FinancialExecutionAuthorization` in shared contracts:

- `purpose`: literal `independent` or `cross_followup`.
- `source_run_id` and `request_message_id`: required nonblank strings only for
  cross_followup; forbidden for independent.

Add optional `execution_authorization=None` to dispatcher.create. Persist a
validated non-None value in existing immutable creation_inputs JSON; include it
in ordinary and concurrent full creation identity. None omits the key, preserving
legacy create identity. Snapshot exposes the validated authorization or None.
No table, migration, artifact/envelope schema, default General registry, budget
ceiling or execution_profile change. Invalid inputs fail without writes/calls.

The trusted application, not request text or a role model, supplies this field.
Router initial requests (including both standalone modes and Combined members)
explicitly use independent. Before creating any further-evidence target, router
uses cross_followup with the deterministic REQUEST message ID and Portfolio
source ID. This is intent, not permission: only the accepted immutable
cross_admitted REQUEST authorizes its target to execute. Creation without
admission remains durable but inert. An orphan must stay inert through restore,
advance, worker delivery and crash recovery.

## Atomic execution authority and TTL

For a guarded run, dispatcher.start uses canonical conversation-before-run CAS
locking from ADR-0003. Under the claim transaction and before claim, status/event,
budget reservation or provider/tool call, it verifies a persisted cross_admitted
MARKET_EVIDENCE_REQUEST that matches the exact message ID and source and original
target, conversation, correlation, kinds, execution profiles, request as_of and
creation authorization. It checks the absolute deadline at the claim decision,
not a previously captured router timestamp. Terminal/no-op replay invokes no new
work. A missing/mismatched admission rejects explicitly and rolls back all DML.

A positively admitted but expired new delivery performs one fenced transition
to existing `expired` status and an existing namespaced MAS expiry event, without
model/tool/round/hop/follow-up reservation. Duplicate expired delivery is a no-op.
This intentional expiry write is distinct from missing-admission zero-DML denial.
Expose a stable denial exception/code for callers; do not silently return success.

RuntimeContext guards must also honor the admitted absolute deadline during
execution, including external wait bounds, before each new model/tool reservation,
checkpoint and final artifact write. Expired in-flight work cannot persist a late
result or start another call. Record a fenced terminal expiry when still owned;
pause/cancel/stale ownership takes precedence. Running synchronous I/O threads
cannot be forcibly killed; their read-only execution may finish, but they cannot
authorize or persist late runtime output. Existing active deadline remains an
independent stricter bound where applicable, and cannot be reset by replay.

Historical admission replay does not authorize fresh expired execution. A
previously selected Portfolio artifact retains the reviewed W6 historical-context
semantics; that is not a new follow-up delivery. An initial independent Market
run does not acquire a follow-up deadline merely by sharing a correlation.

## Retry and independence

Retry preserves the parent's execution authorization in creation identity; it
must not silently become independent. A retry child may reuse only the exact
original admitted logical request through validated immutable retry ancestry:
same conversation, profile, correlation, domain, request and authorization, with
the relation target equal to the original authorized ancestor. Detect cycles and
bound traversal; reject before child creation if authorization cannot be proven.
The original absolute deadline never extends. This does not create a new cross
message, extra hop or follow-up. Ordinary legacy retries retain their old semantics.

After admission, the source's later completion/cancellation does not rewrite the
target's independent lifecycle or immutable authorization. Target cancellation
and pause use its own CAS/fencing. Initial independent Portfolio and Market runs
must keep working if a peer, optional follow-up or its admission is unavailable.

## Queue/router compatibility and fail-closed legacy ambiguity

Legacy direct runtime calls with None retain the accepted W1 identity and behavior.
New router scheduling always requires its explicit origin metadata; restore must
not classify a relation-free run as standalone. A legacy ambiguous router run
without origin cannot be silently upgraded or inferred; reject it, preserving
historical rows. Existing standalone queue runs with None authorization and no
explicit requested correlation remain supported by the trusted profile mapping.
An explicit-correlation legacy run without origin is rejected by queue delivery;
no production W6 entrypoint has been deployed. Configured worker profiles remain
unsupported unless an independently reviewed trusted mapping exists.

All normal worker entrypoints use the same guarded shared start authority. There
is no second queue-only execution implementation. Router delivery, restore and
advance respect durable intent; worker/root assembly cannot bypass it by starting
a supposedly standalone target. Unknown origin is explicit, not a demo fallback.

## Review, validation, rollback

Independent design review precedes isolated shared runtime implementation. Then
independent implementation review, bounded W6 router repair, worker assembly
repair and full integration validation precede W6 Gate. Ownership: runtime worker
shared contracts/dispatch plus dedicated authorization tests; W6 owner integration
and dedicated cross tests; Lead worker/factory wiring and docs. Parallel writers
use different worktrees and do not modify shared files concurrently.

Required proofs: exact/concurrent creation identity, None compatibility; inert
create/admit orphan through restore/advance/two worker entries; expiry between
preflight and claim; expiry during a role/tool and before checkpoint/final write;
no calls/reservations/late artifact; monotonic expiry/no-op replay; pending-review,
pause/cancel/lease recovery; immutable retry origin and original TTL; all three
actual-driver modes and unavailability; existing profile/admission/General tests.
Use disposable SQLite and separately compiled PostgreSQL SQL; do not claim live
infrastructure. Preserve all failure logs and holdings hashes. No real trades.

Rollback disables cross entrypoints and deliveries first. Retain persisted origin
JSON and immutable history. Do not roll back to a worker that ignores guarded
metadata. General and independent legacy direct runtime remain available.
