"""Bulk Redirect Manager Dialog.
Supports:
1. Multi-Domain Batch Setup: Select multiple domains with checkboxes and apply uniform redirect rules.
2. Raw Text / CSV Batch Import: Parse domain -> url or CSV format and match against loaded Cloudflare zones.
3. Asynchronous execution with real-time progress bar, error handling, and audit reporting.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QRadioButton,
    QButtonGroup,
    QCheckBox,
    QProgressBar,
    QMessageBox,
    QFrame,
    QScrollArea,
    QApplication,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from src.cloudflare.zones import ZoneItem
from src.security.validation import (
    normalize_hostname,
    validate_destination_url,
    validate_status_code,
)
from src.ui.workers import BulkCreateRedirectsWorker, BulkPurgeRedirectsWorker


class BulkRedirectDialog(QDialog):
    """Modern modal dialog for batch redirect creation across multiple Cloudflare zones."""

    bulk_completed = Signal(int)  # emits number of created rules

    def __init__(self, zones: List[ZoneItem], preselected_zone_ids: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.zones = zones or []
        self.preselected_zone_ids = set(preselected_zone_ids or [])
        self.worker: Optional[BulkCreateRedirectsWorker] = None

        self.setWindowTitle("⚡ Bulk Redirect Manager — ALL INCOMING 301 & 302")
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(960, max(760, int(avail.width() * 0.88)))
            target_h = min(620, max(460, int(avail.height() * 0.88)))
            self.resize(target_w, target_h)
        else:
            self.resize(880, 560)
        self.setMinimumSize(720, 440)
        self.setStyleSheet("QDialog { background-color: #0F172A; border: 1px solid #1E293B; border-radius: 10px; }")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # Header Title & Description
        header_frame = QFrame()
        header_frame.setProperty("class", "card")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(3)

        title_lbl = QLabel("Bulk Redirect Manager (Batch URL Forwarding)")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        header_layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Terapkan aturan ALL INCOMING Single Redirect ke banyak domain sekaligus atau impor via format teks/CSV."
        )
        desc_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        header_layout.addWidget(desc_lbl)
        main_layout.addWidget(header_frame)

        # Tabs: Tab 1 (Multi-Domain Batch) & Tab 2 (Text/CSV Import)
        self.tabs = QTabWidget()

        # TAB 1: Multi-Domain Batch Selection
        tab1_widget = QWidget()
        self._setup_tab1(tab1_widget)
        self.tabs.addTab(tab1_widget, "🌐 Pilih Banyak Domain Sekaligus")

        # TAB 2: Text / CSV Import
        tab2_widget = QWidget()
        self._setup_tab2(tab2_widget)
        self.tabs.addTab(tab2_widget, "📝 Impor Teks / Format CSV")

        # TAB 3: Bulk Purge 301/302
        tab3_widget = QWidget()
        self._setup_tab3(tab3_widget)
        self.tabs.addTab(tab3_widget, "🗑️ Hapus Massal 301/302")

        main_layout.addWidget(self.tabs, stretch=1)

        # Bottom Progress & Control Bar
        self.progress_frame = QFrame()
        self.progress_frame.setProperty("class", "card")
        self.progress_frame.hide()
        prog_layout = QVBoxLayout(self.progress_frame)
        prog_layout.setContentsMargins(14, 10, 14, 10)
        prog_layout.setSpacing(6)

        self.progress_lbl = QLabel("Menyiapkan proses bulk...")
        self.progress_lbl.setStyleSheet("font-weight: 600; color: #00F0FF; font-size: 12px;")
        prog_layout.addWidget(self.progress_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        prog_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.progress_frame)

        # Footer Actions
        footer_layout = QHBoxLayout()
        self.status_footer_lbl = QLabel(f"Total zona domain terdeteksi: <b>{len(self.zones)}</b>")
        self.status_footer_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        footer_layout.addWidget(self.status_footer_lbl)

        footer_layout.addStretch()

        self.close_btn = QPushButton("Tutup")
        self.close_btn.setProperty("class", "btn-secondary")
        self.close_btn.clicked.connect(self.close)
        footer_layout.addWidget(self.close_btn)

        main_layout.addLayout(footer_layout)

    def _setup_tab1(self, parent_widget: QWidget):
        layout = QHBoxLayout(parent_widget)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(14)

        # Left: Domain Selection List
        left_box = QFrame()
        left_box.setProperty("class", "card")
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        left_title = QLabel("1. Pilih Domain Sumber:")
        left_title.setStyleSheet("font-weight: 700; color: #FFFFFF; font-size: 13px;")
        left_layout.addWidget(left_title)

        # Search box
        self.tab1_search = QLineEdit()
        self.tab1_search.setPlaceholderText("🔍 Cari domain...")
        self.tab1_search.textChanged.connect(self._filter_tab1_table)
        left_layout.addWidget(self.tab1_search)

        # Select all / Clear buttons
        sel_row = QHBoxLayout()
        sel_all_btn = QPushButton("Pilih Semua")
        sel_all_btn.setProperty("class", "btn-secondary")
        sel_all_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        sel_all_btn.clicked.connect(self._select_all_tab1)
        sel_row.addWidget(sel_all_btn)

        clr_all_btn = QPushButton("Kosongkan Pilihan")
        clr_all_btn.setProperty("class", "btn-secondary")
        clr_all_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        clr_all_btn.clicked.connect(self._clear_all_tab1)
        sel_row.addWidget(clr_all_btn)

        paste_sel_btn = QPushButton("📋 Pilih dari Daftar Teks")
        paste_sel_btn.setProperty("class", "btn-secondary")
        paste_sel_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        paste_sel_btn.setToolTip("Tempelkan daftar domain untuk mencentang otomatis")
        paste_sel_btn.clicked.connect(self._select_from_pasted_list)
        sel_row.addWidget(paste_sel_btn)

        sel_row.addStretch()
        self.tab1_count_lbl = QLabel("0 dipilih")
        self.tab1_count_lbl.setStyleSheet("color: #00F0FF; font-weight: 700; font-size: 12px;")
        sel_row.addWidget(self.tab1_count_lbl)
        left_layout.addLayout(sel_row)

        # Table of zones
        self.tab1_table = QTableWidget()
        self.tab1_table.setColumnCount(4)
        self.tab1_table.setHorizontalHeaderLabels(["Pilih", "Domain", "Akun CF", "Status"])
        t1_header = self.tab1_table.horizontalHeader()
        t1_header.setMinimumSectionSize(50)
        t1_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        t1_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        t1_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        t1_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tab1_table.setColumnWidth(2, 130)
        self.tab1_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tab1_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        left_layout.addWidget(self.tab1_table)

        layout.addWidget(left_box, stretch=3)

        # Right: Redirect Settings Form wrapped in ScrollArea for small laptop screens
        right_box = QFrame()
        right_box.setProperty("class", "card")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        right_title = QLabel("2. Pengaturan Redirect Massal:")
        right_title.setStyleSheet("font-weight: 700; color: #FFFFFF; font-size: 13px;")
        right_layout.addWidget(right_title)

        # Destination URL
        dest_lbl = QLabel("URL Tujuan:")
        dest_lbl.setStyleSheet("font-weight: 600; color: #E2E8F0; font-size: 11px;")
        right_layout.addWidget(dest_lbl)

        self.tab1_dest_input = QLineEdit()
        self.tab1_dest_input.setPlaceholderText("https://domain-tujuan.com/")
        right_layout.addWidget(self.tab1_dest_input)

        # Status Code Radio
        status_lbl = QLabel("Status HTTP:")
        status_lbl.setStyleSheet("font-weight: 600; color: #E2E8F0; font-size: 11px;")
        right_layout.addWidget(status_lbl)

        stat_frame = QFrame()
        stat_frame.setStyleSheet("background: #090D16; border: 1px solid #1E293B; border-radius: 6px; padding: 6px;")
        stat_layout = QVBoxLayout(stat_frame)
        stat_layout.setSpacing(4)
        self.tab1_stat_group = QButtonGroup(self)
        self.tab1_stat_301 = QRadioButton("301 — Permanent (Wajib)")
        self.tab1_stat_302 = QRadioButton("302 — Temporary")
        self.tab1_stat_301.setChecked(True)
        self.tab1_stat_group.addButton(self.tab1_stat_301, 301)
        self.tab1_stat_group.addButton(self.tab1_stat_302, 302)
        stat_layout.addWidget(self.tab1_stat_301)
        stat_layout.addWidget(self.tab1_stat_302)
        right_layout.addWidget(stat_frame)

        # Coverage Radio
        cov_lbl = QLabel("Cakupan Domain:")
        cov_lbl.setStyleSheet("font-weight: 600; color: #E2E8F0; font-size: 11px;")
        right_layout.addWidget(cov_lbl)

        cov_frame = QFrame()
        cov_frame.setStyleSheet("background: #090D16; border: 1px solid #1E293B; border-radius: 6px; padding: 6px;")
        cov_layout = QVBoxLayout(cov_frame)
        cov_layout.setSpacing(4)
        self.tab1_cov_group = QButtonGroup(self)
        self.tab1_cov_all = QRadioButton("All incoming requests (Apex & subdomain)")
        self.tab1_cov_both = QRadioButton("Domain Utama & www (Keduanya)")
        self.tab1_cov_apex = QRadioButton("Domain Utama saja")
        self.tab1_cov_www = QRadioButton("www saja")
        self.tab1_cov_all.setChecked(True)
        self.tab1_cov_group.addButton(self.tab1_cov_all, 0)
        self.tab1_cov_group.addButton(self.tab1_cov_both, 1)
        self.tab1_cov_group.addButton(self.tab1_cov_apex, 2)
        self.tab1_cov_group.addButton(self.tab1_cov_www, 3)
        cov_layout.addWidget(self.tab1_cov_all)
        cov_layout.addWidget(self.tab1_cov_both)
        cov_layout.addWidget(self.tab1_cov_apex)
        cov_layout.addWidget(self.tab1_cov_www)
        right_layout.addWidget(cov_frame)

        # Checkboxes for options
        tab1_type_lbl = QLabel("📌 Tipe: <b>Static URL</b> (Direkomendasikan Cloudflare)")
        tab1_type_lbl.setTextFormat(Qt.TextFormat.RichText)
        tab1_type_lbl.setStyleSheet("color: #34D399; font-size: 11px;")
        right_layout.addWidget(tab1_type_lbl)

        self.tab1_preserve_path = QCheckBox("Preserve Path")
        self.tab1_preserve_path.setChecked(False)
        self.tab1_preserve_path.hide()

        self.tab1_preserve_query = QCheckBox("Preserve Query (?key=val)")
        self.tab1_preserve_query.setChecked(True)
        right_layout.addWidget(self.tab1_preserve_query)

        self.tab1_enabled_chk = QCheckBox("Status Rule: Langsung Aktifkan")
        self.tab1_enabled_chk.setChecked(True)
        right_layout.addWidget(self.tab1_enabled_chk)

        right_layout.addSpacing(6)

        # Submit button
        self.tab1_submit_btn = QPushButton("🚀 Terapkan Bulk Redirect ke Domain Terpilih")
        self.tab1_submit_btn.setProperty("class", "btn-primary")
        self.tab1_submit_btn.clicked.connect(self._on_tab1_submit)
        right_layout.addWidget(self.tab1_submit_btn)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setStyleSheet("background: transparent;")
        right_scroll.setWidget(right_box)
        layout.addWidget(right_scroll, stretch=2)
        self._populate_tab1_table()

    def _setup_tab2(self, parent_widget: QWidget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(12)

        info_box = QFrame()
        info_box.setStyleSheet("background: #090D16; border: 1px solid #1E293B; border-radius: 8px; padding: 10px;")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(3)
        lbl_help_title = QLabel("Format yang Didukung:")
        lbl_help_title.setStyleSheet("font-weight: 700; color: #38BDF8; font-size: 12px;")
        info_layout.addWidget(lbl_help_title)

        lbl_help_desc = QLabel(
            "• <code>domain1.com</code> (Cukup nama domain jika Anda mengisi 'URL Tujuan Bersama' di bawah)<br>"
            "• <code>domain2.com -> https://target.com/</code> [301/302]<br>"
            "• <code>domain3.com,https://target.com/,301</code> (Format CSV)<br>"
            "• <code>domain4.com https://target.com/ 302</code>"
        )
        lbl_help_desc.setStyleSheet("color: #CBD5E1; font-size: 11px;")
        info_layout.addWidget(lbl_help_desc)
        layout.addWidget(info_box)

        # Quick Target URL Frame
        quick_dest_frame = QFrame()
        quick_dest_frame.setStyleSheet("background: #090D16; border: 1px solid #1E293B; border-radius: 8px; padding: 10px;")
        quick_dest_layout = QHBoxLayout(quick_dest_frame)
        quick_dest_layout.setContentsMargins(10, 8, 10, 8)
        quick_dest_layout.setSpacing(10)

        quick_lbl = QLabel("🎯 URL Tujuan Bersama (Opsional):")
        quick_lbl.setStyleSheet("font-weight: 700; color: #38BDF8; font-size: 12px;")
        quick_dest_layout.addWidget(quick_lbl)

        self.tab2_default_dest = QLineEdit()
        self.tab2_default_dest.setPlaceholderText("https://domain-tujuan.com/ (Otomatis dipakai jika baris hanya berisi domain)")
        quick_dest_layout.addWidget(self.tab2_default_dest, stretch=1)

        self.tab2_default_code_301 = QRadioButton("301")
        self.tab2_default_code_302 = QRadioButton("302")
        self.tab2_default_code_301.setChecked(True)
        self.tab2_default_code_group = QButtonGroup(self)
        self.tab2_default_code_group.addButton(self.tab2_default_code_301, 301)
        self.tab2_default_code_group.addButton(self.tab2_default_code_302, 302)
        quick_dest_layout.addWidget(self.tab2_default_code_301)
        quick_dest_layout.addWidget(self.tab2_default_code_302)

        auto_format_btn = QPushButton("⚡ Tempelkan Target ke Teks")
        auto_format_btn.setProperty("class", "btn-secondary")
        auto_format_btn.setToolTip("Otomatis menambahkan '-> [URL Tujuan]' ke setiap domain pada kotak teks di bawah")
        auto_format_btn.setStyleSheet("padding: 5px 12px; font-size: 11px;")
        auto_format_btn.clicked.connect(self._auto_format_tab2_text)
        quick_dest_layout.addWidget(auto_format_btn)

        layout.addWidget(quick_dest_frame)

        # Options row for Tab 2
        tab2_opts_row = QHBoxLayout()
        tab2_opts_row.setSpacing(14)

        tab2_type_lbl = QLabel("📌 Tipe: <b>Static URL</b>")
        tab2_type_lbl.setTextFormat(Qt.TextFormat.RichText)
        tab2_type_lbl.setStyleSheet("color: #34D399; font-size: 11px;")
        tab2_opts_row.addWidget(tab2_type_lbl)

        self.tab2_preserve_path = QCheckBox("Preserve Path")
        self.tab2_preserve_path.setChecked(False)
        self.tab2_preserve_path.hide()

        self.tab2_preserve_query = QCheckBox("Preserve Query String (?key=val)")
        self.tab2_preserve_query.setChecked(True)
        tab2_opts_row.addWidget(self.tab2_preserve_query)
        tab2_opts_row.addStretch()

        layout.addLayout(tab2_opts_row)

        # Text area with compact height so table below has enough space
        self.tab2_text = QTextEdit()
        self.tab2_text.setPlaceholderText(
            "Paste daftar redirect di sini (satu baris per domain)...\n\n"
            "Contoh:\n"
            "domainlama.com -> https://domainbaru.com/\n"
            "domainlain.com,https://tujuan.com/,301\n"
            "domainketiga.com https://tujuan.com/ 302\n"
            "domainkeempat.com (Otomatis pakai URL Tujuan Bersama di atas)"
        )
        self.tab2_text.setMinimumHeight(75)
        self.tab2_text.setMaximumHeight(120)
        layout.addWidget(self.tab2_text)

        # Parse & Validate Button
        parse_row = QHBoxLayout()
        parse_btn = QPushButton("🔍 Parse & Validasi")
        parse_btn.setProperty("class", "btn-secondary")
        parse_btn.clicked.connect(self._parse_tab2_text)
        parse_row.addWidget(parse_btn)

        self.tab2_parse_summary = QLabel("")
        self.tab2_parse_summary.setStyleSheet("font-weight: 600; font-size: 11px;")
        parse_row.addWidget(self.tab2_parse_summary)
        parse_row.addStretch()

        self.tab2_submit_btn = QPushButton("🚀 Terapkan Semua Aturan Terverifikasi")
        self.tab2_submit_btn.setProperty("class", "btn-primary")
        self.tab2_submit_btn.setEnabled(False)
        self.tab2_submit_btn.clicked.connect(self._on_tab2_submit)
        parse_row.addWidget(self.tab2_submit_btn)

        layout.addLayout(parse_row)

        # Parsed items preview table
        self.tab2_table = QTableWidget()
        self.tab2_table.setColumnCount(7)
        self.tab2_table.setHorizontalHeaderLabels([
            "Status", "Domain Sumber", "Akun CF", "Zona Cloudflare", "URL Tujuan", "Status Code", "Keterangan"
        ])
        t2_header = self.tab2_table.horizontalHeader()
        t2_header.setMinimumSectionSize(65)
        t2_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        t2_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        t2_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        t2_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        t2_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        t2_header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        t2_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        self.tab2_table.setColumnWidth(1, 150)
        self.tab2_table.setColumnWidth(2, 130)
        self.tab2_table.setColumnWidth(3, 140)
        self.tab2_table.setColumnWidth(6, 170)
        self.tab2_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tab2_table.setMinimumHeight(140)
        layout.addWidget(self.tab2_table, stretch=1)

        self.tab2_parsed_items: List[Dict[str, Any]] = []

    def _populate_tab1_table(self):
        self.tab1_table.setRowCount(len(self.zones))
        for row, z in enumerate(self.zones):
            chk = QCheckBox()
            if z.id in self.preselected_zone_ids:
                chk.setChecked(True)
            chk.toggled.connect(self._update_tab1_count)
            self.tab1_table.setCellWidget(row, 0, chk)

            name_item = QTableWidgetItem(z.name)
            self.tab1_table.setItem(row, 1, name_item)

            acc_item = QTableWidgetItem(f"👤 {z.account_label or 'Akun Utama'}")
            acc_item.setForeground(QColor("#38BDF8"))
            self.tab1_table.setItem(row, 2, acc_item)

            is_active = (z.status.lower() == "active")
            stat_item = QTableWidgetItem(f"● {z.status.upper()}" if is_active else f"○ {z.status.upper()}")
            stat_item.setForeground(QColor("#34D399" if is_active else "#FBBF24"))
            self.tab1_table.setItem(row, 3, stat_item)

        self._update_tab1_count()

    def _filter_tab1_table(self, query: str):
        query = query.strip().lower()
        for row in range(self.tab1_table.rowCount()):
            item = self.tab1_table.item(row, 1)
            if not query or (item and query in item.text().lower()):
                self.tab1_table.setRowHidden(row, False)
            else:
                self.tab1_table.setRowHidden(row, True)

    def _select_all_tab1(self):
        for row in range(self.tab1_table.rowCount()):
            if not self.tab1_table.isRowHidden(row):
                chk = self.tab1_table.cellWidget(row, 0)
                if isinstance(chk, QCheckBox):
                    chk.setChecked(True)
        self._update_tab1_count()

    def _clear_all_tab1(self):
        for row in range(self.tab1_table.rowCount()):
            chk = self.tab1_table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox):
                chk.setChecked(False)
        self._update_tab1_count()

    def _select_from_pasted_list(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("📋 Pilih Domain Berdasarkan Daftar Teks")
        dlg.resize(480, 320)
        vbox = QVBoxLayout(dlg)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(10)

        lbl = QLabel("Tempelkan daftar domain yang ingin dicentang (pisahkan baris baru / spasi / koma):")
        lbl.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        vbox.addWidget(lbl)

        txt = QTextEdit(dlg)
        txt.setPlaceholderText("domain1.com\ndomain2.com\n...")
        vbox.addWidget(txt)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Batal", dlg)
        btn_cancel.setProperty("class", "btn-secondary")
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_cancel)

        btn_ok = QPushButton("✓ Centang Domain", dlg)
        btn_ok.setProperty("class", "btn-primary")
        btn_row.addWidget(btn_ok)
        vbox.addLayout(btn_row)

        def on_apply():
            raw_text = txt.toPlainText()
            import re
            tokens = [t.lower().strip() for t in re.split(r"[\r\n\t,; ]+", raw_text) if t.strip()]
            cleaned = set()
            for t in tokens:
                t = t.removeprefix("http://").removeprefix("https://").split("/")[0].strip()
                if t:
                    cleaned.add(t)
                    if t.startswith("www."):
                        cleaned.add(t[4:])
            matched_count = 0
            for row in range(self.tab1_table.rowCount()):
                zone_name = self.zones[row].name.lower()
                chk = self.tab1_table.cellWidget(row, 0)
                if isinstance(chk, QCheckBox):
                    if zone_name in cleaned or f"www.{zone_name}" in cleaned:
                        chk.setChecked(True)
                        matched_count += 1
            self._update_tab1_count()
            dlg.accept()
            QMessageBox.information(self, "Hasil Pemilihan", f"Berhasil mencentang {matched_count} domain yang cocok dari daftar.")

        btn_ok.clicked.connect(on_apply)
        dlg.exec()

    def _update_tab1_count(self):
        count = 0
        for row in range(self.tab1_table.rowCount()):
            chk = self.tab1_table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                count += 1
        self.tab1_count_lbl.setText(f"{count} domain dipilih")

    def _on_tab1_submit(self):
        # Gather selected zones
        selected_zones: List[ZoneItem] = []
        for row in range(self.tab1_table.rowCount()):
            chk = self.tab1_table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                selected_zones.append(self.zones[row])

        if not selected_zones:
            QMessageBox.warning(self, "Peringatan", "Pilih minimal satu domain terlebih dahulu.")
            return

        dest_url = self.tab1_dest_input.text().strip()
        if not dest_url:
            QMessageBox.warning(self, "Peringatan", "Masukkan URL Tujuan terlebih dahulu.")
            return

        try:
            norm_dest, _ = validate_destination_url(dest_url)
        except Exception as exc:
            QMessageBox.critical(self, "Validasi Gagal", f"URL Tujuan tidak valid:\n{exc}")
            return

        status_code = self.tab1_stat_group.checkedId()
        cov_id = self.tab1_cov_group.checkedId()
        cov_map = {0: "all", 1: "both", 2: "apex", 3: "www"}
        coverage = cov_map.get(cov_id, "all")

        preserve_p = self.tab1_preserve_path.isChecked()
        preserve_q = self.tab1_preserve_query.isChecked()
        enabled = self.tab1_enabled_chk.isChecked()

        confirm_msg = (
            f"Anda akan menerapkan aturan ALL INCOMING Single Redirect ke <b>{len(selected_zones)}</b> domain:\n\n"
            f"• URL Tujuan: {norm_dest}\n"
            f"• Tipe URL: STATIC\n"
            f"• Status Code: {status_code}\n"
            f"• Cakupan: {coverage.upper()}\n"
            f"• Preserve Query: {'ON' if preserve_q else 'OFF'}\n"
            f"• Status Rule: {'Aktif' if enabled else 'Nonaktif'}\n\n"
            f"Lanjutkan proses bulk?"
        )
        reply = QMessageBox.question(
            self,
            "Konfirmasi Bulk Redirect",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Prepare batch payloads
        items_to_create = []
        for z in selected_zones:
            items_to_create.append({
                "zone_id": z.id,
                "account_id": z.account_id,
                "source_hostname": z.name,
                "destination_url": norm_dest,
                "coverage": coverage,
                "status_code": status_code,
                "preserve_path": preserve_p,
                "preserve_query_string": preserve_q,
                "enabled": enabled,
            })

        self._start_bulk_worker(items_to_create)

    def _auto_format_tab2_text(self):
        target = self.tab2_default_dest.text().strip()
        if not target:
            QMessageBox.warning(
                self,
                "Perhatian",
                "Masukkan URL Tujuan Bersama terlebih dahulu di kolom samping (contoh: https://target.com/).",
            )
            return

        if not target.startswith("http://") and not target.startswith("https://"):
            target = "https://" + target

        code = self.tab2_default_code_group.checkedId()
        text = self.tab2_text.toPlainText()
        lines = text.split("\n")
        new_lines = []
        for line in lines:
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("#"):
                new_lines.append(line)
                continue
            if "->" in trimmed or "," in trimmed:
                new_lines.append(line)
            else:
                parts = trimmed.split()
                if len(parts) == 1:
                    new_lines.append(f"{parts[0]} -> {target} {code}")
                elif len(parts) == 2 and parts[1].isdigit():
                    new_lines.append(f"{parts[0]} -> {target} {parts[1]}")
                else:
                    new_lines.append(line)
        self.tab2_text.setPlainText("\n".join(new_lines))
        self._parse_tab2_text()

    def _parse_tab2_text(self):
        text = self.tab2_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Info", "Masukkan daftar baris terlebih dahulu.")
            return

        default_target = self.tab2_default_dest.text().strip()
        if default_target and not default_target.startswith("http://") and not default_target.startswith("https://"):
            default_target = "https://" + default_target
        default_code = self.tab2_default_code_group.checkedId()

        lines = [line.strip() for line in text.split("\n") if line.strip() and not line.strip().startswith("#")]
        zone_map = {z.name.lower(): z for z in self.zones}

        parsed: List[Dict[str, Any]] = []
        for line in lines:
            src = ""
            dest = ""
            code = default_code if default_code in (301, 302) else 301

            # Try formats:
            # 1. source -> destination [code]
            if "->" in line:
                parts = line.split("->")
                src = parts[0].strip()
                rem = parts[1].strip().split()
                dest = rem[0].strip() if rem else ""
                if len(rem) > 1 and rem[1].isdigit():
                    code = int(rem[1])
            # 2. source,destination,code (CSV)
            elif "," in line:
                parts = [p.strip() for p in line.split(",")]
                src = parts[0]
                dest = parts[1] if len(parts) > 1 else ""
                if len(parts) > 2 and parts[2].isdigit():
                    code = int(parts[2])
            # 3. whitespace separated
            else:
                parts = line.split()
                src = parts[0]
                dest = parts[1] if len(parts) > 1 else ""
                if len(parts) > 2 and parts[2].isdigit():
                    code = int(parts[2])

            # Fallback to default_target if dest is empty
            if not dest and default_target:
                dest = default_target
                code = default_code

            # Validation
            matched_zone = None
            is_valid = False
            err_reason = ""

            try:
                norm_src = normalize_hostname(src)
                # Find matching zone (either exact match or parent domain)
                if norm_src.lower() in zone_map:
                    matched_zone = zone_map[norm_src.lower()]
                else:
                    # check apex if www
                    apex = norm_src[4:] if norm_src.startswith("www.") else norm_src
                    if apex.lower() in zone_map:
                        matched_zone = zone_map[apex.lower()]

                if not matched_zone:
                    err_reason = "Zona tidak ditemukan di akun Cloudflare aktif"
                else:
                    if not dest:
                        raise ValueError("URL tujuan kosong. Isi 'URL Tujuan Bersama' di atas atau gunakan: domain.com -> https://target.com/")
                    norm_dest, _ = validate_destination_url(dest, source_host=norm_src)
                    valid_code = validate_status_code(code)
                    is_valid = True
                    dest = norm_dest
                    code = valid_code
            except Exception as exc:
                err_reason = str(exc)

            parsed.append({
                "valid": is_valid,
                "source": src,
                "zone": matched_zone,
                "destination": dest,
                "status_code": code,
                "reason": "Siap diterapkan" if is_valid else err_reason,
            })

        self.tab2_parsed_items = parsed
        self.tab2_table.setRowCount(len(parsed))

        valid_count = sum(1 for p in parsed if p["valid"])
        mono_font = QFont("Consolas", 9)
        self.tab2_table.verticalHeader().setDefaultSectionSize(28)

        for row, p in enumerate(parsed):
            stat_item = QTableWidgetItem("● Valid" if p["valid"] else "○ Gagal")
            stat_item.setFont(mono_font)
            stat_item.setForeground(QColor("#34D399" if p["valid"] else "#F87171"))
            stat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tab2_table.setItem(row, 0, stat_item)

            src_item = QTableWidgetItem(p["source"])
            src_item.setFont(mono_font)
            src_item.setForeground(QColor("#F8FAFC"))
            self.tab2_table.setItem(row, 1, src_item)

            acc_str = f"👤 {p['zone'].account_label}" if (p["zone"] and getattr(p["zone"], "account_label", None)) else "-"
            acc_item = QTableWidgetItem(acc_str)
            acc_item.setFont(mono_font)
            acc_item.setForeground(QColor("#38BDF8"))
            self.tab2_table.setItem(row, 2, acc_item)

            z_str = p["zone"].name if p["zone"] else "-"
            z_item = QTableWidgetItem(z_str)
            z_item.setFont(mono_font)
            z_item.setForeground(QColor("#94A3B8"))
            self.tab2_table.setItem(row, 3, z_item)

            dest_item = QTableWidgetItem(p["destination"])
            dest_item.setFont(mono_font)
            dest_item.setForeground(QColor("#38BDF8"))
            self.tab2_table.setItem(row, 4, dest_item)

            code_item = QTableWidgetItem(str(p["status_code"]))
            code_item.setFont(mono_font)
            code_item.setForeground(QColor("#38BDF8" if p["status_code"] == 301 else "#FB923C"))
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tab2_table.setItem(row, 5, code_item)

            reas_item = QTableWidgetItem(p["reason"])
            if not p["valid"]:
                reas_item.setForeground(QColor("#FBBF24"))
            else:
                reas_item.setForeground(QColor("#94A3B8"))
            self.tab2_table.setItem(row, 6, reas_item)

        self.tab2_parse_summary.setText(f"Hasil: <b>{valid_count}</b> valid dari <b>{len(parsed)}</b> baris.")
        if valid_count > 0:
            self.tab2_submit_btn.setEnabled(True)
            self.tab2_parse_summary.setStyleSheet("color: #00F0FF; font-size: 12px;")
        else:
            self.tab2_submit_btn.setEnabled(False)
            self.tab2_parse_summary.setStyleSheet("color: #FF4D6D; font-size: 12px;")

    def _on_tab2_submit(self):
        valid_items = [p for p in self.tab2_parsed_items if p["valid"]]
        if not valid_items:
            return

        confirm_msg = (
            f"Terapkan <b>{len(valid_items)}</b> aturan redirect terverifikasi ke Cloudflare?"
        )
        reply = QMessageBox.question(
            self,
            "Konfirmasi Bulk Import",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        preserve_p = self.tab2_preserve_path.isChecked()
        preserve_q = self.tab2_preserve_query.isChecked()
        items_to_create = []
        for p in valid_items:
            items_to_create.append({
                "zone_id": p["zone"].id,
                "account_id": p["zone"].account_id,
                "source_hostname": p["source"],
                "destination_url": p["destination"],
                "coverage": "all",
                "status_code": p["status_code"],
                "preserve_path": preserve_p,
                "preserve_query_string": preserve_q,
                "enabled": True,
            })

        self._start_bulk_worker(items_to_create)

    def _start_bulk_worker(self, items: List[Dict[str, Any]]):
        self.tabs.setEnabled(False)
        self.progress_frame.show()
        self.progress_bar.setValue(0)
        self.progress_lbl.setText(f"Memulai proses {len(items)} aturan...")
        self.close_btn.setEnabled(False)

        self.worker = BulkCreateRedirectsWorker(items, parent=self)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error.connect(self._on_worker_error)
        self.worker.start()

    def _on_worker_progress(self, current: int, total: int, msg: str):
        pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.progress_lbl.setText(f"[{current}/{total}] {msg}")

    def _on_worker_finished(self, summary: Dict[str, Any]):
        self.tabs.setEnabled(True)
        self.close_btn.setEnabled(True)
        success_count = summary.get("success", 0)
        failed_count = summary.get("failed", 0)
        errors = summary.get("errors", [])

        self.progress_bar.setValue(100)
        self.progress_lbl.setText(f"Selesai! {success_count} berhasil, {failed_count} gagal/dilewati.")

        err_details = "\n".join(errors[:10])
        if len(errors) > 10:
            err_details += f"\n... dan {len(errors) - 10} lainnya."

        msg = f"Proses Bulk Redirect selesai!\n\n• Berhasil: {success_count}\n• Gagal/Dilewati: {failed_count}"
        if errors:
            msg += f"\n\nRincian Kendala:\n{err_details}"

        QMessageBox.information(self, "Bulk Selesai", msg)
        self.bulk_completed.emit(success_count)
        self.accept()

    def _on_worker_error(self, err_msg: str):
        self.tabs.setEnabled(True)
        self.close_btn.setEnabled(True)
        self.progress_lbl.setText(f"Terjadi kesalahan: {err_msg}")
        QMessageBox.critical(self, "Error Bulk", f"Gagal mengeksekusi bulk redirect:\n{err_msg}")

    def _setup_tab3(self, parent_widget: QWidget):
        layout = QHBoxLayout(parent_widget)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(14)

        # Left: Domain Selection
        left_box = QFrame()
        left_box.setProperty("class", "card")
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        left_title = QLabel("1. Pilih Domain yang Ingin Dibersihkan:")
        left_title.setStyleSheet("font-weight: 700; color: #FF4D6D; font-size: 13px;")
        left_layout.addWidget(left_title)

        self.tab3_search = QLineEdit()
        self.tab3_search.setPlaceholderText("🔍 Cari domain...")
        self.tab3_search.textChanged.connect(self._filter_tab3_table)
        left_layout.addWidget(self.tab3_search)

        sel_row = QHBoxLayout()
        sel_all_btn = QPushButton("Pilih Semua")
        sel_all_btn.setProperty("class", "btn-secondary")
        sel_all_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        sel_all_btn.clicked.connect(self._select_all_tab3)
        sel_row.addWidget(sel_all_btn)

        clr_all_btn = QPushButton("Kosongkan Pilihan")
        clr_all_btn.setProperty("class", "btn-secondary")
        clr_all_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        clr_all_btn.clicked.connect(self._clear_all_tab3)
        sel_row.addWidget(clr_all_btn)

        sel_row.addStretch()
        self.tab3_count_lbl = QLabel("0 dipilih")
        self.tab3_count_lbl.setStyleSheet("color: #FF4D6D; font-weight: 700; font-size: 12px;")
        sel_row.addWidget(self.tab3_count_lbl)
        left_layout.addLayout(sel_row)

        self.tab3_table = QTableWidget()
        self.tab3_table.setColumnCount(3)
        self.tab3_table.setHorizontalHeaderLabels(["Pilih", "Domain", "Akun / Status"])
        t3_header = self.tab3_table.horizontalHeader()
        t3_header.setMinimumSectionSize(50)
        t3_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        t3_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        t3_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tab3_table.setColumnWidth(2, 120)
        self.tab3_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tab3_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        left_layout.addWidget(self.tab3_table)

        layout.addWidget(left_box, stretch=3)

        # Right: Purge Settings wrapped in ScrollArea for small laptop screens
        right_box = QFrame()
        right_box.setProperty("class", "card")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        right_title = QLabel("2. Opsi Penghapusan Massal:")
        right_title.setStyleSheet("font-weight: 700; color: #FFFFFF; font-size: 13px;")
        right_layout.addWidget(right_title)

        status_lbl = QLabel("Jenis Redirect yang Dihapus:")
        status_lbl.setStyleSheet("font-weight: 600; color: #E2E8F0; font-size: 11px;")
        right_layout.addWidget(status_lbl)

        p_frame = QFrame()
        p_frame.setStyleSheet("background: #0B0F19; border: 1px solid #233454; border-radius: 6px; padding: 6px;")
        p_layout = QVBoxLayout(p_frame)
        p_layout.setSpacing(4)

        self.tab3_filter_group = QButtonGroup(self)
        self.tab3_rad_all = QRadioButton("Semua (301 Permanent & 302 Temporary)")
        self.tab3_rad_301 = QRadioButton("Hanya 301 Permanent")
        self.tab3_rad_302 = QRadioButton("Hanya 302 Temporary")
        self.tab3_rad_all.setChecked(True)

        self.tab3_filter_group.addButton(self.tab3_rad_all, 0)
        self.tab3_filter_group.addButton(self.tab3_rad_301, 301)
        self.tab3_filter_group.addButton(self.tab3_rad_302, 302)

        p_layout.addWidget(self.tab3_rad_all)
        p_layout.addWidget(self.tab3_rad_301)
        p_layout.addWidget(self.tab3_rad_302)
        right_layout.addWidget(p_frame)

        warn_box = QFrame()
        warn_box.setStyleSheet("background: #240E14; border: 1px solid #FF4D6D; border-radius: 6px; padding: 8px;")
        warn_layout = QVBoxLayout(warn_box)
        warn_lbl = QLabel(
            "⚠️ <b>PERINGATAN:</b> Tindakan ini akan menghapus aturan Single Redirect "
            "dari seluruh domain terpilih. Sangat berguna untuk membersihkan konfigurasi lama secara menyeluruh."
        )
        warn_lbl.setWordWrap(True)
        warn_lbl.setStyleSheet("color: #FF8598; font-size: 11px;")
        warn_layout.addWidget(warn_lbl)
        right_layout.addWidget(warn_box)

        right_layout.addSpacing(6)

        self.tab3_submit_btn = QPushButton("🗑️ Hapus Massal 301/302 dari Domain Terpilih")
        self.tab3_submit_btn.setProperty("class", "btn-danger")
        self.tab3_submit_btn.clicked.connect(self._on_tab3_submit)
        right_layout.addWidget(self.tab3_submit_btn)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setStyleSheet("background: transparent;")
        right_scroll.setWidget(right_box)
        layout.addWidget(right_scroll, stretch=2)
        self._populate_tab3_table()

    def _populate_tab3_table(self):
        self.tab3_table.setRowCount(len(self.zones))
        for row, z in enumerate(self.zones):
            chk = QCheckBox()
            if z.id in self.preselected_zone_ids:
                chk.setChecked(True)
            chk.toggled.connect(self._update_tab3_count)
            self.tab3_table.setCellWidget(row, 0, chk)

            self.tab3_table.setItem(row, 1, QTableWidgetItem(z.name))
            acc_str = f"{z.account_label or 'Akun 1'} ({z.status})"
            self.tab3_table.setItem(row, 2, QTableWidgetItem(acc_str))

        self._update_tab3_count()

    def _filter_tab3_table(self, query: str):
        query = query.strip().lower()
        for row in range(self.tab3_table.rowCount()):
            item = self.tab3_table.item(row, 1)
            if not query or (item and query in item.text().lower()):
                self.tab3_table.setRowHidden(row, False)
            else:
                self.tab3_table.setRowHidden(row, True)

    def _select_all_tab3(self):
        for row in range(self.tab3_table.rowCount()):
            if not self.tab3_table.isRowHidden(row):
                chk = self.tab3_table.cellWidget(row, 0)
                if isinstance(chk, QCheckBox):
                    chk.setChecked(True)
        self._update_tab3_count()

    def _clear_all_tab3(self):
        for row in range(self.tab3_table.rowCount()):
            chk = self.tab3_table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox):
                chk.setChecked(False)
        self._update_tab3_count()

    def _update_tab3_count(self):
        count = 0
        for row in range(self.tab3_table.rowCount()):
            chk = self.tab3_table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                count += 1
        self.tab3_count_lbl.setText(f"{count} domain dipilih")

    def _on_tab3_submit(self):
        selected_zones: List[ZoneItem] = []
        for row in range(self.tab3_table.rowCount()):
            chk = self.tab3_table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                selected_zones.append(self.zones[row])

        if not selected_zones:
            QMessageBox.warning(self, "Peringatan", "Pilih minimal satu domain untuk dibersihkan.")
            return

        status_code = self.tab3_filter_group.checkedId()
        type_str = "Semua (301 & 302)" if status_code == 0 else f"{status_code} saja"
        confirm_msg = (
            f"PERINGATAN PENGHAPUSAN MASSAL:\n\n"
            f"Anda akan menghapus aturan redirect ({type_str}) dari <b>{len(selected_zones)}</b> domain terpilih.\n\n"
            f"Apakah Anda yakin ingin melanjutkan?"
        )
        reply = QMessageBox.warning(
            self,
            "Konfirmasi Hapus Massal",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        zone_items = [
            {
                "zone_id": z.id,
                "account_id": z.account_id,
                "zone_name": z.name,
            }
            for z in selected_zones
        ]

        self.tabs.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.progress_frame.show()
        self.progress_bar.setValue(0)
        self.progress_lbl.setText(f"Menghapus redirect dari {len(zone_items)} domain...")

        self.purge_worker = BulkPurgeRedirectsWorker(zone_items, status_filter=status_code, parent=self)
        self.purge_worker.progress.connect(self._on_worker_progress)
        self.purge_worker.finished.connect(self._on_purge_finished)
        self.purge_worker.error.connect(self._on_worker_error)
        self.purge_worker.start()

    def _on_purge_finished(self, summary: dict):
        self.tabs.setEnabled(True)
        self.close_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        deleted = summary.get("success", 0)
        self.progress_lbl.setText(f"Selesai! {deleted} aturan berhasil dihapus.")
        QMessageBox.information(self, "Pembersihan Selesai", f"Berhasil menghapus <b>{deleted}</b> aturan redirect.")
        self.bulk_completed.emit(deleted)
        self.accept()

