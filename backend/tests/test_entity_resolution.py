from app.entity_resolution.resolver import resolve_entities


def test_exact_rc_can_resolve_entity_while_preserving_legal_form_conflict():
    result = resolve_entities(
        {"legal_name": "ALPHA DISTRIBUTION", "rc": "16B0123456", "legal_form": "SARL"},
        {"legal_name": "Alpha Distribution", "rc": "16 B 0123456", "legal_form": "EURL"},
    )
    assert result["relation"] == "LIKELY_SAME_ENTITY"
    assert result["exact_identifier_match"] is True
    assert result["legal_form_conflict"] is True


def test_conflicting_identifier_prevents_automatic_merge():
    result = resolve_entities(
        {"legal_name": "DELTA SERVICES", "rc": "31B1111111"},
        {"legal_name": "DELTA SERVICES", "rc": "31B9999999"},
    )
    assert result["relation"] == "CONFLICTING_IDENTIFIERS"
