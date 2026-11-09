"""Cloudflare API Client using httpx.

SECURITY MEASURES:
- TLS Certificate Verification is strictly enforced (verify=True).
- follow_redirects=False to ensure Authorization headers are never leaked.
- Token is retrieved dynamically from session and never stored permanently in headers.
- Multi-Account support: allows specifying account_id or token_override.
- Request/response logging masks all credentials.
- Strict timeouts to prevent GUI hangs.
"""

from typing import Dict, Any, Optional
import httpx
from src.config import settings
from src.security.session import active_session
from src.utils.errors import (
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ApiError,
    NetworkError,
    sanitize_message,
)

BASE_URL = settings.CLOUDFLARE_API_BASE_URL
DEFAULT_TIMEOUT = httpx.Timeout(
    connect=settings.TIMEOUT_CONNECT,
    read=settings.TIMEOUT_READ,
    write=settings.TIMEOUT_WRITE,
    pool=settings.TIMEOUT_POOL,
)


class CloudflareClient:
    """Manages secure HTTPS communication with the Cloudflare API."""

    def __init__(self):
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=BASE_URL,
                timeout=DEFAULT_TIMEOUT,
                verify=True,  # STRICT: never allow verify=False
                follow_redirects=False,  # STRICT: do not auto-forward auth headers
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": settings.USER_AGENT,
                },
            )
        return self._client

    def _get_auth_headers(
        self,
        account_id: Optional[str] = None,
        token_override: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> Dict[str, str]:
        if token_override:
            token = token_override
        elif account_id:
            token = active_session.get_token_for(account_id)
        else:
            # Auto-route to the matching account for the target zone if possible
            resolved_acc_id = None
            if endpoint and endpoint.startswith("zones/"):
                parts = endpoint.split("/")
                if len(parts) >= 2:
                    zid = parts[1]
                    for acc in active_session.get_all_accounts():
                        for z in getattr(acc, "zones", []):
                            if getattr(z, "id", "") == zid:
                                resolved_acc_id = acc.account_id
                                break
                        if resolved_acc_id:
                            break
            if resolved_acc_id:
                token = active_session.get_token_for(resolved_acc_id)
            else:
                token = active_session.get_token()

        if not token:
            raise AuthenticationError("Tidak ada token aktif dalam sesi. Silakan hubungkan akun Cloudflare terlebih dahulu.")
        return {"Authorization": f"Bearer {token}"}

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None,
        token_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Performs an authenticated HTTPS request to Cloudflare API."""
        client = self._get_client()
        url = endpoint.lstrip("/")
        headers = self._get_auth_headers(account_id=account_id, token_override=token_override, endpoint=url)

        try:
            response = client.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json_data,
                headers=headers,
            )
        except httpx.TimeoutException:
            raise NetworkError("Koneksi ke Cloudflare API waktu habis (Timeout). Coba lagi beberapa saat.")
        except httpx.ConnectError:
            raise NetworkError("Gagal terhubung ke Cloudflare API. Periksa koneksi internet atau firewall.")
        except httpx.RequestError as exc:
            clean_err = sanitize_message(str(exc))
            raise NetworkError(f"Kesalahan jaringan saat menghubungi Cloudflare: {clean_err}")

        # Handle HTTP error statuses
        if response.status_code == 401:
            raise AuthenticationError("Autentikasi gagal (HTTP 401). Token Cloudflare tidak valid.")
        elif response.status_code == 403:
            raise ForbiddenError("Akses ditolak (HTTP 403). Token tidak memiliki izin yang diperlukan.")
        elif response.status_code == 404:
            raise NotFoundError("Data tidak ditemukan (HTTP 404) pada Cloudflare API.")
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_sec = int(retry_after) if retry_after and retry_after.isdigit() else None
            raise RateLimitError(retry_after=retry_sec)

        # Parse response body
        try:
            data = response.json()
        except Exception:
            raise ApiError(f"Respons Cloudflare bukan JSON valid (HTTP {response.status_code}).")

        # Check Cloudflare success flag
        if not data.get("success", False):
            errors = data.get("errors", [])
            msg = "Operasi Cloudflare gagal."
            if errors:
                msg = errors[0].get("message", msg)
            raise ApiError(msg, errors=errors, status_code=response.status_code)

        return data

    def verify_token(self, token: Optional[str] = None) -> Dict[str, Any]:
        """Tests the token connection using /user/tokens/verify."""
        res = self.request("GET", "user/tokens/verify", token_override=token)
        return res.get("result", {})

    def close(self):
        """Closes the underlying HTTP client connection pool."""
        if self._client is not None and not self._client.is_closed:
            self._client.close()
            self._client = None


# Global API client instance
cf_client = CloudflareClient()
