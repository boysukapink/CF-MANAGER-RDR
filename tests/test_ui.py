"""Test for UI MainWindow instantiation and theme toggling.
Uses PySide6 QTest or headless offscreen platform.
"""

import os
import pytest
from src.ui.main_window import MainWindow


def test_main_window_instantiation(qapp):
    window = MainWindow()
    assert window.windowTitle() == "Cloudflare Redirect Manager"
    assert window.stack.count() == 6

    # Test page switching
    window.switch_page("domains")
    assert window.stack.currentIndex() == 1

    window.switch_page("redirects")
    assert window.stack.currentIndex() == 2

    # Test theme toggle
    initial_theme = window.is_dark_theme
    window.toggle_theme()
    assert window.is_dark_theme != initial_theme
    window.toggle_theme()
    window.close()


def test_redirect_page_safe_zone_info_when_empty(qapp):
    from src.ui.redirect_page import RedirectPage

    page = RedirectPage()
    # When no zone is set
    zid, zname = page._get_current_zone_info()
    assert zid is None
    assert zname == ""

    # Ensure opening dialogs does not throw IndexError
    toast_messages = []
    page.show_toast.connect(lambda msg, err: toast_messages.append((msg, err)))

    page._open_add_dialog()
    assert len(toast_messages) == 1
    assert "Pilih zona" in toast_messages[0][0]

    page._open_delete_all_dialog()
    assert len(toast_messages) == 2
    assert "Pilih zona" in toast_messages[1][0]


def test_redirect_page_list_selection(qapp):
    from src.ui.redirect_page import RedirectPage
    from src.cloudflare.redirects import RedirectRule

    page = RedirectPage()
    # Add dummy rules
    rules = [
        RedirectRule(
            {
                "id": "rule_1",
                "enabled": True,
                "expression": 'http.host eq "example.com"',
                "action_parameters": {
                    "from_value": {
                        "status_code": 301,
                        "preserve_query_string": True,
                        "target_url": {"value": "https://target.com"},
                    }
                },
            },
            zone_id="zone_1",
            ruleset_id="rs_1",
        ),
        RedirectRule(
            {
                "id": "rule_2",
                "enabled": False,
                "expression": 'true',
                "action_parameters": {
                    "from_value": {
                        "status_code": 302,
                        "preserve_query_string": False,
                        "target_url": {"value": "https://target2.com"},
                    }
                },
            },
            zone_id="zone_1",
            ruleset_id="rs_1",
        ),
    ]

    page._on_redirects_loaded("rs_1", rules)
    assert page.table.rowCount() == 2

    # Test Select All in list
    page._toggle_select_all_clicked()
    selected = page._get_selected_rules()
    assert len(selected) == 2

    # Test Deselect All in list
    page._deselect_all()
    selected = page._get_selected_rules()
    assert len(selected) == 0


def test_redirect_form_dialog_defaults_301_and_all_incoming(qapp):
    from src.ui.redirect_page import RedirectFormDialog

    dlg = RedirectFormDialog(zone_name="example.com", zone_id="z1", existing_rule=None)
    assert dlg.cov_all.isChecked() is True
    assert dlg.status_301.isChecked() is True
    assert dlg.preserve_path_chk.isChecked() is False
    assert dlg.preserve_query_chk.isChecked() is True
    dlg.close()


def test_redirect_page_multi_account_columns_and_all_zones(qapp):
    from src.ui.redirect_page import RedirectPage
    from src.cloudflare.zones import ZoneItem
    from src.cloudflare.redirects import RedirectRule

    page = RedirectPage()
    # Check table column count: 9 columns (including "Akun CF" at column 2)
    assert page.table.columnCount() == 9
    assert page.table.horizontalHeaderItem(2).text() == "Akun CF"

    # Set mock zones from multiple accounts
    z1 = ZoneItem({"id": "z1", "name": "domain-cf1.com", "status": "active"}, account_id="acc1", account_label="CF Utama")
    z2 = ZoneItem({"id": "z2", "name": "domain-cf2.com", "status": "active"}, account_id="acc2", account_label="CF Cadangan")
    page.set_zones([z1, z2])

    # zone_combo should have 3 items: "Semua Domain (Gabung Semua Akun CF)", "domain-cf1.com", "domain-cf2.com"
    assert page.zone_combo.count() == 3
    assert page.zone_combo.itemData(0) == "all"
    assert "CF Utama" in page.zone_combo.itemText(1)
    assert "CF Cadangan" in page.zone_combo.itemText(2)

    # Load redirect rules with account information
    r1 = RedirectRule(
        {
            "id": "r1",
            "enabled": True,
            "expression": "true",
            "action_parameters": {
                "from_value": {
                    "status_code": 301,
                    "target_url": {"value": "https://dest1.com"},
                }
            },
        },
        zone_id="z1",
        ruleset_id="rs1",
        zone_name="domain-cf1.com",
        account_id="acc1",
        account_label="CF Utama",
    )
    r2 = RedirectRule(
        {
            "id": "r2",
            "enabled": True,
            "expression": "true",
            "action_parameters": {
                "from_value": {
                    "status_code": 301,
                    "target_url": {"value": "https://dest2.com"},
                }
            },
        },
        zone_id="z2",
        ruleset_id="rs2",
        zone_name="domain-cf2.com",
        account_id="acc2",
        account_label="CF Cadangan",
    )

    page._on_redirects_loaded("rs_all", [r1, r2])
    assert page.table.rowCount() == 2
    # Check column 2 has the account label
    assert "CF Utama" in page.table.item(0, 2).text()
    assert "CF Cadangan" in page.table.item(1, 2).text()
    page.close()



