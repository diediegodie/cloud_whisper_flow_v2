"""Floating record button for Background Mode."""

from PySide6.QtWidgets import QPushButton, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QPoint, Signal
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
        self.restore_button.move(self.width() - 24, 4)
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

        # Install event filters so child widgets forward mouse events to the
        # floating widget, allowing dragging when clicking on the inner button
        # or restore button while preserving their normal click behavior.
        try:
            self.button.installEventFilter(self)
            self.restore_button.installEventFilter(self)
        except Exception:
            pass



    def eventFilter(self, watched, event):
        """Forward mouse events from child widgets to the floating widget so
        dragging works when clicking any child control, without preventing
        the child from receiving clicks (we return False so the child's
        normal behavior still runs).
        """
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QEvent
        try:
            if event.type() in (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonMove,
                QEvent.Type.MouseButtonRelease,
            ):
                if isinstance(event, QMouseEvent):
                    # Mouse press: initialize drag offset but do not accept the
                    # event so the child still receives clicks.
                    if event.type() == QEvent.Type.MouseButtonPress:
                        if event.button() == Qt.MouseButton.LeftButton:
                            try:
                                gp = event.globalPosition().toPoint()
                            except Exception:
                                gp = event.globalPos()
                            try:
                                self._drag_position = self._get_drag_offset(gp)
                            except Exception:
                                pass
                            try:
                                self._request_system_move()
                            except Exception:
                                pass
                    # Mouse move: update parent position when dragging
                    elif event.type() == QEvent.Type.MouseButtonMove:
                        if event.buttons() & Qt.MouseButton.LeftButton:
                            try:
                                gp = event.globalPosition().toPoint()
                            except Exception:
                                gp = event.globalPos()
                            new_pos = gp - self._drag_position
                            try:
                                self.move(new_pos)
                            except Exception:
                                pass
                    # Mouse release: persist position
                    else:
                        try:
                            self._persist_position()
                        except Exception:
                            pass
        except Exception:
            pass
        # Return False so that the child widget also processes the event
        return super().eventFilter(watched, event)

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
            # Use DraggableWidget helper for consistent offset calculation
            self._drag_position = self._get_drag_offset(gp)
            print(f"[DBG floating_button] mousePress gp={gp} drag_offset={self._drag_position}")
            # Request Wayland-managed move if supported
            self._request_system_move()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            try:
                gp = event.globalPosition().toPoint()
            except Exception:
                gp = event.globalPos()
            new_pos = gp - self._drag_position
            self.move(new_pos)
            print(f"[DBG floating_button] mouseMove moved_to={new_pos}")
            # Persist position via DraggableWidget helper
            try:
                self._persist_position()
            except Exception:
                pass
            event.accept()

    def eventFilter(self, obj, event):
        """Forward mouse events from child widgets to the floating widget handlers.

        This allows dragging the floating button even when the user clicks on the
        visible child QPushButton(s).
        """
        try:
            from PySide6.QtCore import QEvent
            from PySide6.QtGui import QMouseEvent
        except Exception:
            return super().eventFilter(obj, event)

        if isinstance(event, QMouseEvent):
            # Forward press/move/release to the widget so dragging works when
            # interacting with child controls. Return False so the child also
            # receives the event (keeps button toggle behavior intact).
            try:
                if event.type() in (
                    QEvent.Type.MouseButtonPress,
                    QEvent.Type.MouseButtonRelease,
                ):
                    try:
                        self.mousePressEvent(event)
                    except Exception:
                        pass
                elif event.type() == QEvent.Type.MouseMove:
                    try:
                        self.mouseMoveEvent(event)
                    except Exception:
                        pass
            except Exception:
                pass
            return False

        return super().eventFilter(obj, event)

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
            saved_pos = getattr(self, "_saved_pos", None)
            if saved_pos is not None:
                print(
                    f"[DBG floating_button] showEvent restoring saved_pos={saved_pos}"
                )
                try:
                    self._restore_position()
                except Exception:
                    pass
            else:
                print(
                    "[DBG floating_button] showEvent no saved_pos, positioning bottom-right"
                )
                self.position_bottom_right()
        except Exception:
            pass
        super().showEvent(event)
