"""Redirect Manager Page.
Handles creating, updating, toggling, simulating, and deleting Cloudflare ALL INCOMING Single Redirect rules.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialog,
    QLineEdit,
    QRadioButton,
    QButtonGroup,
    QCheckBox,
    QProgressBar,
    QMessageBox,
    QFrame,
    QTextEdit,
    QScrollArea,
    QApplication,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
import httpx
from src.cloudflare.zones import ZoneItem
from src.cloudflare.redirects import RedirectRule
from src.security.validation import (
    validate_destination_url,
    simulate_redirect,
)
from src.ui.components import DangerConfirmDialog
from src.ui.bulk_dialog import BulkRedirectDialog
from src.ui.delete_all_dialog import DeleteAllRedirectsDialog
from src.ui.workers import (
    FetchRedirectsWorker,
    CreateRedirectWorker,
    UpdateRedirectWorker,
    ToggleRedirectWorker,
    DeleteRedirectWorker,
    BulkDeleteRedirectsWorker,
    BulkToggleRedirectsWorker,
)


class RedirectFormDialog(QDialog):
    """Dialog for creating or updating an ALL INCOMING Single Redirect rule."""

    def __init__(
        self,
        zone_name: str,
        zone_id: str,
        existing_rule: Optional[RedirectRule] = None,
        all_zones: Optional[List[ZoneItem]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.all_zones = all_zones or []
        self.zone_name = zone_name
        self.zone_id = zone_id
        self.existing_rule = existing_rule
        is_edit = existing_rule is not None

        self.setWindowTitle(
            f"{'Edit' if is_edit else 'Tambah'} ALL INCOMING Redirect — {zone_name}"
        )
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_h = min(560, max(440, int(avail.height() * 0.82)))
            self.resize(600, target_h)
        else:
            self.resize(600, 500)
        self.setMinimumSize(480, 360)
        self.setStyleSheet("QDialog { background-color: #0F172A; border: 1px solid #1E293B; border-radius: 10px; }")
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(8)

        # Title
        title_text = "Edit Aturan Redirect" if self.existing_rule else "Buat ALL INCOMING Redirect"
        self.title_lbl = QLabel(f"{title_text} ({self.zone_name})")
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        root_layout.addWidget(self.title_lbl)

        # ScrollArea for form content so on 14" screen buttons are never cut off
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(4, 4, 10, 4)
        layout.setSpacing(10)

        # Mode Badge
        mode_box = QFrame()
        mode_box.setStyleSheet("background-color: #090D16; border: 1px solid #1E293B; border-radius: 6px; padding: 6px 10px;")
        mode_layout = QHBoxLayout(mode_box)
        mode_lbl = QLabel("Mode Redirect: <b>ALL INCOMING</b> (Semua request domain & subdomain dialihkan)")
        mode_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")
        mode_layout.addWidget(mode_lbl)
        layout.addWidget(mode_box)

        # Domain Picker if multiple zones are available
        if self.all_zones and len(self.all_zones) > 1 and not self.existing_rule:
            zone_pick_lbl = QLabel("Pilih Domain Sumber (Semua Akun CF Tergabung):")
            zone_pick_lbl.setStyleSheet("font-weight: 600; color: #CBD5E1;")
            layout.addWidget(zone_pick_lbl)

            self.zone_picker = QComboBox()
            for z in self.all_zones:
                self.zone_picker.addItem(f"{z.name} — [CF: {z.account_label}]", z.id)

            for i in range(self.zone_picker.count()):
                if self.zone_picker.itemData(i) == self.zone_id:
                    self.zone_picker.setCurrentIndex(i)
                    break

            def on_picker_change(idx):
                zid = self.zone_picker.itemData(idx)
                match_z = next((z for z in self.all_zones if z.id == zid), None)
                if match_z:
                    self.zone_id = match_z.id
                    self.zone_name = match_z.name
                    self.title_lbl.setText(f"Buat ALL INCOMING Redirect ({self.zone_name})")
                    self.cov_all.setText(f"All incoming requests (Terapkan ke seluruh request domain/subdomain di {self.zone_name})")
                    self.cov_both.setText(f"Domain Utama & www (Keduanya: {self.zone_name} + www.{self.zone_name})")
                    self.cov_apex.setText(f"Domain Utama saja ({self.zone_name})")
                    self.cov_www.setText(f"www saja (www.{self.zone_name})")
                    self._update_preview()

            self.zone_picker.currentIndexChanged.connect(on_picker_change)
            layout.addWidget(self.zone_picker)

        # Hostname Coverage
        cov_lbl = QLabel("Cakupan Hostname Sumber:")
        cov_lbl.setStyleSheet("font-weight: 600; color: #CBD5E1;")
        layout.addWidget(cov_lbl)

        cov_frame = QFrame()
        cov_frame.setStyleSheet("background-color: #090D16; border: 1px solid #1E293B; border-radius: 6px; padding: 8px;")
        cov_layout = QVBoxLayout(cov_frame)

        self.cov_group = QButtonGroup(self)
        self.cov_all = QRadioButton(f"All incoming requests (Terapkan ke seluruh request domain/subdomain di {self.zone_name})")
        self.cov_both = QRadioButton(f"Domain Utama & www (Keduanya: {self.zone_name} + www.{self.zone_name})")
        self.cov_apex = QRadioButton(f"Domain Utama saja ({self.zone_name})")
        self.cov_www = QRadioButton(f"www saja (www.{self.zone_name})")

        self.cov_group.addButton(self.cov_all, 0)
        self.cov_group.addButton(self.cov_both, 1)
        self.cov_group.addButton(self.cov_apex, 2)
        self.cov_group.addButton(self.cov_www, 3)

        cov_layout.addWidget(self.cov_all)
        cov_layout.addWidget(self.cov_both)
        cov_layout.addWidget(self.cov_apex)
        cov_layout.addWidget(self.cov_www)
        layout.addWidget(cov_frame)

        # Destination URL
        dest_lbl = QLabel("URL Tujuan:")
        dest_lbl.setStyleSheet("font-weight: 600; color: #CBD5E1;")
        layout.addWidget(dest_lbl)

        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText("https://domaintujuan.com/")
        self.dest_input.textChanged.connect(self._update_preview)
        layout.addWidget(self.dest_input)

        # Status Code Selection
        status_lbl = QLabel("Status HTTP Redirect:")
        status_lbl.setStyleSheet("font-weight: 600; color: #CBD5E1;")
        layout.addWidget(status_lbl)

        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #090D16; border: 1px solid #1E293B; border-radius: 6px; padding: 8px;")
        status_layout = QVBoxLayout(status_frame)

        self.status_group = QButtonGroup(self)
        self.status_301 = QRadioButton("301 — Permanent Redirect (Wajib / Standar)")
        self.status_302 = QRadioButton("302 — Temporary Redirect (Sementara)")
        self.status_group.addButton(self.status_301, 301)
        self.status_group.addButton(self.status_302, 302)

        status_layout.addWidget(self.status_301)
        status_layout.addWidget(self.status_302)
        layout.addWidget(status_frame)

        # Toggles: Preserve Path, Preserve Query, Enabled
        opt_lbl = QLabel("Opsi Pengalihan URL:")
        opt_lbl.setStyleSheet("font-weight: 600; color: #CBD5E1;")
        layout.addWidget(opt_lbl)

        opt_frame = QFrame()
        opt_frame.setStyleSheet("background-color: #090D16; border: 1px solid #1E293B; border-radius: 6px; padding: 8px;")
        opt_layout = QVBoxLayout(opt_frame)

        type_lbl = QLabel("📌 Tipe Redirect: <b>Static URL</b> (Direkomendasikan Cloudflare — Valid & Mudah Dibaca)")
        type_lbl.setTextFormat(Qt.TextFormat.RichText)
        type_lbl.setStyleSheet("color: #34D399; font-size: 11px;")
        opt_layout.addWidget(type_lbl)

        self.preserve_path_chk = QCheckBox("Preserve Path")
        self.preserve_path_chk.setChecked(False)
        self.preserve_path_chk.hide()  # Selalu Static URL sesuai kebutuhan pengguna

        self.preserve_query_chk = QCheckBox("Preserve Query String (Pertahankan ?query, contoh: ?id=10 tetap ?id=10)")
        self.preserve_query_chk.setChecked(True)
        self.preserve_query_chk.toggled.connect(self._update_preview)
        opt_layout.addWidget(self.preserve_query_chk)

        self.enabled_chk = QCheckBox("Status Rule: Aktif (Enabled)")
        self.enabled_chk.setChecked(True)
        opt_layout.addWidget(self.enabled_chk)

        layout.addWidget(opt_frame)

        # Realtime Preview Box
        self.preview_lbl = QLabel("")
        self.preview_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-family: Consolas, monospace; background: #0A0F1D; padding: 8px; border-radius: 4px;")
        self.preview_lbl.setWordWrap(True)
        layout.addWidget(self.preview_lbl)

        # Cloudflare DNS Notice
        dns_notice = QLabel(
            "⚠️ <b>Catatan DNS Cloudflare:</b> Pastikan DNS Record A/CNAME untuk domain ini "
            "telah di-proxy (Awan Oranye) di Cloudflare agar trafik melewati Single Redirects."
        )
        dns_notice.setTextFormat(Qt.TextFormat.RichText)
        dns_notice.setStyleSheet("color: #FBBF24; font-size: 11px;")
        dns_notice.setWordWrap(True)
        layout.addWidget(dns_notice)

        # Pre-fill if editing
        if self.existing_rule:
            self.dest_input.setText(self.existing_rule.destination_url)
            if self.existing_rule.coverage in ("all", "all_incoming"):
                self.cov_all.setChecked(True)
            elif self.existing_rule.coverage == "apex":
                self.cov_apex.setChecked(True)
            elif self.existing_rule.coverage == "www":
                self.cov_www.setChecked(True)
            else:
                self.cov_both.setChecked(True)

            if self.existing_rule.status_code == 302:
                self.status_302.setChecked(True)
            else:
                self.status_301.setChecked(True)

            self.preserve_path_chk.setChecked(self.existing_rule.preserve_path)
            self.preserve_query_chk.setChecked(self.existing_rule.preserve_query_string)
            self.enabled_chk.setChecked(self.existing_rule.enabled)
        else:
            self.cov_all.setChecked(True)
            self.status_301.setChecked(True)

        self._update_preview()

        scroll.setWidget(scroll_widget)
        root_layout.addWidget(scroll, stretch=1)

        # Action Buttons pinned at bottom
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Batal")
        cancel_btn.setProperty("class", "btn-secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.save_btn = QPushButton("Simpan ke Cloudflare")
        self.save_btn.setProperty("class", "btn-primary")
        self.save_btn.clicked.connect(self._validate_and_confirm)
        btn_layout.addWidget(self.save_btn)

        root_layout.addLayout(btn_layout)

    def _get_selected_coverage(self) -> str:
        if self.cov_all.isChecked():
            return "all"
        elif self.cov_apex.isChecked():
            return "apex"
        elif self.cov_www.isChecked():
            return "www"
        return "both"

    def _update_preview(self):
        dest = self.dest_input.text().strip() or "https://domaintujuan.com"
        preserve_q = self.preserve_query_chk.isChecked()

        sample_in = f"https://{self.zone_name}/promo?id=123"
        _, sample_out, _ = simulate_redirect(
            sample_in,
            self.zone_name,
            dest,
            self._get_selected_coverage(),
            False,  # Static URL: direct fixed destination URL
            preserve_q,
        )
        self.preview_lbl.setText(f"Contoh Simulasi (Static URL):\n{sample_in}  ➔  {sample_out}")

    def _validate_and_confirm(self):
        dest = self.dest_input.text().strip()
        try:
            norm_dest, is_sub = validate_destination_url(dest, source_host=self.zone_name)
        except Exception as e:
            QMessageBox.critical(self, "Validasi Gagal", str(e))
            return

        coverage = self._get_selected_coverage()
        status_code = 301 if self.status_301.isChecked() else 302
        preserve_p = self.preserve_path_chk.isChecked()
        preserve_q = self.preserve_query_chk.isChecked()
        enabled = self.enabled_chk.isChecked()

        warning_extra = ""
        if is_sub:
            warning_extra = "\n\n⚠️ PERINGATAN: Domain tujuan berada pada domain atau subdomain yang sama!"
        if status_code == 301:
            warning_extra += "\n\n⚠️ PERHATIAN: Redirect 301 disimpan permanen oleh browser pengguna."

        if coverage in ("all", "all_incoming"):
            cov_str = "All incoming requests (Semua Request)"
        elif coverage == "both":
            cov_str = "Domain Utama & www"
        elif coverage == "apex":
            cov_str = "Domain Utama saja"
        else:
            cov_str = "www saja"

        confirm_msg = (
            f"Konfirmasi ALL INCOMING Redirect:\n\n"
            f"• Domain Sumber: {self.zone_name} ({cov_str})\n"
            f"• URL Tujuan   : {norm_dest}\n"
            f"• Status HTTP  : {status_code}\n"
            f"• Preserve Path: {'ON' if preserve_p else 'OFF'}\n"
            f"• Preserve Query: {'ON' if preserve_q else 'OFF'}\n"
            f"• Status Rule  : {'Aktif (Enabled)' if enabled else 'Nonaktif (Disabled)'}"
            f"{warning_extra}\n\n"
            f"Terapkan aturan ini ke Cloudflare?"
        )

        reply = QMessageBox.question(
            self,
            "Konfirmasi Terapkan Rule",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.validated_data = {
                "zone_id": self.zone_id,
                "source_hostname": self.zone_name,
                "destination_url": norm_dest,
                "coverage": coverage,
                "status_code": status_code,
                "preserve_path": preserve_p,
                "preserve_query_string": preserve_q,
                "enabled": enabled,
            }
            self.accept()


class TestRedirectDialog(QDialog):
    """Dialog for simulating and testing URL redirects against a rule."""

    def __init__(self, rule: RedirectRule, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.setWindowTitle(f"Test Redirect — {rule.source_display}")
        self.setMinimumWidth(560)
        self.setStyleSheet("QDialog { background-color: #0F172A; border: 1px solid #1E293B; border-radius: 10px; }")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel(f"Uji Aturan Redirect ({self.rule.source_display})")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #38BDF8;")
        layout.addWidget(title)

        rule_summary = (
            f"• Mode: ALL INCOMING ({self.rule.coverage.upper()})\n"
            f"• Tujuan: {self.rule.destination_url}\n"
            f"• Status HTTP: {self.rule.status_code}\n"
            f"• Preserve Path: {'ON' if self.rule.preserve_path else 'OFF'} | Preserve Query: {'ON' if self.rule.preserve_query_string else 'OFF'}"
        )
        summary_lbl = QLabel(rule_summary)
        summary_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; background: #090D16; border: 1px solid #1E293B; padding: 10px; border-radius: 6px;")
        layout.addWidget(summary_lbl)

        # Simulation Input
        sim_lbl = QLabel("Masukkan URL Uji:")
        sim_lbl.setStyleSheet("font-weight: 600; color: #CBD5E1;")
        layout.addWidget(sim_lbl)

        self.test_url_input = QLineEdit()
        self.test_url_input.setText(f"https://{self.rule.source_hostname}/promo/diskon?ref=test")
        layout.addWidget(self.test_url_input)

        btn_row = QHBoxLayout()
        sim_btn = QPushButton("🧪 Simulasikan Pengalihan")
        sim_btn.setProperty("class", "btn-primary")
        sim_btn.clicked.connect(self._run_simulation)
        btn_row.addWidget(sim_btn)

        self.live_btn = QPushButton("🌐 Cek Live HTTP Request")
        self.live_btn.setProperty("class", "btn-secondary")
        self.live_btn.clicked.connect(self._run_live_probe)
        btn_row.addWidget(self.live_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Results area
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setMinimumHeight(130)
        self.result_box.setStyleSheet("background-color: #090D16; color: #F8FAFC; border: 1px solid #1E293B; font-family: Consolas, monospace; font-size: 12px; border-radius: 6px; padding: 6px;")
        layout.addWidget(self.result_box)

        close_btn = QPushButton("Tutup")
        close_btn.setProperty("class", "btn-secondary")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._run_simulation()

    def _run_simulation(self):
        url = self.test_url_input.text().strip()
        matched, out_url, desc = simulate_redirect(
            url,
            self.rule.source_hostname,
            self.rule.destination_url,
            self.rule.coverage,
            self.rule.preserve_path,
            self.rule.preserve_query_string,
        )
        if matched:
            res_text = (
                f"[HASIL SIMULASI LOGIKA]\n"
                f"Status  : COCOK (MATCH)\n"
                f"Input   : {url}\n"
                f"Dialihkan ke: {out_url}\n"
                f"HTTP Code   : {self.rule.status_code}\n"
                f"Keterangan  : {desc}"
            )
        else:
            res_text = (
                f"[HASIL SIMULASI LOGIKA]\n"
                f"Status  : TIDAK COCOK\n"
                f"Input   : {url}\n"
                f"Alasan  : {desc}"
            )
        self.result_box.setPlainText(res_text)

    def _run_live_probe(self):
        url = self.test_url_input.text().strip()
        self.result_box.setPlainText("Mengirim permintaan HTTP probe langsung ke server...\n")
        try:
            with httpx.Client(timeout=8.0, verify=True, follow_redirects=False) as client:
                resp = client.get(url)
                location = resp.headers.get("Location", "-")
                server = resp.headers.get("Server", "-")
                cf_ray = resp.headers.get("CF-RAY", "-")
                
                res = (
                    f"[HASIL LIVE HTTP PROBE]\n"
                    f"URL Uji      : {url}\n"
                    f"HTTP Status  : {resp.status_code}\n"
                    f"Header Location: {location}\n"
                    f"Server       : {server}\n"
                    f"Cloudflare RAY : {cf_ray}\n\n"
                )
                if resp.status_code in (301, 302, 307, 308):
                    res += "✅ Redirect aktif dan berhasil merespons dari Cloudflare!"
                else:
                    res += "ℹ️ Respons bukan redirect. Pastikan DNS record domain sudah di-proxy (Awan Oranye) di Cloudflare."
                self.result_box.setPlainText(res)
        except Exception as e:
            self.result_box.setPlainText(f"[GAGAL MENGHUBUNGI LIVE SERVER]\nError: {str(e)}\nPastikan domain memiliki koneksi internet aktif dan DNS terhubung.")


class RedirectPage(QWidget):
    """Page for listing and managing ALL INCOMING Single Redirect rules."""

    show_toast = Signal(str, bool)
    redirects_count_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.zones: List[ZoneItem] = []
        self.current_ruleset_id: Optional[str] = None
        self.current_rules: List[RedirectRule] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header Row
        header_row = QHBoxLayout()
        title_lbl = QLabel("Redirect Manager — ALL INCOMING 301 & 302")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        self.add_btn = QPushButton("➕ Tambah Redirect")
        self.add_btn.setProperty("class", "btn-primary")
        self.add_btn.clicked.connect(self._open_add_dialog)
        header_row.addWidget(self.add_btn)

        self.bulk_btn = QPushButton("⚡ Bulk Redirects")
        self.bulk_btn.setProperty("class", "btn-neon-cyan")
        self.bulk_btn.clicked.connect(self._open_bulk_dialog)
        header_row.addWidget(self.bulk_btn)

        self.clean_all_btn = QPushButton("🗑️ Hapus All 301/302")
        self.clean_all_btn.setProperty("class", "btn-danger")
        self.clean_all_btn.clicked.connect(self._open_delete_all_dialog)
        header_row.addWidget(self.clean_all_btn)

        self.refresh_btn = QPushButton("🔄 Refresh Rules")
        self.refresh_btn.setProperty("class", "btn-secondary")
        self.refresh_btn.clicked.connect(self.load_redirects_for_selected_zone)
        header_row.addWidget(self.refresh_btn)

        layout.addLayout(header_row)

        # Zone & Filter Controls Frame
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet(
            "background-color: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 6px 10px;"
        )
        ctrl_layout = QHBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(8, 4, 8, 4)
        ctrl_layout.setSpacing(10)

        zone_lbl = QLabel("Zona:")
        zone_lbl.setStyleSheet("font-weight: 600; color: #94A3B8; font-size: 12px;")
        ctrl_layout.addWidget(zone_lbl)

        self.zone_combo = QComboBox()
        self.zone_combo.currentIndexChanged.connect(self.load_redirects_for_selected_zone)
        ctrl_layout.addWidget(self.zone_combo, stretch=3)

        self.select_all_btn = QPushButton("☑️ Pilih Semua")
        self.select_all_btn.setProperty("class", "btn-secondary")
        self.select_all_btn.clicked.connect(self._toggle_select_all_clicked)
        ctrl_layout.addWidget(self.select_all_btn)

        self.zone_info_lbl = QLabel("")
        self.zone_info_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")
        ctrl_layout.addWidget(self.zone_info_lbl)

        layout.addWidget(ctrl_card)

        # Bulk Actions Bar (Appears when 1 or more rules are checked in table list)
        self.bulk_bar = QFrame()
        self.bulk_bar.setProperty("class", "card")
        self.bulk_bar.setStyleSheet(
            "padding: 6px 12px; background-color: #0F172A; border: 1px solid #38BDF8; border-radius: 8px;"
        )
        self.bulk_bar.hide()
        bulk_bar_layout = QHBoxLayout(self.bulk_bar)
        bulk_bar_layout.setContentsMargins(10, 4, 10, 4)
        bulk_bar_layout.setSpacing(10)

        self.bulk_sel_lbl = QLabel("0 aturan dipilih dalam list:")
        self.bulk_sel_lbl.setStyleSheet("font-weight: 700; color: #38BDF8; font-size: 12px;")
        bulk_bar_layout.addWidget(self.bulk_sel_lbl)

        self.bulk_delete_btn = QPushButton("🗑️ Hapus Terpilih")
        self.bulk_delete_btn.setProperty("class", "btn-danger")
        self.bulk_delete_btn.setToolTip("Hapus semua aturan yang dicentang di dalam list secara permanen")
        self.bulk_delete_btn.clicked.connect(self._bulk_delete)
        bulk_bar_layout.addWidget(self.bulk_delete_btn)

        self.bulk_enable_btn = QPushButton("⚡ Aktifkan")
        self.bulk_enable_btn.setProperty("class", "btn-success")
        self.bulk_enable_btn.clicked.connect(lambda: self._bulk_toggle(True))
        bulk_bar_layout.addWidget(self.bulk_enable_btn)

        self.bulk_disable_btn = QPushButton("⏸️ Nonaktifkan")
        self.bulk_disable_btn.setProperty("class", "btn-secondary")
        self.bulk_disable_btn.clicked.connect(lambda: self._bulk_toggle(False))
        bulk_bar_layout.addWidget(self.bulk_disable_btn)

        self.bulk_clear_btn = QPushButton("✕ Batal Pilih")
        self.bulk_clear_btn.setProperty("class", "btn-secondary")
        self.bulk_clear_btn.clicked.connect(self._deselect_all)
        bulk_bar_layout.addWidget(self.bulk_clear_btn)

        bulk_bar_layout.addStretch()
        layout.addWidget(self.bulk_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Empty State
        self.empty_lbl = QLabel("Belum ada aturan Single Redirect yang terpasang pada zona ini.")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet("color: #64748B; font-size: 14px; padding: 40px;")
        self.empty_lbl.hide()
        layout.addWidget(self.empty_lbl)

        # Table matching requirements:
        # Checkbox | Source Domain | Akun CF | Mode | Destination URL | Status Code | Tipe & Query | Status | Actions
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Pilih", "Source Domain", "Akun CF", "Mode", "Destination URL", "Status Code", "Tipe & Query", "Status", "Actions"
        ])
        r_header = self.table.horizontalHeader()
        r_header.setMinimumSectionSize(50)
        r_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        r_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        r_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        r_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        r_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        r_header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        r_header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        r_header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        r_header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 130)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def set_zones(self, zones: List[ZoneItem]):
        self.zones = zones
        self.zone_combo.blockSignals(True)
        self.zone_combo.clear()
        if len(zones) > 0:
            self.zone_combo.addItem(f"🌐 Semua Domain (Gabung Semua Akun CF — {len(zones)} Domain)", "all")
            for z in zones:
                acc_tag = f" — [{z.account_label}]" if z.account_label else ""
                self.zone_combo.addItem(f"{z.name} ({z.status}){acc_tag}", z.id)
        self.zone_combo.blockSignals(False)

        if len(zones) > 0:
            self.zone_combo.setCurrentIndex(0)
            self.load_redirects_for_selected_zone()
        else:
            self.table.setRowCount(0)
            self.empty_lbl.setText("Belum ada zona domain yang tersedia.")
            self.empty_lbl.show()

    def select_zone_by_id(self, zone_id: str):
        for i in range(self.zone_combo.count()):
            if self.zone_combo.itemData(i) == zone_id:
                self.zone_combo.setCurrentIndex(i)
                break

    def load_redirects_for_selected_zone(self):
        zone_id = self.zone_combo.currentData()
        if not zone_id:
            return

        # Ensure active account matches selected zone's account if single zone
        if zone_id != "all":
            matching_zone = next((z for z in self.zones if z.id == zone_id), None)
            if matching_zone and matching_zone.account_id:
                try:
                    active_session.switch_account(matching_zone.account_id)
                except Exception:
                    pass

        self.progress_bar.show()
        self.refresh_btn.setEnabled(False)
        self.add_btn.setEnabled(False)

        worker = FetchRedirectsWorker(zone_id, zones=self.zones, parent=self)
        worker.finished.connect(self._on_redirects_loaded)
        worker.error.connect(self._on_redirects_error)
        worker.start()

    def _on_redirects_loaded(self, ruleset_id: str, rules: List[RedirectRule]):
        self.progress_bar.hide()
        self.refresh_btn.setEnabled(True)
        self.add_btn.setEnabled(True)

        self.current_ruleset_id = ruleset_id
        self.current_rules = rules
        self.redirects_count_changed.emit(len(rules))
        if ruleset_id == "all":
            self.zone_info_lbl.setText(f"{len(rules)} Total Rules (Semua Akun CF)")
        else:
            self.zone_info_lbl.setText(f"{len(rules)}/10 Rules (Free Limit)")

        self.table.setRowCount(len(rules))
        if len(rules) == 0:
            self.empty_lbl.show()
            self.table.hide()
        else:
            self.empty_lbl.hide()
            self.table.show()

        self.bulk_bar.hide()
        mono_font = QFont("Consolas", 9)
        self.table.verticalHeader().setDefaultSectionSize(30)

        for row, r in enumerate(rules):
            # 0. Checkbox
            chk = QCheckBox()
            chk.setStyleSheet("margin-left: 6px;")
            chk.toggled.connect(self._update_bulk_selection_state)
            self.table.setCellWidget(row, 0, chk)

            # 1. Source Domain
            src_item = QTableWidgetItem(r.source_display)
            src_item.setFont(mono_font)
            src_item.setForeground(QColor("#F8FAFC"))
            self.table.setItem(row, 1, src_item)

            # 2. Akun CF
            acc_label = r.account_label or "Akun Utama"
            acc_item = QTableWidgetItem(f"👤 {acc_label}")
            acc_item.setFont(mono_font)
            acc_item.setForeground(QColor("#38BDF8"))
            self.table.setItem(row, 2, acc_item)

            # 3. Mode
            mode_item = QTableWidgetItem(r.mode)
            mode_item.setForeground(QColor("#94A3B8"))
            self.table.setItem(row, 3, mode_item)

            # 4. Destination URL
            dest_item = QTableWidgetItem(r.destination_url)
            dest_item.setFont(mono_font)
            dest_item.setForeground(QColor("#38BDF8"))
            self.table.setItem(row, 4, dest_item)

            # 5. Status Code
            code_item = QTableWidgetItem(str(r.status_code))
            code_item.setFont(mono_font)
            if r.status_code == 301:
                code_item.setForeground(QColor("#38BDF8"))
            else:
                code_item.setForeground(QColor("#FB923C"))
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, code_item)

            # 6. Tipe & Query info
            redir_type = getattr(r, "redirect_type", "Static")
            q_info = "Query: ON" if r.preserve_query_string else "Query: OFF"
            path_str = f"{redir_type}  •  {q_info}"
            pres_item = QTableWidgetItem(path_str)
            pres_item.setFont(mono_font)
            if redir_type == "Static":
                pres_item.setForeground(QColor("#34D399"))
            else:
                pres_item.setForeground(QColor("#FBBF24"))
            self.table.setItem(row, 6, pres_item)

            # 7. Status (Enabled / Disabled)
            stat_str = "● Aktif" if r.enabled else "○ Nonaktif"
            status_item = QTableWidgetItem(stat_str)
            if r.enabled:
                status_item.setForeground(QColor("#34D399"))
            else:
                status_item.setForeground(QColor("#64748B"))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 7, status_item)

            # 8. Action Buttons Container
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)

            # Edit Button
            edit_btn = QPushButton("Edit")
            edit_btn.setProperty("class", "btn-action-edit")
            edit_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            edit_btn.clicked.connect(lambda checked=False, rule=r: self._open_edit_dialog(rule))
            action_layout.addWidget(edit_btn)

            # Toggle Status Button
            toggle_btn = QPushButton("Nonaktifkan" if r.enabled else "Aktifkan")
            toggle_btn.setProperty("class", "btn-action-toggle")
            toggle_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            toggle_btn.clicked.connect(lambda checked=False, rule=r: self._toggle_rule(rule))
            action_layout.addWidget(toggle_btn)

            # Test Button
            test_btn = QPushButton("Test")
            test_btn.setProperty("class", "btn-action-test")
            test_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            test_btn.clicked.connect(lambda checked=False, rule=r: self._open_test_dialog(rule))
            action_layout.addWidget(test_btn)

            # Delete Button (1/1)
            del_btn = QPushButton("Hapus")
            del_btn.setProperty("class", "btn-action-delete")
            del_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            del_btn.setToolTip("Hapus aturan ini dari Cloudflare (1/1)")
            del_btn.clicked.connect(lambda checked=False, rule=r: self._confirm_delete(rule))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 8, action_widget)

    def _on_redirects_error(self, err_msg: str):
        self.progress_bar.hide()
        self.refresh_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.show_toast.emit(f"Gagal memuat aturan redirect: {err_msg}", True)

    def _get_current_zone_info(self) -> tuple[Optional[str], str]:
        zid = self.zone_combo.currentData()
        txt = self.zone_combo.currentText().strip()
        if not zid or not txt:
            return None, ""
        if zid == "all":
            return "all", "Semua Domain"
        parts = txt.split()
        zname = parts[0] if parts else ""
        return zid, zname

    def _open_add_dialog(self):
        zid, zname = self._get_current_zone_info()
        if not zid:
            self.show_toast.emit("Pilih zona domain terlebih dahulu.", True)
            return

        if not self.zones:
            self.show_toast.emit("Belum ada zona domain yang tersedia.", True)
            return

        if zid == "all":
            first_z = self.zones[0]
            zone_id = first_z.id
            zone_name = first_z.name
            existing_rule = next((r for r in self.current_rules if r.zone_id == zone_id), None)
        else:
            matching_zone = next((z for z in self.zones if z.id == zid), None)
            zone_name = matching_zone.name if matching_zone else zname
            zone_id = zid
            existing_rule = next((r for r in self.current_rules if r.zone_id == zid), None)

        dlg = RedirectFormDialog(
            zone_name=zone_name,
            zone_id=zone_id,
            existing_rule=existing_rule,
            all_zones=self.zones,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.validated_data
            target_zid = data.get("zone_id", zone_id)
            target_source = data["source_hostname"]

            self.progress_bar.show()
            self.add_btn.setEnabled(False)

            matched_zone = next((z for z in self.zones if z.id == target_zid), None)
            if matched_zone and matched_zone.account_id:
                try:
                    active_session.switch_account(matched_zone.account_id)
                except Exception:
                    pass

            worker = CreateRedirectWorker(
                zone_id=target_zid,
                source_hostname=target_source,
                destination_url=data["destination_url"],
                coverage=data["coverage"],
                status_code=data["status_code"],
                preserve_path=data["preserve_path"],
                preserve_query_string=data["preserve_query_string"],
                enabled=data["enabled"],
                parent=self,
            )
            worker.finished.connect(self._on_mutation_success)
            worker.error.connect(self._on_mutation_error)
            worker.start()

    def _open_edit_dialog(self, rule: RedirectRule):
        zone_id = rule.zone_id
        matching_z = next((z for z in self.zones if z.id == zone_id), None)
        zone_name = rule.zone_name or (matching_z.name if matching_z else rule.source_hostname)
        if not zone_name or zone_name == "*":
            zone_name = "Domain"

        if matching_z and matching_z.account_id:
            try:
                active_session.switch_account(matching_z.account_id)
            except Exception:
                pass

        dlg = RedirectFormDialog(
            zone_name=zone_name,
            zone_id=zone_id,
            existing_rule=rule,
            all_zones=self.zones,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.validated_data
            self.progress_bar.show()

            worker = UpdateRedirectWorker(
                zone_id=rule.zone_id,
                ruleset_id=rule.ruleset_id,
                rule_id=rule.id,
                source_hostname=data["source_hostname"],
                destination_url=data["destination_url"],
                coverage=data["coverage"],
                status_code=data["status_code"],
                preserve_path=data["preserve_path"],
                preserve_query_string=data["preserve_query_string"],
                enabled=data["enabled"],
                parent=self,
            )
            worker.finished.connect(self._on_mutation_success)
            worker.error.connect(self._on_mutation_error)
            worker.start()

    def _toggle_rule(self, rule: RedirectRule):
        new_state = not rule.enabled
        self.progress_bar.show()
        worker = ToggleRedirectWorker(
            zone_id=rule.zone_id,
            ruleset_id=rule.ruleset_id,
            rule_id=rule.id,
            enabled=new_state,
            parent=self,
        )
        worker.finished.connect(self._on_mutation_success)
        worker.error.connect(self._on_mutation_error)
        worker.start()

    def _open_test_dialog(self, rule: RedirectRule):
        dlg = TestRedirectDialog(rule, self)
        dlg.exec()

    def _on_mutation_success(self, res: dict):
        self.progress_bar.hide()
        self.add_btn.setEnabled(True)
        self.show_toast.emit("Perubahan aturan berhasil disimpan ke Cloudflare!", False)
        self.load_redirects_for_selected_zone()

    def _on_mutation_error(self, err_msg: str):
        self.progress_bar.hide()
        self.add_btn.setEnabled(True)
        self.show_toast.emit(f"Gagal memperbarui aturan di Cloudflare: {err_msg}", True)

    def _confirm_delete(self, rule: RedirectRule):
        details = (
            f"Domain Sumber: {rule.source_display}\n"
            f"URL Tujuan   : {rule.destination_url}\n"
            f"Status/Mode  : {rule.status_code} ({rule.mode})\n"
            f"Rule ID      : {rule.id}"
        )
        dlg = DangerConfirmDialog(
            title="Konfirmasi Hapus Redirect (1/1)",
            message=f"Apakah Anda yakin ingin menghapus aturan redirect untuk '{rule.source_display}' secara permanen?",
            details=details,
            confirm_btn_text="🗑️ Hapus Aturan Ini",
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.progress_bar.show()
            worker = DeleteRedirectWorker(
                zone_id=rule.zone_id,
                ruleset_id=rule.ruleset_id,
                rule_id=rule.id,
                parent=self,
            )
            worker.finished.connect(self._on_delete_success)
            worker.error.connect(self._on_mutation_error)
            worker.start()

    def _on_delete_success(self, res: dict):
        self.progress_bar.hide()
        self.show_toast.emit("Aturan redirect berhasil dihapus dari Cloudflare.", False)
        self.load_redirects_for_selected_zone()

    def clear(self):
        self.table.setRowCount(0)
        self.current_rules = []
        self.current_ruleset_id = None
        self.empty_lbl.hide()
        self.bulk_bar.hide()

    def _toggle_select_all_clicked(self):
        total = self.table.rowCount()
        if total == 0:
            return
        selected = self._get_selected_rules()
        should_check = len(selected) < total
        for row in range(total):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox):
                chk.blockSignals(True)
                chk.setChecked(should_check)
                chk.blockSignals(False)
        self._update_bulk_selection_state()

    def _deselect_all(self):
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox):
                chk.blockSignals(True)
                chk.setChecked(False)
                chk.blockSignals(False)
        self._update_bulk_selection_state()

    def _update_bulk_selection_state(self):
        count = len(self._get_selected_rules())
        total = self.table.rowCount()

        if hasattr(self, "select_all_btn"):
            if total > 0 and count == total:
                self.select_all_btn.setText("⬜ Batal Pilih Semua")
            else:
                self.select_all_btn.setText("☑️ Pilih Semua di List")

        if count > 0:
            self.bulk_sel_lbl.setText(f"<b>{count}</b> aturan dipilih dalam list:")
            self.bulk_delete_btn.setText(f"🗑️ Hapus Terpilih ({count})")
            self.bulk_bar.show()
        else:
            self.bulk_bar.hide()

    def _get_selected_rules(self) -> List[RedirectRule]:
        selected = []
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked() and row < len(self.current_rules):
                selected.append(self.current_rules[row])
        return selected

    def _open_bulk_dialog(self):
        cur_zid = self.zone_combo.currentData()
        preselected = [cur_zid] if cur_zid else []
        dlg = BulkRedirectDialog(self.zones, preselected_zone_ids=preselected, parent=self)
        dlg.bulk_completed.connect(self._on_bulk_completed)
        dlg.exec()

    def _open_delete_all_dialog(self):
        zone_id, zone_name = self._get_current_zone_info()
        if not zone_id or not zone_name:
            self.show_toast.emit("Pilih zona domain terlebih dahulu.", True)
            return

        dlg = DeleteAllRedirectsDialog(
            zone_name=zone_name,
            zone_id=zone_id,
            current_rules=self.current_rules,
            all_zones=self.zones,
            parent=self,
        )
        dlg.rules_deleted.connect(lambda count: self.show_toast.emit(f"{count} aturan redirect berhasil dihapus!", False))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_redirects_for_selected_zone()

    def _on_bulk_completed(self, count: int):
        self.show_toast.emit(f"{count} aturan redirect berhasil diproses via Bulk Manager!", False)
        self.load_redirects_for_selected_zone()

    def _bulk_toggle(self, enabled: bool):
        selected = self._get_selected_rules()
        if not selected:
            return

        action_name = "mengaktifkan" if enabled else "menonaktifkan"
        reply = QMessageBox.question(
            self,
            "Konfirmasi Ubah Status Terpilih",
            f"Apakah Anda yakin ingin {action_name} <b>{len(selected)}</b> aturan redirect terpilih di dalam list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.progress_bar.show()
        items = [
            {
                "zone_id": r.zone_id,
                "ruleset_id": r.ruleset_id,
                "rule_id": r.id,
                "source_hostname": r.source_hostname,
            }
            for r in selected
        ]
        worker = BulkToggleRedirectsWorker(items, enabled=enabled, parent=self)
        worker.finished.connect(self._on_bulk_toggle_finished)
        worker.error.connect(self._on_mutation_error)
        worker.start()

    def _on_bulk_toggle_finished(self, summary: dict):
        self.progress_bar.hide()
        succ = summary.get("success", 0)
        self.show_toast.emit(f"Status {succ} aturan berhasil diperbarui.", False)
        self.load_redirects_for_selected_zone()

    def _bulk_delete(self):
        selected = self._get_selected_rules()
        if not selected:
            return

        reply = QMessageBox.warning(
            self,
            "Konfirmasi Hapus Terpilih di List",
            f"PERINGATAN: Apakah Anda yakin ingin menghapus <b>{len(selected)}</b> aturan redirect terpilih secara permanen dari Cloudflare?\n\n"
            "Tindakan ini diproses langsung di tools dan tidak dapat dibatalkan.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.progress_bar.show()
        items = [
            {
                "zone_id": r.zone_id,
                "ruleset_id": r.ruleset_id,
                "rule_id": r.id,
                "source_hostname": r.source_hostname,
            }
            for r in selected
        ]
        worker = BulkDeleteRedirectsWorker(items, parent=self)
        worker.finished.connect(self._on_bulk_delete_finished)
        worker.error.connect(self._on_mutation_error)
        worker.start()

    def _on_bulk_delete_finished(self, summary: dict):
        self.progress_bar.hide()
        succ = summary.get("success", 0)
        self.show_toast.emit(f"Berhasil menghapus {succ} aturan redirect dari list!", False)
        self.load_redirects_for_selected_zone()
