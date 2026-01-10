from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget


class DraggableWidget(QWidget):
    """Minimal helper to centralize drag/position persistence and Wayland move."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_position = QPoint()
        self._saved_pos = None
        self._saved_size = None

    def _get_drag_offset(self, global_pos):
        """Return QPoint offset used for dragging calculations."""
        if hasattr(global_pos, 'toPoint'):
            gp = global_pos.toPoint()
        else:
            gp = global_pos
        return gp - self.pos()

    def _persist_position(self):
        """Persist current position into internal saved slot."""
        try:
            self._saved_pos = self.pos()
        except Exception:
            self._saved_pos = None

    def _restore_position(self):
        """Restore position if previously persisted."""
        from PySide6.QtCore import QPoint, QSize
        pos = getattr(self, "_saved_pos", None)
        if isinstance(pos, QPoint):
            try:
                self.move(pos)
            except Exception:
                pass

    def _persist_geometry(self):
        """Persist current position and size into internal saved slots."""
        try:
            self._saved_pos = self.pos()
        except Exception:
            self._saved_pos = None
        try:
            self._saved_size = self.size()
        except Exception:
            self._saved_size = None

    def _restore_geometry(self):
        """Restore position and size if previously persisted."""
        from PySide6.QtCore import QPoint, QSize
        pos = getattr(self, "_saved_pos", None)
        size = getattr(self, "_saved_size", None)
        if isinstance(pos, QPoint):
            try:
                self.move(pos)
            except Exception:
                pass
        if isinstance(size, QSize):
            try:
                self.resize(size)
            except Exception:
                pass

    def _request_system_move(self):
        """Request the platform window to start a system move (Wayland helper)."""
        wh = None
        try:
            win = self.window()
            wh = win.windowHandle() if win is not None else None
        except Exception:
            wh = None

        if wh is not None and hasattr(wh, 'startSystemMove'):
            try:
                wh.startSystemMove()
                return True
            except Exception:
                return False
        return False
