from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QTextEdit,
    QComboBox,
    QApplication,
)
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QFont

from .styles import (
    DARK_THEME,
    RECORD_BUTTON_IDLE,
    RECORD_BUTTON_RECORDING,
    STATUS_READY,
    STATUS_RECORDING,
)
from .tray_icon import TrayIcon
from .floating_button import FloatingRecordButton


class TitleBar(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.parent_window = parent
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        title = QLabel("● Voice Translator", self)
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        layout.addStretch()

        self.min_btn = QPushButton("─", self)
        self.min_btn.setObjectName("minimizeButton")
        self.min_btn.setFixedSize(30, 30)
        # Minimize should turn the app into the floating icon (not a normal taskbar minimize)
        self.min_btn.clicked.connect(self.parent_window._minimize_to_floating)
        layout.addWidget(self.min_btn)

        self.close_btn = QPushButton("×", self)
        self.close_btn.setObjectName("closeButton")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.clicked.connect(self.parent_window._quit_app)
        layout.addWidget(self.close_btn)

    def mousePressEvent(self, event):
        # Forward to parent to allow dragging from title bar
        try:
            self.parent_window.mousePressEvent(event)
        except Exception:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        try:
            self.parent_window.mouseMoveEvent(event)
        except Exception:
            super().mouseMoveEvent(event)


class FloatingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._drag_position = QPoint()
        self._setup_window()
        self._setup_ui()
        # Tray and floating button (initialized after UI)
        try:
            self._setup_tray()
            self._setup_floating_button()
        except Exception:
            # If tray isn't available in the environment (headless/test), skip
            pass

    def _setup_window(self):
        self.setWindowTitle("Voice Translator")
        # Use explicit WindowType enum to satisfy static type checkers (Pylance)
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setFixedSize(450, 500)
        self.setStyleSheet(DARK_THEME)

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        # Slightly tighter spacing for a compact, modern layout
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)

        # Title bar at top
        self.title_bar = TitleBar(self)
        self.main_layout.insertWidget(0, self.title_bar)

        # Status label
        self.status_label = QLabel("✅ Ready - Press F8 to record", self)
        self.status_label.setStyleSheet(STATUS_READY + " font-size: 14px;")
        self.main_layout.addWidget(self.status_label)

        # --- Portuguese section ---
        self.pt_label = QLabel("🇧🇷 Portuguese (editable):", self)
        self.main_layout.addWidget(self.pt_label)

        self.portuguese_text = QTextEdit(self)
        self.portuguese_text.setPlaceholderText(
            "Transcribed Portuguese text will appear here..."
        )
        self.portuguese_text.setMinimumHeight(80)
        self.main_layout.addWidget(self.portuguese_text)

        pt_btn_row = QHBoxLayout()
        self.pt_copy_btn = QPushButton("📋 Copy", self)
        self.pt_copy_btn.clicked.connect(lambda: self._copy_text(self.portuguese_text))
        pt_btn_row.addWidget(self.pt_copy_btn)

        self.pt_clear_btn = QPushButton("🗑️ Clear", self)
        self.pt_clear_btn.clicked.connect(self.portuguese_text.clear)
        pt_btn_row.addWidget(self.pt_clear_btn)

        pt_btn_row.addStretch()
        self.main_layout.addLayout(pt_btn_row)

        # --- Language selector & translate ---
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Translate to:", self))
        self.language_combo = QComboBox(self)
        languages = [
            "English",
            "Spanish",
            "French",
            "German",
            "Italian",
            "Japanese",
            "Chinese",
        ]
        self.language_combo.addItems(languages)
        lang_row.addWidget(self.language_combo)

        self.translate_btn = QPushButton("🔄 Translate", self)
        lang_row.addWidget(self.translate_btn)
        lang_row.addStretch()
        self.main_layout.addLayout(lang_row)

        # --- Translation section ---
        self.trans_label = QLabel("🇺🇸 Translation:", self)
        self.main_layout.addWidget(self.trans_label)

        self.translation_text = QTextEdit(self)
        self.translation_text.setPlaceholderText("Translated text will appear here...")
        self.translation_text.setMinimumHeight(80)
        self.translation_text.setReadOnly(True)
        self.main_layout.addWidget(self.translation_text)

        trans_btn_row = QHBoxLayout()
        self.trans_copy_btn = QPushButton("📋 Copy", self)
        self.trans_copy_btn.clicked.connect(
            lambda: self._copy_text(self.translation_text)
        )
        trans_btn_row.addWidget(self.trans_copy_btn)

        self.trans_clear_btn = QPushButton("🗑️ Clear", self)
        self.trans_clear_btn.clicked.connect(self.translation_text.clear)
        trans_btn_row.addWidget(self.trans_clear_btn)

        trans_btn_row.addStretch()
        self.main_layout.addLayout(trans_btn_row)

        # --- Record button ---
        record_row = QHBoxLayout()
        record_row.addStretch()
        self.record_button = QPushButton("⏺ REC", self)
        self.record_button.setCheckable(True)
        self.record_button.setFixedSize(80, 80)
        self.record_button.setStyleSheet(RECORD_BUTTON_IDLE)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.record_button.setFont(font)
        self.record_button.toggled.connect(self._on_record_toggled)
        record_row.addWidget(self.record_button)
        record_row.addStretch()
        self.main_layout.addLayout(record_row)

    # --- Tray & Floating Button integration ---
    def _setup_tray(self):
        """Set up system tray icon and connect signals."""
        self.tray = TrayIcon(self)
        self.tray.show_requested.connect(self._show_window)
        self.tray.quit_requested.connect(self._quit_app)
        self.tray.show()

    def _setup_floating_button(self):
        """Create floating record button used when app is minimized."""
        self.floating_button = FloatingRecordButton()
        self.floating_button.toggled.connect(self._on_floating_button_toggled)
        # Allow double-click on floating button to restore the main window
        try:
            self.floating_button.show_requested.connect(self._show_window)
        except Exception:
            pass
        self.floating_button.position_bottom_right()
        self.floating_button.hide()

    def _show_window(self):
        """Show and focus the main window; hide floating button."""
        self.show()
        self.raise_()
        self.activateWindow()
        # Restore previous geometry if available
        try:
            if getattr(self, "_saved_geometry", None):
                self.setGeometry(self._saved_geometry)
        except Exception:
            pass
        try:
            self.floating_button.hide()
        except Exception:
            pass

    def _quit_app(self):
        """Quit the application."""
        from PySide6.QtWidgets import QApplication

        QApplication.quit()

    def _minimize_to_floating(self):
        """Minimize the app into the floating button instead of normal minimize.

        Save current geometry so it can be restored when reopening the window.
        """
        # Save geometry to restore later
        try:
            self._saved_geometry = self.geometry()
        except Exception:
            self._saved_geometry = None
        # Hide main window and show floating button + tray notification
        self.hide()
        try:
            # Re-position before showing in case screen geometry changed
            self.floating_button.position_bottom_right()
            self.floating_button.show()
        except Exception:
            pass
        try:
            self.tray.show_message(
                "Voice Translator", "Running in background. Press F8 to record."
            )
        except Exception:
            pass

    def _on_floating_button_toggled(self, checked: bool):
        """Sync floating button toggle with main record button."""
        try:
            self.record_button.setChecked(checked)
        except Exception:
            pass

    def changeEvent(self, event):
        """Handle window state changes (minimize -> show floating button)."""
        super().changeEvent(event)
        try:
            if event.type() == event.Type.WindowStateChange:
                if self.isMinimized():
                    # Show floating button when minimized
                    self.floating_button.show()
                else:
                    self.floating_button.hide()
        except Exception:
            pass

    def closeEvent(self, event):
        """Close the application when the window is closed (X).

        The TitleBar X and window manager close action should quit the app.
        """
        try:
            self._quit_app()
        except Exception:
            super().closeEvent(event)

    def _copy_text(self, text_edit: QTextEdit):
        clipboard = QApplication.clipboard()
        clipboard.setText(text_edit.toPlainText())
        try:
            # update status with copy feedback
            self.status_label.setText("📋 Copied to clipboard!")
            # revert status after a short delay, preserving recording state
            QTimer.singleShot(1500, self._restore_status)
        except Exception:
            pass

    def _restore_status(self):
        """Restore status label depending on current recording state."""
        try:
            if getattr(self, "record_button", None) and self.record_button.isChecked():
                self.status_label.setText("🔴 Recording...")
                self.status_label.setStyleSheet(
                    STATUS_RECORDING + " font-size: 14px;"
                )
            else:
                self.status_label.setText("✅ Ready - Press F8 to record")
                self.status_label.setStyleSheet(STATUS_READY + " font-size: 14px;")
        except Exception:
            pass

    def _on_record_toggled(self, checked: bool):
        if checked:
            self.record_button.setText("⏹ STOP")
            self.record_button.setStyleSheet(RECORD_BUTTON_RECORDING)
            try:
                self.status_label.setText("🔴 Recording...")
                self.status_label.setStyleSheet(STATUS_RECORDING + " font-size: 14px;")
            except Exception:
                pass
        else:
            self.record_button.setText("⏺ REC")
            self.record_button.setStyleSheet(RECORD_BUTTON_IDLE)
            try:
                self.status_label.setText("✅ Ready - Press F8 to record")
                self.status_label.setStyleSheet(STATUS_READY + " font-size: 14px;")
            except Exception:
                pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # store offset between mouse global pos and window top-left
            try:
                gp = event.globalPosition().toPoint()
            except Exception:
                gp = event.globalPos()
            self._drag_position = gp - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            try:
                gp = event.globalPosition().toPoint()
            except Exception:
                gp = event.globalPos()
            new_pos = gp - self._drag_position
            self.move(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)


if __name__ == "__main__":
    # Quick manual smoke-check (not run during import)
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    w = FloatingWidget()
    w.show()
    sys.exit(app.exec())
