"""PySide6 Background Workers for non-blocking Cloudflare API operations.
Ensures GUI remains responsive at all times and threads do not access UI widgets directly.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtCore import QThread, Signal
from src.cloudflare.client import cf_client
from src.cloudflare.zones import fetch_all_zones
from src.cloudflare.redirects import (
    get_zone_redirect_ruleset,
    create_redirect_rule,
    update_redirect_rule,
    toggle_redirect_rule_status,
    delete_redirect_rule,
)
from src.security.session import active_session
from src.utils.errors import sanitize_message
from src.utils.audit import session_audit


class ConnectWorker(QThread):
    """Verifies token and adds account to multi-account session."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, token: str, label: str = "", parent=None):
        super().__init__(parent)
        self.token = token
        self.label = label

    def run(self):
        try:
            # Verify token directly first
            verify_res = cf_client.verify_token(token=self.token)
            status = verify_res.get("status", "active")
            
            # Add to in-memory multi-account session
            account_id = active_session.add_account(label=self.label, token=self.token)
            zones = fetch_all_zones(account_id=account_id)
            
            acc_obj = active_session.active_account
            final_label = acc_obj.label if acc_obj else self.label
            session_audit.record("CONNECT_ACCOUNT", final_label, "SUCCESS", f"Zones count: {len(zones)}")
            
            self.finished.emit({
                "status": status,
                "zones": zones,
                "account_id": account_id,
                "label": final_label,
                "message": f"Akun '{final_label}' berhasil terhubung ke Cloudflare API."
            })
        except Exception as exc:
            err_msg = sanitize_message(str(exc))
            session_audit.record("CONNECT_ACCOUNT", self.label or "New Account", "FAILED", err_msg)
            self.error.emit(err_msg)
        finally:
            self.token = ""


class FetchZonesWorker(QThread):
    """Fetches accessible zones for specific account or all accounts in background."""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, status_filter: Optional[str] = None, account_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.status_filter = status_filter
        self.account_id = account_id

    def run(self):
        try:
            zones = fetch_all_zones(self.status_filter, account_id=self.account_id)
            self.finished.emit(zones)
        except Exception as exc:
            self.error.emit(sanitize_message(str(exc)))


class FetchRedirectsWorker(QThread):
    """Fetches rules for a zone or all zones in background."""
    finished = Signal(str, list)  # ruleset_id, rules
    error = Signal(str)

    def __init__(self, zone_id: str, zones: Optional[List[Any]] = None, parent=None):
        super().__init__(parent)
        self.zone_id = zone_id
        self.zones = zones or []

    def run(self):
        try:
            if self.zone_id == "all":
                all_rules = []
                for z in self.zones:
                    try:
                        _, rules = get_zone_redirect_ruleset(
                            z.id,
                            zone_name=z.name,
                            account_id=z.account_id,
                            account_label=z.account_label,
                        )
                        all_rules.extend(rules)
                    except Exception:
                        pass
                self.finished.emit("all", all_rules)
            else:
                ruleset_id, rules = get_zone_redirect_ruleset(self.zone_id)
                self.finished.emit(ruleset_id or "", rules)
        except Exception as exc:
            self.error.emit(sanitize_message(str(exc)))


class CreateRedirectWorker(QThread):
    """Creates a redirect rule (or updates existing rule on zone) in background."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        zone_id: str,
        source_hostname: str,
        destination_url: str,
        coverage: str = "all",
        status_code: int = 301,
        preserve_path: bool = False,
        preserve_query_string: bool = True,
        enabled: bool = True,
        description: Optional[str] = None,
        dry_run: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.zone_id = zone_id
        self.source_hostname = source_hostname
        self.destination_url = destination_url
        self.coverage = coverage
        self.status_code = status_code
        self.preserve_path = preserve_path
        self.preserve_query_string = preserve_query_string
        self.enabled = enabled
        self.description = description
        self.dry_run = dry_run

    def run(self):
        try:
            res = create_redirect_rule(
                zone_id=self.zone_id,
                source_hostname=self.source_hostname,
                destination_url=self.destination_url,
                coverage=self.coverage,
                status_code=self.status_code,
                preserve_path=self.preserve_path,
                preserve_query_string=self.preserve_query_string,
                enabled=self.enabled,
                description=self.description,
                dry_run=self.dry_run,
            )
            self.finished.emit(res)
        except Exception as exc:
            self.error.emit(sanitize_message(str(exc)))


class UpdateRedirectWorker(QThread):
    """Updates an existing redirect rule in background."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        zone_id: str,
        ruleset_id: str,
        rule_id: str,
        source_hostname: str,
        destination_url: str,
        coverage: str = "all",
        status_code: int = 301,
        preserve_path: bool = False,
        preserve_query_string: bool = True,
        enabled: bool = True,
        description: Optional[str] = None,
        dry_run: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.zone_id = zone_id
        self.ruleset_id = ruleset_id
        self.rule_id = rule_id
        self.source_hostname = source_hostname
        self.destination_url = destination_url
        self.coverage = coverage
        self.status_code = status_code
        self.preserve_path = preserve_path
        self.preserve_query_string = preserve_query_string
        self.enabled = enabled
        self.description = description
        self.dry_run = dry_run

    def run(self):
        try:
            res = update_redirect_rule(
                zone_id=self.zone_id,
                ruleset_id=self.ruleset_id,
                rule_id=self.rule_id,
                source_hostname=self.source_hostname,
                destination_url=self.destination_url,
                coverage=self.coverage,
                status_code=self.status_code,
                preserve_path=self.preserve_path,
                preserve_query_string=self.preserve_query_string,
                enabled=self.enabled,
                description=self.description,
                dry_run=self.dry_run,
            )
            self.finished.emit(res)
        except Exception as exc:
            self.error.emit(sanitize_message(str(exc)))


