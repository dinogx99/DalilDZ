import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.entity_resolution.resolver import resolve_entities  # noqa: E402


def main() -> int:
    path = ROOT / "evals" / "entity_resolution" / "cases.jsonl"
    failures = []
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        total += 1
        case = json.loads(line)
        result = resolve_entities(case["submitted"], case["observed"])
        if result["relation"] != case["expected_relation"]:
            failures.append(
                f"{case['id']}: relation {result['relation']} != {case['expected_relation']}"
            )
        if "expected_legal_form_conflict" in case and (
            result["legal_form_conflict"] != case["expected_legal_form_conflict"]
        ):
            failures.append(f"{case['id']}: legal_form_conflict mismatch")

    print(f"entity-resolution evals: {total - len(failures)}/{total} passed")
    for failure in failures:
        print(f"FAIL: {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
