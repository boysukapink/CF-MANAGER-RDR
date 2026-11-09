"""Cloudflare Single Redirects (URL Forwarding) Manager.
Uses Cloudflare Rulesets API under the 'http_request_dynamic_redirect' phase.
Supports ALL INCOMING redirect mode with Apex, WWW, or Both coverage,
301 Permanent / 302 Temporary, Preserve Path, and Preserve Query String toggles.
"""

from typing import List, Dict, Any, Optional, Tuple
import re
from urllib.parse import urlsplit
from src.cloudflare.client import cf_client
from src.security.validation import (
    normalize_hostname,
    validate_destination_url,
    build_all_incoming_expression,
    validate_status_code,
)
from src.utils.errors import NotFoundError, ValidationError
from src.utils.audit import session_audit

PHASE_DYNAMIC_REDIRECT = "http_request_dynamic_redirect"


class RedirectRule:
    def __init__(
        self,
        data: Dict[str, Any],
        zone_id: str,
        ruleset_id: str,
        zone_name: Optional[str] = None,
        account_id: Optional[str] = None,
        account_label: Optional[str] = None,
    ):
        self.id: str = data.get("id", "")
        self.zone_id: str = zone_id
        self.ruleset_id: str = ruleset_id
        self.zone_name: str = zone_name or ""
        self.account_id: str = account_id or ""
        self.account_label: str = account_label or ""
        self.description: str = data.get("description", "Single Redirect Rule")
        self.enabled: bool = data.get("enabled", True)
        self.expression: str = data.get("expression", "")

        # Try to resolve account info if not passed
        if not self.account_label or not self.account_id:
            try:
                from src.security.session import active_session
                for acc in active_session.get_all_accounts():
                    for z in getattr(acc, "zones", []):
                        if getattr(z, "id", "") == self.zone_id:
                            self.account_id = acc.account_id
                            self.account_label = acc.label
                            if not self.zone_name:
                                self.zone_name = z.name
                            break
                    if self.account_id:
                        break
            except Exception:
                pass
        if not self.account_label:
            self.account_label = "Akun Utama"

        action_params = data.get("action_parameters", {})
        from_value = action_params.get("from_value", {}) if isinstance(action_params, dict) else {}

        self.status_code: int = from_value.get("status_code", 301)
        self.preserve_query_string: bool = from_value.get("preserve_query_string", False)

        target_url = from_value.get("target_url", {})
        if "value" in target_url:
            self.target_url_raw: str = target_url["value"]
            self.preserve_path: bool = False
            self.destination_url: str = self.target_url_raw
            self.redirect_type: str = "Static"
        elif "expression" in target_url:
            self.target_url_raw: str = target_url["expression"]
            self.preserve_path = "http.request.uri.path" in self.target_url_raw
            expr_match = re.search(r'concat\("([^"]+)"', self.target_url_raw)
            self.destination_url = expr_match.group(1) if expr_match else self.target_url_raw
            self.redirect_type: str = "Dynamic"
        else:
            self.target_url_raw = ""
            self.preserve_path = False
            self.destination_url = ""
            self.redirect_type: str = "Static"

        # Analyze hostname coverage from expression
        expr_clean = self.expression.strip()
        if expr_clean == "true":
            self.coverage = "all"
            host_cand = self.zone_name
            if not host_cand:
                desc_match = re.search(r'ALL INCOMING Redirect\s+([^\s]+)', self.description)
                if desc_match:
                    host_cand = desc_match.group(1).rstrip("(")
            self.source_hostname = host_cand or "*"
            self.source_display = f"{self.source_hostname} (All incoming requests)" if self.source_hostname != "*" else "* (All incoming requests)"
            self.mode = "ALL INCOMING (All requests)"
        else:
            hosts_found = re.findall(r'http\.host\s+(?:eq|==)\s+"([^"]+)"', self.expression)
            if len(hosts_found) >= 2:
                self.coverage = "both"
                # Choose apex as main source
                apex_cand = next((h for h in hosts_found if not h.startswith("www.")), hosts_found[0])
                self.source_hostname = apex_cand
                self.source_display = f"{apex_cand} (+ www)"
            elif len(hosts_found) == 1:
                h = hosts_found[0]
                if h.startswith("www."):
                    self.coverage = "www"
                    self.source_hostname = h
                    self.source_display = f"{h} (www only)"
                else:
                    self.coverage = "apex"
                    self.source_hostname = h
                    self.source_display = f"{h} (Apex only)"
            else:
                self.source_hostname = self.expression
                self.source_display = self.expression
                self.coverage = "custom"
            self.mode = "ALL INCOMING"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "account_id": self.account_id,
            "account_label": self.account_label,
            "description": self.description,
            "enabled": self.enabled,
            "source_hostname": self.source_hostname,
            "source_display": self.source_display,
            "destination_url": self.destination_url,
            "status_code": self.status_code,
            "mode": self.mode,
            "redirect_type": self.redirect_type,
            "coverage": self.coverage,
            "preserve_path": self.preserve_path,
            "preserve_query_string": self.preserve_query_string,
            "expression": self.expression,
        }


