"""Floating record button for Background Mode."""

import logging
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, Signal, QObject, QEvent, QPointF
from PySide6.QtGui import QMouseEvent
from .drag_utils import DraggableWidget


class FloatingRecordButton(DraggableWidget):
    """Floating button shown when app is minimized.

    Signals:
        toggled(bool): emits True when recording starts
    """

    toggled = Signal(bool)
    # Emitted when user double-clicks the floating widget to restore main window
    show_requested = Signal()

    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        """Configure window properties."""
        # Use explicit WindowType to satisfy static type checkers
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # Use explicit WidgetAttribute to satisfy static type checkers
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(70, 70)

    def _setup_ui(self):
        """Set up the button UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.button = QPushButton("⏺", self)
        self.button.setFixedSize(60, 60)
        self.button.setCheckable(True)
        self.button.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(220, 53, 69, 0.9);
                border-radius: 30px;
                border: 2px solid #dc3545;
                color: white;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: rgba(220, 53, 69, 1.0);
            }
            QPushButton:checked {
                background-color: rgba(220, 53, 69, 1.0);
                border: 3px solid white;
            }
            """
        )
        self.button.toggled.connect(self._on_toggled)
        layout.addWidget(self.button)
        # Install event filter so clicks/drags on the child button are also
        # observed by the floating widget (allowing dragging when clicking the icon).
        try:
            self.button.installEventFilter(self)
        except Exception:
            pass

        # Add a small '+' button to restore the main window (replaces double-click)
        self.restore_button = QPushButton("+", self)
        self.restore_button.setFixedSize(22, 22)
        self.restore_button.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(0,0,0,0.4);
                color: white;
                border-radius: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0,0,0,0.6);
            }
            """
        )
        self.restore_button.clicked.connect(lambda: self.show_requested.emit())
        # Position in top-right corner of the floating widget
        self._position_restore_button()
        # raise() may be unsupported on some QPA platforms (offscreen).
        try:
            from PySide6.QtGui import QGuiApplication

            if QGuiApplication.platformName() != "offscreen":
                self.restore_button.raise_()
        except Exception:
            # If platformName is unavailable or raise_() fails, silently continue
            pass

        # Install event filter on restore button as well so dragging works when
        # user clicks near the restore control.
        try:
            self.restore_button.installEventFilter(self)
        except Exception:
            pass


    def _on_toggled(self, checked: bool):
        """Handle button toggle and emit signal."""
        if checked:
            self.button.setText("⏹")
        else:
            self.button.setText("⏺")
        self.toggled.emit(checked)

    def set_recording(self, recording: bool):
        """Set the recording state externally."""
        self.button.setChecked(recording)

    # Dragging support
    def _to_qpoint(self, global_pos):
        """Normalize a global position (QPointF or QPoint) to QPoint."""
        try:
            if isinstance(global_pos, QPointF):
                return global_pos.toPoint()
        except Exception:
            pass
        return global_pos

    def _position_restore_button(self):
        try:
            self.restore_button.move(self.width() - 24, 4)
        except Exception:
            pass

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            gp = self._to_qpoint(event.globalPosition())
            # Use DraggableWidget helper for consistent offset calculation
            self._drag_position = self._get_drag_offset(event.globalPosition())
            logging.debug(f"[DBG floating_button] mousePress gp={gp} drag_offset={self._drag_position}")
            # Request Wayland-managed move if supported
            self._request_system_move()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            gp = self._to_qpoint(event.globalPosition())
            new_pos = gp - self._drag_position
            self.move(new_pos)
            logging.debug(f"[DBG floating_button] mouseMove moved_to={new_pos}")
            # Persist position via DraggableWidget helper
            try:
                self._persist_position()
            except Exception:
                pass
            event.accept()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Forward mouse events from child widgets to the floating widget handlers.

        This allows dragging the floating button even when the user clicks on the
        visible child QPushButton(s). Keep returning False when forwarding so
        the child still receives the event (preserves toggle behavior).
        """
        if isinstance(event, QMouseEvent):
            try:
                et = event.type()
                if et == QEvent.Type.MouseButtonPress:
                    try:
                        self.mousePressEvent(event)
                    except Exception:
                        pass
                elif et == QEvent.Type.MouseButtonRelease:
                    try:
                        self.mouseReleaseEvent(event)
                    except Exception:
                        pass
                elif et == QEvent.Type.MouseMove:
                    try:
                        self.mouseMoveEvent(event)
                    except Exception:
                        pass
            except Exception:
                pass
            return False

        return super().eventFilter(watched, event)

    def position_bottom_right(self):
        """Position button at bottom-right of primary screen with 20px margin."""
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - 90
        y = screen.height() - 90
        logging.debug(f"[DBG floating_button] position_bottom_right -> x={x} y={y}")
        self.move(x, y)

    def resizeEvent(self, event):
        """Keep the small restore button positioned at top-right when resized."""
        self._position_restore_button()
        super().resizeEvent(event)

    def showEvent(self, event):
        """Ensure restore button is correctly positioned when shown and restore saved position."""
        try:
            self._position_restore_button()
            saved_pos = getattr(self, "_saved_pos", None)
            if saved_pos is not None:
                logging.debug(f"[DBG floating_button] showEvent restoring saved_pos={saved_pos}")
                try:
                    self._restore_position()
                except Exception:
                    pass
            else:
                logging.debug("[DBG floating_button] showEvent no saved_pos, positioning bottom-right")
                self.position_bottom_right()
        except Exception:
            pass
        super().showEvent(event)