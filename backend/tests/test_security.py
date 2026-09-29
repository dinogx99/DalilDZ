import socket

import pytest

from app.services.security import resolve_public_ips, sanitize_filename, validate_public_url


def _dns(ip: str):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/x",
        "http://127.0.0.1/x",
        "http://169.254.169.254/latest/meta-data",
        "ftp://example.com/file",
        "http://user:pass@example.com/",
    ],
)
def test_ssrf_and_unsafe_urls_are_rejected(url):
    with pytest.raises(ValueError):
        validate_public_url(url)


def test_private_dns_answer_is_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: _dns("10.0.0.8"))
    with pytest.raises(ValueError, match="SSRF_BLOCKED"):
        resolve_public_ips("example.com")


def test_global_dns_answer_is_allowed(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: _dns("8.8.8.8"))
    assert resolve_public_ips("example.com") == {"8.8.8.8"}


def test_filename_is_sanitized_and_bounded():
    result = sanitize_filename("../../invoice<>.pdf")
    assert "/" not in result
    assert "<" not in result
    assert len(result) <= 200
