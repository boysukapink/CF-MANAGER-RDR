"""Unit tests for Bulk Redirect features.
Tests BulkRedirectDialog, line parsing, and bulk worker execution.
"""

import os
import pytest
from src.cloudflare.zones import ZoneItem
from src.ui.bulk_dialog import BulkRedirectDialog
from src.ui.workers import (
    BulkCreateRedirectsWorker,
    BulkDeleteRedirectsWorker,
    BulkToggleRedirectsWorker,
)


def test_bulk_dialog_instantiation(qapp):
    z1 = ZoneItem({"id": "zone1", "name": "example1.com", "status": "active", "plan": {"name": "Free"}}, account_label="Acc 1")
    z2 = ZoneItem({"id": "zone2", "name": "example2.com", "status": "active", "plan": {"name": "Pro"}}, account_label="Acc 2")

    dlg = BulkRedirectDialog(zones=[z1, z2], preselected_zone_ids=["zone1"])
    assert dlg.windowTitle().startswith("⚡ Bulk Redirect Manager")
    assert dlg.tab1_table.rowCount() == 2
    assert dlg.tab1_table.cellWidget(0, 0).isChecked() is True
    assert dlg.tab1_table.cellWidget(1, 0).isChecked() is False
    dlg.close()


def test_bulk_text_parser(qapp):
    z1 = ZoneItem({"id": "z1", "name": "situslama.com", "status": "active", "plan": {"name": "Free"}})
    z2 = ZoneItem({"id": "z2", "name": "tokobaru.net", "status": "active", "plan": {"name": "Free"}})

    dlg = BulkRedirectDialog(zones=[z1, z2])

    input_text = """
    # Komentar
    situslama.com -> https://situstujuan.com/ 301
    tokobaru.net,https://tujuanbaru.com/,302
    unknownzone.com -> https://tujuan.com/
    invalid-line-here
    """
    dlg.tab2_text.setPlainText(input_text)
    dlg._parse_tab2_text()

    assert len(dlg.tab2_parsed_items) == 4
    # First item valid 301
    assert dlg.tab2_parsed_items[0]["valid"] is True
    assert dlg.tab2_parsed_items[0]["status_code"] == 301
    assert dlg.tab2_parsed_items[0]["destination"] == "https://situstujuan.com/"

    # Second item valid 302
    assert dlg.tab2_parsed_items[1]["valid"] is True
    assert dlg.tab2_parsed_items[1]["status_code"] == 302

    # Third item: unknown zone
    assert dlg.tab2_parsed_items[2]["valid"] is False
    assert "tidak ditemukan" in dlg.tab2_parsed_items[2]["reason"].lower()

    # Fourth item: invalid line
    assert dlg.tab2_parsed_items[3]["valid"] is False

    dlg.close()


def test_bulk_text_parser_with_default_destination(qapp):
    z1 = ZoneItem({"id": "z1", "name": "situslama.com", "status": "active", "plan": {"name": "Free"}})
    z2 = ZoneItem({"id": "z2", "name": "tokobaru.net", "status": "active", "plan": {"name": "Free"}})

    dlg = BulkRedirectDialog(zones=[z1, z2])
    dlg.tab2_default_dest.setText("https://situstarget.com/")
    dlg.tab2_default_code_301.setChecked(True)

    input_text = """
    situslama.com
    tokobaru.net
    """
    dlg.tab2_text.setPlainText(input_text)
    dlg._parse_tab2_text()

    assert len(dlg.tab2_parsed_items) == 2
    assert dlg.tab2_parsed_items[0]["valid"] is True
    assert dlg.tab2_parsed_items[0]["destination"] == "https://situstarget.com/"
    assert dlg.tab2_parsed_items[0]["status_code"] == 301

    assert dlg.tab2_parsed_items[1]["valid"] is True
    assert dlg.tab2_parsed_items[1]["destination"] == "https://situstarget.com/"
    assert dlg.tab2_parsed_items[1]["status_code"] == 301
    dlg.close()


