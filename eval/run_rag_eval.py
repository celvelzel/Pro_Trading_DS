"""RAG fixture integrity runner with explicit answerable denominator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("rag_cases.jsonl"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    valid = [case for case in cases if case.get("answerable") and case.get("expected_chunk")]
    refusal = [case for case in cases if not case.get("answerable")]
    results = [{"id": case["id"], "passed": bool(case.get("query") and (case.get("expected_chunk") or not case.get("answerable"))), "answerable": bool(case.get("answerable")), "expected_chunk": case.get("expected_chunk")} for case in cases]
    output = args.output or Path(__file__).with_name("results") / "rag-fixture-integrity.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in results) + "\n", encoding="utf-8")
    summary = {"cases": len(cases), "answerable_cases": len(valid), "refusal_cases": len(refusal), "fixture_integrity": sum(row["passed"] for row in results) / len(results) if results else 0, "recall_at_k": "requires live retriever run", "citation_support_rate": "requires live answer run"}
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if all(row["passed"] for row in results) else 1


if __name__ == "__main__":
    sys.exit(main())