class ToggleRedirectWorker(QThread):
    """Toggles rule enabled/disabled in background."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, zone_id: str, ruleset_id: str, rule_id: str, enabled: bool, dry_run: bool = False, parent=None):
        super().__init__(parent)
        self.zone_id = zone_id
        self.ruleset_id = ruleset_id
        self.rule_id = rule_id
        self.enabled = enabled
        self.dry_run = dry_run

    def run(self):
        try:
            res = toggle_redirect_rule_status(
                zone_id=self.zone_id,
                ruleset_id=self.ruleset_id,
                rule_id=self.rule_id,
                enabled=self.enabled,
                dry_run=self.dry_run,
            )
            self.finished.emit(res)
        except Exception as exc:
            self.error.emit(sanitize_message(str(exc)))


class DeleteRedirectWorker(QThread):
    """Deletes a redirect rule in background."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, zone_id: str, ruleset_id: str, rule_id: str, dry_run: bool = False, parent=None):
        super().__init__(parent)
        self.zone_id = zone_id
        self.ruleset_id = ruleset_id
        self.rule_id = rule_id
        self.dry_run = dry_run

    def run(self):
        try:
            res = delete_redirect_rule(
                zone_id=self.zone_id,
                ruleset_id=self.ruleset_id,
                rule_id=self.rule_id,
                dry_run=self.dry_run,
            )
            self.finished.emit(res)
        except Exception as exc:
            self.error.emit(sanitize_message(str(exc)))


