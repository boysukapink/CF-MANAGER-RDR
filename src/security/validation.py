"""Input validation and sanitization for Cloudflare redirects.

Ensures:
- IDNA normalization for internationalized domain names (punycode)
- Source hostname format validation
- Destination URL scheme restriction (http/https only)
- Credential injection rejection (user:pass@)
- Control characters and dangerous payload rejection
- Loop detection (source host == target host)
- Safe Cloudflare expression generation with proper string escaping
"""

import re
from urllib.parse import urlsplit
import idna
from typing import Tuple, Optional
from src.utils.errors import ValidationError


HOSTNAME_REGEX = re.compile(
    r"^(?!-)[A-Za-z0-9-_]{1,63}(?<!-)(\.[A-Za-z0-9-_]{1,63})*\.[A-Za-z]{2,}$"
)

# Reject any non-printable ASCII or control characters
CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def normalize_hostname(hostname: str) -> str:
    """Normalizes hostname, trimming whitespace, lowercasing, and encoding IDNA (punycode)."""
    if not hostname:
        raise ValidationError("Hostname sumber tidak boleh kosong.")
    
    clean = hostname.strip().lower()

    if clean == "*":
        return "*"

    # Reject control characters
    if CONTROL_CHAR_REGEX.search(clean):
        raise ValidationError("Hostname mengandung karakter kontrol yang tidak valid.")

    # Remove trailing dot if present
    if clean.endswith("."):
        clean = clean[:-1]

    # Convert IDN (e.g., münchen.de -> xn--mnchen-3ya.de)
    try:
        clean = idna.encode(clean).decode("ascii")
    except Exception as e:
        raise ValidationError(f"Hostname IDNA tidak valid: {str(e)}")

    if not HOSTNAME_REGEX.match(clean):
        raise ValidationError(f"Format hostname tidak valid: '{clean}'. Contoh: 'domain.com' atau 'sub.domain.com'.")

    return clean


def validate_destination_url(url: str, source_host: Optional[str] = None) -> Tuple[str, bool]:
    """Validates destination URL.
    Returns:
        (normalized_url: str, is_same_or_subdomain: bool)
    Raises:
        ValidationError if URL is invalid, uses forbidden scheme, or has embedded credentials.
    """
    if not url:
        raise ValidationError("URL tujuan tidak boleh kosong.")

    clean_url = url.strip()

    if CONTROL_CHAR_REGEX.search(clean_url):
        raise ValidationError("URL tujuan mengandung karakter kontrol yang berbahaya.")

    # If URL contains a scheme (e.g. ftp://, javascript:, file://), check scheme first
    has_scheme = bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", clean_url))
    if not has_scheme:
        clean_url = "https://" + clean_url

    try:
        parsed = urlsplit(clean_url)
    except Exception as e:
        raise ValidationError(f"URL tujuan tidak dapat diurai: {str(e)}")

    # Reject non-http/https schemes
    if parsed.scheme not in ("http", "https"):
        raise ValidationError(f"Skema '{parsed.scheme}' tidak diizinkan. Hanya HTTP dan HTTPS yang diperbolehkan.")

    # Reject embedded userinfo (e.g., user:pass@host)
    if parsed.username or parsed.password:
        raise ValidationError("URL tujuan tidak boleh mengandung kredensial pengguna (user:password@).")

    if not parsed.hostname:
        raise ValidationError("URL tujuan tidak memiliki hostname yang valid.")

    # Validate destination host with IDNA
    dest_host = parsed.hostname.lower()
    try:
        dest_host = idna.encode(dest_host).decode("ascii")
    except Exception as e:
        raise ValidationError(f"Hostname tujuan IDNA tidak valid: {str(e)}")

    if not HOSTNAME_REGEX.match(dest_host):
        raise ValidationError(f"Hostname tujuan tidak valid: '{dest_host}'.")

    # Reconstruct normalized URL with IDNA hostname
    port_part = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
    path_part = parsed.path if parsed.path else "/"
    query_part = f"?{parsed.query}" if parsed.query else ""
    fragment_part = f"#{parsed.fragment}" if parsed.fragment else ""

    normalized_url = f"{parsed.scheme}://{dest_host}{port_part}{path_part}{query_part}{fragment_part}"

    # Loop and subdomain checks if source_host is provided
    is_same_or_sub = False
    if source_host and source_host != "*":
        norm_source = normalize_hostname(source_host)
        if norm_source != "*" and norm_source == dest_host and (path_part == "/" or not path_part):
            raise ValidationError(
                f"Loop redirect terdeteksi! Domain asal ({norm_source}) sama dengan domain tujuan ({dest_host}) tanpa perubahan path."
            )
        if norm_source != "*" and (norm_source == dest_host or dest_host.endswith("." + norm_source) or norm_source.endswith("." + dest_host)):
            is_same_or_sub = True

    return normalized_url, is_same_or_sub


