"""Floating record button for Background Mode."""

from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QPoint, Signal, QEvent
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
        self.restore_button.move(self.width() - 24, 4)
        # raise() may be unsupported on some QPA platforms (offscreen).
        try:
            from PySide6.QtGui import QGuiApplication

            if QGuiApplication.platformName() != "offscreen":
                self.restore_button.raise_()
        except Exception:
            # If platformName is unavailable or raise_() fails, silently continue
            pass

        # Install event filters so child widgets forward mouse events to the
        # floating widget. This ensures dragging works when clicking anywhere
        # on the control (button or small restore button).
        try:
            self.button.installEventFilter(self)
            self.restore_button.installEventFilter(self)
        except Exception:
            pass

        # Allow dragging the floating widget when interacting with the small restore button.
        orig_restore_press = getattr(self.restore_button, "mousePressEvent", None)
        orig_restore_move = getattr(self.restore_button, "mouseMoveEvent", None)
        orig_restore_release = getattr(self.restore_button, "mouseReleaseEvent", None)

        def _restore_mousePress(event: QMouseEvent):
            if callable(orig_restore_press):
                try:
                    orig_restore_press(event)
                except Exception:
                    pass
            if event.button() == Qt.MouseButton.LeftButton:
                try:
                    gp = event.globalPosition().toPoint()
                except Exception:
                    gp = event.globalPos()
                try:
                    self._drag_position = self._get_drag_offset(gp)
                except Exception:
                    try:
                        self._drag_position = gp - self.frameGeometry().topLeft()
                    except Exception:
                        self._drag_position = QPoint()
                print(
                    f"[DBG floating_button] restore_mousePress gp={gp} drag_offset={self._drag_position}"
                )
                event.accept()

        def _restore_mouseMove(event: QMouseEvent):
            if event.buttons() & Qt.MouseButton.LeftButton:
                try:
                    gp = event.globalPosition().toPoint()
                except Exception:
                    gp = event.globalPos()
                new_pos = gp - self._drag_position
                self.move(new_pos)
                print(f"[DBG floating_button] restore_mouseMove moved_to={new_pos}")
                # persist position
                try:
                    self._persist_position()
                except Exception:
                    pass
                event.accept()
            else:
                if callable(orig_restore_move):
                    try:
                        orig_restore_move(event)
                    except Exception:
                        pass

        def _restore_mouseRelease(event: QMouseEvent):
            if callable(orig_restore_release):
                try:
                    orig_restore_release(event)
                except Exception:
                    pass

        self.restore_button.mousePressEvent = _restore_mousePress
        self.restore_button.mouseMoveEvent = _restore_mouseMove
        self.restore_button.mouseReleaseEvent = _restore_mouseRelease

        # Forward mouse press/move events from the inner button to the
        # floating widget so users can drag by the button itself.
        # Preserve original handlers if present.
        orig_press = getattr(self.button, "mousePressEvent", None)
        orig_move = getattr(self.button, "mouseMoveEvent", None)
        orig_release = getattr(self.button, "mouseReleaseEvent", None)

        def _button_mousePress(event: QMouseEvent):
            if callable(orig_press):
                try:
                    orig_press(event)
                except Exception:
                    pass
            if event.button() == Qt.MouseButton.LeftButton:
                try:
                    gp = event.globalPosition().toPoint()
                except Exception:
                    gp = event.globalPos()
                try:
                    self._drag_position = self._get_drag_offset(gp)
                except Exception:
                    try:
                        self._drag_position = gp - self.frameGeometry().topLeft()
                    except Exception:
                        self._drag_position = QPoint()
                print(
                    f"[DBG floating_button] button_mousePress gp={gp} drag_offset={self._drag_position}"
                )
                event.accept()

        def _button_mouseMove(event: QMouseEvent):
            if event.buttons() & Qt.MouseButton.LeftButton:
                try:
                    gp = event.globalPosition().toPoint()
                except Exception:
                    gp = event.globalPos()
                new_pos = gp - self._drag_position
                self.move(new_pos)
                print(f"[DBG floating_button] button_mouseMove moved_to={new_pos}")
                try:
                    self._persist_position()
                except Exception:
                    pass
                event.accept()
            else:
                if callable(orig_move):
                    try:
                        orig_move(event)
                    except Exception:
                        pass

        def _button_mouseRelease(event: QMouseEvent):
            if callable(orig_release):
                try:
                    orig_release(event)
                except Exception:
                    pass

        self.button.mousePressEvent = _button_mousePress
        self.button.mouseMoveEvent = _button_mouseMove
        self.button.mouseReleaseEvent = _button_mouseRelease

    def eventFilter(self, obj, event):
        """Forward mouse events from child widgets to the floating widget so
        dragging works when clicking any child control."""
        if event.type() in (
            QEvent.MouseButtonPress,
            QEvent.MouseButtonRelease,
            QEvent.MouseMove,
        ):
            print(f"[DBG floating_button] eventFilter: obj={obj} type={event.type()}")
            # Map press/move/release to widget handlers
            if event.type() == QEvent.MouseButtonPress:
                self.mousePressEvent(event)
            elif event.type() == QEvent.MouseMove:
                self.mouseMoveEvent(event)
            else:
                # MouseButtonRelease
                try:
                    # persist last position on release
                    self._persist_position()
                except Exception:
                    pass
                try:
                    # allow original handlers to run too
                    orig = getattr(obj, "mouseReleaseEvent", None)
                    if callable(orig):
                        orig(event)
                except Exception:
                    pass
            try:
                event.accept()
            except Exception:
                pass
            return True  # swallow event after forwarding to avoid child stealing events
        return super().eventFilter(obj, event)

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
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                gp = event.globalPosition().toPoint()
            except Exception:
                gp = event.globalPos()
            try:
                self._drag_position = gp - self.pos()
            except Exception:
                self._drag_position = gp - self.frameGeometry().topLeft()
            print(
                f"[DBG floating_button] mousePress gp={gp} drag_offset={self._drag_position}"
            )
            # Request compositor-managed move on Wayland so the window actually follows the pointer
            try:
                self._request_system_move()
            except Exception:
                pass
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            try:
                gp = event.globalPosition().toPoint()
            except Exception:
                gp = event.globalPos()
            new_pos = gp - self._drag_position
            self.move(new_pos)
            print(
                f"[DBG floating_button] mouseMove moved_to={new_pos} saved_pos-> {self.pos()}"
            )
            try:
                self._persist_position()
            except Exception:
                pass
            event.accept()

    def position_bottom_right(self):
        """Position button at bottom-right of primary screen with 20px margin."""
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - 90
        y = screen.height() - 90
        print(f"[DBG floating_button] position_bottom_right -> x={x} y={y}")
        self.move(x, y)

    def resizeEvent(self, event):
        """Keep the small restore button positioned at top-right when resized."""
        try:
            self.restore_button.move(self.width() - 24, 4)
        except Exception:
            pass
        super().resizeEvent(event)

    def showEvent(self, event):
        """Ensure restore button is correctly positioned when shown and restore saved position."""
        try:
            self.restore_button.move(self.width() - 24, 4)
            if getattr(self, "_saved_pos", None):
                print(
                    f"[DBG floating_button] showEvent restoring saved_pos={self._saved_pos}"
                )
                self.move(self._saved_pos)
            else:
                print(
                    "[DBG floating_button] showEvent no saved_pos, positioning bottom-right"
                )
                self.position_bottom_right()
        except Exception:
            pass
        super().showEvent(event)
