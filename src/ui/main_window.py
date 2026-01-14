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
from PySide6.QtCore import Qt, QTimer, QCoreApplication
from PySide6.QtGui import QFont, QKeySequence

# Prefer direct import at runtime; fall back to dynamic lookup to satisfy linters/stubs
try:
    from PySide6.QtWidgets import QShortcut  # type: ignore
except Exception:
    from PySide6 import QtWidgets as _QtWidgets  # type: ignore

    QShortcut = getattr(_QtWidgets, "QShortcut", None)

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
import logging
from src.utils.hotkeys import HotkeyManager


class TitleBar(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        # Cast parent to concrete FloatingWidget so static checkers know available attributes
        self.parent_window = cast("FloatingWidget", parent)
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
        # DraggableWidget handles: _drag_position, _saved_pos, _saved_size
        from src.core.translator import Translator

        self.translator = Translator()
        self.translation_worker = None
        self._setup_window()
        self._setup_ui()
        # Tray and floating button (initialized after UI)
        # Set up tray and floating button independently so one failing doesn't prevent the other.
        try:
            self._setup_tray()
        except Exception as e:
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
            self._hotkey_manager = HotkeyManager(self)
            self._hotkey_manager.register_f8(lambda: signals.toggle_recording.emit())
        except Exception as e:
            logging.exception(f"_setup_global_hotkey failed: {e}")

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

    # --- Small helpers to reduce duplication ---
    def _write_debug_log(self, msg: str) -> None:
        try:
            import os

            log_path = os.path.expanduser("~/.voice_translator_debug.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    def _register_local_f8(self) -> None:
        try:
            if QShortcut is None:
                return
            self._f8_shortcut = QShortcut(QKeySequence("F8"), self)
            # Avoid setContext for static-analysis compatibility
            self._f8_shortcut.activated.connect(lambda: signals.toggle_recording.emit())
            self._f8_shortcut.setEnabled(True)
            self._write_debug_log(
                "[DBG main_window] Registered app-focused F8 shortcut"
            )
            print("[DBG main_window] Registered app-focused F8 shortcut")
        except Exception:
            pass

    def _set_status(
        self, text: str, style: Optional[str] = None, timeout_ms: int = 1500
    ) -> None:
        try:
            self.status_label.setText(text)
            if style is not None:
                self.status_label.setStyleSheet(style + " font-size: 14px;")
            # restore default after timeout
            if timeout_ms:
                QTimer.singleShot(timeout_ms, self._restore_status)
        except Exception:
            pass

    def _add_copy_clear_row(
        self, text_edit: QTextEdit, prefix: Optional[str] = None
    ) -> None:
        try:
            row = QHBoxLayout()
            copy_btn = QPushButton("📋 Copy", self)
            copy_btn.clicked.connect(lambda: self._copy_text(text_edit))
            row.addWidget(copy_btn)

            clear_btn = QPushButton("🗑️ Clear", self)
            clear_btn.clicked.connect(text_edit.clear)
            row.addWidget(clear_btn)

            row.addStretch()
            self.main_layout.addLayout(row)
            if prefix:
                try:
                    setattr(self, f"{prefix}_copy_btn", copy_btn)
                    setattr(self, f"{prefix}_clear_btn", clear_btn)
                except Exception:
                    pass
        except Exception:
            pass

    def _persist_geometry(self) -> None:
        try:
            self._persist_position()
            try:
                self._saved_size = self.size()
            except Exception:
                pass
            print(
                f"[DBG main_window] persisted pos={getattr(self, '_saved_pos', None)} size={getattr(self, '_saved_size', None)}"
            )
        except Exception:
            pass

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

        self._add_copy_clear_row(self.portuguese_text, prefix="pt")

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

        # Connect translation button
        self.translate_btn.clicked.connect(self._on_translate_clicked)

        # --- Translation section ---
        self.trans_label = QLabel("🇺🇸 Translation:", self)
        self.main_layout.addWidget(self.trans_label)

        self.translation_text = QTextEdit(self)
        self.translation_text.setPlaceholderText("Translated text will appear here...")
        self.translation_text.setMinimumHeight(80)
        self.translation_text.setReadOnly(True)
        self.main_layout.addWidget(self.translation_text)

        self._add_copy_clear_row(self.translation_text, prefix="trans")

        # Connect translation signals
        try:
            signals.translation_started.connect(self._on_translation_started)
            signals.translation_complete.connect(self._on_translation_complete)
            signals.translation_error.connect(self._on_translation_error)
        except Exception as e:
            print(f"[DBG main_window] Failed to connect translation signals: {e}")

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
            # Also register an application-scoped F8 shortcut (focused window only)
            try:
                self._register_local_f8()
            except Exception:
                pass
        except Exception:
            pass

    def _on_translate_clicked(self):
        from src.core.workers import TranslationWorker

        # use top-level `signals` imported earlier
        text = self.portuguese_text.toPlainText()
        target_language = self.language_combo.currentText()
        # Avoid multiple concurrent workers
        worker = getattr(self, "translation_worker", None)
        if worker is not None:
            try:
                worker.quit()
            except Exception:
                pass
        self.translation_worker = TranslationWorker(
            self.translator, text, target_language
        )
        self.translation_worker.start()

    def _on_translation_started(self):
        self.status_label.setText("🔄 Translating...")
        self.status_label.setStyleSheet(STATUS_RECORDING + " font-size: 14px;")
        self.translation_text.setPlainText("")

    def _on_translation_complete(self, translated_text):
        self.translation_text.setPlainText(translated_text)
        self.status_label.setText("✅ Translation complete")
        self.status_label.setStyleSheet(STATUS_READY + " font-size: 14px;")

    def _on_translation_error(self, error_msg):
        self.status_label.setText(f"❌ Translation error: {error_msg}")
        self.status_label.setStyleSheet(STATUS_READY + " font-size: 14px;")

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
            # Delegate hotkey setup to HotkeyManager when available.
            if getattr(self, "_hotkey_manager", None):
                try:
                    self._hotkey_manager.register_f8(
                        lambda: signals.toggle_recording.emit()
                    )
                except Exception:
                    # As a last resort, register an app-focused shortcut
                    try:
                        self._register_local_f8()
                    except Exception:
                        pass
            else:
                try:
                    self._register_local_f8()
                except Exception:
                    pass
        except Exception as e:
            logging.exception(f"_setup_global_hotkey failed: {e}")

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
            saved_size = getattr(self, "_saved_size", None)
            if saved_size is not None:
                try:
                    self.resize(saved_size)
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
        # Clean up global hotkey if registered via HotkeyManager
        try:
            if getattr(self, "_hotkey_manager", None):
                try:
                    self._hotkey_manager.unregister_all()
                except Exception:
                    pass
        except Exception:
            pass
        # Use QCoreApplication.instance() to quit safely without assuming global QApplication
        try:
            app = QCoreApplication.instance()
            # Use typing.cast so static analyzers know `app` may be None or a QCoreApplication
            app = cast(Optional[QCoreApplication], app)
            if app is not None:
                try:
                    app.quit()
                except Exception:
                    pass
        except Exception:
            # Last resort: attempt to call QApplication.quit() if available
            try:
                from PySide6.QtWidgets import QApplication

                QApplication.quit()
            except Exception:
                pass

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
                    saved_fb_pos = getattr(self.floating_button, "_saved_pos", None)
                    if saved_fb_pos is not None:
                        try:
                            self.floating_button.move(saved_fb_pos)
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
                worker = getattr(self, "worker", None)
                if worker is not None:
                    try:
                        worker.stop_recording()
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
            # Get global mouse position
            try:
                gp = event.globalPosition().toPoint()
            except Exception:
                gp = event.globalPos()
            # Use DraggableWidget's _get_drag_offset helper
            self._drag_position = self._get_drag_offset(gp)
            print(
                f"[DBG main_window] mousePress gp={gp} drag_offset={self._drag_position}"
            )
            # Request system move for Wayland support
            self._request_system_move()
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
            print(f"[DBG main_window] mouseMove moved_to={new_pos}")
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        """Handle focused key presses as a fallback for global hotkeys.

        Specifically capture F8 and emit signals.toggle_recording when the app
        has focus. This does not require QShortcut and works across PySide6
        variations where QShortcut may fail to import.
        """
        try:
            key = event.key()
            # Resolve F8 value robustly without direct enum attribute access
            qt_key_enum = getattr(Qt, "Key", None)
            if qt_key_enum is not None:
                f8_val = (
                    getattr(qt_key_enum, "Key_F8", None)
                    or getattr(qt_key_enum, "F8", None)
                    or getattr(qt_key_enum, "KeyF8", None)
                )
            else:
                f8_val = (
                    getattr(Qt, "Key_F8", None)
                    or getattr(Qt, "F8", None)
                    or getattr(Qt, "KeyF8", None)
                )

            if f8_val is not None and key == f8_val:
                try:
                    signals.toggle_recording.emit()
                    self._write_debug_log(
                        "[DBG main_window] keyPressEvent: F8 pressed, emitted toggle_recording"
                    )
                except Exception:
                    pass
                event.accept()
                return
        except Exception:
            pass
        try:
            super().keyPressEvent(event)
        except Exception:
            # Some Qt platforms may not implement keyPressEvent; ignore silently
            pass

    def moveEvent(self, event):
        """Persist position whenever the window is moved."""
        try:
            self._persist_geometry()
        except Exception:
            pass
        super().moveEvent(event)

    def resizeEvent(self, event):
        """Persist geometry whenever the window is resized."""
        try:
            self._persist_geometry()
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
