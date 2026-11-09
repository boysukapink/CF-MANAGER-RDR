"""Professional Cloudflare & Linear-Tier UI Styling for FlareRedirect.
Designed with disciplined engineering aesthetics, high typographic clarity,
refined contrast, and subtle Cloudflare signature amber/orange accents.
"""

DARK_THEME = """
/* =========================================================================
   GLOBAL APPLICATION WINDOW & TYPOGRAPHY
   ========================================================================= */
QMainWindow, QDialog {
    background-color: #090D16;
    color: #F8FAFC;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', Roboto, sans-serif;
    font-size: 12px;
}

QWidget {
    color: #F1F5F9;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', Roboto, sans-serif;
}

/* =========================================================================
   SIDEBAR NAVIGATION
   ========================================================================= */
#Sidebar {
    background-color: #070B12;
    border-right: 1px solid #1E293B;
    min-width: 195px;
    max-width: 195px;
}

#SidebarTitle {
    color: #F8FAFC;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.4px;
    padding: 14px 14px 10px 14px;
}

QPushButton.nav-btn {
    background-color: transparent;
    color: #94A3B8;
    text-align: left;
    padding: 8px 12px;
    border: 1px solid transparent;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    margin: 1px 6px;
}

QPushButton.nav-btn:hover {
    background-color: #111827;
    color: #F8FAFC;
    border: 1px solid #1F2937;
}

QPushButton.nav-btn:checked, QPushButton.nav-btn.active {
    background-color: #172133;
    color: #F8FAFC;
    font-weight: 600;
    border-left: 3px solid #F38020;
    border-top: 1px solid #1E293B;
    border-bottom: 1px solid #1E293B;
    border-right: 1px solid #1E293B;
}

/* =========================================================================
   HEADER BAR
   ========================================================================= */
#Header {
    background-color: #090D16;
    border-bottom: 1px solid #1E293B;
    padding: 8px 16px;
}

#HeaderTitle {
    font-size: 15px;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: 0.2px;
}

/* =========================================================================
   CARDS & PANELS
   ========================================================================= */
QFrame.card {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 12px;
}

QFrame.card:hover {
    border: 1px solid #29384E;
}

QLabel.card-title {
    color: #94A3B8;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel.card-value {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 700;
    margin-top: 2px;
}

/* =========================================================================
   BUTTONS
   ========================================================================= */

/* Primary Button (Cloudflare Amber Flame) */
QPushButton.btn-primary {
    background-color: #F38020;
    color: #FFFFFF;
    border: 1px solid #FA9D48;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton.btn-primary:hover {
    background-color: #E57317;
    border: 1px solid #FFAD66;
}

QPushButton.btn-primary:pressed {
    background-color: #CC620E;
}

/* Accent Cyan Button (Bulk & Action Accents) */
QPushButton.btn-neon-cyan {
    background-color: #0369A1;
    color: #F0F9FF;
    border: 1px solid #0284C7;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton.btn-neon-cyan:hover {
    background-color: #0284C7;
    border: 1px solid #38BDF8;
}

QPushButton.btn-neon-cyan:pressed {
    background-color: #075985;
}

/* Secondary Button (Neutral Dark Slate) */
QPushButton.btn-secondary {
    background-color: #172133;
    color: #E2E8F0;
    border: 1px solid #29384E;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
    font-size: 12px;
}

QPushButton.btn-secondary:hover {
    background-color: #1F2D44;
    color: #FFFFFF;
    border: 1px solid #3B4D68;
}

QPushButton.btn-secondary:pressed {
    background-color: #121A28;
}

/* Danger Button (Quiet Crimson) */
QPushButton.btn-danger {
    background-color: #991B1B;
    color: #FEE2E2;
    border: 1px solid #B91C1C;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton.btn-danger:hover {
    background-color: #B91C1C;
    border: 1px solid #EF4444;
    color: #FFFFFF;
}

QPushButton.btn-danger:pressed {
    background-color: #7F1D1D;
}

/* Success Button (Subdued Emerald) */
QPushButton.btn-success {
    background-color: #065F46;
    color: #D1FAE5;
    border: 1px solid #059669;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton.btn-success:hover {
    background-color: #059669;
    border: 1px solid #10B981;
    color: #FFFFFF;
}

QPushButton.btn-success:pressed {
    background-color: #064E3B;
}

/* Table Compact Action Buttons */
QPushButton.btn-action-edit {
    background-color: #082F49;
    color: #38BDF8;
    border: 1px solid #0369A1;
    border-radius: 4px;
    padding: 3px 8px;
    font-weight: 500;
    font-size: 11px;
}

QPushButton.btn-action-edit:hover {
    background-color: #0284C7;
    color: #FFFFFF;
    border: 1px solid #38BDF8;
}

QPushButton.btn-action-toggle {
    background-color: #2D2008;
    color: #FBBF24;
    border: 1px solid #78350F;
    border-radius: 4px;
    padding: 3px 8px;
    font-weight: 500;
    font-size: 11px;
}

QPushButton.btn-action-toggle:hover {
    background-color: #D97706;
    color: #FFFFFF;
    border: 1px solid #FBBF24;
}

QPushButton.btn-action-test {
    background-color: #1E1B4B;
    color: #A5B4FC;
    border: 1px solid #3730A3;
    border-radius: 4px;
    padding: 3px 8px;
    font-weight: 500;
    font-size: 11px;
}

QPushButton.btn-action-test:hover {
    background-color: #4338CA;
    color: #FFFFFF;
    border: 1px solid #818CF8;
}

QPushButton.btn-action-delete {
    background-color: #360E16;
    color: #F87171;
    border: 1px solid #7F1D1D;
    border-radius: 4px;
    padding: 3px 8px;
    font-weight: 500;
    font-size: 11px;
}

QPushButton.btn-action-delete:hover {
    background-color: #B91C1C;
    color: #FFFFFF;
    border: 1px solid #EF4444;
}

QPushButton:disabled {
    background-color: #0F172A;
    color: #475569;
    border: 1px solid #1E293B;
}

/* =========================================================================
   INPUTS, DROPDOWNS & CONTROLS
   ========================================================================= */
QLineEdit, QComboBox, QTextEdit {
    background-color: #090D16;
    color: #F8FAFC;
    border: 1px solid #283548;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #F38020;
    background-color: #0C121E;
}

QComboBox::drop-down {
    border: none;
    padding-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #0F172A;
    color: #F8FAFC;
    selection-background-color: #F38020;
    selection-color: #FFFFFF;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 3px;
}

QCheckBox, QRadioButton {
    color: #E2E8F0;
    font-size: 12px;
    spacing: 6px;
    font-weight: 500;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 15px;
    height: 15px;
    border-radius: 3px;
    border: 1px solid #3B4D68;
    background-color: #090D16;
}

QRadioButton::indicator {
    border-radius: 8px;
}

QCheckBox::indicator:checked {
    background-color: #F38020;
    border: 1px solid #FA9D48;
}

QRadioButton::indicator:checked {
    background-color: #F38020;
    border: 1px solid #FA9D48;
}

/* =========================================================================
   TAB WIDGET
   ========================================================================= */
QTabWidget::pane {
    border: 1px solid #1E293B;
    border-radius: 8px;
    background-color: #0F172A;
    padding: 8px;
}

QTabBar::tab {
    background-color: #0B1120;
    color: #94A3B8;
    border: 1px solid #1E293B;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
    margin-right: 3px;
}

QTabBar::tab:hover {
    background-color: #141E33;
    color: #F8FAFC;
}

QTabBar::tab:selected {
    background-color: #0F172A;
    color: #F38020;
    border-top: 2px solid #F38020;
    border-left: 1px solid #1E293B;
    border-right: 1px solid #1E293B;
    border-bottom: 1px solid #0F172A;
}

/* =========================================================================
   TABLES
   ========================================================================= */
QTableWidget {
    background-color: #0B1120;
    color: #F8FAFC;
    gridline-color: #1A2438;
    border: 1px solid #1E293B;
    border-radius: 6px;
    selection-background-color: #17253D;
    selection-color: #FFFFFF;
    font-size: 12px;
}

QTableWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #151F33;
}

QTableWidget::item:hover {
    background-color: #121C30;
}

QHeaderView::section {
    background-color: #070B14;
    color: #94A3B8;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #1E293B;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.3px;
}

/* Badges */
QLabel.badge-active {
    background-color: #052E16;
    color: #4ADE80;
    border: 1px solid #166534;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: 11px;
}

QLabel.badge-pending {
    background-color: #451A03;
    color: #FBBF24;
    border: 1px solid #78350F;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: 11px;
}

QLabel.badge-disconnected {
    background-color: #1E293B;
    color: #94A3B8;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: 11px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #090D16;
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #1E293B;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #334155;
}

QScrollBar:horizontal {
    border: none;
    background: #090D16;
    height: 6px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal {
    background: #1E293B;
    min-width: 20px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal:hover {
    background: #334155;
}

/* Progress Bar */
QProgressBar {
    background-color: #090D16;
    border: 1px solid #1E293B;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: #FFFFFF;
    font-weight: 600;
    font-size: 10px;
}

QProgressBar::chunk {
    background-color: #F38020;
    border-radius: 4px;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog {
    background-color: #F8FAFC;
    color: #0F172A;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', Roboto, sans-serif;
    font-size: 12px;
}

QWidget {
    color: #1E293B;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', Roboto, sans-serif;
}

#Sidebar {
    background-color: #FFFFFF;
    border-right: 1px solid #E2E8F0;
    min-width: 195px;
    max-width: 195px;
}

#SidebarTitle {
    color: #0F172A;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.4px;
    padding: 14px 14px 10px 14px;
}

QPushButton.nav-btn {
    background-color: transparent;
    color: #64748B;
    text-align: left;
    padding: 8px 12px;
    border: 1px solid transparent;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    margin: 1px 6px;
}

QPushButton.nav-btn:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}

QPushButton.nav-btn:checked, QPushButton.nav-btn.active {
    background-color: #F1F5F9;
    color: #0F172A;
    font-weight: 600;
    border-left: 3px solid #F38020;
    border-top: 1px solid #E2E8F0;
    border-bottom: 1px solid #E2E8F0;
    border-right: 1px solid #E2E8F0;
}

#Header {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    padding: 8px 16px;
}

#HeaderTitle {
    font-size: 15px;
    font-weight: 700;
    color: #0F172A;
    letter-spacing: 0.2px;
}

QFrame.card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px;
}

QLabel.card-title {
    color: #64748B;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel.card-value {
    color: #0F172A;
    font-size: 22px;
    font-weight: 700;
    margin-top: 2px;
}

QPushButton.btn-primary {
    background-color: #F38020;
    color: #FFFFFF;
    border: 1px solid #FA9D48;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton.btn-primary:hover {
    background-color: #E57317;
}

QPushButton.btn-neon-cyan {
    background-color: #0284C7;
    color: #FFFFFF;
    border: 1px solid #0369A1;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton.btn-secondary {
    background-color: #F8FAFC;
    color: #334155;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
    font-size: 12px;
}

QPushButton.btn-secondary:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}

QPushButton.btn-danger {
    background-color: #DC2626;
    color: #FFFFFF;
    border: 1px solid #B91C1C;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton.btn-success {
    background-color: #10B981;
    color: #FFFFFF;
    border: 1px solid #059669;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton.btn-action-edit {
    background-color: #F0F9FF;
    color: #0284C7;
    border: 1px solid #BAE6FD;
    border-radius: 4px;
    padding: 3px 8px;
    font-weight: 500;
    font-size: 11px;
}

QPushButton.btn-action-toggle {
    background-color: #FFFBEB;
    color: #D97706;
    border: 1px solid #FDE68A;
    border-radius: 4px;
    padding: 3px 8px;
    font-weight: 500;
    font-size: 11px;
}

QPushButton.btn-action-test {
    background-color: #EEF2FF;
    color: #4F46E5;
    border: 1px solid #C7D2FE;
    border-radius: 4px;
    padding: 3px 8px;
    font-weight: 500;
    font-size: 11px;
}

QPushButton.btn-action-delete {
    background-color: #FEF2F2;
    color: #DC2626;
    border: 1px solid #FECACA;
    border-radius: 4px;
    padding: 3px 8px;
    font-weight: 500;
    font-size: 11px;
}

QLineEdit, QComboBox, QTextEdit {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #F38020;
}

QTabWidget::pane {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background-color: #FFFFFF;
    padding: 8px;
}

QTabBar::tab {
    background-color: #F8FAFC;
    color: #64748B;
    border: 1px solid #E2E8F0;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
    margin-right: 3px;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #F38020;
    border-top: 2px solid #F38020;
}

QTableWidget {
    background-color: #FFFFFF;
    color: #0F172A;
    gridline-color: #F1F5F9;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    selection-background-color: #F1F5F9;
    selection-color: #0F172A;
    font-size: 12px;
}

QTableWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #F1F5F9;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    font-weight: 600;
    font-size: 11px;
}
"""