def test_auto_format_tab2_text(qapp):
    z1 = ZoneItem({"id": "z1", "name": "situslama.com", "status": "active", "plan": {"name": "Free"}})
    dlg = BulkRedirectDialog(zones=[z1])
    dlg.tab2_default_dest.setText("https://target.com/")
    dlg.tab2_default_code_302.setChecked(True)

    dlg.tab2_text.setPlainText("situslama.com")
    dlg._auto_format_tab2_text()

    assert "situslama.com -> https://target.com/ 302" in dlg.tab2_text.toPlainText()
    assert dlg.tab2_parsed_items[0]["valid"] is True
    dlg.close()


def test_bulk_create_worker_execution(qapp, monkeypatch):
    calls = []

    def mock_create(*args, **kwargs):
        calls.append(kwargs)
        return {"success": True}

    monkeypatch.setattr("src.ui.workers.create_redirect_rule", mock_create)

    items = [
        {
            "zone_id": "z1",
            "source_hostname": "site1.com",
            "destination_url": "https://dest.com/",
            "coverage": "both",
            "status_code": 302,
        },
        {
            "zone_id": "z2",
            "source_hostname": "site2.com",
            "destination_url": "https://dest2.com/",
            "coverage": "both",
            "status_code": 301,
        },
    ]

    worker = BulkCreateRedirectsWorker(items)
    result = None

    def on_finished(res):
        nonlocal result
        result = res

    worker.finished.connect(on_finished)
    worker.run()

    assert result is not None
    assert result["success"] == 2
    assert result["failed"] == 0
    assert len(calls) == 2


def test_delete_all_dialog_instantiation(qapp):
    from src.cloudflare.redirects import RedirectRule
    from src.ui.delete_all_dialog import DeleteAllRedirectsDialog

    raw_rule = {
        "id": "rule_1",
        "description": "Rule 1",
        "enabled": True,
        "expression": "true",
        "action_parameters": {
            "from_value": {
                "status_code": 301,
                "target_url": {"value": "https://target.com/"}
            }
        }
    }
    r = RedirectRule(raw_rule, zone_id="z1", ruleset_id="rs1")
    dlg = DeleteAllRedirectsDialog(
        zone_name="domainku.com",
        zone_id="z1",
        current_rules=[r],
    )
    assert dlg.table.rowCount() == 1
    assert dlg.table.columnCount() == 7
    assert "301" in dlg.table.item(0, 5).text()
    dlg.close()


def test_bulk_purge_worker_execution(qapp, monkeypatch):
    from src.ui.workers import BulkPurgeRedirectsWorker
    from src.cloudflare.redirects import RedirectRule

    deleted_ids = []

    def mock_get_ruleset(zone_id):
        r1 = RedirectRule({
            "id": "r1",
            "expression": "true",
            "action": "redirect",
            "action_parameters": {"from_value": {"status_code": 301, "target_url": {"value": "https://a.com"}}}
        }, zone_id=zone_id, ruleset_id="rs1")
        r2 = RedirectRule({
            "id": "r2",
            "expression": "true",
            "action": "redirect",
            "action_parameters": {"from_value": {"status_code": 302, "target_url": {"value": "https://b.com"}}}
        }, zone_id=zone_id, ruleset_id="rs1")
        return "rs1", [r1, r2]

    def mock_delete(zone_id, ruleset_id, rule_id):
        deleted_ids.append(rule_id)
        return {"success": True}

    monkeypatch.setattr("src.ui.workers.get_zone_redirect_ruleset", mock_get_ruleset)
    monkeypatch.setattr("src.ui.workers.delete_redirect_rule", mock_delete)

    # Test purging only 301
    worker = BulkPurgeRedirectsWorker(
        zone_items=[{"zone_id": "z1", "zone_name": "example.com"}],
        status_filter=301,
    )
    res_301 = None
    worker.finished.connect(lambda res: setattr(worker, "res", res))
    worker.run()
    assert worker.res["success"] == 1
    assert "r1" in deleted_ids
    assert "r2" not in deleted_ids
