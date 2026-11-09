"""Unit tests for in-memory multi-account session token lifecycle and audit logging.
"""

import pytest
from src.security.session import MultiAccountSessionManager
from src.utils.audit import SessionAuditLog


def test_multi_account_lifecycle():
    manager = MultiAccountSessionManager()
    assert not manager.is_connected
    assert manager.account_count == 0

    # Add Account 1
    acc1_id = manager.add_account("Akun Pribadi", "token_account_1_abcdef")
    assert manager.is_connected
    assert manager.account_count == 1
    assert manager.active_id == acc1_id
    assert manager.get_token() == "token_account_1_abcdef"

    # Add Account 2
    acc2_id = manager.add_account("Akun Bisnis", "token_account_2_123456")
    assert manager.account_count == 2
    # Active is still acc1 until switched
    assert manager.active_id == acc1_id

    # Switch to Account 2
    manager.switch_account(acc2_id)
    assert manager.active_id == acc2_id
    assert manager.get_token() == "token_account_2_123456"

    # Check token_for specific account
    assert manager.get_token_for(acc1_id) == "token_account_1_abcdef"
    assert manager.get_token_for(acc2_id) == "token_account_2_123456"

    # Remove single account
    manager.remove_account(acc2_id)
    assert manager.account_count == 1
    assert manager.active_id == acc1_id
    assert manager.get_token() == "token_account_1_abcdef"

    # Disconnect all & zero memory
    manager.disconnect_all()
    assert not manager.is_connected
    assert manager.account_count == 0
    assert manager.get_token() is None


def test_session_empty_token_rejection():
    manager = MultiAccountSessionManager()
    with pytest.raises(ValueError):
        manager.add_account("Test", "   ")


def test_session_audit_log_clean():
    audit = SessionAuditLog()
    audit.record("CREATE_REDIRECT", "example.com", "SUCCESS", "Created rule for test")
    entries = audit.get_entries()
    assert len(entries) == 1
    assert entries[0].target == "example.com"
    assert entries[0].status == "SUCCESS"

    # Ensure sensitive Bearer headers are masked if passed
    audit.record("API_CALL", "example.com", "FAILED", "Error with Bearer 1234567890abcdef1234567890abcdef")
    entries = audit.get_entries()
    assert len(entries) == 2
    assert "Bearer [REDACTED]" in entries[1].details

    csv_data = audit.export_csv()
    assert "CREATE_REDIRECT" in csv_data

    json_data = audit.export_json()
    assert "example.com" in json_data


def test_session_cleanup_on_exit():
    manager = MultiAccountSessionManager()
    manager.add_account("Akun Exit", "temporary_session_token_123")
    assert manager.is_connected
    # Simulate app exit
    manager.disconnect()
    assert not manager.is_connected
    assert manager.get_token() is None
