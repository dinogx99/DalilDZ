import asyncio
from datetime import datetime, timezone
import socket
import ssl
from urllib.parse import quote

from app.normalization.algeria import normalize_domain
from app.services.security import resolve_public_ips
from app.services.web_intelligence import SourceFetchError, fetch_public_url


def _tls_metadata(host: str) -> dict:
    context = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=6) as raw:
        with context.wrap_socket(raw, server_hostname=host) as tls:
            cert = tls.getpeercert()
            subject = dict(item for part in cert.get("subject", ()) for item in part)
            issuer = dict(item for part in cert.get("issuer", ()) for item in part)
            return {
                "common_name": subject.get("commonName"),
                "issuer_common_name": issuer.get("commonName"),
                "not_before": cert.get("notBefore"),
                "not_after": cert.get("notAfter"),
                "cipher": tls.cipher()[0] if tls.cipher() else None,
                "protocol": tls.version(),
            }


async def collect_domain_metadata(value: str) -> dict:
    domain = normalize_domain(value)
    if not domain:
        raise ValueError("INVALID_DOMAIN")

    addresses = sorted(resolve_public_ips(domain))
    evidence: list[dict] = [
        {
            "field": "domain",
            "value": domain,
            "confidence": 1.0,
            "method": "canonical_domain",
            "source_url": None,
            "metadata": {},
        },
        {
            "field": "dns_addresses",
            "value": ", ".join(addresses),
            "confidence": 1.0,
            "method": "dns_a_aaaa_resolution",
            "source_url": None,
            "metadata": {"addresses": addresses},
        },
    ]

    tls = None
    try:
        tls = await asyncio.to_thread(_tls_metadata, domain)
        if tls.get("common_name"):
            evidence.append(
                {
                    "field": "tls_common_name",
                    "value": tls["common_name"],
                    "confidence": 1.0,
                    "method": "tls_certificate",
                    "source_url": f"https://{domain}",
                    "metadata": tls,
                }
            )
    except (OSError, ssl.SSLError):
        tls = {"available": False}

    rdap = None
    try:
        result = await fetch_public_url(
            f"https://rdap.org/domain/{quote(domain, safe='')}",
            respect_robots=False,
        )
        if "json" in result.content_type:
            import json

            rdap = json.loads(result.body.decode("utf-8"))
            registrar = None
            for entity in rdap.get("entities", []):
                roles = entity.get("roles", [])
                if "registrar" in roles:
                    registrar = entity.get("handle")
                    break
            if registrar:
                evidence.append(
                    {
                        "field": "rdap_registrar",
                        "value": registrar,
                        "confidence": 1.0,
                        "method": "rdap",
                        "source_url": result.final_url,
                        "metadata": {},
                    }
                )
    except (SourceFetchError, ValueError, OSError):
        rdap = {"available": False}

    return {
        "domain": domain,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "addresses": addresses,
        "tls": tls,
        "rdap": rdap,
        "evidence": evidence,
    }
