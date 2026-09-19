# Evaluation

The evaluation fixtures are intentionally deterministic and do not call a model provider or a market-data service.

## Commands

Run from the repository root:

```powershell
$env:PYTHONPATH="backend"
python eval/run_agent_eval.py
python eval/run_rag_eval.py
python eval/run_recovery_eval.py
```

Results are written as JSONL under `eval/results/` so each run can be reviewed or archived with the corresponding code revision.

## Current scope

- `agent_cases.jsonl`: 30 planner/state-machine contract cases.
- `rag_cases.jsonl`: 20 retrieval fixture and refusal cases.
- Agent evaluation reports deterministic pass/fail counts.
- RAG evaluation reports fixture integrity, answerable/refusal counts, and explicitly marks live recall/citation metrics as unavailable until a live retriever/answer run is configured.
- Recovery evaluation reports deterministic pause/cancel/replan/expiry and terminal-state cases.

These fixtures validate contracts and regression behavior; they are not a claim of investment performance or production retrieval quality.
