"""Custom error definitions for Cloudflare Redirect Manager.
Ensures no sensitive data (tokens, authorization headers) is ever leaked in error messages.
"""

from typing import Optional, List, Dict, Any


def sanitize_message(msg: str) -> str:
    """Strip out potential tokens or sensitive substrings from error messages."""
    if not msg:
        return ""
    # In case any Bearer token appears, mask it
    import re
    cleaned = re.sub(r'Bearer\s+[A-Za-z0-9_\-]+', 'Bearer [REDACTED]', msg, flags=re.IGNORECASE)
    cleaned = re.sub(r'([A-Za-z0-9_\-]{32,})', '[REDACTED_SECRET]', cleaned)
    return cleaned


class CFManagerError(Exception):
    """Base exception class for CFManager."""
    def __init__(self, message: str, details: Optional[str] = None):
        safe_msg = sanitize_message(message)
        self.message = safe_msg
        self.details = sanitize_message(details) if details else None
        super().__init__(safe_msg)


class ValidationError(CFManagerError):
    """Raised when user input or data validation fails."""
    pass


class AuthenticationError(CFManagerError):
    """Raised on HTTP 401: Invalid or expired API Token."""
    def __init__(self, message: str = "Token API Cloudflare tidak valid atau kedaluwarsa."):
        super().__init__(message)


class ForbiddenError(CFManagerError):
    """Raised on HTTP 403: Insufficient API Token permissions."""
    def __init__(self, message: str = "Izin token tidak mencukupi untuk melakukan operasi ini. Pastikan token memiliki izin Zone:Read dan Single Redirect:Edit."):
        super().__init__(message)


class NotFoundError(CFManagerError):
    """Raised on HTTP 404: Resource not found."""
    def __init__(self, message: str = "Sumber daya Cloudflare tidak ditemukan."):
        super().__init__(message)


class RateLimitError(CFManagerError):
    """Raised on HTTP 429: Cloudflare rate limit reached."""
    def __init__(self, retry_after: Optional[int] = None):
        msg = f"Batas laju permintaan Cloudflare (Rate Limit) tercapai. Coba lagi dalam {retry_after} detik." if retry_after else "Batas laju permintaan Cloudflare (Rate Limit) tercapai. Silakan tunggu sebentar."
        super().__init__(msg)
        self.retry_after = retry_after


class ApiError(CFManagerError):
    """Raised when Cloudflare API returns errors with success=False."""
    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None, status_code: int = 400):
        self.status_code = status_code
        self.api_errors = errors or []
        formatted = []
        for err in self.api_errors:
            code = err.get("code", "")
            err_msg = sanitize_message(err.get("message", ""))
            formatted.append(f"[{code}] {err_msg}" if code else err_msg)
        details = "; ".join(formatted) if formatted else None
        super().__init__(message, details=details)


class NetworkError(CFManagerError):
    """Raised when network connection fails, times out, or TLS error occurs."""
    def __init__(self, message: str = "Gagal terhubung ke Cloudflare API. Periksa koneksi internet Anda."):
        super().__init__(message)
