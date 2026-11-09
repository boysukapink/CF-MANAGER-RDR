"""Domain Manager Page (Multi-Account Enabled).
Displays accessible Cloudflare zones with account filter, search, and bulk selection.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QProgressBar,
    QCheckBox,
    QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from src.cloudflare.zones import ZoneItem
from src.security.session import active_session
from src.ui.workers import FetchZonesWorker
from src.ui.bulk_dialog import BulkRedirectDialog


class DomainPage(QWidget):
    """Page for viewing and searching Cloudflare zones across multiple accounts."""

    view_redirects_for_zone = Signal(str, str)  # zone_id, zone_name
    show_toast = Signal(str, bool)
    zones_updated = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_zones: List[ZoneItem] = []
        self.current_filtered_zones: List[ZoneItem] = []
        self.worker: Optional[FetchZonesWorker] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header Row
        header_row = QHBoxLayout()
        title_lbl = QLabel("Domain Manager")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC;")
        header_row.addWidget(title_lbl)

        self.count_badge = QLabel("0 Domain")
        self.count_badge.setStyleSheet(
            "background-color: #1E293B; color: #94A3B8; border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: 600;"
        )
        header_row.addWidget(self.count_badge)

        header_row.addStretch()

        self.bulk_btn = QPushButton("⚡ Setup Bulk Redirect")
        self.bulk_btn.setProperty("class", "btn-neon-cyan")
        self.bulk_btn.clicked.connect(self._open_bulk_dialog)
        header_row.addWidget(self.bulk_btn)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setProperty("class", "btn-secondary")
        self.refresh_btn.clicked.connect(self.load_domains)
        header_row.addWidget(self.refresh_btn)
        layout.addLayout(header_row)

        # Controls Row (Search + Account Filter + Status Filter + Select All)
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 8px 12px;")
        ctrl_layout = QHBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(8, 4, 8, 4)
        ctrl_layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari nama domain...")
        self.search_input.textChanged.connect(self._filter_table)
        ctrl_layout.addWidget(self.search_input, stretch=3)

        # Account Filter
        acc_lbl = QLabel("Akun:")
        acc_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        ctrl_layout.addWidget(acc_lbl)

        self.account_combo = QComboBox()
        self.account_combo.addItem("Semua Akun", "all")
        self.account_combo.currentIndexChanged.connect(self._on_account_filter_changed)
        ctrl_layout.addWidget(self.account_combo, stretch=2)

        # Status Filter
        filter_lbl = QLabel("Status:")
        filter_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        ctrl_layout.addWidget(filter_lbl)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "Active", "Pending", "Initializing", "Moved"])
        self.status_combo.currentTextChanged.connect(self._filter_table)
        ctrl_layout.addWidget(self.status_combo, stretch=1)

        # Select All Checkbox
        self.select_all_chk = QCheckBox("Pilih Semua")
        self.select_all_chk.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        self.select_all_chk.stateChanged.connect(self._toggle_select_all)
        ctrl_layout.addWidget(self.select_all_chk)

        layout.addWidget(ctrl_card)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Empty state label
        self.empty_lbl = QLabel("Tidak ada domain yang ditemukan. Hubungkan akun Cloudflare terlebih dahulu.")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet("color: #64748B; font-size: 13px; padding: 40px;")
        self.empty_lbl.hide()
        layout.addWidget(self.empty_lbl)

        # Table: Pilih | Nama Domain | Akun CF | Status | Paket Plan | Zone ID | Aksi
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Pilih", "Nama Domain", "Akun CF", "Status", "Paket Plan", "Zone ID", "Aksi"
        ])
        d_header = self.table.horizontalHeader()
        d_header.setMinimumSectionSize(50)
        d_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        d_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        d_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        d_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        d_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        d_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        d_header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(5, 130)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(30)
        layout.addWidget(self.table)

    def refresh_account_combo(self):
        self.account_combo.blockSignals(True)
        cur_data = self.account_combo.currentData()
        self.account_combo.clear()
        self.account_combo.addItem("Semua Akun", "all")
        for acc in active_session.get_all_accounts():
            self.account_combo.addItem(f"👤 {acc.label}", acc.account_id)

        idx = self.account_combo.findData(cur_data)
        if idx >= 0:
            self.account_combo.setCurrentIndex(idx)
        else:
            self.account_combo.setCurrentIndex(0)
        self.account_combo.blockSignals(False)

    def _on_account_filter_changed(self):
        self.load_domains()

    def load_domains(self):
        self.refresh_account_combo()
        target_acc_id = self.account_combo.currentData() or "all"

        self.progress_bar.show()
        self.refresh_btn.setEnabled(False)

        self.worker = FetchZonesWorker(
            status_filter=self.status_combo.currentText(),
            account_id=target_acc_id,
            parent=self,
        )
        self.worker.finished.connect(self._on_zones_loaded)
        self.worker.error.connect(self._on_zones_error)
        self.worker.start()

    def _on_zones_loaded(self, zones: List[ZoneItem]):
        self.progress_bar.hide()
        self.refresh_btn.setEnabled(True)
        self.all_zones = zones
        self._filter_table()
        self.zones_updated.emit(zones)
        self.show_toast.emit(f"Berhasil memuat {len(zones)} domain dari Cloudflare.", False)

    def _on_zones_error(self, err_msg: str):
        self.progress_bar.hide()
        self.refresh_btn.setEnabled(True)
        self.show_toast.emit(f"Gagal memuat domain: {err_msg}", True)

    def _toggle_select_all(self, state: int):
        checked = (state == Qt.CheckState.Checked.value or state == 2)
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox):
                chk.setChecked(checked)

    def _filter_table(self):
        query = self.search_input.text().strip().lower()
        selected_status = self.status_combo.currentText().lower()
        selected_acc_id = self.account_combo.currentData()

        filtered = []
        for z in self.all_zones:
            if query and query not in z.name.lower():
                continue
            if selected_status != "all" and z.status.lower() != selected_status:
                continue
            if selected_acc_id and selected_acc_id != "all" and z.account_id != selected_acc_id:
                continue
            filtered.append(z)

        self.current_filtered_zones = filtered
        self.count_badge.setText(f"{len(filtered)} Domain")
        self.table.setRowCount(len(filtered))

        if len(filtered) == 0:
            self.empty_lbl.show()
            self.table.hide()
        else:
            self.empty_lbl.hide()
            self.table.show()

        mono_font = QFont("Consolas", 9)

        for row, z in enumerate(filtered):
            # 0. Checkbox
            chk = QCheckBox()
            chk.setStyleSheet("margin-left: 6px;")
            self.table.setCellWidget(row, 0, chk)

            # 1. Domain Name
            name_item = QTableWidgetItem(z.name)
            name_item.setFont(mono_font)
            name_item.setForeground(QColor("#F8FAFC"))
            self.table.setItem(row, 1, name_item)

            # 2. Account Label
            acc_item = QTableWidgetItem(z.account_label)
            acc_item.setForeground(QColor("#38BDF8"))
            self.table.setItem(row, 2, acc_item)

            # 3. Status
            is_active = (z.status.lower() == "active")
            status_item = QTableWidgetItem(f"● {z.status.upper()}" if is_active else f"○ {z.status.upper()}")
            status_item.setForeground(QColor("#34D399" if is_active else "#FBBF24"))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, status_item)

            # 4. Plan
            plan_item = QTableWidgetItem(z.plan_name)
            plan_item.setForeground(QColor("#94A3B8"))
            plan_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, plan_item)

            # 5. Zone ID
            id_item = QTableWidgetItem(z.id)
            id_item.setFont(mono_font)
            id_item.setForeground(QColor("#64748B"))
            id_item.setToolTip(z.id)
            self.table.setItem(row, 5, id_item)

            # 6. Action button
            action_btn = QPushButton("Redirects →")
            action_btn.setProperty("class", "btn-action-edit")
            action_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            action_btn.clicked.connect(
                lambda checked=False, zid=z.id, zname=z.name: self.view_redirects_for_zone.emit(zid, zname)
            )
            self.table.setCellWidget(row, 6, action_btn)

    def _open_bulk_dialog(self):
        selected_ids = []
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked() and row < len(self.current_filtered_zones):
                selected_ids.append(self.current_filtered_zones[row].id)

        dlg = BulkRedirectDialog(self.all_zones, preselected_zone_ids=selected_ids, parent=self)
        dlg.bulk_completed.connect(
            lambda count: self.show_toast.emit(f"{count} aturan bulk redirect berhasil dibuat!", False)
        )
        dlg.exec()

    def set_zones(self, zones: List[ZoneItem]):
        self.all_zones = zones
        self._filter_table()

    def clear(self):
        self.all_zones = []
        self.table.setRowCount(0)
        self.empty_lbl.hide()
        self.count_badge.setText("0 Domain")
