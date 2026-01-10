from typing import Optional, cast

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
from PySide6.QtGui import QFont, QGuiApplication

from .styles import (
    DARK_THEME,
    RECORD_BUTTON_IDLE,
    RECORD_BUTTON_RECORDING,
    STATUS_READY,
    STATUS_RECORDING,
)
from .tray_icon import TrayIcon
from .floating_button import FloatingRecordButton

from src.core.transcriber import Transcriber, TranscriberError
from src.core.workers import RecordingWorker
from src.utils.signals import signals
from .drag_utils import DraggableWidget


class TitleBar(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        # Cast parent to concrete FloatingWidget so static checkers know available attributes
        self.parent_window = cast("FloatingWidget", parent)
        self._setup_ui()
        # Install event filters on child widgets so clicks anywhere on the
        # title bar can be used to drag the parent window.
        try:
            for child in self.findChildren(QWidget) or []:
                child.installEventFilter(self)
        except Exception:
            pass

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent

        if event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonRelease,
        ):
            # Forward mouse events to parent window for dragging behavior.
            try:
                if event.type() == QEvent.Type.MouseButtonPress:
                    if isinstance(event, QMouseEvent):
                        try:
                            self.parent_window.mousePressEvent(event)
                        except Exception:
                            pass
                elif event.type() == QEvent.Type.MouseMove:
                    if isinstance(event, QMouseEvent):
                        try:
                            self.parent_window.mouseMoveEvent(event)
                        except Exception:
                            pass
                else:
                    # persist position on release - parent handles persistence
                    try:
                        pass
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                event.accept()
            except Exception:
                pass
            return True
        return super().eventFilter(watched, event)

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
        # TitleBar should forward mouse press events to the parent floating widget
        from PySide6.QtGui import QMouseEvent
        if isinstance(event, QMouseEvent):
            try:
                self.parent_window.mousePressEvent(event)
            except Exception:
                pass
        else:
            try:
                super().mousePressEvent(event)
            except Exception:
                pass

    def mouseMoveEvent(self, event):
        # TitleBar should forward mouse move events to the parent floating widget
        from PySide6.QtGui import QMouseEvent
        if isinstance(event, QMouseEvent):
            try:
                self.parent_window.mouseMoveEvent(event)
            except Exception:
                pass
        else:
            try:
                super().mouseMoveEvent(event)
            except Exception:
                pass


