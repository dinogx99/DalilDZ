from enum import StrEnum
from hashlib import sha256
import json
import uuid
from urllib.parse import urlparse

from rapidfuzz.fuzz import token_set_ratio

from app.normalization.algeria import (
    normalize_address,
    normalize_company_name,
    normalize_domain,
    normalize_identifier,
    normalize_legal_form,
    normalize_phone,
    normalize_wilaya,
)


class Status(StrEnum):
    VERIFIED = "VERIFIED"
    CONSISTENT = "CONSISTENT"
    CONFLICTING = "CONFLICTING"
    NOT_FOUND = "NOT_FOUND"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    OUTDATED = "OUTDATED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class SourceHealth(StrEnum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    MANUAL_ONLY = "MANUAL_ONLY"


def uid() -> str:
    return str(uuid.uuid4())


def fingerprint(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


def similarity(left: str | None, right: str | None) -> float:
    a = normalize_company_name(left) or ""
    b = normalize_company_name(right) or ""
    return round(token_set_ratio(a, b) / 100, 3)


def compare_claim(field: str, submitted: str | None, observed: str | None) -> tuple[Status, dict]:
    if observed is None:
        return Status.NOT_VERIFIABLE, {
            "method": "no_comparable_evidence",
            "explanation": "No comparable evidence value was available.",
        }
    if submitted is None:
        return Status.CONSISTENT, {
            "method": "observed_only",
            "explanation": "Evidence was observed but no submitted value existed for comparison.",
        }

    if field in {"rc", "nif", "nis", "ai"}:
        left = normalize_identifier(submitted)
        right = normalize_identifier(observed)
        status = Status.VERIFIED if left == right else Status.CONFLICTING
        return status, {
            "method": "exact_normalized_identifier",
            "submitted_normalized": left,
            "observed_normalized": right,
            "explanation": "Identifiers match exactly after normalization."
            if status == Status.VERIFIED
            else "Identifiers differ after normalization.",
        }

    if field == "legal_form":
        left = normalize_legal_form(submitted)
        right = normalize_legal_form(observed)
        if not left or not right:
            return Status.MANUAL_REVIEW_REQUIRED, {
                "method": "legal_form_normalization",
                "submitted_normalized": left,
                "observed_normalized": right,
                "explanation": "At least one legal form could not be normalized deterministically.",
            }
        status = Status.VERIFIED if left == right else Status.CONFLICTING
        return status, {
            "method": "legal_form_normalization",
            "submitted_normalized": left,
            "observed_normalized": right,
            "explanation": "Legal forms match."
            if status == Status.VERIFIED
            else f"Legal-form conflict: {left} versus {right}.",
        }

    if field == "wilaya":
        left = normalize_wilaya(submitted)
        right = normalize_wilaya(observed)
        status = Status.VERIFIED if left == right else Status.CONFLICTING
        return status, {
            "method": "algerian_wilaya_normalization",
            "submitted_normalized": left,
            "observed_normalized": right,
            "explanation": "Wilaya values match after normalization."
            if status == Status.VERIFIED
            else f"Wilaya conflict: {left} versus {right}.",
        }

    if field in {"phone", "telephone"}:
        left = normalize_phone(submitted)
        right = normalize_phone(observed)
        status = Status.CONSISTENT if left == right else Status.CONFLICTING
        return status, {
            "method": "e164_like_phone_normalization",
            "submitted_normalized": left,
            "observed_normalized": right,
            "explanation": "Phone numbers match after Algerian dialing normalization."
            if status == Status.CONSISTENT
            else "Phone numbers differ after normalization.",
        }

    if field in {"website", "domain"}:
        left = normalize_domain(submitted)
        right = normalize_domain(observed)
        status = Status.CONSISTENT if left == right else Status.CONFLICTING
        return status, {
            "method": "canonical_domain_comparison",
            "submitted_normalized": left,
            "observed_normalized": right,
            "explanation": "Domains are consistent." if status == Status.CONSISTENT else "Domains differ.",
        }

    if field == "email":
        left_domain = submitted.rsplit("@", 1)[-1].lower() if "@" in submitted else None
        right_domain = observed.rsplit("@", 1)[-1].lower() if "@" in observed else None
        status = Status.CONSISTENT if submitted.casefold() == observed.casefold() else Status.CONFLICTING
        if left_domain and right_domain and left_domain == right_domain:
            status = Status.CONSISTENT
        return status, {
            "method": "email_or_domain_comparison",
            "explanation": "Email evidence is consistent at address or domain level."
            if status == Status.CONSISTENT
            else "Email evidence does not match the submitted address/domain.",
        }

    if field == "address":
        left = normalize_address(submitted) or ""
        right = normalize_address(observed) or ""
        score = round(token_set_ratio(left, right) / 100, 3)
        status = Status.CONSISTENT if score >= 0.86 else Status.MANUAL_REVIEW_REQUIRED
        return status, {
            "method": "normalized_address_token_similarity",
            "similarity": score,
            "explanation": f"Address token similarity is {score:.0%}.",
        }

    score = similarity(submitted, observed)
    status = Status.CONSISTENT if score >= 0.88 else Status.MANUAL_REVIEW_REQUIRED
    return status, {
        "method": "normalized_token_set_similarity",
        "similarity": score,
        "explanation": f"Normalized text similarity is {score:.0%}.",
    }


def compare(field: str, submitted: str | None, observed: str | None) -> tuple[Status, dict]:
    return compare_claim(field, submitted, observed)


def origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"
