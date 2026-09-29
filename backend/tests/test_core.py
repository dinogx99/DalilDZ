from app.core.domain import Status, fingerprint


def test_status_model_contains_required_semantics():
    required = {
        "VERIFIED",
        "CONSISTENT",
        "CONFLICTING",
        "NOT_FOUND",
        "NOT_VERIFIABLE",
        "SOURCE_UNAVAILABLE",
        "OUTDATED",
        "MANUAL_REVIEW_REQUIRED",
    }
    assert required == {item.value for item in Status}


def test_fingerprint_is_key_order_independent():
    assert fingerprint({"b": 2, "a": 1}) == fingerprint({"a": 1, "b": 2})
