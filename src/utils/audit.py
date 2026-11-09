"""In-memory session audit logger.
Keeps track of actions during the active session.
Never stores tokens, authorization headers, or sensitive secrets.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import csv
import io
import json
from src.config import settings
from src.utils.errors import sanitize_message


class AuditLogEntry:
    def __init__(self, action: str, target: str, status: str, details: str = "", rule_id: Optional[str] = None):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.action = action
        self.target = target
        self.status = status
        self.details = details
        self.rule_id = rule_id or "-"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "target": self.target,
            "status": self.status,
            "rule_id": self.rule_id,
            "details": self.details
        }


class SessionAuditLog:
    """Stores audit entries in-memory only for the duration of the current session."""
    def __init__(self):
        self._entries: List[AuditLogEntry] = []

    def record(self, action: str, target: str, status: str, details: str = "", rule_id: Optional[str] = None):
        # Ensure no token leaks into details
        clean_details = sanitize_message(details)
        if len(self._entries) >= settings.MAX_AUDIT_LOG_ENTRIES:
            self._entries.pop(0)
        entry = AuditLogEntry(action, target, status, clean_details, rule_id)
        self._entries.append(entry)

    def get_entries(self) -> List[AuditLogEntry]:
        return list(self._entries)

    def clear(self):
        """Clears all audit log entries."""
        self._entries.clear()

    def export_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Action", "Target", "Status", "Rule ID", "Details"])
        for e in self._entries:
            writer.writerow([e.timestamp, e.action, e.target, e.status, e.rule_id, e.details])
        return output.getvalue()

    def export_json(self) -> str:
        return json.dumps([e.to_dict() for e in self._entries], indent=2)


# Global in-memory audit log instance
session_audit = SessionAuditLog()
