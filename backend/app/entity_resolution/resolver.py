from typing import Any

from app.core.domain import Status, compare_claim, similarity
from app.normalization.algeria import normalize_identifier, normalize_legal_form


IDENTIFIER_FIELDS = ("rc", "nif", "nis")


def resolve_entities(submitted: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    exact_identifier_match = False
    identifier_conflict = False

    for field in IDENTIFIER_FIELDS:
        left = submitted.get(field)
        right = observed.get(field)
        if left and right:
            equal = normalize_identifier(str(left)) == normalize_identifier(str(right))
            exact_identifier_match = exact_identifier_match or equal
            identifier_conflict = identifier_conflict or not equal
            status, meta = compare_claim(field, str(left), str(right))
            checks.append({"field": field, "status": status.value, **meta})

    name_score = None
    if submitted.get("legal_name") and observed.get("legal_name"):
        name_score = similarity(
            str(submitted["legal_name"]),
            str(observed["legal_name"]),
        )
        status, meta = compare_claim(
            "legal_name",
            str(submitted["legal_name"]),
            str(observed["legal_name"]),
        )
        checks.append({"field": "legal_name", "status": status.value, **meta})

    legal_form_conflict = False
    if submitted.get("legal_form") and observed.get("legal_form"):
        left_form = normalize_legal_form(str(submitted["legal_form"]))
        right_form = normalize_legal_form(str(observed["legal_form"]))
        legal_form_conflict = bool(left_form and right_form and left_form != right_form)
        status, meta = compare_claim(
            "legal_form",
            str(submitted["legal_form"]),
            str(observed["legal_form"]),
        )
        checks.append({"field": "legal_form", "status": status.value, **meta})

    if identifier_conflict:
        relation = "CONFLICTING_IDENTIFIERS"
    elif exact_identifier_match:
        relation = "LIKELY_SAME_ENTITY"
    elif name_score is not None and name_score >= 0.92:
        relation = "LIKELY_SAME_ENTITY"
    elif name_score is not None and name_score >= 0.78:
        relation = "POSSIBLE_MATCH"
    else:
        relation = "INSUFFICIENT_EVIDENCE"

    return {
        "relation": relation,
        "exact_identifier_match": exact_identifier_match,
        "legal_form_conflict": legal_form_conflict,
        "name_similarity": name_score,
        "checks": checks,
        "note": (
            "Entity resolution is an identity-matching aid, not a trust, legitimacy, "
            "fraud or safety assessment."
        ),
    }
