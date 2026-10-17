"""Small deterministic retrieval evaluation with real local embeddings; no AMD calls."""

import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from app.rag.retrieval import ApprovedRetriever
from app.storage.database import initialize


def main():
    cases = json.loads(
        (Path(__file__).resolve().parents[2] / "tests/data/rag_cases.json").read_text()
    )
    with TemporaryDirectory(prefix="shift-eval-") as directory:
        path = directory + "/evaluation.sqlite3"
        initialize(path)
        passed = 0
        for case in cases:
            start = time.perf_counter()
            nodes = ApprovedRetriever(path, case["machine"]).retrieve(case["question"])
            actual = sorted({n.node.metadata["record_id"] for n in nodes})
            ok = actual == sorted(case["expected"])
            passed += int(ok)
            print(
                json.dumps(
                    {
                        "machine": case["machine"],
                        "question": case["question"],
                        "expected": case["expected"],
                        "retrieved": actual,
                        "passed": ok,
                        "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                    }
                )
            )
        print(
            json.dumps(
                {
                    "cases_passed": passed,
                    "cases_total": len(cases),
                    "embedding": "real local MiniLM",
                    "inference_calls": 0,
                }
            )
        )
        if passed != len(cases):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
