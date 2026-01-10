import sys
from PySide6.QtCore import qInstallMessageHandler
import traceback

def _qt_message_handler(msg_type, context, message):
    try:
        txt = str(message)
        if "raise()" in txt or "does not support raise" in txt:
            import sys as _sys

            traceback.print_stack(file=_sys.stderr)
    except Exception:
        pass
    try:
        import sys as _sys

        _sys.stderr.write(str(message) + "\n")
    except Exception:
        pass

qInstallMessageHandler(_qt_message_handler)

from src.main import main

if __name__ == "__main__":
    main()
