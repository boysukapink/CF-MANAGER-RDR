"""Unit tests for domain and URL validation, IDNA conversion, loop detection, and escaping.
"""

import pytest
from src.security.validation import (
    normalize_hostname,
    validate_destination_url,
    build_cloudflare_expression,
    validate_status_code,
    escape_cloudflare_string,
)
from src.utils.errors import ValidationError


def test_normalize_hostname_valid():
    assert normalize_hostname("example.com") == "example.com"
    assert normalize_hostname("SUB.EXAMPLE.COM") == "sub.example.com"
    assert normalize_hostname("  blog.domain.co.id  ") == "blog.domain.co.id"


def test_normalize_hostname_idna():
    # münchen.de -> xn--mnchen-3ya.de
    punycode = normalize_hostname("münchen.de")
    assert punycode == "xn--mnchen-3ya.de"


def test_normalize_hostname_invalid():
    with pytest.raises(ValidationError):
        normalize_hostname("")

    with pytest.raises(ValidationError):
        normalize_hostname("   ")

    with pytest.raises(ValidationError):
        normalize_hostname("-invalid.com")

    with pytest.raises(ValidationError):
        normalize_hostname("domain with space.com")

    with pytest.raises(ValidationError):
        normalize_hostname("domain\nnewline.com")


def test_validate_destination_url_valid():
    url, is_sub = validate_destination_url("https://target.com/page", source_host="example.com")
    assert url == "https://target.com/page"
    assert not is_sub

    # Automatically prepends https:// if missing
    url2, _ = validate_destination_url("destination.org")
    assert url2 == "https://destination.org/"


def test_validate_destination_url_subdomain_warning():
    _, is_sub = validate_destination_url("https://sub.example.com", source_host="example.com")
    assert is_sub is True


def test_validate_destination_url_loop_rejection():
    # Exact same host and root path must raise ValidationError
    with pytest.raises(ValidationError, match="Loop redirect terdeteksi"):
        validate_destination_url("https://example.com/", source_host="example.com")


def test_validate_destination_url_scheme_restriction():
    with pytest.raises(ValidationError, match="Skema 'ftp' tidak diizinkan"):
        validate_destination_url("ftp://files.example.com/file.zip")

    with pytest.raises(ValidationError, match="Skema 'javascript' tidak diizinkan"):
        validate_destination_url("javascript:alert(1)")


def test_validate_destination_url_credentials_rejection():
    with pytest.raises(ValidationError, match="kredensial pengguna"):
        validate_destination_url("https://user:password@target.com")


def test_validate_destination_url_control_characters():
    with pytest.raises(ValidationError, match="karakter kontrol"):
        validate_destination_url("https://target.com/\x00malicious")


def test_escape_cloudflare_string():
    raw = 'test"domain\\name'
    escaped = escape_cloudflare_string(raw)
    assert escaped == 'test\\"domain\\\\name'


def test_build_cloudflare_expression():
    expr = build_cloudflare_expression("old.example.com")
    assert expr == 'http.host eq "old.example.com"'

    expr_idna = build_cloudflare_expression("münchen.de")
    assert expr_idna == 'http.host eq "xn--mnchen-3ya.de"'


def test_validate_status_code():
    assert validate_status_code(301) == 301
    assert validate_status_code(302) == 302

    with pytest.raises(ValidationError):
        validate_status_code(200)

    with pytest.raises(ValidationError):
        validate_status_code(404)
