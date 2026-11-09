"""Dashboard page for Cloudflare Redirect Manager.
Displays high-level metrics, connection status, and session activity.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from src.security.session import active_session
from src.utils.audit import session_audit
from src.ui.components import StatCard, StatusBadge


class DashboardPage(QWidget):
    """Main dashboard displaying session metrics and audit activity."""

    navigate_to = Signal(str)  # page_name
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # Top Bar
        top_bar = QHBoxLayout()
        header_title = QLabel("Overview")
        header_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC;")
        top_bar.addWidget(header_title)
        top_bar.addStretch()

        self.quick_bulk_btn = QPushButton("⚡ Bulk Redirects")
        self.quick_bulk_btn.setProperty("class", "btn-neon-cyan")
        self.quick_bulk_btn.clicked.connect(lambda: self.navigate_to.emit("redirects"))
        top_bar.addWidget(self.quick_bulk_btn)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setProperty("class", "btn-secondary")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        top_bar.addWidget(self.refresh_btn)

        layout.addLayout(top_bar)

        # Connection Banner Card
        self.conn_banner = QFrame()
        self.conn_banner.setProperty("class", "card")
        banner_layout = QHBoxLayout(self.conn_banner)
        banner_layout.setContentsMargins(18, 14, 18, 14)
        banner_layout.setSpacing(14)

        conn_info_layout = QVBoxLayout()
        conn_info_layout.setSpacing(2)
        self.banner_title = QLabel("Cloudflare API Connection")
        self.banner_title.setStyleSheet("font-weight: 700; font-size: 14px; color: #F8FAFC;")
        self.banner_sub = QLabel("Belum terhubung ke Cloudflare API. Silakan masukkan token API.")
        self.banner_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        conn_info_layout.addWidget(self.banner_title)
        conn_info_layout.addWidget(self.banner_sub)
        banner_layout.addLayout(conn_info_layout)

        banner_layout.addStretch()

        self.conn_badge = StatusBadge("Disconnected", "disconnected")
        banner_layout.addWidget(self.conn_badge)

        self.connect_nav_btn = QPushButton("Hubungkan Akun")
        self.connect_nav_btn.setProperty("class", "btn-primary")
        self.connect_nav_btn.clicked.connect(lambda: self.navigate_to.emit("connect"))
        banner_layout.addWidget(self.connect_nav_btn)

        layout.addWidget(self.conn_banner)

        # Stat Cards Grid (4 columns)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        self.accounts_card = StatCard("Akun Cloudflare", "0", "Total akun di sesi")
        stats_layout.addWidget(self.accounts_card)

        self.domains_card = StatCard("Domain Terhubung", "0", "Total zona aktif di akun")
        stats_layout.addWidget(self.domains_card)

        self.redirects_card = StatCard("Redirect Aturan", "0", "Single Redirects terpasang")
        stats_layout.addWidget(self.redirects_card)

        self.activity_card = StatCard("Aktivitas Sesi", "0", "Tindakan API sesi saat ini")
        stats_layout.addWidget(self.activity_card)

        layout.addLayout(stats_layout)

        # Session Activity Table Section
        activity_section = QVBoxLayout()
        activity_section.setSpacing(8)

        act_title_row = QHBoxLayout()
        act_title = QLabel("Riwayat Aktivitas Sesi Ini")
        act_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F8FAFC;")
        act_title_row.addWidget(act_title)
        act_title_row.addStretch()

        act_note = QLabel("Data aktivitas hanya tersimpan di RAM selama aplikasi terbuka")
        act_note.setStyleSheet("font-size: 11px; color: #64748B;")
        act_title_row.addWidget(act_note)
        activity_section.addLayout(act_title_row)

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(5)
        self.activity_table.setHorizontalHeaderLabels([
            "Waktu", "Tindakan", "Target Domain", "Status", "Detail"
        ])
        act_header = self.activity_table.horizontalHeader()
        act_header.setMinimumSectionSize(60)
        act_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        act_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        act_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        act_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        act_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.activity_table.setColumnWidth(2, 140)
        self.activity_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.activity_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.activity_table.verticalHeader().setDefaultSectionSize(28)
        self.activity_table.setMinimumHeight(200)
        activity_section.addWidget(self.activity_table)

        layout.addLayout(activity_section)

        scroll.setWidget(scroll_widget)
        root_layout.addWidget(scroll)

    def update_metrics(self, domains_count: int, redirects_count: int):
        self.accounts_card.set_value(str(active_session.account_count))
        self.domains_card.set_value(str(domains_count))
        self.redirects_card.set_value(str(redirects_count))
        self.update_activity_table()

    def update_activity_table(self):
        entries = session_audit.get_entries()
        self.activity_card.set_value(str(len(entries)))
        self.activity_table.setRowCount(len(entries))

        mono_font = QFont("Consolas", 9)

        for row, e in enumerate(reversed(entries)):
            item_time = QTableWidgetItem(e.timestamp)
            item_time.setFont(mono_font)
            item_time.setForeground(QColor("#94A3B8"))
            self.activity_table.setItem(row, 0, item_time)

            item_act = QTableWidgetItem(e.action)
            item_act.setForeground(QColor("#F8FAFC"))
            self.activity_table.setItem(row, 1, item_act)

            item_target = QTableWidgetItem(e.target)
            item_target.setFont(mono_font)
            item_target.setForeground(QColor("#38BDF8"))
            self.activity_table.setItem(row, 2, item_target)

            item_status = QTableWidgetItem(e.status)
            if e.status.lower() in ("success", "ok", "berhasil"):
                item_status.setForeground(QColor("#34D399"))
            elif e.status.lower() in ("error", "failed", "gagal"):
                item_status.setForeground(QColor("#F87171"))
            else:
                item_status.setForeground(QColor("#94A3B8"))
            self.activity_table.setItem(row, 3, item_status)

            item_det = QTableWidgetItem(e.details)
            item_det.setForeground(QColor("#94A3B8"))
            self.activity_table.setItem(row, 4, item_det)

    def update_connection_state(self, is_connected: bool):
        if is_connected:
            acc_count = active_session.account_count
            self.conn_badge.set_status("connected", f"Connected ({acc_count} Akun)")
            acc = active_session.active_account
            acc_label = acc.label if acc else "Cloudflare"
            last_conn = active_session.last_connected_at or "Sesi ini"
            self.banner_sub.setText(f"Akun Aktif: {acc_label}  •  Terhubung: {last_conn}  •  Total: {acc_count} Akun")
            self.connect_nav_btn.setText("Kelola Akun")
            self.accounts_card.set_value(str(acc_count))
        else:
            self.conn_badge.set_status("disconnected", "Disconnected")
            self.banner_sub.setText("Belum terhubung ke Cloudflare API. Silakan masukkan token API.")
            self.connect_nav_btn.setText("Hubungkan Akun")
            self.accounts_card.set_value("0")
            self.domains_card.set_value("0")
            self.redirects_card.set_value("0")
        self.update_activity_table()
