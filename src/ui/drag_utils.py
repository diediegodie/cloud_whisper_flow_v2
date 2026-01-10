from PySide6.QtCore import QPoint
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget


class DraggableWidget(QWidget):
    """Minimal helper to centralize drag/position persistence and Wayland move."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_position = QPoint()
        self._saved_pos = None
        self._saved_size = None

    def _get_drag_offset(self, global_pos: QPoint) -> QPoint:
        """Calculate drag offset from global mouse position.
        
        Args:
            global_pos: Global mouse position as QPoint
            
        Returns:
            QPoint offset between global position and window position
        """
        try:
            if hasattr(global_pos, 'toPoint'):
                gp = global_pos.toPoint()
            else:
                gp = global_pos
            return gp - self.pos()
        except Exception:
            # Fallback for edge cases
            return gp - self.frameGeometry().topLeft()

    def _persist_position(self) -> None:
        """Save current position for later restoration."""
        try:
            self._saved_pos = self.pos()
        except Exception:
            self._saved_pos = None

    def _restore_position(self) -> None:
        """Restore saved position if available."""
        from PySide6.QtCore import QPoint
        pos = getattr(self, "_saved_pos", None)
        if isinstance(pos, QPoint):
            try:
                self.move(pos)
            except Exception:
                pass

    def _request_system_move(self) -> bool:
        """Request Wayland compositor-managed move if available.
        
        Returns:
            True if startSystemMove was called, False otherwise.
        """
        try:
            if QGuiApplication.platformName().lower().startswith("wayland"):
                wh = self.window().windowHandle()
                if wh is not None:
                    wh.startSystemMove()
                    return True
        except Exception:
            pass
        return False
