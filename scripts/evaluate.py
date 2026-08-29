from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.database import SessionLocal, create_tables  # noqa: E402
from app.db.seed import seed_schemes  # noqa: E402
from app.schemas.models import ChatRequest  # noqa: E402
from app.services.container import ServiceContainer  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate JanScope against the local golden dataset")
    parser.add_argument("--output", type=Path, help="Optional JSON result path")
    args = parser.parse_args()

    settings = get_settings()
    cases = json.loads((ROOT / "evaluation" / "golden_dataset.json").read_text(encoding="utf-8"))
    create_tables()
    services = ServiceContainer(settings)
    details = []
    latencies = []
    with SessionLocal() as db:
        seed_schemes(db, settings)
        services.retrieval.initialize_from_database(db, force_rebuild=True)
        for case in cases:
            started = time.perf_counter()
            response = services.workflow.run(db, ChatRequest(message=case["message"], language="auto"))
            latency_ms = (time.perf_counter() - started) * 1000
            latencies.append(latency_ms)
            slugs = [item.slug for item in response.recommended_schemes]
            intent_ok = response.intent == case["expected_intent"]
            scheme_ok = not case.get("expected_scheme") or case["expected_scheme"] in slugs
            citation_ok = bool(response.sources) == bool(case.get("expect_sources", True))
            clarification_ok = not case.get("expect_clarification") or response.needs_clarification
            details.append(
                {
                    "id": case["id"],
                    "intent_ok": intent_ok,
                    "scheme_ok": scheme_ok,
                    "citation_ok": citation_ok,
                    "clarification_ok": clarification_ok,
                    "actual_intent": response.intent,
                    "actual_schemes": slugs,
                    "latency_ms": round(latency_ms, 2),
                }
            )

    def rate(key: str, subset=None) -> float:
        items = [item for item in details if subset is None or subset(item)]
        return round(100 * sum(bool(item[key]) for item in items) / max(len(items), 1), 1)

    report = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "mode": services.llm.mode,
        "vector_backend": services.retrieval.backend_name,
        "test_question_count": len(cases),
        "intent_accuracy_percent": rate("intent_ok"),
        "expected_scheme_retrieval_rate_percent": rate(
            "scheme_ok",
            lambda item: next(case for case in cases if case["id"] == item["id"]).get("expected_scheme"),
        ),
        "citation_behavior_accuracy_percent": rate("citation_ok"),
        "required_clarification_rate_percent": rate(
            "clarification_ok",
            lambda item: next(case for case in cases if case["id"] == item["id"]).get("expect_clarification"),
        ),
        "average_response_time_ms": round(sum(latencies) / max(len(latencies), 1), 2),
        "details": details,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