class BulkCreateRedirectsWorker(QThread):
    """Creates multiple redirect rules across zones with progress reporting."""
    progress = Signal(int, int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, items: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.items = items

    def run(self):
        try:
            total = len(self.items)
            success_count = 0
            failed_count = 0
            errors = []
            failed_items = []
            success_items = []

            for idx, item in enumerate(self.items, start=1):
                zone_id = item["zone_id"]
                account_id = item.get("account_id")
                account_label = item.get("account_label", "")
                source = item["source_hostname"]
                dest = item["destination_url"]
                cov = item.get("coverage", "all")
                status_code = item.get("status_code", 301)
                preserve_p = item.get("preserve_path", False)
                preserve_q = item.get("preserve_query_string", True)
                enabled = item.get("enabled", True)

                self.progress.emit(idx, total, f"Memproses: {source}")

                if account_id:
                    try:
                        active_session.switch_account(account_id)
                    except Exception:
                        pass

                try:
                    create_redirect_rule(
                        zone_id=zone_id,
                        source_hostname=source,
                        destination_url=dest,
                        coverage=cov,
                        status_code=status_code,
                        preserve_path=preserve_p,
                        preserve_query_string=preserve_q,
                        enabled=enabled,
                    )
                    success_count += 1
                    success_items.append({
                        "source": source,
                        "destination": dest,
                        "account_label": account_label,
                        "status_code": status_code,
                    })
                except Exception as exc:
                    failed_count += 1
                    clean_err = sanitize_message(str(exc))
                    err_text = f"{source}: {clean_err}"
                    errors.append(err_text)
                    failed_items.append({
                        "source": source,
                        "destination": dest,
                        "account_label": account_label,
                        "zone_id": zone_id,
                        "error": clean_err,
                        "status_code": status_code,
                    })

            self.finished.emit({
                "success": success_count,
                "failed": failed_count,
                "errors": errors,
                "failed_items": failed_items,
                "success_items": success_items,
            })
        except Exception as exc:
            self.error.emit(sanitize_message(str(exc)))


class BulkDeleteRedirectsWorker(QThread):
    """Deletes multiple redirect rules safely with progress reporting."""
    progress = Signal(int, int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, items: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.items = items

    def run(self):
        try:
            total = len(self.items)
            success_count = 0
            failed_count = 0
            errors = []

            for idx, item in enumerate(self.items, start=1):
                zone_id = item["zone_id"]
                ruleset_id = item["ruleset_id"]
                rule_id = item["rule_id"]
                source = item.get("source_hostname", rule_id)
                account_id = item.get("account_id")

                self.progress.emit(idx, total, f"Menghapus: {source}")

                if account_id:
                    try:
                        active_session.switch_account(account_id)
                    except Exception:
                        pass

                try:
                    delete_redirect_rule(
                        zone_id=zone_id,
                        ruleset_id=ruleset_id,
                        rule_id=rule_id,
                    )
                    success_count += 1
                except Exception as exc:
                    failed_count += 1
                    errors.append(f"{source}: {sanitize_message(str(exc))}")

            self.finished.emit({
                "success": success_count,
                "failed": failed_count,
                "errors": errors,
            })
        except Exception as exc:
            self.error.emit(sanitize_message(str(exc)))


class BulkToggleRedirectsWorker(QThread):
    """Toggles enabled status for multiple redirect rules."""
    progress = Signal(int, int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, items: List[Dict[str, Any]], enabled: bool, parent=None):
        super().__init__(parent)
        self.items = items
        self.enabled = enabled

    def run(self):
        try:
            total = len(self.items)
            success_count = 0
            failed_count = 0
            errors = []

            for idx, item in enumerate(self.items, start=1):
                zone_id = item["zone_id"]
                ruleset_id = item["ruleset_id"]
                rule_id = item["rule_id"]
                source = item.get("source_hostname", rule_id)
                account_id = item.get("account_id")

                action_name = "Mengaktifkan" if self.enabled else "Menonaktifkan"
                self.progress.emit(idx, total, f"{action_name}: {source}")

                if account_id:
                    try:
                        active_session.switch_account(account_id)
                    except Exception:
                        pass

                try:
                    toggle_redirect_rule_status(
                        zone_id=zone_id,
                        ruleset_id=ruleset_id,
                        rule_id=rule_id,
                        enabled=self.enabled,
                    )
                    success_count += 1
                except Exception as exc:
                    failed_count += 1
                    errors.append(f"{source}: {sanitize_message(str(exc))}")

            self.finished.emit({
                "success": success_count,
                "failed": failed_count,
                "errors": errors,
            })
        except Exception as exc:
            self.error.emit(sanitize_message(str(exc)))


class BulkPurgeRedirectsWorker(QThread):
    """Purges all 301/302 redirect rules across multiple zones."""
    progress = Signal(int, int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, zone_items: List[Dict[str, Any]], status_filter: int = 0, parent=None):
        super().__init__(parent)
        self.zone_items = zone_items  # list of {"zone_id": ..., "account_id": ..., "zone_name": ...}
        self.status_filter = status_filter  # 0: all, 301: 301 only, 302: 302 only

    def run(self):
        try:
            total_zones = len(self.zone_items)
            deleted_count = 0
            errors = []

            for idx, z in enumerate(self.zone_items, start=1):
                zid = z["zone_id"]
                zname = z.get("zone_name", zid)
                aid = z.get("account_id")

                self.progress.emit(idx, total_zones, f"Memeriksa zona: {zname}")
                if aid:
                    try:
                        active_session.switch_account(aid)
                    except Exception:
                        pass

                try:
                    ruleset_id, rules = get_zone_redirect_ruleset(zid)
                    if not ruleset_id or not rules:
                        continue

                    matching_rules = []
                    for r in rules:
                        if self.status_filter == 301 and r.status_code == 301:
                            matching_rules.append(r)
                        elif self.status_filter == 302 and r.status_code == 302:
                            matching_rules.append(r)
                        elif self.status_filter == 0:
                            matching_rules.append(r)

                    for r in matching_rules:
                        try:
                            delete_redirect_rule(zid, ruleset_id, r.id)
                            deleted_count += 1
                        except Exception as e:
                            errors.append(f"{zname} ({r.id}): {sanitize_message(str(e))}")
                except Exception as exc:
                    errors.append(f"{zname}: {sanitize_message(str(exc))}")

            self.finished.emit({
                "success": deleted_count,
                "errors": errors,
            })
        except Exception as exc:
            self.error.emit(sanitize_message(str(exc)))


