Hotkeys
=======

Overview
--------

This project prefers to register a global F8 hotkey using the Python `keyboard`
library when available. If `keyboard` is not present or the OS denies the
permission (common on Linux/Wayland without elevated privileges), the app
falls back to an application-focused `QShortcut` that works while the app has
focus.

Linux limitations
-----------------

- The `keyboard` library requires elevated privileges on many Linux setups to
  capture global key events. On Wayland, global key capturing is often not
  supported by `keyboard` at all.
- Recommended options:
  - Run on a platform where `keyboard` works (Windows/macOS with accessibility
    permissions configured).
  - Implement a platform-specific adapter (X11/Wayland) or a small helper
    daemon with appropriate privileges.

Testing
-------

Tests mock the presence/absence of `keyboard` and the Qt `QShortcut` APIs so
you can run them without OS-level privileges. To run the hotkey tests:

```bash
pytest tests/test_hotkeys.py -q
```

Implementation notes
--------------------

- Hotkey logic is centralized in `src/utils/hotkeys.py` (`HotkeyManager`).
- The UI delegates registration and cleanup to the manager; fallback behavior
  is intentionally conservative to avoid raising in environments without
  GUI or elevated permissions.
