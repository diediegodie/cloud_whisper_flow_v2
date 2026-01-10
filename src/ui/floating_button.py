"""Floating record button for Background Mode."""

from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QMouseEvent


class FloatingRecordButton(QWidget):
    """Floating button shown when app is minimized.

    Signals:
        toggled(bool): emits True when recording starts
    """

    toggled = Signal(bool)
    # Emitted when user double-clicks the floating widget to restore main window
    show_requested = Signal()

    def __init__(self):
        super().__init__()
        self._drag_position = QPoint()
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
        self.restore_button.raise_()

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
                self._drag_position = gp - self.frameGeometry().topLeft()
                event.accept()

        def _button_mouseMove(event: QMouseEvent):
            if event.buttons() & Qt.MouseButton.LeftButton:
                try:
                    gp = event.globalPosition().toPoint()
                except Exception:
                    gp = event.globalPos()
                self.move(gp - self._drag_position)
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
            self._drag_position = gp - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def position_bottom_right(self):
        """Position button at bottom-right of primary screen with 20px margin."""
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - 90
        y = screen.height() - 90
        self.move(x, y)

    def resizeEvent(self, event):
        """Keep the small restore button positioned at top-right when resized."""
        try:
            self.restore_button.move(self.width() - 24, 4)
        except Exception:
            pass
        super().resizeEvent(event)

    def showEvent(self, event):
        """Ensure restore button is correctly positioned when shown."""
        try:
            self.restore_button.move(self.width() - 24, 4)
        except Exception:
            pass
        super().showEvent(event)
