# ADR-0004: Persist financial execution profile across worker delivery

- Status: Proposed; bootstrap integration blocked pending design and implementation review.
- Date: 2026-10-08
- Scope: application assembly and additive financial runtime provenance identity.

## Reproduced gap

Independent offline reproduction created the same MU/as_of request using explicit custom role providers and a history adapter with MU prices 100 to 200. Direct execution returned 100 percent; a second queued run delivered in a fresh worker instead used the default synthetic dataset and returned approximately -8.091908 percent, with synthetic role summaries and fixture://financial-demo/v1 event references. Existing creation_inputs records no provider/data assembly identity. Worker domain isolation is repaired (nine scoped tests pass), but source substitution prevents accepting bootstrap.

## Decision

Add optional keyword-only `execution_profile: str | None = None` to FinancialMASDispatcher construction. This is an immutable deployment configuration identifier, not a credential, user preference, business state or arbitrary prompt. Validate a string of 1–128 characters with no leading/trailing whitespace; reject rather than normalize aliases. A non-None value is stored in existing FinancialRun.creation_inputs JSON and participates in full create idempotency comparison. Legacy None omits the key and preserves previous creation-input equality. snapshot exposes the stored profile as an additive field. No table, migration, artifact or request schema changes are required.

Before start acquires any claim, changes versions/events or calls models/tools, require the dispatcher's profile to equal the stored run profile. A mismatch raises an explicit execution-profile error outside the existing swallowed stale-worker FinancialConflict handler, leaving status, checkpoint, counters and artifacts unchanged. Matching legacy None assemblies remain usable directly; a None assembler cannot execute a profiled run and a profiled assembler cannot execute an unprofiled run. Lifecycle reads and versioned pause/cancel/approve are not execution and remain usable without an assembler profile.

Retry preserves the parent's immutable profile. It requires a matching assembly before creating a child; the child cannot be silently relabeled by a different deployment. Existing retry authority, correlation, budgets and parent semantics remain unchanged.

The application factory's default pure synthetic providers and data are identified as `synthetic-demo-v1`. This identifier is reserved: neither demo=False nor a custom-data/provider assembly may claim it. The demo factory only uses this fixed identity and rejects custom provider/history/evidence/portfolio-data overrides. Configured non-demo assemblies require an explicit different execution_profile plus complete trusted adapters/providers; no automatic provider/environment fallback exists. The same profile must refer to the same versioned data/model configuration across restarts. Configuration identifiers contain no secrets; a trusted operator-owned reconstruction mapping binds each deployed identifier to its versioned configuration, and version changes require a new identifier. The initial worker mapping binds only the built-in demo factory; arbitrary labels are not executable deployment registrations. An optional scoped cross-artifact resolver is communication wiring, not permission to change source datasets, and must still validate immutable references.

Fresh workers inspect persisted kind and profile. They rebuild only the requested deployed domain and only an explicitly supported profile. Initially the built-in mapping supports `synthetic-demo-v1`. Unknown configured profiles and legacy missing profiles produce an explicit unsupported-execution-profile error without defaulting to demo, producing an artifact, consuming budget or changing persistence. Existing unprofiled financial runs remain readable/cancellable and can continue through a matching explicitly injected legacy dispatcher; worker execution requires an operator-supplied registered profile reconstruction in a separately reviewed extension. General worker dispatch is unchanged.

Combined router assembly must use the same configured identity on both runs and any new follow-up Market run; it never infers assembly configuration from symbol/snapshot ID, goal or idempotency key. W6 worker is informed of this additional prerequisite before resuming implementation.

## Validation and rollback

Independent tests cover default demo fresh worker completion and duplicate delivery; disabled-peer imports for both worker entrypoints; configured-vs-demo data substitution rejection across fresh processes; matching configured direct execution; missing/unknown profiles; profile-aware ordinary/concurrent idempotency; mismatched start and retry with complete no-write/no-call proofs; matching profile retry inheritance; legacy None identity and direct execution compatibility; unchanged General tools/lifecycle. Existing full Backend regression remains required after integration. This profile identifies an assembly; it does not claim real-provider, trading or live distributed recovery validation.

Rollback disables the new application factory/worker financial reconstruction mapping. Persisted profile JSON remains readable; do not remove or rewrite it to force execution. Domain/state/artifacts and General remain intact. Further profile registries or configured-provider deployment support require explicit implementation and verification; no claim of such support is made here.
