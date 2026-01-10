"""System tray icon management."""

# QSystemTrayIcon and QMenu are imported lazily in _setup_tray to avoid system tray setup in headless environments
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Signal, QObject

from src.utils.paths import get_assets_path


class TrayIcon(QObject):
    """System tray icon with context menu.

    Emits:
        show_requested: request to show the main window
        settings_requested: request to open settings
        quit_requested: request to quit the application
    """

    show_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_tray()

    def _setup_tray(self):
        """Set up system tray icon and menu.

        Lazily import QSystemTrayIcon and QMenu and skip setup when the
        system tray is not available (headless / test environments).
        """
        # Import lazily to avoid initializing platform tray integration on import
        from PySide6.QtWidgets import QSystemTrayIcon, QMenu

        # If system tray not available, skip tray setup
        try:
            if not QSystemTrayIcon.isSystemTrayAvailable():
                return
        except Exception:
            # If the availability check fails for any reason, skip setup
            return

        # parent may be None; QSystemTrayIcon expects a QWidget parent or None
        self.tray = QSystemTrayIcon(self.parent())

        # Icon path
        icon_path = get_assets_path() / "icon.png"
        if icon_path.exists():
            self.tray.setIcon(QIcon(str(icon_path)))
        else:
            # Fallback to a standard Qt icon
            from PySide6.QtWidgets import QStyle, QApplication

            self.tray.setIcon(
                QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
            )

        self.tray.setToolTip("Voice Translator")

        # Context menu
        self.menu = QMenu()

        self.show_action = QAction("Show", self.menu)
        self.show_action.triggered.connect(self._emit_show)
        self.menu.addAction(self.show_action)

        self.menu.addSeparator()

        self.settings_action = QAction("Settings", self.menu)
        self.settings_action.triggered.connect(self._emit_settings)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        self.quit_action = QAction("Quit", self.menu)
        self.quit_action.triggered.connect(self._emit_quit)
        self.menu.addAction(self.quit_action)

        self.tray.setContextMenu(self.menu)

        # Left click shows window
        self.tray.activated.connect(self._on_activated)

    def _emit_show(self):
        self.show_requested.emit()

    def _emit_settings(self):
        self.settings_requested.emit()

    def _emit_quit(self):
        self.quit_requested.emit()

    def _on_activated(self, reason):
        """Handle tray icon activation.

        Left-click (Trigger) is treated as a request to show the window.
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_requested.emit()

    def show(self):
        """Display the tray icon."""
        self.tray.show()

    def hide(self):
        """Hide the tray icon."""
        self.tray.hide()

    def show_message(self, title: str, message: str):
        """Show a balloon notification from the tray icon.

        Args:
            title: Notification title
            message: Notification body
        """
        self.tray.showMessage(title, message)
