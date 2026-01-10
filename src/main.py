"""Voice Translator - entrypoint.

Launch the Qt GUI by default. If the GUI cannot start (missing PySide6 or
running in a headless environment), fall back to a minimal text message.
"""

import builtins
import os

# Lightweight debug print wrapper: preserve original print but also persist
# lines that begin with [DBG to a per-user temporary log for later inspection.
_orig_print = builtins.print
_log_path = os.path.expanduser("~/.voice_translator_debug.log")

def _dbg_print(*args, **kwargs):
    _orig_print(*args, **kwargs)
    try:
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        msg = sep.join(str(a) for a in args) + end
        if msg.startswith("[DBG"):
            with open(_log_path, "a", encoding="utf-8") as f:
                f.write(msg)
    except Exception:
        # Never let logging break the app
        pass

builtins.print = _dbg_print


def main() -> None:
    try:
        from PySide6.QtWidgets import QApplication
        import sys

        # Import GUI after confirming PySide6 is available
        from src.ui.main_window import FloatingWidget

        app = QApplication.instance() or QApplication(sys.argv)

        # Install a Qt message handler to capture stack traces for problematic
        # platform plugin warnings (e.g., 'This plugin does not support raise()').
        try:
            from PySide6.QtCore import qInstallMessageHandler
            import traceback as _traceback

            def _qt_message_handler(msg_type, context, message):
                try:
                    txt = str(message)
                    if "raise()" in txt or "does not support raise" in txt:
                        import sys as _sys

                        _traceback.print_stack(file=_sys.stderr)
                except Exception:
                    pass
                try:
                    # forward message to stderr so it still appears
                    import sys as _sys

                    _sys.stderr.write(str(message) + "\n")
                except Exception:
                    pass

            qInstallMessageHandler(_qt_message_handler)
        except Exception:
            pass

        w = FloatingWidget()
        w.show()
        sys.exit(app.exec())
    except Exception as e:
        # Fall back to a simple CLI message when GUI cannot be started
        print("Voice Translator starting (GUI unavailable):", e)


if __name__ == "__main__":
    main()
