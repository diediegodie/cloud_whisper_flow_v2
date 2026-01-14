"""HotkeyManager: centralizes global and local hotkey logic.

This module prefers the `keyboard` library for global hotkeys when available
and permitted; otherwise it falls back to an application-focused `QShortcut`.

The API is intentionally small to make testing and mocking straightforward.
"""

from typing import Optional, Callable
import logging


logger = logging.getLogger(__name__)


class HotkeyManager:
    def __init__(self, parent: Optional[object] = None):
        # parent is typically a QWidget (e.g. FloatingWidget) but tests may pass None or a plain object
        self.parent = parent
        self._keyboard = None
        self._keyboard_hotkey = None
        self._shortcut = None

    def _log(self, msg: str) -> None:
        try:
            # Prefer widget debug helper if available
            if getattr(self.parent, "_write_debug_log", None):
                try:
                    self.parent._write_debug_log(msg)
                except Exception:
                    pass
        finally:
            logger.debug(msg)

    def register_f8(self, callback: Optional[Callable] = None) -> None:
        """Attempt to register a global F8 hotkey; fall back to a local shortcut.

        :param callback: callable to invoke when F8 is pressed
        """
        try:
            # Local import so tests can control sys.modules
            import keyboard  # type: ignore

            # Guard against monkeypatching cases where sys.modules['keyboard'] is None
            if keyboard is None or not hasattr(keyboard, "add_hotkey"):
                raise ImportError("keyboard module not available")

            try:
                handler = keyboard.add_hotkey("f8", callback)
                self._keyboard = keyboard
                self._keyboard_hotkey = handler
                self._log("[HotkeyManager] Registered global hotkey F8")
                return
            except Exception as e:  # pragma: no cover - platform dependent
                self._log(f"[HotkeyManager] Failed to register global hotkey: {e}")
        except Exception:
            # Treat any import/availability issue as a signal to fall back
            self._log(
                "[HotkeyManager] keyboard module not available; falling back to local shortcut"
            )

        # Fallback to application-focused shortcut
        try:
            self.register_local_f8(self.parent, callback)
            self._log("[HotkeyManager] Registered app-focused F8 shortcut as fallback")
        except Exception as e:  # pragma: no cover - defensive
            self._log(f"[HotkeyManager] Failed to register local F8 shortcut: {e}")

    def register_local_f8(
        self,
        parent_widget: Optional[object] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        """Register a QShortcut-bound F8 that works while the application has focus.

        This method performs a local import of PySide6 types so tests can monkeypatch
        them without importing the full UI stack at test collection time.
        """
        if parent_widget is None:
            parent_widget = self.parent
        if parent_widget is None:
            return

        try:
            from PySide6.QtWidgets import QShortcut  # type: ignore
            from PySide6.QtGui import QKeySequence  # type: ignore
        except Exception:
            # If Qt isn't available in the environment, behave as a no-op
            self._log(
                "[HotkeyManager] Qt not available for local shortcut registration"
            )
            return

        try:
            seq = QKeySequence("F8")
            shortcut = QShortcut(seq, parent_widget)
            if hasattr(shortcut, "activated"):
                try:
                    # Connect signal safely; some test fakes provide a simple `activated.connect`
                    shortcut.activated.connect(callback)
                except Exception:
                    # Some test doubles return a simple object; try setting attribute instead
                    try:
                        setattr(shortcut, "_cb", callback)
                    except Exception:
                        pass
            try:
                shortcut.setEnabled(True)
            except Exception:
                pass
            self._shortcut = shortcut
            self._log("[HotkeyManager] Local F8 shortcut registered")
        except Exception as e:  # pragma: no cover - defensive
            self._log(
                f"[HotkeyManager] Exception while registering local shortcut: {e}"
            )

    def unregister_all(self) -> None:
        """Remove any registered hotkeys and clean up resources."""
        # Remove global keyboard hotkey
        try:
            if self._keyboard and self._keyboard_hotkey:
                try:
                    # Some keyboard implementations expose remove_hotkey
                    remove = getattr(self._keyboard, "remove_hotkey", None)
                    if callable(remove):
                        remove(self._keyboard_hotkey)
                    else:
                        # Try to call by passing handler directly
                        try:
                            self._keyboard.remove_hotkey(self._keyboard_hotkey)
                        except Exception:
                            pass
                except Exception:
                    pass
                finally:
                    self._keyboard_hotkey = None
                    self._keyboard = None
        except Exception:
            pass

        # Disable local shortcut if present
        try:
            if self._shortcut is not None:
                try:
                    # best-effort: disable and drop reference
                    if hasattr(self._shortcut, "setEnabled"):
                        try:
                            self._shortcut.setEnabled(False)
                        except Exception:
                            pass
                except Exception:
                    pass
                finally:
                    self._shortcut = None
        except Exception:
            pass


from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class HotkeyManager:
    """Simple HotkeyManager that abstracts global hotkey registration.

    It tries to use the `keyboard` module for a global hotkey and falls back to a
    widget-scoped QShortcut when a QWidget is provided.
    """

    def __init__(self, widget: Optional[object] = None):
        # widget is a QWidget when provided; kept as object to avoid importing Qt at module import time
        self.widget = widget
        self._keyboard = None
        self._keyboard_hotkey = None
        self._shortcut = None

    def register_f8(self, callback: Callable[[], None]) -> None:
        """Register F8 to call callback.

        If the `keyboard` module is available, register a global hotkey. Otherwise,
        if a widget was provided, register a QShortcut on that widget.
        """
        try:
            import keyboard  # type: ignore
        except Exception:
            logger.info("keyboard module not available; attempting QShortcut fallback")
            if self.widget is not None:
                try:
                    from PySide6.QtWidgets import QShortcut
                    from PySide6.QtGui import QKeySequence

                    self._shortcut = QShortcut(QKeySequence("F8"), self.widget)
                    self._shortcut.activated.connect(callback)
                    self._shortcut.setEnabled(True)
                    logger.info("Registered app-focused F8 shortcut")
                    return
                except Exception:
                    logger.exception("Failed to register QShortcut fallback")
            logger.warning(
                "No keyboard module and no widget fallback available; hotkey disabled"
            )
            return

        try:
            handler = keyboard.add_hotkey("f8", callback)
            self._keyboard = keyboard
            self._keyboard_hotkey = handler
            logger.info("Registered global hotkey F8")
        except Exception:
            logger.exception(
                "Failed to register global hotkey via keyboard; trying QShortcut fallback"
            )
            if self.widget is not None:
                try:
                    from PySide6.QtWidgets import QShortcut
                    from PySide6.QtGui import QKeySequence

                    self._shortcut = QShortcut(QKeySequence("F8"), self.widget)
                    self._shortcut.activated.connect(callback)
                    self._shortcut.setEnabled(True)
                    logger.info("Registered app-focused F8 shortcut as fallback")
                except Exception:
                    logger.exception("Failed to register fallback QShortcut")

    def unregister_all(self) -> None:
        """Unregister any registered hotkeys/shortcuts."""
        if self._keyboard is not None:
            try:
                self._keyboard.remove_hotkey(self._keyboard_hotkey)
                logger.info("Removed global hotkey F8")
            except Exception:
                logger.exception("Failed removing global hotkey")
            self._keyboard = None
            self._keyboard_hotkey = None
        if self._shortcut is not None:
            try:
                self._shortcut.setEnabled(False)
                logger.info("Disabled app-focused F8 shortcut")
            except Exception:
                logger.exception("Failed disabling QShortcut")
            self._shortcut = None
