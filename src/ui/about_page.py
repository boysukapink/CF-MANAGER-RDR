"""About Page for Cloudflare Redirect Manager.
Displays application version, purpose, and official documentation links.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt


class AboutPage(QWidget):
    """About page displaying software metadata and Cloudflare documentation links."""

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
        layout.setSpacing(14)

        # Title
        header_title = QLabel("Tentang Aplikasi")
        header_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC;")
        layout.addWidget(header_title)

        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        app_title = QLabel("Cloudflare Redirect Manager")
        app_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F38020;")
        card_layout.addWidget(app_title)

        app_ver = QLabel("Versi 1.0.0 — Desktop Windows Standalone Edition")
        app_ver.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 500;")
        card_layout.addWidget(app_ver)

        desc = QLabel(
            "Aplikasi desktop mandiri Windows untuk mengelola Cloudflare Single Redirects (URL Forwarding) "
            "secara instan, aman, dan tanpa perantara pihak ketiga. Dibuat menggunakan Python 3, PySide6 (Qt for Python), "
            "dan HTTPX dengan verifikasi sertifikat TLS aktif penuh."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #E2E8F0; font-size: 12px; line-height: 1.5;")
        card_layout.addWidget(desc)

        card_layout.addSpacing(6)

        tech_title = QLabel("📚 Tautan Dokumentasi Resmi:")
        tech_title.setStyleSheet("font-weight: 700; color: #F8FAFC; font-size: 12px;")
        card_layout.addWidget(tech_title)

        links_lbl = QLabel(
            "• <b>Cloudflare Single Redirects API:</b><br>"
            "&nbsp;&nbsp;<a href='https://developers.cloudflare.com/rules/url-forwarding/single-redirects/create-api/' style='color: #F38020;'>"
            "https://developers.cloudflare.com/rules/url-forwarding/single-redirects/create-api/</a><br><br>"
            "• <b>Cloudflare API Tokens Portal:</b><br>"
            "&nbsp;&nbsp;<a href='https://dash.cloudflare.com/profile/api-tokens' style='color: #F38020;'>"
            "https://dash.cloudflare.com/profile/api-tokens</a><br><br>"
            "• <b>Cloudflare API Permissions Reference:</b><br>"
            "&nbsp;&nbsp;<a href='https://developers.cloudflare.com/fundamentals/api/reference/permissions/' style='color: #F38020;'>"
            "https://developers.cloudflare.com/fundamentals/api/reference/permissions/</a>"
        )
        links_lbl.setTextFormat(Qt.TextFormat.RichText)
        links_lbl.setOpenExternalLinks(True)
        links_lbl.setStyleSheet("color: #CBD5E1; font-size: 11px; line-height: 1.5;")
        card_layout.addWidget(links_lbl)

        layout.addWidget(card)

        scroll.setWidget(scroll_widget)
        root_layout.addWidget(scroll)
