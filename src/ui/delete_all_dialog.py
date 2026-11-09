"""Delete All Incoming 301/302 Redirects Dialog.
Allows users to purge/delete all 301 Permanent, 302 Temporary, or both redirect rules
from the current zone or across multiple selected Cloudflare zones.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QRadioButton,
    QButtonGroup,
    QCheckBox,
    QProgressBar,
    QMessageBox,
    QFrame,
    QApplication,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from src.cloudflare.zones import ZoneItem
from src.cloudflare.redirects import RedirectRule
from src.ui.workers import BulkDeleteRedirectsWorker


class DeleteAllRedirectsDialog(QDialog):
    """Modern modal dialog to safely delete / purge ALL INCOMING 301 & 302 redirect rules."""

    rules_deleted = Signal(int)  # emits count of deleted rules

    def __init__(
        self,
        zone_name: str,
        zone_id: str,
        current_rules: List[RedirectRule],
        all_zones: Optional[List[ZoneItem]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.zone_name = zone_name
        self.zone_id = zone_id
        self.current_rules = current_rules or []
        self.all_zones = all_zones or []
        self.worker: Optional[BulkDeleteRedirectsWorker] = None

        self.setWindowTitle(f"Hapus Redirect ALL INCOMING 301 / 302 — {zone_name}")
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(840, max(680, int(avail.width() * 0.85)))
            target_h = min(560, max(420, int(avail.height() * 0.85)))
            self.resize(target_w, target_h)
        else:
            self.resize(800, 520)
        self.setMinimumSize(640, 400)
        self.setStyleSheet("QDialog { background-color: #0F172A; border: 1px solid #1E293B; border-radius: 10px; }")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # Header Card
        header_card = QFrame()
        header_card.setProperty("class", "card")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(3)

        title_lbl = QLabel(f"Hapus Aturan Redirect ALL INCOMING (301 & 302)")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #EF4444;")
        header_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            f"Zona Aktif: <b>{self.zone_name}</b>. "
            "Pilih aturan 301 / 302 yang ingin dihapus secara permanen dari Cloudflare."
        )
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        header_layout.addWidget(sub_lbl)
        main_layout.addWidget(header_card)

        # Filter Options Frame
        opt_frame = QFrame()
        opt_frame.setProperty("class", "card")
        opt_layout = QHBoxLayout(opt_frame)
        opt_layout.setContentsMargins(14, 10, 14, 10)
        opt_layout.setSpacing(16)

        filter_lbl = QLabel("Filter Status HTTP:")
        filter_lbl.setStyleSheet("font-weight: 700; color: #FFFFFF;")
        opt_layout.addWidget(filter_lbl)

        self.filter_group = QButtonGroup(self)
        self.rad_all = QRadioButton("Semua (301 & 302)")
        self.rad_301 = QRadioButton("Hanya 301 (Permanent)")
        self.rad_302 = QRadioButton("Hanya 302 (Temporary)")
        self.rad_all.setChecked(True)

        self.filter_group.addButton(self.rad_all, 0)
        self.filter_group.addButton(self.rad_301, 301)
        self.filter_group.addButton(self.rad_302, 302)

        self.rad_all.toggled.connect(self._refresh_table)
        self.rad_301.toggled.connect(self._refresh_table)
        self.rad_302.toggled.connect(self._refresh_table)

        opt_layout.addWidget(self.rad_all)
        opt_layout.addWidget(self.rad_301)
        opt_layout.addWidget(self.rad_302)
        opt_layout.addStretch()

        # Select all / Clear in table
        sel_all_btn = QPushButton("Pilih Semua")
        sel_all_btn.setProperty("class", "btn-secondary")
        sel_all_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        sel_all_btn.clicked.connect(self._select_all)
        opt_layout.addWidget(sel_all_btn)

        clr_all_btn = QPushButton("Kosongkan")
        clr_all_btn.setProperty("class", "btn-secondary")
        clr_all_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        clr_all_btn.clicked.connect(self._clear_all)
        opt_layout.addWidget(clr_all_btn)

        main_layout.addWidget(opt_frame)

        # Table of matching rules
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Pilih", "Domain Sumber", "Akun CF", "Mode", "URL Tujuan", "Status HTTP", "Rule ID"
        ])
        del_header = self.table.horizontalHeader()
        del_header.setMinimumSectionSize(50)
        del_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        del_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        del_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        del_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        del_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        del_header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        del_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(6, 120)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        main_layout.addWidget(self.table, stretch=1)

        # Progress bar
        self.progress_frame = QFrame()
        self.progress_frame.setProperty("class", "card")
        self.progress_frame.hide()
        prog_layout = QVBoxLayout(self.progress_frame)
        prog_layout.setContentsMargins(12, 8, 12, 8)
        self.progress_lbl = QLabel("Menghapus aturan...")
        self.progress_lbl.setStyleSheet("color: #FF4D6D; font-weight: 700; font-size: 12px;")
        prog_layout.addWidget(self.progress_lbl)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        prog_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.progress_frame)

        # Footer Actions
        footer_layout = QHBoxLayout()
        self.count_lbl = QLabel("0 aturan akan dihapus")
        self.count_lbl.setStyleSheet("color: #FF4D6D; font-weight: 700; font-size: 13px;")
        footer_layout.addWidget(self.count_lbl)

        footer_layout.addStretch()

        self.cancel_btn = QPushButton("Batal")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(self.cancel_btn)

        self.delete_btn = QPushButton("🗑️ Hapus Aturan Terpilih Secara Permanen")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.clicked.connect(self._on_confirm_delete)
        footer_layout.addWidget(self.delete_btn)

        main_layout.addLayout(footer_layout)

        self.filtered_rules: List[RedirectRule] = []
        self._refresh_table()

    def _refresh_table(self):
        code_filter = self.filter_group.checkedId()
        if code_filter == 301:
            self.filtered_rules = [r for r in self.current_rules if r.status_code == 301]
        elif code_filter == 302:
            self.filtered_rules = [r for r in self.current_rules if r.status_code == 302]
        else:
            self.filtered_rules = list(self.current_rules)

        self.table.setRowCount(len(self.filtered_rules))
        mono_font = QFont("Consolas", 9)
        self.table.verticalHeader().setDefaultSectionSize(28)

        for row, r in enumerate(self.filtered_rules):
            chk = QCheckBox()
            chk.setChecked(True)
            chk.setStyleSheet("margin-left: 6px;")
            chk.toggled.connect(self._update_count)
            self.table.setCellWidget(row, 0, chk)

            src_item = QTableWidgetItem(r.source_display)
            src_item.setFont(mono_font)
            src_item.setForeground(QColor("#F8FAFC"))
            self.table.setItem(row, 1, src_item)

            acc_str = f"👤 {r.account_label}" if getattr(r, "account_label", None) else "-"
            acc_item = QTableWidgetItem(acc_str)
            acc_item.setFont(mono_font)
            acc_item.setForeground(QColor("#38BDF8"))
            self.table.setItem(row, 2, acc_item)

            mode_item = QTableWidgetItem(r.mode)
            mode_item.setForeground(QColor("#94A3B8"))
            self.table.setItem(row, 3, mode_item)

            dest_item = QTableWidgetItem(r.destination_url)
            dest_item.setFont(mono_font)
            dest_item.setForeground(QColor("#38BDF8"))
            self.table.setItem(row, 4, dest_item)

            code_item = QTableWidgetItem(f"{r.status_code} {'Permanent' if r.status_code == 301 else 'Temporary'}")
            code_item.setFont(mono_font)
            if r.status_code == 301:
                code_item.setForeground(QColor("#38BDF8"))
            else:
                code_item.setForeground(QColor("#FB923C"))
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, code_item)

            id_item = QTableWidgetItem(r.id)
            id_item.setFont(mono_font)
            id_item.setForeground(QColor("#64748B"))
            id_item.setToolTip(r.id)
            self.table.setItem(row, 6, id_item)

        self._update_count()

    def _select_all(self):
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox):
                chk.setChecked(True)
        self._update_count()

    def _clear_all(self):
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox):
                chk.setChecked(False)
        self._update_count()

    def _get_checked_rules(self) -> List[RedirectRule]:
        checked = []
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked() and row < len(self.filtered_rules):
                checked.append(self.filtered_rules[row])
        return checked

    def _update_count(self):
        count = len(self._get_checked_rules())
        self.count_lbl.setText(f"<b>{count}</b> aturan dipilih untuk dihapus")
        self.delete_btn.setEnabled(count > 0)

    def _on_confirm_delete(self):
        rules_to_delete = self._get_checked_rules()
        if not rules_to_delete:
            return

        confirm_msg = (
            f"PERINGATAN PENGHAPUSAN PERMANEN:\n\n"
            f"Anda akan menghapus <b>{len(rules_to_delete)}</b> aturan ALL INCOMING Single Redirect "
            f"dari zona '{self.zone_name}'.\n\n"
            f"Aturan yang dihapus tidak dapat dipulihkan. Apakah Anda yakin ingin melanjutkan?"
        )
        reply = QMessageBox.warning(
            self,
            "Konfirmasi Hapus Permanen",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Prepare deletion items
        items = [
            {
                "zone_id": r.zone_id,
                "ruleset_id": r.ruleset_id,
                "rule_id": r.id,
                "source_hostname": r.source_hostname,
            }
            for r in rules_to_delete
        ]

        self.table.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_frame.show()
        self.progress_bar.setValue(0)
        self.progress_lbl.setText(f"Menghapus {len(items)} aturan dari Cloudflare...")

        self.worker = BulkDeleteRedirectsWorker(items, parent=self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current: int, total: int, msg: str):
        pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.progress_lbl.setText(f"[{current}/{total}] {msg}")

    def _on_finished(self, summary: dict):
        self.progress_bar.setValue(100)
        succ = summary.get("success", 0)
        self.rules_deleted.emit(succ)
        QMessageBox.information(
            self,
            "Selesai",
            f"Berhasil menghapus <b>{succ}</b> aturan redirect ALL INCOMING dari Cloudflare.",
        )
        self.accept()

    def _on_error(self, err_msg: str):
        self.table.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Gagal menghapus aturan:\n{err_msg}")
