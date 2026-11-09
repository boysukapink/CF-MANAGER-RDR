"""Connect Cloudflare Page (Multi-Account Edition).
Allows user to add multiple Cloudflare accounts, switch active accounts,
and securely remove or disconnect accounts in-memory.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from src.security.session import active_session
from src.ui.workers import ConnectWorker


class ConnectPage(QWidget):
    """Page for connecting and managing multiple Cloudflare accounts."""

    connection_changed = Signal(bool)  # is_connected
    show_toast = Signal(str, bool)     # message, is_error
    account_switched = Signal(str)     # account_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: ConnectWorker = None
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
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        # Title & Subtitle
        header_layout = QVBoxLayout()
        header_title = QLabel("Koneksi Cloudflare API (Multi-Akun)")
        header_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC;")
        header_sub = QLabel(
            "Hubungkan dan kelola banyak akun Cloudflare sekaligus dalam satu sesi. "
            "Setiap token disimpan aman hanya di RAM dan langsung dibersihkan saat diputuskan atau aplikasi ditutup."
        )
        header_sub.setWordWrap(True)
        header_sub.setStyleSheet("font-size: 11px; color: #94A3B8; margin-top: 2px;")
        header_layout.addWidget(header_title)
        header_layout.addWidget(header_sub)
        layout.addLayout(header_layout)

        # Add Account Form Card
        form_card = QFrame()
        form_card.setProperty("class", "card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(10)

        form_title = QLabel("➕ Tambah Akun Cloudflare Baru")
        form_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #F8FAFC;")
        form_layout.addWidget(form_title)

        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(12)

        # Account Label / Alias
        lbl_vbox = QVBoxLayout()
        lbl_label = QLabel("Label / Nama Akun:")
        lbl_label.setStyleSheet("font-weight: 600; color: #E2E8F0; font-size: 12px;")
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Contoh: Akun Utama / Akun Klien A")
        lbl_vbox.addWidget(lbl_label)
        lbl_vbox.addWidget(self.label_input)
        inputs_row.addLayout(lbl_vbox, stretch=2)

        # Token Input
        tok_vbox = QVBoxLayout()
        tok_label = QLabel("Cloudflare API Token:")
        tok_label.setStyleSheet("font-weight: 600; color: #E2E8F0; font-size: 12px;")
        
        tok_hbox = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Tempel token API di sini (contoh: v8x_abc...)")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.returnPressed.connect(self.handle_connect)
        tok_hbox.addWidget(self.token_input)

        self.toggle_echo_btn = QPushButton("👁️ Show")
        self.toggle_echo_btn.setProperty("class", "btn-secondary")
        self.toggle_echo_btn.setStyleSheet("padding: 6px 12px;")
        self.toggle_echo_btn.clicked.connect(self.toggle_token_visibility)
        tok_hbox.addWidget(self.toggle_echo_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setProperty("class", "btn-secondary")
        self.clear_btn.setStyleSheet("padding: 6px 12px;")
        self.clear_btn.clicked.connect(self.clear_input_token)
        tok_hbox.addWidget(self.clear_btn)

        tok_vbox.addWidget(tok_label)
        tok_vbox.addLayout(tok_hbox)
        inputs_row.addLayout(tok_vbox, stretch=4)

        form_layout.addLayout(inputs_row)

        # Connect button
        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("🔗 Hubungkan & Tambah Akun")
        self.connect_btn.setProperty("class", "btn-primary")
        self.connect_btn.setMinimumHeight(38)
        self.connect_btn.clicked.connect(self.handle_connect)
        btn_row.addWidget(self.connect_btn)
        btn_row.addStretch()
        form_layout.addLayout(btn_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        form_layout.addWidget(self.progress_bar)

        layout.addWidget(form_card)

        # Connected Accounts List Card
        list_card = QFrame()
        list_card.setProperty("class", "card")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(20, 18, 20, 18)
        list_layout.setSpacing(12)

        top_list_row = QHBoxLayout()
        list_title = QLabel("📋 Daftar Akun Cloudflare Terhubung di Sesi Ini")
        list_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        top_list_row.addWidget(list_title)
        top_list_row.addStretch()

        self.disconnect_all_btn = QPushButton("⚠️ Putuskan Semua Akun")
        self.disconnect_all_btn.setProperty("class", "btn-danger")
        self.disconnect_all_btn.setStyleSheet("padding: 6px 14px; font-size: 12px;")
        self.disconnect_all_btn.clicked.connect(self.handle_disconnect_all)
        top_list_row.addWidget(self.disconnect_all_btn)

        list_layout.addLayout(top_list_row)

        self.account_table = QTableWidget()
        self.account_table.setColumnCount(5)
        self.account_table.setHorizontalHeaderLabels([
            "Nama / Label Akun", "Status", "Total Domain", "Waktu Terhubung", "Aksi"
        ])
        acc_header = self.account_table.horizontalHeader()
        acc_header.setMinimumSectionSize(60)
        acc_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        acc_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        acc_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        acc_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        acc_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.account_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.account_table.setAlternatingRowColors(True)
        self.account_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.account_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        list_layout.addWidget(self.account_table)

        layout.addWidget(list_card)

        # Permissions Guide Box
        guide_frame = QFrame()
        guide_frame.setProperty("class", "card")
        guide_layout = QVBoxLayout(guide_frame)
        guide_layout.setContentsMargins(14, 10, 14, 10)
        guide_layout.setSpacing(6)

        guide_title = QLabel("📋 Catatan Izin Minimum Setiap Akun")
        guide_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #F38020;")
        guide_layout.addWidget(guide_title)

        guide_text = QLabel(
            "Untuk setiap akun Cloudflare yang dihubungkan, pastikan token memiliki izin:<br>"
            "&bull; <b>Zone &rarr; Zone &rarr; Read</b> &nbsp;&bull; <b>Zone &rarr; Single Redirect &rarr; Edit</b>.<br>"
            "Anda dapat berganti antar akun secara instan melalui dropdown pemilih akun di pojok atas atau tabel di atas."
        )
        guide_text.setTextFormat(Qt.TextFormat.RichText)
        guide_text.setStyleSheet("color: #CBD5E1; font-size: 11px;")
        guide_layout.addWidget(guide_text)

        layout.addWidget(guide_frame)

        scroll.setWidget(scroll_widget)
        root_layout.addWidget(scroll)

        self.refresh_account_table()

    def toggle_token_visibility(self):
        if self.token_input.echoMode() == QLineEdit.EchoMode.Password:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_echo_btn.setText("🔒 Hide")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_echo_btn.setText("👁️ Show")

    def clear_input_token(self):
        self.token_input.clear()
        self.label_input.clear()

    def handle_connect(self):
        token = self.token_input.text().strip()
        label = self.label_input.text().strip()
        if not token:
            self.show_toast.emit("Silakan masukkan token API Cloudflare terlebih dahulu.", True)
            return

        self.connect_btn.setEnabled(False)
        self.progress_bar.show()

        self.worker = ConnectWorker(token, label=label, parent=self)
        self.worker.finished.connect(self._on_connect_success)
        self.worker.error.connect(self._on_connect_error)
        self.worker.start()

    def _on_connect_success(self, result: dict):
        self.progress_bar.hide()
        self.connect_btn.setEnabled(True)
        self.token_input.clear()
        self.label_input.clear()

        self.show_toast.emit(result.get("message", "Akun berhasil terhubung!"), False)
        self.refresh_account_table()
        self.connection_changed.emit(True)

    def _on_connect_error(self, err_msg: str):
        self.progress_bar.hide()
        self.connect_btn.setEnabled(True)
        self.show_toast.emit(f"Koneksi akun gagal: {err_msg}", True)

    def refresh_account_table(self):
        accounts = active_session.get_all_accounts()
        self.account_table.setRowCount(len(accounts))
        active_id = active_session.active_id

        self.disconnect_all_btn.setEnabled(len(accounts) > 0)
        mono_font = QFont("Consolas", 9)
        self.account_table.verticalHeader().setDefaultSectionSize(30)

        for row, acc in enumerate(accounts):
            is_active = (acc.account_id == active_id)

            # Label
            lbl_item = QTableWidgetItem(f"★ {acc.label} (Aktif)" if is_active else acc.label)
            lbl_item.setForeground(QColor("#38BDF8" if is_active else "#F8FAFC"))
            self.account_table.setItem(row, 0, lbl_item)

            # Status
            status_item = QTableWidgetItem("● Aktif" if is_active else "○ Siaga")
            status_item.setForeground(QColor("#34D399" if is_active else "#94A3B8"))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.account_table.setItem(row, 1, status_item)

            # Domain count
            dom_item = QTableWidgetItem(f"{len(acc.zones)} Domain")
            dom_item.setForeground(QColor("#CBD5E1"))
            dom_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.account_table.setItem(row, 2, dom_item)

            # Connected At
            time_item = QTableWidgetItem(acc.connected_at)
            time_item.setFont(mono_font)
            time_item.setForeground(QColor("#94A3B8"))
            self.account_table.setItem(row, 3, time_item)

            # Action Buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(6)

            if not is_active:
                switch_btn = QPushButton("Gunakan Akun Ini")
                switch_btn.setProperty("class", "btn-action-edit")
                switch_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
                switch_btn.clicked.connect(lambda checked=False, aid=acc.account_id: self._switch_to_account(aid))
                action_layout.addWidget(switch_btn)

            rm_btn = QPushButton("Putuskan")
            rm_btn.setProperty("class", "btn-action-delete")
            rm_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            rm_btn.clicked.connect(lambda checked=False, aid=acc.account_id, albl=acc.label: self._remove_account(aid, albl))
            action_layout.addWidget(rm_btn)

            self.account_table.setCellWidget(row, 4, action_widget)

    def _switch_to_account(self, account_id: str):
        active_session.switch_account(account_id)
        self.refresh_account_table()
        acc = active_session.active_account
        label = acc.label if acc else account_id
        self.show_toast.emit(f"Beralih ke akun: {label}", False)
        self.account_switched.emit(account_id)
        self.connection_changed.emit(True)

    def _remove_account(self, account_id: str, label: str):
        reply = QMessageBox.question(
            self,
            "Putuskan Akun",
            f"Apakah Anda yakin ingin memutuskan akun '{label}'?\nToken akan dibersihkan dari RAM.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            active_session.remove_account(account_id)
            self.refresh_account_table()
            is_conn = active_session.is_connected
            self.show_toast.emit(f"Akun '{label}' telah diputuskan.", False)
            self.connection_changed.emit(is_conn)

    def handle_disconnect_all(self):
        reply = QMessageBox.question(
            self,
            "Putuskan Semua Akun",
            "Apakah Anda yakin ingin memutuskan seluruh akun Cloudflare?\nSemua token di RAM akan dinolkan.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            active_session.disconnect_all()
            self.refresh_account_table()
            self.show_toast.emit("Seluruh akun telah diputuskan dan memori dibersihkan.", False)
            self.connection_changed.emit(False)