def get_zone_redirect_ruleset(
    zone_id: str,
    zone_name: Optional[str] = None,
    account_id: Optional[str] = None,
    account_label: Optional[str] = None,
) -> Tuple[Optional[str], List[RedirectRule]]:
    """Fetches the Single Redirect ruleset and its rules for a given zone.
    Returns:
        (ruleset_id: Optional[str], rules: List[RedirectRule])
    """
    if not zone_name or not account_id or not account_label:
        try:
            from src.security.session import active_session
            for acc in active_session.get_all_accounts():
                for z in getattr(acc, "zones", []):
                    if z.id == zone_id:
                        zone_name = zone_name or z.name
                        account_id = account_id or acc.account_id
                        account_label = account_label or acc.label
                        break
                if account_id:
                    break
        except Exception:
            pass

    endpoint = f"zones/{zone_id}/rulesets/phases/{PHASE_DYNAMIC_REDIRECT}/entrypoint"
    try:
        response = cf_client.request("GET", endpoint, account_id=account_id)
        result = response.get("result", {})
        ruleset_id = result.get("id")
        raw_rules = result.get("rules", [])
        rules = [
            RedirectRule(
                r,
                zone_id=zone_id,
                ruleset_id=ruleset_id,
                zone_name=zone_name,
                account_id=account_id,
                account_label=account_label,
            )
            for r in raw_rules
            if r.get("action") == "redirect"
        ]
        return ruleset_id, rules
    except NotFoundError:
        # Phase entrypoint has not been created yet
        return None, []


def is_file_or_endpoint_path(path: str) -> bool:
    """Checks if a URL path points to an explicit file (e.g. .html, .php, .htm, .aspx, etc.)
    where appending incoming URI path is invalid.
    """
    clean_path = path.rstrip("/")
    if not clean_path:
        return False
    last_segment = clean_path.split("/")[-1]
    return "." in last_segment and not last_segment.startswith(".")


