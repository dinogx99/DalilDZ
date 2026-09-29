from app.core.domain import SourceHealth
from app.services.domain_intelligence import collect_domain_metadata
from app.services.web_intelligence import SourceFetchError, collect_website_metadata
from app.sources.base import CollectionResult, EvidenceSourceAdapter, SourceEvidence


class CNRCManualSource(EvidenceSourceAdapter):
    source_id = "cnrc_manual"
    display_name = "CNRC / Sidjilcom manual verification"
    source_type = "OFFICIAL_REGISTRY"
    official = True
    automation_mode = "MANUAL_ONLY"
    limitations = (
        "DalilDZ does not claim an undocumented CNRC API. Use the manual evidence "
        "workflow and record the official URL/value with provenance."
    )
    supported_fields = ("legal_name", "rc", "nif", "legal_form", "wilaya", "activities")

    async def health_check(self) -> SourceHealth:
        return SourceHealth.MANUAL_ONLY

    async def collect(self, claims: dict[str, str]) -> CollectionResult:
        return CollectionResult(health=SourceHealth.MANUAL_ONLY)


class WebsitePublicSource(EvidenceSourceAdapter):
    source_id = "company_website"
    display_name = "Submitted company website"
    source_type = "PUBLIC_WEBSITE"
    supported_fields = (
        "legal_name",
        "rc",
        "nif",
        "nis",
        "ai",
        "legal_form",
        "website",
        "email",
        "phone",
    )
    limitations = (
        "A company-controlled website is self-published evidence. It can support "
        "consistency checks but is not equivalent to an official registry."
    )

    async def health_check(self) -> SourceHealth:
        return SourceHealth.AVAILABLE

    async def collect(self, claims: dict[str, str]) -> CollectionResult:
        website = claims.get("website")
        if not website:
            return CollectionResult(health=SourceHealth.AVAILABLE)
        try:
            result = await collect_website_metadata(website)
        except (SourceFetchError, ValueError, OSError) as exc:
            return CollectionResult(
                health=SourceHealth.DEGRADED,
                error_code=str(exc),
            )
        return CollectionResult(
            health=SourceHealth.AVAILABLE,
            evidence=[SourceEvidence(**item) for item in result["evidence"]],
            snapshot_hash=result["snapshot_hash"],
            snapshot_metadata=result["snapshot_metadata"],
        )


class DomainTechnicalSource(EvidenceSourceAdapter):
    source_id = "domain_intelligence"
    display_name = "DNS / TLS / RDAP"
    source_type = "PUBLIC_TECHNICAL"
    supported_fields = (
        "website",
        "domain",
        "dns_addresses",
        "tls_common_name",
        "rdap_registrar",
    )
    limitations = (
        "Domain and certificate metadata are technical observations only. Domain age, "
        "DNS presence or TLS availability are not evidence of business legitimacy."
    )

    async def health_check(self) -> SourceHealth:
        return SourceHealth.AVAILABLE

    async def collect(self, claims: dict[str, str]) -> CollectionResult:
        website = claims.get("website")
        if not website:
            return CollectionResult(health=SourceHealth.AVAILABLE)
        try:
            result = await collect_domain_metadata(website)
        except (ValueError, OSError) as exc:
            return CollectionResult(
                health=SourceHealth.DEGRADED,
                error_code=str(exc),
            )
        return CollectionResult(
            health=SourceHealth.AVAILABLE,
            evidence=[SourceEvidence(**item) for item in result["evidence"]],
            snapshot_metadata={
                "domain": result["domain"],
                "checked_at": result["checked_at"],
                "tls_available": bool(result.get("tls")),
                "rdap_available": bool(result.get("rdap")),
            },
        )


ADAPTERS: list[EvidenceSourceAdapter] = [
    CNRCManualSource(),
    WebsitePublicSource(),
    DomainTechnicalSource(),
]
