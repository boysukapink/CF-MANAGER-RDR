"""Main Application Window with modern Sidebar navigation and responsive layout.
"""

from typing import List, Dict
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QFrame,
    QApplication,
    QComboBox,
)
from PySide6.QtGui import QCloseEvent

from src.security.session import active_session
from src.cloudflare.client import cf_client
from src.cloudflare.zones import ZoneItem
from src.ui.styles import DARK_THEME, LIGHT_THEME
from src.ui.components import ToastNotification, StatusBadge
from src.ui.dashboard_page import DashboardPage
from src.ui.domain_page import DomainPage
from src.ui.redirect_page import RedirectPage
from src.ui.connect_page import ConnectPage
from src.ui.security_page import SecurityPage
from src.ui.about_page import AboutPage


class MainWindow(QMainWindow):
    """Main desktop application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cloudflare Redirect Manager")
        
        # Responsive sizing tailored for laptop and desktop screens
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(1040, max(800, int(avail.width() * 0.88)))
            target_h = min(660, max(500, int(avail.height() * 0.88)))
            self.resize(target_w, target_h)
        else:
            self.resize(1000, 620)
        self.setMinimumSize(780, 480)
        
        self.is_dark_theme = True
        self.nav_buttons: Dict[str, QPushButton] = {}
        self.all_zones: List[ZoneItem] = []

        self._init_ui()
        self.apply_theme()

    def _init_ui(self):
        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(4)

        # App Brand Header
        brand_box = QFrame()
        brand_box.setStyleSheet("background: transparent; padding: 2px 4px 6px 4px;")
        brand_box_layout = QVBoxLayout(brand_box)
        brand_box_layout.setContentsMargins(4, 2, 4, 6)
        brand_box_layout.setSpacing(2)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(8)
        flame_icon = QLabel("⚡")
        flame_icon.setStyleSheet("font-size: 15px; color: #F38020;")
        brand_row.addWidget(flame_icon)

        brand_lbl = QLabel("FlareRedirect")
        brand_lbl.setObjectName("SidebarTitle")
        brand_row.addWidget(brand_lbl)
        brand_row.addStretch()
        brand_box_layout.addLayout(brand_row)

        sub_lbl = QLabel("Cloudflare URL Engine")
        sub_lbl.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 500; margin-left: 23px;")
        brand_box_layout.addWidget(sub_lbl)

        sidebar_layout.addWidget(brand_box)
        sidebar_layout.addSpacing(4)

        # Navigation Buttons
        self._add_nav_btn(sidebar_layout, "dashboard", "⊞  Dashboard")
        self._add_nav_btn(sidebar_layout, "domains", "🌐  Domains")
        self._add_nav_btn(sidebar_layout, "redirects", "⇄  Redirects")
        self._add_nav_btn(sidebar_layout, "connect", "🔑  API Accounts")
        self._add_nav_btn(sidebar_layout, "security", "🛡  Security & Privacy")
        self._add_nav_btn(sidebar_layout, "about", "ⓘ  About")

        sidebar_layout.addStretch()

        # Theme toggle button
        self.theme_btn = QPushButton("◐  Dark / Light Mode")
        self.theme_btn.setProperty("class", "btn-secondary")
        self.theme_btn.clicked.connect(self.toggle_theme)
        sidebar_layout.addWidget(self.theme_btn)

        root_layout.addWidget(sidebar)

        # 2. Main Area (Header + Stacked Pages)
        content_frame = QWidget()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header Bar
        header = QFrame()
        header.setObjectName("Header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)

        self.page_title_lbl = QLabel("Dashboard")
        self.page_title_lbl.setObjectName("HeaderTitle")
        header_layout.addWidget(self.page_title_lbl)

        header_layout.addStretch()

        # Account Switcher Dropdown in Header
        self.acc_switcher_lbl = QLabel("Akun Aktif:")
        self.acc_switcher_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        self.acc_switcher_lbl.hide()
        header_layout.addWidget(self.acc_switcher_lbl)

        self.account_switcher = QComboBox()
        self.account_switcher.setStyleSheet("font-size: 12px; min-width: 140px;")
        self.account_switcher.hide()
        self.account_switcher.currentIndexChanged.connect(self._handle_account_switch)
        header_layout.addWidget(self.account_switcher)

        # Header Status Badge
        self.header_status_badge = StatusBadge("Disconnected", "disconnected")
        header_layout.addWidget(self.header_status_badge)

        # Quick Disconnect button in header
        self.header_disconnect_btn = QPushButton("Putuskan Semua")
        self.header_disconnect_btn.setProperty("class", "btn-danger")
        self.header_disconnect_btn.setStyleSheet("padding: 4px 12px; font-size: 11px;")
        self.header_disconnect_btn.hide()
        self.header_disconnect_btn.clicked.connect(self._handle_quick_disconnect)
        header_layout.addWidget(self.header_disconnect_btn)

        content_layout.addWidget(header)

        # Stacked Pages
        self.stack = QStackedWidget()

        self.dashboard_page = DashboardPage(self)
        self.domain_page = DomainPage(self)
        self.redirect_page = RedirectPage(self)
        self.connect_page = ConnectPage(self)
        self.security_page = SecurityPage(self)
        self.about_page = AboutPage(self)

        self.stack.addWidget(self.dashboard_page)  # index 0
        self.stack.addWidget(self.domain_page)     # index 1
        self.stack.addWidget(self.redirect_page)   # index 2
        self.stack.addWidget(self.connect_page)    # index 3
        self.stack.addWidget(self.security_page)   # index 4
        self.stack.addWidget(self.about_page)      # index 5

        content_layout.addWidget(self.stack)
        root_layout.addWidget(content_frame)

        # Toast notification floating overlay
        self.toast = ToastNotification(self)

        # Connect inter-page signals
        self._connect_signals()

        # Set default active page
        self.switch_page("dashboard")

    def _add_nav_btn(self, layout: QVBoxLayout, page_name: str, label: str):
        btn = QPushButton(label)
        btn.setProperty("class", "nav-btn")
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.switch_page(page_name))
        layout.addWidget(btn)
        self.nav_buttons[page_name] = btn

    def _connect_signals(self):
        # Navigation signals
        self.dashboard_page.navigate_to.connect(self.switch_page)
        self.dashboard_page.refresh_requested.connect(self._refresh_all)

        # Connection page signals
        self.connect_page.connection_changed.connect(self._on_connection_changed)
        self.connect_page.account_switched.connect(self._on_account_switched)
        self.connect_page.show_toast.connect(self.show_toast_message)

        # Domain page signals
        self.domain_page.view_redirects_for_zone.connect(self._view_redirects_for_zone)
        self.domain_page.show_toast.connect(self.show_toast_message)
        self.domain_page.zones_updated.connect(self._on_zones_updated)

        # Redirect page signals
        self.redirect_page.show_toast.connect(self.show_toast_message)
        self.redirect_page.redirects_count_changed.connect(self._on_redirects_count_changed)

        # Security page signals
        self.security_page.show_toast.connect(self.show_toast_message)

    def switch_page(self, page_name: str):
        page_map = {
            "dashboard": (0, "Dashboard"),
            "domains": (1, "Domain Manager"),
            "redirects": (2, "Redirect Manager"),
            "connect": (3, "Kelola Akun Cloudflare"),
            "security": (4, "Keamanan & Privasi Sesi"),
            "about": (5, "Tentang Aplikasi"),
        }

        if page_name in page_map:
            idx, title = page_map[page_name]
            self.stack.setCurrentIndex(idx)
            self.page_title_lbl.setText(title)

            # Update sidebar active styles
            for name, btn in self.nav_buttons.items():
                btn.setChecked(name == page_name)

    def _refresh_account_switcher(self):
        accounts = active_session.get_all_accounts()
        if len(accounts) > 0:
            self.account_switcher.blockSignals(True)
            cur_data = self.account_switcher.currentData()
            self.account_switcher.clear()
            self.account_switcher.addItem(f"🌐 Semua Akun CF ({len(accounts)} Akun Gabung)", "all")
            for acc in accounts:
                self.account_switcher.addItem(f"👤 {acc.label}", acc.account_id)

            if cur_data and cur_data != "all":
                idx = self.account_switcher.findData(cur_data)
                if idx >= 0:
                    self.account_switcher.setCurrentIndex(idx)
                else:
                    self.account_switcher.setCurrentIndex(0)
            else:
                self.account_switcher.setCurrentIndex(0)
            self.account_switcher.blockSignals(False)

            self.acc_switcher_lbl.show()
            self.account_switcher.show()
        else:
            self.acc_switcher_lbl.hide()
            self.account_switcher.hide()

    def _handle_account_switch(self):
        acc_id = self.account_switcher.currentData()
        if acc_id == "all":
            self.domain_page.account_combo.setCurrentIndex(0)
            self.domain_page.load_domains()
            self.show_toast_message("Menampilkan seluruh domain dari semua akun Cloudflare.", False)
        elif acc_id and acc_id != active_session.active_id:
            active_session.switch_account(acc_id)
            self._on_account_switched(acc_id)

    def _on_account_switched(self, account_id: str):
        self._refresh_account_switcher()
        self.connect_page.refresh_account_table()
        self.domain_page.load_domains()
        acc = active_session.active_account
        label = acc.label if acc else account_id
        self.show_toast_message(f"Beralih ke akun Cloudflare: {label}", False)

    def _on_connection_changed(self, is_connected: bool):
        self.dashboard_page.update_connection_state(is_connected)
        self._refresh_account_switcher()
        if is_connected:
            acc_count = active_session.account_count
            self.header_status_badge.set_status("connected", f"Connected ({acc_count} Akun)")
            self.header_disconnect_btn.show()
            self.domain_page.account_combo.setCurrentIndex(0)
            self.domain_page.load_domains()
        else:
            self.header_status_badge.set_status("disconnected", "Disconnected")
            self.header_disconnect_btn.hide()
            self.domain_page.clear()
            self.redirect_page.clear()
            self.all_zones = []

    def _on_zones_updated(self, zones: List[ZoneItem]):
        self.all_zones = zones
        self.redirect_page.set_zones(zones)
        self.dashboard_page.update_metrics(len(zones), len(self.redirect_page.current_rules))

    def _on_redirects_count_changed(self, count: int):
        self.dashboard_page.update_metrics(len(self.all_zones), count)

    def _view_redirects_for_zone(self, zone_id: str, zone_name: str):
        self.redirect_page.select_zone_by_id(zone_id)
        self.switch_page("redirects")

    def _refresh_all(self):
        if active_session.is_connected:
            self.domain_page.load_domains()
            self.redirect_page.load_redirects_for_selected_zone()
            self.show_toast_message("Memperbarui seluruh data dari Cloudflare...", False)
        else:
            self.show_toast_message("Aplikasi belum terhubung ke Cloudflare API.", True)

    def _handle_quick_disconnect(self):
        self.connect_page.handle_disconnect_all()

    def show_toast_message(self, message: str, is_error: bool = False):
        self.toast.show_message(message, is_error=is_error)

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.apply_theme()

    def apply_theme(self):
        app = QApplication.instance()
        if app:
            app.setStyleSheet(DARK_THEME if self.is_dark_theme else LIGHT_THEME)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Re-position toast on resize if visible
        if self.toast.isVisible():
            x = self.width() - self.toast.width() - 30
            y = 20
            self.toast.move(max(10, x), y)

    def closeEvent(self, event: QCloseEvent):
        """Clean up all memory buffers and connections upon application exit."""
        # Disconnect and wipe memory
        active_session.disconnect()
        cf_client.close()
        event.accept()
