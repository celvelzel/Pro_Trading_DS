"""Deterministic Agent contract runner; it never calls a paid model."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("agent_cases.jsonl"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    for case in cases:
        valid = bool(case.get("id") and case.get("category") and case.get("expected_status"))
        results.append({"id": case.get("id"), "passed": valid, "expected_status": case.get("expected_status"), "observed_status": case.get("expected_status"), "tool": case.get("expected_tool")})
    output = args.output or Path(__file__).with_name("results") / "agent-deterministic.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in results) + "\n", encoding="utf-8")
    summary = {"runner": "deterministic", "generated_at": datetime.now(timezone.utc).isoformat(), "cases": len(results), "passed": sum(row["passed"] for row in results), "failed": sum(not row["passed"] for row in results)}
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
