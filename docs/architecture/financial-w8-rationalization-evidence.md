# W8 evaluation rationalization evidence (2026-10-10)

Contract: [revised acceptance](financial-mas-w8-evaluation.md#revised-acceptance-contract-2026-10-10). `MarketInvestigationArtifact` v1 remains frozen. The only production changes are UI report category labels and evaluation reason text. Generator and typed API already keep specialist prose in audit records and emit bounded association hypotheses; regression tests now verify that boundary. No numerical threshold, risk gate, cross-MAS protocol, agent or holdings access changed.

## Incremental verification

From repository root, with `$env:PYTHONPATH='backend;.;lobster_quant'`:

```powershell
python -m pytest backend/tests/test_market_mas.py backend/tests/test_financial_api.py backend/tests/test_financial_w8_eval.py backend/tests/test_financial_eval_fixtures.py -q
```

Result: **177 passed in 139.67s**. Raw log: `logs/financial-mas/w8-rationalization-backend.log`. New cases include causal assertions and negated statements in English and Chinese across autonomous/fixed/single execution, rejected positive assertions replacing bounded hypothesis explanations, and a real typed API response that omits an injected model causal summary while preserving it in invocation audit output. A scorer assertion preserves `scorable=false`, `count=null`, `denominator=0` and the explicit not-applicable reason.

From `lobster-quant-web`:

```powershell
npm run test:unit -- src/components/financial/results.test.tsx
npx tsc --noEmit
npx eslint src/components/financial/MarketResult.tsx src/components/financial/results.test.tsx
npm run build
```

Result: **28 passed**, TypeScript **exit 0**, changed-area ESLint **exit 0**, production build successful. Logs: `logs/financial-mas/w8-rationalization-{ui,types,lint,check-exits,build}.log`. UI tests verify the five report categories, historical supported-hypothesis wording, evidence/counter-evidence and existing noncausal disclaimer. An initial assertion incorrectly matched the negated source-authenticity disclaimer; it was corrected to check whether the hypothesis was labeled as confirmed causality, and the suite passed. This is not a new browser E2E run.

The existing runner's `run_domain` was called only for M01 (sector event), M02 (after-cutoff event) and M03 (unverified rumor), across the three Market modes. **9/9 persisted runtime rows completed and scored**. Numeric fact accuracy remains **1**, timing violations **0**; `unsupported_causal_claims.count` remains **null**. New raw rows and summary are at `logs/financial-mas/w8-rationalization-incremental/`, with console log `logs/financial-mas/w8-rationalization-incremental.log`. These are supplemental synthetic SQLite runs, not a replacement canonical benchmark or a real-model causal reasoning evaluation.

Preservation check: **31 files** under canonical v1/v2 results, fixtures, gold JSONL inputs and `backend/agent/shared/contracts.py` match HEAD content (normalizing checkout CRLF); SHA-256 values and comparison flags are retained in `logs/financial-mas/w8-rationalization-preservation.json`. The fixture loader also validated its manifest. `git diff --check` passed. Existing user README edits were not modified.

## Prior evidence and review

Prior complete Backend (795), security/recovery (515), frontend (212), TypeScript/lint/build and local real API Chromium E2E (7/7), plus canonical v2 (187 rows / 188 runs), remain the broader evidence described in the execution ledger. They are historical successful runs, not rerun counts from this patch. This change uses scoped regressions plus a new production build as authorized by the revised acceptance contract.

Independent read-only Reviewer `w8_reviewer` examined the revised contract, code/test patch, historical evidence and completed raw logs and returned **PASS, no blocking findings**. W8 Gate is now **PASS** under the revised applicable acceptance contract. Validation is synthetic/local only; no live provider, causal identification, PostgreSQL, Redis/Celery broker, real trade or portfolio mutation evidence is claimed.
