"""Unit tests for ALL INCOMING redirect rule building, coverage, modes, simulations, and mutations.
"""

import pytest
from src.cloudflare.redirects import (
    build_all_incoming_payload,
    build_rule_payload,
    create_redirect_rule,
    update_redirect_rule,
    toggle_redirect_rule_status,
)
from src.cloudflare.zones import find_matching_zone, ZoneItem
from src.security.validation import simulate_redirect, build_all_incoming_expression


def test_build_all_incoming_both_coverage():
    payload = build_all_incoming_payload(
        source_domain="domainlama.com",
        destination_url="https://domainbaru.com/",
        coverage="both",
        status_code=301,
        preserve_path=True,
        preserve_query_string=True,
        enabled=True,
    )

    assert payload["action"] == "redirect"
    assert payload["enabled"] is True
    assert payload["expression"] == '(http.host eq "domainlama.com" or http.host eq "www.domainlama.com")'
    
    from_val = payload["action_parameters"]["from_value"]
    assert from_val["status_code"] == 301
    assert from_val["preserve_query_string"] is True
    assert "value" in from_val["target_url"]
    assert from_val["target_url"]["value"] == "https://domainbaru.com/"
    assert "expression" not in from_val["target_url"]


def test_build_all_incoming_specific_file_target_no_trailing_slash():
    # When target URL points to a specific file like habanero.html,
    # it must use static "value" (no concat / trailing slash) even if preserve_path=True
    payload = build_all_incoming_payload(
        source_domain="gacor77oficial.com",
        destination_url="https://linkrtpgacor77.com/habanero.html",
        coverage="both",
        status_code=301,
        preserve_path=True,
        preserve_query_string=True,
    )
    from_val = payload["action_parameters"]["from_value"]
    assert from_val["status_code"] == 301
    assert "value" in from_val["target_url"]
    assert from_val["target_url"]["value"] == "https://linkrtpgacor77.com/habanero.html"
    assert "expression" not in from_val["target_url"]


def test_simulate_redirect_specific_file_target_no_trailing_slash():
    # User's case: gacor77oficial.com -> https://linkrtpgacor77.com/habanero.html
    # Visiting https://gacor77oficial.com must redirect to https://linkrtpgacor77.com/habanero.html (NOT .html/)
    matched, out_url, _ = simulate_redirect(
        incoming_url="https://gacor77oficial.com",
        source_domain="gacor77oficial.com",
        destination_url="https://linkrtpgacor77.com/habanero.html",
        coverage="both",
        preserve_path=True,
        preserve_query=True,
    )
    assert matched is True
    assert out_url == "https://linkrtpgacor77.com/habanero.html"

    # Even with incoming path /subpath, file target must redirect directly to the file
    matched2, out_url2, _ = simulate_redirect(
        incoming_url="https://gacor77oficial.com/anything/else",
        source_domain="gacor77oficial.com",
        destination_url="https://linkrtpgacor77.com/habanero.html",
        coverage="both",
        preserve_path=True,
        preserve_query=False,
    )
    assert matched2 is True
    assert out_url2 == "https://linkrtpgacor77.com/habanero.html"


def test_build_all_incoming_apex_only():
    payload = build_all_incoming_payload(
        source_domain="domainlama.com",
        destination_url="https://domainbaru.com",
        coverage="apex",
        status_code=302,
        preserve_path=False,
        preserve_query_string=False,
    )

    assert payload["expression"] == 'http.host eq "domainlama.com"'
    from_val = payload["action_parameters"]["from_value"]
    assert from_val["status_code"] == 302
    assert from_val["preserve_query_string"] is False
    assert from_val["target_url"]["value"] == "https://domainbaru.com/"


def test_build_all_incoming_www_only():
    payload = build_all_incoming_payload(
        source_domain="domainlama.com",
        destination_url="https://domainbaru.com",
        coverage="www",
        status_code=301,
        preserve_path=True,
        preserve_query_string=False,
    )

    assert payload["expression"] == 'http.host eq "www.domainlama.com"'
    from_val = payload["action_parameters"]["from_value"]
    assert from_val["preserve_query_string"] is False
    assert from_val["target_url"]["value"] == "https://domainbaru.com/"
    assert "expression" not in from_val["target_url"]


def test_build_all_incoming_all_requests_coverage():
    payload = build_all_incoming_payload(
        source_domain="domainlama.com",
        destination_url="https://domainbaru.com/",
        coverage="all",
        status_code=301,
        preserve_path=True,
        preserve_query_string=True,
    )
    assert payload["expression"] == "true"
    assert "All incoming requests" in payload["description"]
    assert payload["action_parameters"]["from_value"]["status_code"] == 301


def test_update_redirect_rule_dry_run():
    res = update_redirect_rule(
        zone_id="zone123",
        ruleset_id="ruleset456",
        rule_id="rule789",
        source_hostname="mysite.com",
        destination_url="https://newtarget.com",
        coverage="both",
        status_code=301,
        preserve_path=True,
        preserve_query_string=True,
        dry_run=True,
    )
    assert res["dry_run"] is True
    assert res["rule_id"] == "rule789"
    assert res["payload"]["action_parameters"]["from_value"]["status_code"] == 301


