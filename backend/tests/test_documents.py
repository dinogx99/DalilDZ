import io

from PIL import Image
import pytest

from app.extraction.ocr import DisabledOCRProvider
from app.services.documents import (
    classify_document,
    extract_claims,
    process_document,
    sniff_mime,
)


def make_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_mime_is_detected_from_bytes_not_extension():
    assert sniff_mime(make_png()) == "image/png"
    with pytest.raises(ValueError, match="UNSUPPORTED_FILE_TYPE"):
        sniff_mime(b"not really a pdf.pdf")


def test_document_classification_uses_deterministic_markers():
    assert classify_document("FACTURE\nTotal TTC 1000 DZD") == "invoice"
    assert classify_document("DEVIS N° 22\nOffre de prix") == "devis"
    assert classify_document("Registre de commerce RC: 16B0123456") == "registre_de_commerce"


def test_claim_extraction_keeps_locations_and_normalizes_identifiers():
    text = (
        "Raison sociale: SARL ALPHA DISTRIBUTION\n"
        "RC: 16 B 0123456\n"
        "NIF: 123456789012345\n"
        "Email: office@alpha.dz\n"
        "https://alpha.dz\n"
    )
    claims = extract_claims(text, page=2, method="pdf_text")
    by_field = {}
    for claim in claims:
        by_field.setdefault(claim.field, []).append(claim)
    assert by_field["rc"][0].value == "16B0123456"
    assert by_field["rc"][0].page == 2
    assert by_field["rc"][0].location["start"] < by_field["rc"][0].location["end"]
    assert by_field["legal_form"][0].value == "SARL"
    assert by_field["legal_name"][0].value.startswith("SARL ALPHA")


def test_image_without_configured_ocr_is_retained_as_ocr_required():
    result = process_document(make_png(), DisabledOCRProvider())
    assert result.mime == "image/png"
    assert result.ocr_required is True
    assert result.extraction_method == "direct_text"
    assert result.claims == []
