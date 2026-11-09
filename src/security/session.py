"""In-memory Multi-Account Session Token Management.

CRITICAL SECURITY RULES:
1. Tokens are NEVER written to disk (no DB, JSON, YAML, TOML, INI, .env, registry, cache).
2. Tokens for all connected Cloudflare accounts are stored only in-memory in bytearray buffers during the active session.
3. Upon disconnect or app exit, the memory buffers for all accounts are explicitly zeroed (overwritten with null bytes).
4. Note on Python memory: Python strings are immutable and the garbage collector handles memory.
   While we overwrite the bytearray buffer with 0s and delete references, transient memory copies
   may exist until process termination. We do NOT guarantee 100% RAM wipe beyond OS process boundary.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import gc


class AccountSession:
    """Represents a single authenticated Cloudflare account in-memory."""

    def __init__(self, account_id: str, label: str, token: str, user_info: Optional[str] = None):
        self.account_id: str = account_id
        self.label: str = label
        self._token_buffer: Optional[bytearray] = bytearray(token.strip().encode("utf-8"))
        self.connected_at: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.user_info: Optional[str] = user_info
        self.zones: List[Any] = []

    def get_token(self) -> Optional[str]:
        if self._token_buffer and len(self._token_buffer) > 0:
            return self._token_buffer.decode("utf-8")
        return None

    def clear(self):
        """Zeroes bytearray and removes references."""
        if self._token_buffer is not None:
            for i in range(len(self._token_buffer)):
                self._token_buffer[i] = 0
            self._token_buffer = None
        self.zones.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "label": self.label,
            "connected_at": self.connected_at,
            "user_info": self.user_info or "-",
            "zones_count": len(self.zones),
        }


class MultiAccountSessionManager:
    """Manages multiple in-memory Cloudflare account sessions simultaneously."""

    def __init__(self):
        self._accounts: Dict[str, AccountSession] = {}
        self._active_id: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        return self._active_id is not None and self._active_id in self._accounts

    @property
    def account_count(self) -> int:
        return len(self._accounts)

    @property
    def active_account(self) -> Optional[AccountSession]:
        if self._active_id and self._active_id in self._accounts:
            return self._accounts[self._active_id]
        return None

    @property
    def active_id(self) -> Optional[str]:
        return self._active_id

    @property
    def last_connected_at(self) -> Optional[str]:
        if self.active_account:
            return self.active_account.connected_at
        return None

    def add_account(self, label: str, token: str, user_info: Optional[str] = None) -> str:
        """Adds a new Cloudflare account session in-memory."""
        token_clean = token.strip()
        if not token_clean:
            raise ValueError("Token tidak boleh kosong.")

        account_id = f"acc_{uuid.uuid4().hex[:8]}"
        clean_label = label.strip() if label and label.strip() else f"Akun CF #{len(self._accounts) + 1}"
        session = AccountSession(account_id, clean_label, token_clean, user_info)
        self._accounts[account_id] = session

        # Automatically make active if first account
        if not self._active_id or self._active_id not in self._accounts:
            self._active_id = account_id

        return account_id

    def set_token(self, token: str, label: str = "Akun Utama", user_info: Optional[str] = None) -> str:
        """Legacy helper for backward compatibility."""
        return self.add_account(label, token, user_info)

    def switch_account(self, account_id: str) -> None:
        """Switches the active Cloudflare account."""
        if account_id in self._accounts:
            self._active_id = account_id
        else:
            raise KeyError(f"Akun ID '{account_id}' tidak ditemukan dalam sesi.")

    def get_token(self) -> Optional[str]:
        """Gets active account token."""
        if self.active_account:
            return self.active_account.get_token()
        return None

    def get_token_for(self, account_id: str) -> Optional[str]:
        """Gets token for a specific account."""
        if account_id in self._accounts:
            return self._accounts[account_id].get_token()
        return None

    def remove_account(self, account_id: str) -> None:
        """Removes and zeroes token for a single account."""
        if account_id in self._accounts:
            self._accounts[account_id].clear()
            del self._accounts[account_id]
            if self._active_id == account_id:
                # Switch active account to another one if exists
                self._active_id = next(iter(self._accounts.keys()), None)
            gc.collect()

    def disconnect_all(self) -> None:
        """Disconnects and zeroes memory for all accounts."""
        for acc in list(self._accounts.values()):
            acc.clear()
        self._accounts.clear()
        self._active_id = None
        gc.collect()

    def disconnect(self) -> None:
        """Alias for disconnect_all."""
        self.disconnect_all()

    def clear_token(self) -> None:
        """Alias for disconnect_all for backwards compatibility."""
        self.disconnect_all()

    def get_all_accounts(self) -> List[AccountSession]:
        return list(self._accounts.values())


# Global active multi-account session manager instance (in-memory only)
active_session = MultiAccountSessionManager()
