"""Qt stylesheet definitions for dark theme used across the UI.

Keep colors, sizes and hover states centralized here so components
don't use inline style values.
"""

DARK_THEME = """
QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QLabel {
    color: #ffffff;
}

/* Title-specific tweaks (title label may override weight via code) */
QLabel#titleLabel {
    color: #ffffff;
    font-weight: bold;
}

QTextEdit {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    padding: 8px;
}

QTextEdit:focus {
    border: 1px solid #0078d4;
}

QPushButton {
    background-color: #3a3a3a;
    color: #ffffff;
    border: none;
    border-radius: 5px;
    padding: 6px 12px;
}

QPushButton:hover {
    background-color: #4a4a4a;
}

QPushButton:pressed {
    background-color: #2a2a2a;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    color: #666666;
}

/* Specific titlebar buttons */
QPushButton#minimizeButton {
    background: transparent;
    color: #ffffff;
    border: none;
    font-size: 14px;
}
QPushButton#minimizeButton:hover {
    background-color: #3a3a3a;
}

QPushButton#closeButton {
    background: transparent;
    color: #ffffff;
    border: none;
    font-size: 18px;
}
QPushButton#closeButton:hover {
    background-color: #dc3545;
}

QComboBox {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    padding: 5px 10px;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    color: #ffffff;
    selection-background-color: #0078d4;
}
"""


RECORD_BUTTON_IDLE = """
QPushButton {
    background-color: #dc3545;
    border-radius: 40px;
    border: none;
    color: #ffffff;
}
QPushButton:hover {
    background-color: #c82333;
}
"""


RECORD_BUTTON_RECORDING = """
QPushButton {
    background-color: #dc3545;
    border-radius: 40px;
    border: 3px solid #ffffff;
    color: #ffffff;
}
QPushButton:hover {
    background-color: #c82333;
}
"""


STATUS_READY = "color: #28a745;"
STATUS_RECORDING = "color: #dc3545;"
STATUS_PROCESSING = "color: #ffc107;"
STATUS_ERROR = "color: #dc3545;"
