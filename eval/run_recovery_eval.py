"""Deterministic state/recovery contract runner; no services or model calls."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("recovery_cases.jsonl"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    from agent.state_machine import InvalidStateTransition, transition

    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    for case in cases:
        try:
            observed = transition(case["current"], case["event"])
        except InvalidStateTransition:
            observed = "invalid"
        passed = observed == case["expected"]
        results.append({"id": case["id"], "passed": passed, "expected": case["expected"], "observed": observed})
    output = args.output or Path(__file__).with_name("results") / "recovery-deterministic.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in results) + "\n", encoding="utf-8")
    summary = {
        "runner": "deterministic-recovery",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases": len(results),
        "passed": sum(row["passed"] for row in results),
        "failed": sum(not row["passed"] for row in results),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
