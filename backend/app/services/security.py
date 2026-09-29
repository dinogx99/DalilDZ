import ipaddress
import re
import socket
from urllib.parse import urlparse


BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata",
    "169.254.169.254",
}


def sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", filename).strip(" .")
    return (cleaned or "upload")[-200:]


def resolve_public_ips(host: str) -> set[str]:
    if host.casefold() in BLOCKED_HOSTS:
        raise ValueError("SSRF_BLOCKED")
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("DNS_FAILED") from exc

    addresses = {item[4][0] for item in infos}
    if not addresses:
        raise ValueError("DNS_FAILED")

    for raw in addresses:
        address = ipaddress.ip_address(raw)
        if not address.is_global:
            raise ValueError("SSRF_BLOCKED")
    return addresses


def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("INVALID_URL_SCHEME")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("INVALID_URL")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("UNSAFE_PORT")
    resolve_public_ips(parsed.hostname)
    return url
