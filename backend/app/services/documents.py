from dataclasses import dataclass
from hashlib import sha256
import io
import re

from PIL import Image
from pypdf import PdfReader
import pypdfium2 as pdfium

from app.extraction.ocr import OCRProvider
from app.normalization.algeria import normalize_identifier, normalize_legal_form


PATTERNS: dict[str, re.Pattern[str]] = {
    "rc": re.compile(r"(?i)\bRC\s*[:#\-]?\s*([0-9]{2}\s*[A-Z]\s*[0-9]{5,12})"),
    "nif": re.compile(r"(?i)\bNIF\s*[:#\-]?\s*([0-9\s]{10,24})"),
    "nis": re.compile(r"(?i)\bNIS\s*[:#\-]?\s*([0-9\s]{8,24})"),
    "ai": re.compile(r"(?i)\b(?:AI|ARTICLE\s+D['’]?IMPOSITION)\s*[:#\-]?\s*([A-Z0-9\s]{5,24})"),
    "email": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    "website": re.compile(r"(?i)https?://[^\s)>,]+"),
    "phone": re.compile(r"(?<!\d)(?:\+?213|0)[\s.\-]?[5-7][\d\s.\-]{7,12}"),
    "invoice_number": re.compile(
        r"(?i)\b(?:facture|invoice)\s*(?:n[o°.]*)?\s*[:#\-]?\s*([A-Z0-9/_\-]{2,40})"
    ),
}

LEGAL_FORM_RE = re.compile(
    r"(?i)\b(S\.?A\.?R\.?L|E\.?U\.?R\.?L|S\.?P\.?A|S\.?N\.?C|S\.?C\.?S)\b"
)
NAME_LABEL_RE = re.compile(
    r"(?im)^(?:raison\s+sociale|company|entreprise|soci[eé]t[eé])\s*[:\-]\s*(.{2,160})$"
)


@dataclass
class ExtractedValue:
    field: str
    value: str
    page: int | None
    location: dict
    method: str
    confidence: float | None = None


@dataclass
class ProcessedDocument:
    mime: str
    digest: str
    text: str
    document_type: str
    extraction_method: str
    ocr_required: bool
    claims: list[ExtractedValue]
    pages: int


def sniff_mime(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError("UNSUPPORTED_FILE_TYPE")


def classify_document(text: str) -> str:
    folded = text.casefold()
    candidates = (
        ("registre_de_commerce", ("registre de commerce", "rc n°", "rc:")),
        ("invoice", ("facture", "invoice", "total ttc", "montant ttc")),
        ("devis", ("devis", "quotation", "offre de prix")),
        ("purchase_order", ("bon de commande", "purchase order")),
        ("bank_rib", ("releve d'identite bancaire", "rib", "iban")),
        ("receipt", ("reçu", "receipt", "quittance")),
        ("certificate", ("certificat", "attestation", "certificate")),
    )
    for document_type, markers in candidates:
        if any(marker in folded for marker in markers):
            return document_type
    return "unidentified_commercial_document"


def extract_claims(text: str, page: int | None, method: str) -> list[ExtractedValue]:
    claims: list[ExtractedValue] = []
    for field, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group(1 if match.lastindex else 0).strip(" .,:;")
            if field in {"rc", "nif", "nis", "ai"}:
                value = normalize_identifier(value) or value
            claims.append(
                ExtractedValue(
                    field=field,
                    value=value,
                    page=page,
                    location={"start": match.start(), "end": match.end()},
                    method=method,
                )
            )

    for match in LEGAL_FORM_RE.finditer(text):
        value = normalize_legal_form(match.group(0))
        if value:
            claims.append(
                ExtractedValue(
                    field="legal_form",
                    value=value,
                    page=page,
                    location={"start": match.start(), "end": match.end()},
                    method=method,
                )
            )

    labelled_name = NAME_LABEL_RE.search(text)
    if labelled_name:
        claims.append(
            ExtractedValue(
                field="legal_name",
                value=labelled_name.group(1).strip(),
                page=page,
                location={"start": labelled_name.start(1), "end": labelled_name.end(1)},
                method=method,
            )
        )
    return claims


def _rasterize_pdf(data: bytes, max_pages: int = 20) -> list[bytes]:
    pdf = pdfium.PdfDocument(data)
    rendered: list[bytes] = []
    for index in range(min(len(pdf), max_pages)):
        page = pdf[index]
        bitmap = page.render(scale=2.0)
        image = bitmap.to_pil().convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        rendered.append(buffer.getvalue())
    return rendered


def process_document(data: bytes, ocr_provider: OCRProvider) -> ProcessedDocument:
    mime = sniff_mime(data)
    digest = sha256(data).hexdigest()
    all_claims: list[ExtractedValue] = []
    page_texts: list[str] = []
    extraction_method = "direct_text"
    ocr_required = False

    if mime == "application/pdf":
        reader = PdfReader(io.BytesIO(data), strict=False)
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            page_texts.append(text)
            all_claims.extend(extract_claims(text, page_number, "pdf_text"))

        direct_text = "\n".join(page_texts).strip()
        if len(direct_text) < 20:
            ocr_required = True
            if ocr_provider.provider_id != "disabled":
                extraction_method = f"ocr:{ocr_provider.provider_id}"
                page_texts = []
                all_claims = []
                for page_number, image_bytes in enumerate(_rasterize_pdf(data), start=1):
                    result = ocr_provider.extract_image(image_bytes)
                    page_texts.append(result.text)
                    all_claims.extend(
                        extract_claims(
                            result.text,
                            page_number,
                            f"ocr:{ocr_provider.provider_id}",
                        )
                    )
    else:
        Image.open(io.BytesIO(data)).verify()
        ocr_required = True
        if ocr_provider.provider_id != "disabled":
            extraction_method = f"ocr:{ocr_provider.provider_id}"
            result = ocr_provider.extract_image(data)
            page_texts = [result.text]
            all_claims = extract_claims(
                result.text,
                page=1,
                method=f"ocr:{ocr_provider.provider_id}",
            )

    text = "\n".join(page_texts).strip()
    return ProcessedDocument(
        mime=mime,
        digest=digest,
        text=text,
        document_type=classify_document(text),
        extraction_method=extraction_method,
        ocr_required=ocr_required,
        claims=all_claims,
        pages=max(1, len(page_texts)),
    )
