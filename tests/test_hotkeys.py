import sys
from types import SimpleNamespace

import pytest

from src.utils.hotkeys import HotkeyManager


def test_register_with_keyboard_module(monkeypatch):
    called = {}

    class DummyKeyboard:
        def add_hotkey(self, key, callback):
            called['key'] = key
            called['cb'] = callback
            return 'handler-1'

        def remove_hotkey(self, handler):
            called['removed'] = handler

    monkeypatch.setitem(sys.modules, 'keyboard', DummyKeyboard())

    mgr = HotkeyManager(None)

    def cb():
        called['fired'] = True

    mgr.register_f8(cb)

    assert mgr._keyboard is not None
    assert mgr._keyboard_hotkey == 'handler-1'

    # cleanup
    mgr.unregister_all()
    assert 'removed' in called


def test_register_with_widget_fallback(monkeypatch):
    # Ensure no keyboard module
    monkeypatch.setitem(sys.modules, 'keyboard', None)

    # Provide dummy QShortcut and QKeySequence
    created = {}

    class DummyShortcut:
        def __init__(self, seq, parent):
            created['seq'] = seq
            created['parent'] = parent
            self.activated = SimpleNamespace(connect=lambda cb: created.setdefault('cb', cb))
        def setEnabled(self, v):
            created['enabled'] = v

    monkeypatch.setattr('PySide6.QtWidgets.QShortcut', DummyShortcut, raising=False)
    monkeypatch.setattr('PySide6.QtGui.QKeySequence', lambda s: s, raising=False)

    widget = object()
    mgr = HotkeyManager(widget)

    def cb():
        created['fired'] = True

    mgr.register_f8(cb)

    assert mgr._shortcut is not None
    assert created.get('cb') is not None

    # cleanup should not raise
    mgr.unregister_all()