def build_all_incoming_payload(
    source_domain: str,
    destination_url: str,
    coverage: str = "all",
    status_code: int = 301,
    preserve_path: bool = False,
    preserve_query_string: bool = True,
    enabled: bool = True,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Constructs a Cloudflare Single Redirect rule payload for ALL INCOMING mode.
    Always uses Type: Static (target_url value string) per user requirements,
    making rules valid, clear, and easy to read directly in Cloudflare dashboard.
    """
    norm_source = normalize_hostname(source_domain) if source_domain != "*" else "*"
    norm_dest, _ = validate_destination_url(destination_url, source_host=norm_source if norm_source != "*" else None)
    valid_status = validate_status_code(status_code)

    expression, display_host = build_all_incoming_expression(norm_source, coverage=coverage)
    rule_desc = description or f"ALL INCOMING Redirect {display_host} -> {norm_dest} ({valid_status})"

    from_value = {
        "status_code": valid_status,
        "preserve_query_string": preserve_query_string,
        "target_url": {
            "value": norm_dest
        }
    }

    return {
        "action": "redirect",
        "description": rule_desc,
        "enabled": enabled,
        "expression": expression,
        "action_parameters": {
            "from_value": from_value
        }
    }


def build_rule_payload(
    source_hostname: str,
    destination_url: str,
    status_code: int = 301,
    mode: str = "Root",
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Legacy helper for backward compatibility."""
    preserve_path = (mode == "Preserve Path")
    return build_all_incoming_payload(
        source_domain=source_hostname,
        destination_url=destination_url,
        coverage="apex",
        status_code=status_code,
        preserve_path=preserve_path,
        preserve_query_string=preserve_path,
        description=description,
    )


def create_redirect_rule(
    zone_id: str,
    source_hostname: str,
    destination_url: str,
    status_code: int = 301,
    mode: str = "Root",
    coverage: str = "all",
    preserve_path: Optional[bool] = None,
    preserve_query_string: Optional[bool] = None,
    enabled: bool = True,
    description: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Creates a new Single Redirect rule in Cloudflare, OR edits (updates) the existing
    rule if a redirect rule already exists on this zone (yang lama diedit, bukan ditimpa).
    """
    if preserve_path is None:
        preserve_path = (mode == "Preserve Path")
    if preserve_query_string is None:
        preserve_query_string = True

    payload = build_all_incoming_payload(
        source_domain=source_hostname,
        destination_url=destination_url,
        coverage=coverage,
        status_code=status_code,
        preserve_path=preserve_path,
        preserve_query_string=preserve_query_string,
        enabled=enabled,
        description=description,
    )

    norm_source = normalize_hostname(source_hostname) if source_hostname != "*" else "*"
    try:
        ruleset_id, existing_rules = get_zone_redirect_ruleset(zone_id, zone_name=norm_source if norm_source != "*" else None)
    except Exception:
        if dry_run:
            ruleset_id, existing_rules = None, []
        else:
            raise

    # Check if a redirect rule already exists on this zone
    # If yes: EDIT the existing rule, do NOT duplicate / overwrite ("yang lama di edit, bukan di timpa")
    existing_rule_to_edit: Optional[RedirectRule] = None

    if existing_rules:
        # 1. First priority: match rule with coverage 'all' or expression 'true'
        for r in existing_rules:
            if coverage in ("all", "all_incoming") and (r.coverage in ("all", "all_incoming") or r.expression.strip() == "true"):
                existing_rule_to_edit = r
                break
            if norm_source != "*" and r.source_hostname.lower() in (norm_source.lower(), f"www.{norm_source.lower()}"):
                existing_rule_to_edit = r
                break

        # 2. If coverage is 'all' or zone has redirect rules, edit the existing rule
        if not existing_rule_to_edit:
            if coverage in ("all", "all_incoming") or len(existing_rules) == 1:
                existing_rule_to_edit = existing_rules[0]

    if existing_rule_to_edit and ruleset_id:
        target_source = source_hostname if source_hostname != "*" else (existing_rule_to_edit.source_hostname if existing_rule_to_edit.source_hostname != "*" else norm_source)
        return update_redirect_rule(
            zone_id=zone_id,
            ruleset_id=ruleset_id,
            rule_id=existing_rule_to_edit.id,
            source_hostname=target_source,
            destination_url=destination_url,
            coverage=coverage,
            status_code=status_code,
            preserve_path=preserve_path,
            preserve_query_string=preserve_query_string,
            enabled=enabled,
            description=description,
            dry_run=dry_run,
        )

    if dry_run:
        return {"dry_run": True, "action": "create", "payload": payload}

    if ruleset_id:
        endpoint = f"zones/{zone_id}/rulesets/{ruleset_id}/rules"
        response = cf_client.request("POST", endpoint, json_data=payload)
        session_audit.record(
            "CREATE_REDIRECT",
            norm_source,
            "SUCCESS",
            f"Mode: ALL INCOMING ({coverage}), Status: {status_code}, Path: {preserve_path}, Query: {preserve_query_string}"
        )
        return response
    else:
        endpoint = f"zones/{zone_id}/rulesets"
        ruleset_payload = {
            "name": "default",
            "kind": "zone",
            "phase": PHASE_DYNAMIC_REDIRECT,
            "rules": [payload]
        }
        response = cf_client.request("POST", endpoint, json_data=ruleset_payload)
        session_audit.record("CREATE_REDIRECT_NEW_RULESET", norm_source, "SUCCESS", f"Created ruleset with rule")
        return response


def update_redirect_rule(
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
) -> Dict[str, Any]:
    """Updates an existing Single Redirect rule using PATCH."""
    if not zone_id or not ruleset_id or not rule_id:
        raise ValidationError("Zone ID, Ruleset ID, dan Rule ID wajib diisi untuk pembaruan.")

    payload = build_all_incoming_payload(
        source_domain=source_hostname,
        destination_url=destination_url,
        coverage=coverage,
        status_code=status_code,
        preserve_path=preserve_path,
        preserve_query_string=preserve_query_string,
        enabled=enabled,
        description=description,
    )

    if dry_run:
        return {"dry_run": True, "action": "update", "rule_id": rule_id, "payload": payload}

    # Verify rule still exists
    _, rules = get_zone_redirect_ruleset(zone_id, zone_name=source_hostname if source_hostname != "*" else None)
    target_rule = next((r for r in rules if r.id == rule_id), None)
    if not target_rule:
        raise NotFoundError(f"Aturan dengan ID {rule_id} tidak ditemukan pada zona {zone_id}.")

    endpoint = f"zones/{zone_id}/rulesets/{ruleset_id}/rules/{rule_id}"
    response = cf_client.request("PATCH", endpoint, json_data=payload)
    session_audit.record(
        "UPDATE_REDIRECT",
        source_hostname,
        "SUCCESS",
        f"Rule ID: {rule_id}, Status: {status_code}, Path: {preserve_path}",
        rule_id=rule_id,
    )
    return response


def toggle_redirect_rule_status(
    zone_id: str,
    ruleset_id: str,
    rule_id: str,
    enabled: bool,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Enables or disables a redirect rule without changing its parameters."""
    if not zone_id or not ruleset_id or not rule_id:
        raise ValidationError("Zone ID, Ruleset ID, dan Rule ID wajib diisi.")

    if dry_run:
        return {"dry_run": True, "rule_id": rule_id, "enabled": enabled}

    endpoint = f"zones/{zone_id}/rulesets/{ruleset_id}/rules/{rule_id}"
    payload = {"enabled": enabled}
    response = cf_client.request("PATCH", endpoint, json_data=payload)
    status_str = "ENABLED" if enabled else "DISABLED"
    session_audit.record("TOGGLE_STATUS", rule_id, "SUCCESS", f"Rule {rule_id} -> {status_str}", rule_id=rule_id)
    return response


def delete_redirect_rule(
    zone_id: str,
    ruleset_id: str,
    rule_id: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Deletes a single redirect rule safely by its Rule ID.
    Re-verifies rule exists before deletion. Never deletes the entire ruleset!
    """
    if not zone_id or not ruleset_id or not rule_id:
        raise ValidationError("Zone ID, Ruleset ID, dan Rule ID wajib diisi untuk penghapusan.")

    if dry_run:
        return {"dry_run": True, "zone_id": zone_id, "rule_id": rule_id}

    # Verify rule still exists
    _, rules = get_zone_redirect_ruleset(zone_id)
    target_rule = next((r for r in rules if r.id == rule_id), None)
    if not target_rule:
        raise NotFoundError(f"Aturan dengan ID {rule_id} tidak ditemukan lagi pada zona {zone_id}. Mungkin sudah dihapus.")

    endpoint = f"zones/{zone_id}/rulesets/{ruleset_id}/rules/{rule_id}"
    response = cf_client.request("DELETE", endpoint)
    session_audit.record("DELETE_REDIRECT", target_rule.source_hostname, "SUCCESS", f"Rule ID: {rule_id}", rule_id=rule_id)
    return response
