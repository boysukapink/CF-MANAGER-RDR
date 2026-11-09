"""Security & Privacy Architecture Page.
Explains the in-memory security model, zero-storage policies, and allows sanitized audit log export.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from src.utils.audit import session_audit


class SecurityPage(QWidget):
    """Page detailing token security architecture and active session privacy."""

    show_toast = Signal(str, bool)

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
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        # Title
        header_title = QLabel("Keamanan & Privasi Sesi")
        header_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC;")
        layout.addWidget(header_title)

        # Security Highlights Grid
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        sec_title = QLabel("🛡️ Kebijakan Nol Penyimpanan (Zero-Storage Policy)")
        sec_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #34D399;")
        card_layout.addWidget(sec_title)

        sec_info = QLabel(
            "<b>1. Token Tanpa Persistensi:</b><br>"
            "Token API Cloudflare <i>tidak pernah</i> ditulis ke file disk, SQLite, JSON, YAML, TOML, INI, .env, "
            "registry Windows, atau cache lokal.<br><br>"
            "<b>2. Masa Hidup Memori (In-Memory Only):</b><br>"
            "Token hanya berada di dalam memori proses selama aplikasi berjalan. Saat Anda menekan tombol "
            "<b>Disconnect</b> atau menutup aplikasi, buffer token ditimpa dengan nilai nol (byte zeroing) "
            "dan seluruh referensi dihapus dari objek aplikasi.<br><br>"
            "<b>3. Komunikasi HTTPS Langsung & Aman:</b><br>"
            "Semua permintaan dikirim langsung ke <code>https://api.cloudflare.com</code> tanpa perantara server backend, "
            "tanpa proxy pihak ketiga, dan tanpa bot Telegram. Verifikasi sertifikat TLS aktif penuh (verify=True) "
            "dan penerusan header otorisasi otomatis dinonaktifkan.<br><br>"
            "<b>4. Transparansi Manajemen Memori Python:</b><br>"
            "Python menggunakan automatic memory management dan garbage collector. Kami menggunakan buffer byte mutable "
            "untuk mengurangi salinan token, namun salinan string sementara mungkin ada di RAM proses hingga proses "
            "Windows ditutup seluruhnya. Kami tidak mengklaim jaminan 100% yang mustahil dalam ekosistem Python."
        )
        sec_info.setTextFormat(Qt.TextFormat.RichText)
        sec_info.setWordWrap(True)
        sec_info.setStyleSheet("color: #CBD5E1; font-size: 13px; line-height: 1.6;")
        card_layout.addWidget(sec_info)

        layout.addWidget(card)

        # Audit Export Box
        export_frame = QFrame()
        export_frame.setProperty("class", "card")
        exp_layout = QVBoxLayout(export_frame)
        exp_layout.setSpacing(12)

        exp_title = QLabel("📄 Ekspor Audit Log Sesi Aktif")
        exp_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        exp_layout.addWidget(exp_title)

        exp_desc = QLabel(
            "Anda dapat mengekspor riwayat tindakan sesi aktif (misalnya pembuatan atau penghapusan redirect) "
            "untuk keperluan dokumentasi atau audit kepatuhan. Log hasil ekspor <b>dijamin bersih</b> tanpa token, "
            "tanpa Authorization header, dan tanpa data kredensial."
        )
        exp_desc.setWordWrap(True)
        exp_desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        exp_layout.addWidget(exp_desc)

        btn_row = QHBoxLayout()
        csv_btn = QPushButton("Ekspor ke CSV")
        csv_btn.setProperty("class", "btn-secondary")
        csv_btn.clicked.connect(self._export_csv)
        btn_row.addWidget(csv_btn)

        json_btn = QPushButton("Ekspor ke JSON")
        json_btn.setProperty("class", "btn-secondary")
        json_btn.clicked.connect(self._export_json)
        btn_row.addWidget(json_btn)

        btn_row.addStretch()
        exp_layout.addLayout(btn_row)

        layout.addWidget(export_frame)

        scroll.setWidget(scroll_widget)
        root_layout.addWidget(scroll)

    def _export_csv(self):
        reply = QMessageBox.question(
            self,
            "Konfirmasi Ekspor Log",
            "Apakah Anda ingin mengekspor riwayat tindakan sesi ini ke format CSV?\n"
            "File yang diekspor tidak memuat token maupun kredensial apa pun.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Simpan Log Audit CSV", "cloudflare_audit_log.csv", "CSV Files (*.csv)")
        if file_path:
            try:
                csv_data = session_audit.export_csv()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(csv_data)
                self.show_toast.emit(f"Log berhasil diekspor ke: {file_path}", False)
            except Exception as e:
                self.show_toast.emit(f"Gagal mengekspor file: {str(e)}", True)

    def _export_json(self):
        reply = QMessageBox.question(
            self,
            "Konfirmasi Ekspor Log",
            "Apakah Anda ingin mengekspor riwayat tindakan sesi ini ke format JSON?\n"
            "File yang diekspor tidak memuat token maupun kredensial apa pun.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Simpan Log Audit JSON", "cloudflare_audit_log.json", "JSON Files (*.json)")
        if file_path:
            try:
                json_data = session_audit.export_json()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(json_data)
                self.show_toast.emit(f"Log berhasil diekspor ke: {file_path}", False)
            except Exception as e:
                self.show_toast.emit(f"Gagal mengekspor file: {str(e)}", True)