def test_toggle_redirect_rule_status_dry_run():
    res = toggle_redirect_rule_status("zone123", "ruleset456", "rule789", enabled=False, dry_run=True)
    assert res["dry_run"] is True
    assert res["enabled"] is False


def test_simulate_redirect_all_paths():
    # 1. Homepage with preserve path
    matched, out_url, _ = simulate_redirect(
        incoming_url="https://domainlama.com/",
        source_domain="domainlama.com",
        destination_url="https://domainbaru.com",
        coverage="both",
        preserve_path=True,
        preserve_query=True,
    )
    assert matched is True
    assert out_url == "https://domainbaru.com/"

    # 2. Sub-path /promo?id=123 with Preserve Path & Query ON
    matched, out_url, _ = simulate_redirect(
        incoming_url="https://domainlama.com/promo?id=123",
        source_domain="domainlama.com",
        destination_url="https://domainbaru.com",
        coverage="both",
        preserve_path=True,
        preserve_query=True,
    )
    assert matched is True
    assert out_url == "https://domainbaru.com/promo?id=123"

    # 3. Sub-path /promo?id=123 with Preserve Path & Query OFF
    matched, out_url, _ = simulate_redirect(
        incoming_url="https://domainlama.com/promo?id=123",
        source_domain="domainlama.com",
        destination_url="https://domainbaru.com",
        coverage="both",
        preserve_path=False,
        preserve_query=False,
    )
    assert matched is True
    assert out_url == "https://domainbaru.com/"

    # 4. WWW matching when coverage is 'both'
    matched, out_url, _ = simulate_redirect(
        incoming_url="https://www.domainlama.com/login",
        source_domain="domainlama.com",
        destination_url="https://domainbaru.com",
        coverage="both",
        preserve_path=True,
        preserve_query=False,
    )
    assert matched is True
    assert out_url == "https://domainbaru.com/login"

    # 5. WWW rejected when coverage is 'apex'
    matched, _, desc = simulate_redirect(
        incoming_url="https://www.domainlama.com/login",
        source_domain="domainlama.com",
        destination_url="https://domainbaru.com",
        coverage="apex",
        preserve_path=True,
        preserve_query=False,
    )
    assert matched is False
    assert "tidak cocok" in desc


def test_find_matching_zone_most_specific():
    zones = [
        ZoneItem({"id": "z1", "name": "example.com", "status": "active"}),
        ZoneItem({"id": "z2", "name": "sub.example.com", "status": "active"}),
        ZoneItem({"id": "z3", "name": "other.org", "status": "active"}),
    ]

    match = find_matching_zone("app.sub.example.com", zones)
    assert match is not None
    assert match.id == "z2"

    match2 = find_matching_zone("blog.example.com", zones)
    assert match2 is not None
    assert match2.id == "z1"


def test_create_redirect_rule_defaults_to_301_and_all_incoming(monkeypatch):
    monkeypatch.setattr("src.cloudflare.redirects.get_zone_redirect_ruleset", lambda zid, zone_name=None: (None, []))
    res = create_redirect_rule(
        zone_id="zone_empty",
        source_hostname="mysite.com",
        destination_url="https://target.com",
        dry_run=True,
    )
    assert res["dry_run"] is True
    assert res["action"] == "create"
    payload = res["payload"]
    assert payload["expression"] == "true"
    assert payload["action_parameters"]["from_value"]["status_code"] == 301
    assert payload["action_parameters"]["from_value"]["target_url"]["value"] == "https://target.com/"


def test_create_redirect_rule_edits_existing_rule_instead_of_duplicate(monkeypatch):
    from src.cloudflare.redirects import RedirectRule
    old_rule = RedirectRule(
        {
            "id": "rule_old_123",
            "expression": "true",
            "action": "redirect",
            "action_parameters": {
                "from_value": {
                    "status_code": 301,
                    "target_url": {"value": "https://oldtarget.com/"},
                }
            },
        },
        zone_id="zone_with_existing",
        ruleset_id="ruleset_abc",
    )

    def mock_get_ruleset(zid, zone_name=None):
        return "ruleset_abc", [old_rule]

    monkeypatch.setattr("src.cloudflare.redirects.get_zone_redirect_ruleset", mock_get_ruleset)

    # Calling create_redirect_rule on a zone that already has a rule must EDIT the old rule
    res = create_redirect_rule(
        zone_id="zone_with_existing",
        source_hostname="mysite.com",
        destination_url="https://newtarget.com",
        dry_run=True,
    )

    assert res["dry_run"] is True
    assert res["action"] == "update"
    assert res["rule_id"] == "rule_old_123"
    assert res["payload"]["expression"] == "true"
    assert res["payload"]["action_parameters"]["from_value"]["status_code"] == 301
    assert res["payload"]["action_parameters"]["from_value"]["target_url"]["value"] == "https://newtarget.com/"

