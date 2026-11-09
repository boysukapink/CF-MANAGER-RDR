"""Entry point for Cloudflare Redirect Manager (FlareRedirect).
Desktop Windows Application built with PySide6.
"""

import sys
import os

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from src.config import settings
from src.ui.main_window import MainWindow
from src.security.session import active_session
from src.cloudflare.client import cf_client
from src.utils.errors import sanitize_message
from src.utils.audit import session_audit


def production_excepthook(exc_type, exc_value, exc_traceback):
    """Global exception hook to prevent raw stack trace exposure to end-users."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    safe_msg = sanitize_message(str(exc_value))
    session_audit.record("APPLICATION_ERROR", "SYSTEM", "ERROR", safe_msg)

    app = QApplication.instance()
    if app:
        QMessageBox.critical(
            None,
            "Kesalahan Aplikasi",
            f"Terjadi kesalahan yang tidak terduga pada sistem:\n\n{safe_msg}\n\n"
            "Data kredensial dan sesi Anda tetap aman di memori.",
        )
    else:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)


def main():
    # Install global exception handler
    sys.excepthook = production_excepthook

    # Set high DPI support attributes for modern Windows displays
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(settings.APP_NAME)
    app.setApplicationVersion(settings.APP_VERSION)
    app.setOrganizationName("FlareRedirect")

    window = MainWindow()
    window.show()

    exit_code = 0
    try:
        exit_code = app.exec()
    finally:
        # Guarantee session wipe and client closure on exit
        active_session.disconnect()
        cf_client.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
