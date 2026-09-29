from app.core.domain import Status, compare_claim, similarity
from app.normalization.algeria import (
    normalize_arabic,
    normalize_company_name,
    normalize_domain,
    normalize_identifier,
    normalize_legal_form,
    normalize_phone,
    normalize_wilaya,
    transliterate_arabic,
)


def test_arabic_normalization_removes_diacritics_tatweel_and_hamza_variants():
    assert normalize_arabic("بِئْرُ الـجِير") == "بير الجير"


def test_identifier_normalization_handles_spaces_punctuation_and_arabic_digits():
    assert normalize_identifier("16 B-0123456") == "16B0123456"
    assert normalize_identifier("١٦ B ٠١٢٣٤٥٦") == "16B0123456"


def test_legal_forms_cover_common_algerian_variants():
    assert normalize_legal_form("S.A.R.L. ALPHA") == "SARL"
    assert normalize_legal_form("Entreprise unipersonnelle à responsabilité limitée") == "EURL"
    assert normalize_legal_form("Société par actions") == "SPA"


def test_wilaya_supports_code_latin_and_arabic():
    assert normalize_wilaya("31") == "Oran"
    assert normalize_wilaya("Oran") == "Oran"
    assert normalize_wilaya("وهران") == "Oran"


def test_phone_and_domain_normalization():
    assert normalize_phone("0550 12 34 56") == "+213550123456"
    assert normalize_domain("https://WWW.Example.DZ/contact") == "example.dz"


def test_company_name_removes_legal_form():
    assert normalize_company_name("S.A.R.L. Alpha Distribution") == "alpha distribution"


def test_arabic_transliteration_is_available_for_cross_script_matching():
    assert transliterate_arabic("وهران") == "ouhran"


def test_exact_identifier_check_is_deterministic():
    status, meta = compare_claim("rc", "16B0123456", "16 B 0123456")
    assert status == Status.VERIFIED
    assert meta["method"] == "exact_normalized_identifier"


def test_identifier_conflict_is_explicit():
    status, _ = compare_claim("rc", "16B0123456", "16B9999999")
    assert status == Status.CONFLICTING


def test_legal_form_conflict_is_separate_from_name_similarity():
    status, meta = compare_claim("legal_form", "SARL", "EURL")
    assert status == Status.CONFLICTING
    assert "Legal-form conflict" in meta["explanation"]


def test_name_similarity_handles_order_and_legal_form_noise():
    assert similarity("SARL ALPHA DISTRIBUTION", "Alpha Distribution S.A.R.L") >= 0.95
