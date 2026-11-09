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


def test_bulk_double_check_dialog_prevents_similar_domains(qapp):
    from src.ui.bulk_dialog import BulkDoubleCheckDialog
    from PySide6.QtWidgets import QCheckBox

    items = [
        {"source_hostname": "domainbaru.com", "destination_url": "https://target.com", "status_code": 301, "zone_id": "z1"},
        {"source_hostname": "top-domainbaru.com", "destination_url": "https://target.com", "status_code": 301, "zone_id": "z2"},
    ]
    dlg = BulkDoubleCheckDialog(items)
    assert dlg.table.rowCount() == 2

    # Uncheck row 1 (top-domainbaru.com)
    chk_top = dlg.table.cellWidget(1, 0)
    assert isinstance(chk_top, QCheckBox)
    chk_top.setChecked(False)

    # Confirm
    dlg._on_confirm()
    assert len(dlg.confirmed_items) == 1
    assert dlg.confirmed_items[0]["source_hostname"] == "domainbaru.com"
    dlg.close()


def test_bulk_result_dialog_shows_failed_domains(qapp):
    from src.ui.bulk_dialog import BulkResultDialog

    summary = {
        "success": 1,
        "failed": 2,
        "errors": ["domainerror1.com: Missing DNS", "domainerror2.com: Zone not found"],
        "failed_items": [
            {"source": "domainerror1.com", "account_label": "CF 1", "error": "Missing DNS A/CNAME record"},
            {"source": "domainerror2.com", "account_label": "CF 2", "error": "Zone not found"},
        ],
        "success_items": [
            {"source": "domainsukses.com", "destination": "https://target.com"}
        ]
    }
    dlg = BulkResultDialog(summary)
    assert dlg.fail_table.rowCount() == 2
    assert dlg.fail_table.item(0, 1).text() == "domainerror1.com"
    assert "Missing DNS" in dlg.fail_table.item(0, 3).text()
    assert dlg.fail_table.item(1, 1).text() == "domainerror2.com"
    dlg.close()


def test_bulk_tab1_exact_match_filter(qapp):
    from src.cloudflare.zones import ZoneItem
    from src.ui.bulk_dialog import BulkRedirectDialog

    z1 = ZoneItem({"id": "z1", "name": "domainbaru.com", "status": "active"})
    z2 = ZoneItem({"id": "z2", "name": "top-domainbaru.com", "status": "active"})
    dlg = BulkRedirectDialog(zones=[z1, z2])

    # Default substring filter: searching "domainbaru.com" matches both
    dlg.tab1_exact_chk.setChecked(False)
    dlg._filter_tab1_table("domainbaru.com")
    assert dlg.tab1_table.isRowHidden(0) is False
    assert dlg.tab1_table.isRowHidden(1) is False

    # Exact match filter enabled: only matches "domainbaru.com" exactly!
    dlg.tab1_exact_chk.setChecked(True)
    dlg._filter_tab1_table("domainbaru.com")
    assert dlg.tab1_table.isRowHidden(0) is False
    assert dlg.tab1_table.isRowHidden(1) is True  # top-domainbaru.com is hidden!
    dlg.close()