class FloatingWidget(DraggableWidget):
    def __init__(self):
        super().__init__()
        self._drag_position = QPoint()
        self._setup_window()
        self._setup_ui()
        # Install event filters on all child widgets so clicks anywhere in the window can be used to drag it.
        try:
            for child in self.findChildren(QWidget) or []:
                child.installEventFilter(self)
        except Exception:
            pass
        # Tray and floating button (initialized after UI)
        # Set up tray and floating button independently so one failing doesn't prevent the other.
        try:
            self._setup_tray()
        except Exception as e:
            # Log failure so debugging shows why tray initialization failed.
            import traceback

            print(f"[DBG main_window] _setup_tray failed: {e}")
            traceback.print_exc()
        try:
            self._setup_floating_button()
        except Exception as e:
            import traceback

            print(f"[DBG main_window] _setup_floating_button failed: {e}")
            traceback.print_exc()
        try:
            # Attempt to register a global F8 hotkey to mirror the UI hint.
            # Runs only if `keyboard` package is available and permissions allow it.
            self._setup_global_hotkey()
        except Exception as e:
            print(f"[DBG main_window] _setup_global_hotkey failed: {e}")

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent

        if event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonRelease,
        ):
            # Forward mouse events to this widget's handlers so dragging works when clicking anywhere.
            try:
                if event.type() == QEvent.Type.MouseButtonPress:
                    if isinstance(event, QMouseEvent):
                        try:
                            self.mousePressEvent(event)
                        except Exception:
                            pass
                elif event.type() == QEvent.Type.MouseMove:
                    if isinstance(event, QMouseEvent):
                        try:
                            self.mouseMoveEvent(event)
                        except Exception:
                            pass
                else:
                    # persist position on release
                    try:
                        self._saved_geometry = self.geometry()
                    except Exception:
                        pass
            except Exception:
                pass
            # Swallow the event to avoid child widgets interrupting the drag sequence.
            try:
                event.accept()
            except Exception:
                pass
            return True
        return super().eventFilter(watched, event)

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

        # Transcriber and worker (initialized when recording starts)
        self.transcriber: Optional[Transcriber] = None
        self.worker: Optional[RecordingWorker] = None

        # Connect global signals to UI handlers
        try:
            signals.transcription_complete.connect(self._on_transcription_complete)
            signals.transcription_error.connect(self._on_transcription_error)
            signals.recording_started.connect(
                lambda: self.status_label.setText("🔴 Recording...")
            )
            signals.recording_stopped.connect(
                lambda: self.status_label.setText("✅ Ready - Press F8 to record")
            )
            signals.status_update.connect(lambda s: self.status_label.setText(s))
            # Allow external toggles (e.g. global hotkey) to toggle the record button safely
            try:
                signals.toggle_recording.connect(lambda: self.record_button.toggle())
            except Exception:
                pass
        except Exception:
            pass

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
        try:
            self.floating_button.show_requested.connect(self._show_window)
        except Exception:
            pass
        # Do not force a position here; the floating button will restore its
        # last saved position when shown. Initially keep it hidden.
        self.floating_button.hide()

    def _setup_global_hotkey(self):
        """Register a global F8 hotkey that toggles recording via signals.toggle_recording.

        This is best-effort: if the `keyboard` package is unavailable or the OS denies
        the permission (e.g., macOS accessibility), this will log and continue.
        """
        try:
            import keyboard  # type: ignore
        except Exception:
            print(
                "[DBG main_window] keyboard module not available; global hotkey disabled"
            )
            return
        try:
            # Register F8 to toggle recording; store handler id for cleanup
            handler = keyboard.add_hotkey("f8", lambda: signals.toggle_recording.emit())
            self._keyboard = keyboard
            self._keyboard_hotkey = handler
            print("[DBG main_window] Registered global hotkey F8")
        except Exception as e:
            print(f"[DBG main_window] Failed to register global hotkey: {e}")

    def _show_window(self):
        """Show and focus the main window; hide floating button."""
        self.show()
        # Some QPA platforms (e.g. offscreen) don't support raise(); avoid
        # calling it on those platforms to prevent noisy warnings.
        try:
            from PySide6.QtGui import QGuiApplication

            if QGuiApplication.platformName() != "offscreen":
                try:
                    self.raise_()
                except Exception:
                    pass
        except Exception:
            # If platformName check fails, ignore and continue
            pass
        # Try to activate the window, but ignore if unsupported
        try:
            self.activateWindow()
        except Exception:
            pass
        print(
            f"[DBG main_window] _show_window: saved_pos={getattr(self, '_saved_pos', None)} saved_size={getattr(self, '_saved_size', None)}"
        )
        # Restore previous position/size if available
        try:
            saved_pos = getattr(self, "_saved_pos", None)
            if saved_pos is not None:
                self.move(saved_pos)
            if getattr(self, "_saved_size", None):
                try:
                    self.resize(self._saved_size)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.floating_button.hide()
        except Exception:
            pass

    def _quit_app(self):
        """Quit the application."""
        # Clean up global hotkey if registered
        try:
            if getattr(self, "_keyboard", None):
                try:
                    self._keyboard.remove_hotkey(
                        getattr(self, "_keyboard_hotkey", "f8")
                    )
                    print("[DBG main_window] Removed global hotkey F8")
                except Exception:
                    pass
        except Exception:
            pass
        from PySide6.QtWidgets import QApplication

        QApplication.quit()

    def _minimize_to_floating(self):
        """Minimize the app into the floating button instead of normal minimize.

        Save current geometry so it can be restored when reopening the window.
        """
        # Save position/size to restore later
        try:
            self._saved_pos = self.pos()
            self._saved_size = self.size()
        except Exception:
            self._saved_pos = None
            self._saved_size = None
        print(
            f"[DBG main_window] _minimize_to_floating: saved_pos={getattr(self,'_saved_pos',None)} saved_size={getattr(self,'_saved_size',None)}"
        )
        # Hide main window and show floating button + tray notification
        print(
            f"[DBG main_window] _minimize_to_floating: has_floating_button={hasattr(self, 'floating_button')} floating_button_obj={getattr(self, 'floating_button', None)}"
        )
        self.hide()
        print(
            "[DBG main_window] main window hidden, attempting to show floating_button"
        )
        try:
            # If the floating button was moved by the user previously, restore
            # that position; otherwise, position it at bottom-right.
            if getattr(self, "floating_button", None) is None:
                print(
                    "[DBG main_window] no floating_button attribute - skipping show()"
                )
            else:
                try:
                    if getattr(self.floating_button, "_saved_pos", None):
                        try:
                            self.floating_button.move(self.floating_button._saved_pos)
                        except Exception:
                            print(
                                "[DBG main_window] floating_button.move(saved_pos) failed, positioning bottom-right"
                            )
                            self.floating_button.position_bottom_right()
                    else:
                        self.floating_button.position_bottom_right()
                    self.floating_button.show()
                    print("[DBG main_window] floating_button.show() called")
                except Exception as e:
                    print(f"[DBG main_window] floating_button.show() raised: {e}")
        except Exception as e:
            print(f"[DBG main_window] _minimize_to_floating outer exception: {e}")
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
                self.status_label.setStyleSheet(STATUS_RECORDING + " font-size: 14px;")
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
                self.status_label.setText("⏳ Loading model...")
                # Create and load model (may block briefly)
                self.transcriber = Transcriber()
                try:
                    self.transcriber.load_model()
                except TranscriberError as e:
                    self.status_label.setText(f"Model error: {e}")
                    self.record_button.setChecked(False)
                    return
                # Start worker
                self.worker = RecordingWorker(self.transcriber)
                self.worker.start()
                self.status_label.setText("🔴 Recording...")
                self.status_label.setStyleSheet(STATUS_RECORDING + " font-size: 14px;")
            except Exception as e:
                self.status_label.setText(f"Unexpected: {e}")
                self.record_button.setChecked(False)
        else:
            self.record_button.setText("⏺ REC")
            self.record_button.setStyleSheet(RECORD_BUTTON_IDLE)
            try:
                # Signal worker to stop; worker will emit transcription_complete when done
                if getattr(self, "worker", None):
                    try:
                        self.worker.stop_recording()
                    except Exception:
                        pass
                self.status_label.setText("Processing...")
                self.status_label.setStyleSheet(STATUS_READY + " font-size: 14px;")
            except Exception:
                pass

    def _on_transcription_complete(self, text: str):
        try:
            self.portuguese_text.setPlainText(text)
            self.status_label.setText("✅ Ready - Press F8 to record")
            self.status_label.setStyleSheet(STATUS_READY + " font-size: 14px;")
        except Exception:
            pass

    def _on_transcription_error(self, msg: str):
        try:
            self.status_label.setText(f"Error: {msg}")
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
            # Use window position instead of frameGeometry to compute offset
            try:
                self._drag_position = gp - self.pos()
            except Exception:
                self._drag_position = gp - self.frameGeometry().topLeft()
            print(
                f"[DBG main_window] mousePress gp={gp} drag_offset={self._drag_position}"
            )
            # On some platforms (Wayland) clients must request a system move from the compositor
            try:
                self._request_system_move()
            except Exception:
                pass
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
            print(
                f"[DBG main_window] mouseMove moved_to={new_pos} saved_pos-> {self.pos()}"
            )
            try:
                try:
                    self._persist_position()
                except Exception:
                    self._saved_pos = self.pos()
                try:
                    self._saved_size = self.size()
                except Exception:
                    self._saved_size = None
            except Exception:
                pass
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def moveEvent(self, event):
        """Persist position whenever the window is moved."""
        try:
            try:
                self._persist_position()
            except Exception:
                self._saved_pos = self.pos()
            try:
                self._saved_size = self.size()
            except Exception:
                self._saved_size = None
            print(
                f"[DBG main_window] moveEvent persisted pos={getattr(self, '_saved_pos', None)} size={getattr(self, '_saved_size', None)}"
            )
        except Exception:
            pass
        super().moveEvent(event)

    def resizeEvent(self, event):
        """Persist geometry whenever the window is resized."""
        try:
            try:
                self._persist_position()
            except Exception:
                self._saved_pos = self.pos()
            try:
                self._saved_size = self.size()
            except Exception:
                self._saved_size = None
            print(
                f"[DBG main_window] resizeEvent persisted pos={getattr(self, '_saved_pos', None)} size={getattr(self, '_saved_size', None)}"
            )
        except Exception:
            pass
        super().resizeEvent(event)


if __name__ == "__main__":
    # Quick manual smoke-check (not run during import)
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    w = FloatingWidget()
    w.show()
    sys.exit(app.exec())