def escape_cloudflare_string(value: str) -> str:
    """Safely escapes a string for use in Cloudflare Ruleset Engine expressions."""
    # Cloudflare expressions use double quotes for strings.
    # Escapes backslashes and double quotes.
    return value.replace('\\', '\\\\').replace('"', '\\"')


def build_cloudflare_expression(source_hostname: str) -> str:
    """Builds a secure, escaped Cloudflare Ruleset expression matching the hostname."""
    norm_host = normalize_hostname(source_hostname)
    escaped = escape_cloudflare_string(norm_host)
    return f'http.host eq "{escaped}"'


def build_all_incoming_expression(source_domain: str, coverage: str = "all") -> Tuple[str, str]:
    """Builds Cloudflare Ruleset expression for ALL INCOMING mode.
    Coverage options:
        - 'all': All incoming requests for the entire zone (expression: true)
        - 'apex': Only apex domain (e.g. domain.com)
        - 'www': Only www subdomain (e.g. www.domain.com)
        - 'both': Both apex and www (e.g. domain.com or www.domain.com)
    Returns:
        (expression: str, display_name: str)
    """
    if source_domain.strip() == "*":
        return "true", "* (All incoming requests)"

    norm = normalize_hostname(source_domain)
    # Determine apex and www variants
    if norm.startswith("www."):
        apex = norm[4:]
        www = norm
    else:
        apex = norm
        www = f"www.{norm}"

    escaped_apex = escape_cloudflare_string(apex)
    escaped_www = escape_cloudflare_string(www)

    if coverage in ("all", "all_incoming"):
        return "true", f"{apex} (All incoming requests)"
    elif coverage == "apex":
        return f'http.host eq "{escaped_apex}"', apex
    elif coverage == "www":
        return f'http.host eq "{escaped_www}"', www
    else:  # both
        return f'(http.host eq "{escaped_apex}" or http.host eq "{escaped_www}")', f"{apex} (+ www)"


def simulate_redirect(
    incoming_url: str,
    source_domain: str,
    destination_url: str,
    coverage: str,
    preserve_path: bool,
    preserve_query: bool,
) -> Tuple[bool, str, str]:
    """Simulates how an incoming URL is processed by the ALL INCOMING redirect rule.
    Returns:
        (is_matched: bool, result_url_or_reason: str, status_explanation: str)
    """
    try:
        parsed_in = urlsplit(incoming_url.strip())
        if not parsed_in.hostname:
            return False, "", "URL masukan tidak memiliki hostname yang valid."
        
        in_host = parsed_in.hostname.lower()
        norm_src = normalize_hostname(source_domain)
        if norm_src == "*":
            apex = "*"
            www = "*"
        else:
            apex = norm_src[4:] if norm_src.startswith("www.") else norm_src
            www = f"www.{apex}"

        # Check hostname match
        matched = False
        if coverage in ("all", "all_incoming"):
            matched = True
        elif coverage == "apex" and in_host == apex:
            matched = True
        elif coverage == "www" and in_host == www:
            matched = True
        elif coverage == "both" and (in_host == apex or in_host == www):
            matched = True

        if not matched:
            return False, incoming_url, f"Hostname '{in_host}' tidak cocok dengan aturan ({coverage})."

        # Construct destination URL
        parsed_dest = urlsplit(destination_url.strip())
        dest_scheme = parsed_dest.scheme or "https"
        dest_host = parsed_dest.hostname or ""
        dest_port = f":{parsed_dest.port}" if parsed_dest.port and parsed_dest.port not in (80, 443) else ""
        clean_path = parsed_dest.path.rstrip("/")
        last_seg = clean_path.split("/")[-1] if clean_path else ""
        is_file_target = ("." in last_seg and not last_seg.startswith(".")) or bool(parsed_dest.query)

        # Path handling: only preserve path if destination is not an explicit file/query endpoint
        if preserve_path and not is_file_target:
            dest_base_path = clean_path
            in_path = parsed_in.path or "/"
            final_path = f"{dest_base_path}{in_path}"
        else:
            final_path = parsed_dest.path if parsed_dest.path else "/"

        # Query handling
        final_query = ""
        if preserve_query and parsed_in.query:
            final_query = f"?{parsed_in.query}"
        elif not preserve_query and parsed_dest.query:
            final_query = f"?{parsed_dest.query}"

        result_url = f"{dest_scheme}://{dest_host}{dest_port}{final_path}{final_query}"
        return True, result_url, "Cocok dan dialihkan."
    except Exception as e:
        return False, "", f"Gagal mensimulasikan URL: {str(e)}"


def validate_status_code(code: int) -> int:
    """Validates HTTP status code for redirects (301 or 302)."""
    if code not in (301, 302):
        raise ValidationError("Status HTTP harus 301 (Permanen) atau 302 (Sementara).")
    return code

