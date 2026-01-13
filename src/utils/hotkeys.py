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
            logger.warning("No keyboard module and no widget fallback available; hotkey disabled")
            return

        try:
            handler = keyboard.add_hotkey("f8", callback)
            self._keyboard = keyboard
            self._keyboard_hotkey = handler
            logger.info("Registered global hotkey F8")
        except Exception:
            logger.exception("Failed to register global hotkey via keyboard; trying QShortcut fallback")
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
