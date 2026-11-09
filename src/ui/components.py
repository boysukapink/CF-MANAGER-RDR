"""Reusable UI components for Cloudflare Redirect Manager.
Designed with Linear/Cloudflare-tier aesthetics and compact responsive geometry.
"""

from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QDialog,
    QPushButton,
)
from PySide6.QtCore import Qt, QTimer


class StatCard(QFrame):
    """Modern dashboard stat card with clean typography and subtle border."""

    def __init__(self, title: str, value: str = "0", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setStyleSheet("""
            QFrame.card {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame.card:hover {
                border-color: #334155;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.5px;"
        )
        layout.addWidget(self.title_lbl)

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: #F8FAFC; font-family: -apple-system, Segoe UI, sans-serif;"
        )
        layout.addWidget(self.value_lbl)

        if subtitle:
            self.sub_lbl = QLabel(subtitle)
            self.sub_lbl.setStyleSheet("color: #64748B; font-size: 11px; margin-top: 2px;")
            layout.addWidget(self.sub_lbl)
        else:
            self.sub_lbl = None

    def set_value(self, value: str):
        self.value_lbl.setText(value)

    def set_subtitle(self, subtitle: str):
        if self.sub_lbl:
            self.sub_lbl.setText(subtitle)


class StatusBadge(QLabel):
    """Pill badge showing connection or resource status with dot indicator."""

    def __init__(self, text: str, status_type: str = "disconnected", parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_status(status_type, text)

    def set_status(self, status_type: str, text: str):
        st = status_type.lower()
        # Add dot indicator if not already present
        display_text = text
        if display_text.startswith("● ") or display_text.startswith("○ "):
            pass
        elif st in ("active", "connected", "success"):
            display_text = f"● {text}"
        elif st in ("pending", "initializing"):
            display_text = f"● {text}"
        elif st in ("disconnected", "error", "inactive", "moved"):
            display_text = f"○ {text}"

        self.setText(display_text)

        if st in ("active", "connected", "success"):
            self.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.12);
                color: #34D399;
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 11px;
                padding: 3px 10px;
                font-weight: 600;
                font-size: 11px;
            """)
        elif st in ("pending", "initializing", "warning"):
            self.setStyleSheet("""
                background-color: rgba(245, 158, 11, 0.12);
                color: #FBBF24;
                border: 1px solid rgba(245, 158, 11, 0.35);
                border-radius: 11px;
                padding: 3px 10px;
                font-weight: 600;
                font-size: 11px;
            """)
        elif st in ("301", "permanent"):
            self.setStyleSheet("""
                background-color: rgba(6, 182, 212, 0.12);
                color: #38BDF8;
                border: 1px solid rgba(6, 182, 212, 0.35);
                border-radius: 11px;
                padding: 2px 8px;
                font-weight: 600;
                font-size: 11px;
                font-family: Consolas, monospace;
            """)
        elif st in ("302", "temporary"):
            self.setStyleSheet("""
                background-color: rgba(243, 128, 32, 0.12);
                color: #FB923C;
                border: 1px solid rgba(243, 128, 32, 0.35);
                border-radius: 11px;
                padding: 2px 8px;
                font-weight: 600;
                font-size: 11px;
                font-family: Consolas, monospace;
            """)
        else:  # disconnected, error, inactive
            self.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.12);
                color: #F87171;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 11px;
                padding: 3px 10px;
                font-weight: 600;
                font-size: 11px;
            """)


class DangerConfirmDialog(QDialog):
    """Confirmation modal for destructive actions like deleting redirects."""

    def __init__(
        self,
        title: str,
        message: str,
        details: str = "",
        confirm_btn_text: str = "Hapus Redirect",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setMaximumWidth(520)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        warn_icon = QLabel("⚠️")
        warn_icon.setStyleSheet("font-size: 18px;")
        header_layout.addWidget(warn_icon)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #EF4444;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("font-size: 12px; color: #E2E8F0; line-height: 1.4;")
        layout.addWidget(msg_lbl)

        if details:
            details_frame = QFrame()
            details_frame.setStyleSheet("""
                background-color: #090D16;
                border: 1px solid #1E293B;
                border-radius: 6px;
                padding: 8px 12px;
            """)
            det_layout = QVBoxLayout(details_frame)
            det_layout.setContentsMargins(8, 8, 8, 8)
            det_lbl = QLabel(details)
            det_lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; color: #94A3B8;")
            det_lbl.setWordWrap(True)
            det_layout.addWidget(det_lbl)
            layout.addWidget(details_frame)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Batal")
        cancel_btn.setProperty("class", "btn-secondary")
        cancel_btn.setMinimumHeight(32)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton(confirm_btn_text)
        confirm_btn.setProperty("class", "btn-danger")
        confirm_btn.setMinimumHeight(32)
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)


class ToastNotification(QFrame):
    """Floating banner notification for feedback."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hide()
        self.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 14px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self.icon_lbl = QLabel("✓")
        self.icon_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #10B981;")
        layout.addWidget(self.icon_lbl)

        self.msg_lbl = QLabel("")
        self.msg_lbl.setStyleSheet("color: #F8FAFC; font-weight: 500; font-size: 12px;")
        layout.addWidget(self.msg_lbl)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, message: str, is_error: bool = False, duration_ms: int = 4000):
        self.msg_lbl.setText(message)
        if is_error:
            self.icon_lbl.setText("✕")
            self.icon_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #F87171;")
            self.setStyleSheet("""
                QFrame {
                    background-color: #1A0F14;
                    border: 1px solid #EF4444;
                    border-radius: 8px;
                    padding: 8px 14px;
                }
            """)
        else:
            self.icon_lbl.setText("✓")
            self.icon_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #34D399;")
            self.setStyleSheet("""
                QFrame {
                    background-color: #0A1916;
                    border: 1px solid #10B981;
                    border-radius: 8px;
                    padding: 8px 14px;
                }
            """)
        self.adjustSize()
        if self.parent():
            x = self.parent().width() - self.width() - 24
            y = 16
            self.move(max(10, x), y)
        self.show()
        self.raise_()
        self._timer.start(duration_ms)
