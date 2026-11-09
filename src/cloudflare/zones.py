"""Zone management module for Cloudflare API.
Handles listing zones, pagination, status filtering, multi-account aggregation,
and matching hostnames to zones.
"""

from typing import List, Dict, Any, Optional
from src.config import settings
from src.cloudflare.client import cf_client
from src.security.session import active_session
from src.security.validation import normalize_hostname


class ZoneItem:
    def __init__(self, data: Dict[str, Any], account_id: str = "", account_label: str = ""):
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.status: str = data.get("status", "unknown")
        self.paused: bool = data.get("paused", False)
        plan_data = data.get("plan", {})
        self.plan_name: str = plan_data.get("name", "Free") if isinstance(plan_data, dict) else "Free"
        name_servers = data.get("name_servers", [])
        self.name_servers: List[str] = name_servers if isinstance(name_servers, list) else []
        self.account_id: str = account_id
        self.account_label: str = account_label or "Akun Utama"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "paused": self.paused,
            "plan_name": self.plan_name,
            "name_servers": self.name_servers,
            "account_id": self.account_id,
            "account_label": self.account_label,
        }


def _fetch_zones_for_single_account(
    account_id: str,
    account_label: str,
    status_filter: Optional[str] = None,
) -> List[ZoneItem]:
    """Fetches all zones for a specific account session."""
    zones: List[ZoneItem] = []
    page = 1
    per_page = settings.ZONES_PER_PAGE

    while True:
        params: Dict[str, Any] = {
            "page": page,
            "per_page": per_page,
            "order": "name",
            "direction": "asc",
        }
        if status_filter and status_filter.lower() != "all":
            params["status"] = status_filter.lower()

        response = cf_client.request("GET", "zones", params=params, account_id=account_id)
        results = response.get("result", [])
        for item in results:
            zones.append(ZoneItem(item, account_id=account_id, account_label=account_label))

        result_info = response.get("result_info", {})
        total_pages = result_info.get("total_pages", 1)
        if page >= total_pages or len(results) == 0:
            break
        page += 1

    return zones


def fetch_all_zones(
    status_filter: Optional[str] = None,
    account_id: Optional[str] = None,
) -> List[ZoneItem]:
    """Fetches all accessible zones using Cloudflare pagination.
    If account_id is 'all', aggregates zones from all connected accounts.
    If account_id is None, uses active account.
    """
    if account_id == "all":
        all_zones: List[ZoneItem] = []
        for acc in active_session.get_all_accounts():
            try:
                acc_zones = _fetch_zones_for_single_account(acc.account_id, acc.label, status_filter)
                acc.zones = acc_zones
                all_zones.extend(acc_zones)
            except Exception:
                pass
        return all_zones

    target_acc = None
    if account_id:
        target_acc = next((a for a in active_session.get_all_accounts() if a.account_id == account_id), None)
    else:
        target_acc = active_session.active_account

    if not target_acc:
        return []

    zones = _fetch_zones_for_single_account(target_acc.account_id, target_acc.label, status_filter)
    target_acc.zones = zones
    return zones


def find_matching_zone(hostname: str, available_zones: List[ZoneItem]) -> Optional[ZoneItem]:
    """Finds the most specific zone that matches the given hostname."""
    clean_host = normalize_hostname(hostname)
    best_match: Optional[ZoneItem] = None
    longest_match_len = 0

    for zone in available_zones:
        z_name = zone.name.lower()
        if clean_host == z_name or clean_host.endswith("." + z_name):
            if len(z_name) > longest_match_len:
                longest_match_len = len(z_name)
                best_match = zone

    return best_match
