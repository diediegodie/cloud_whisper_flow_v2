"""Tests for drag_utils module."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_draggable_widget_import():
    """Test that DraggableWidget can be imported successfully."""
    from src.ui.drag_utils import DraggableWidget
    
    assert DraggableWidget is not None
    print("✓ DraggableWidget imports successfully")


def test_draggable_widget_attributes():
    """Test that DraggableWidget has required attributes and methods."""
    from PySide6.QtWidgets import QApplication
    from src.ui.drag_utils import DraggableWidget
    
    # Need QApplication for QWidget
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    widget = DraggableWidget()
    
    # Check attributes
    assert hasattr(widget, '_drag_position')
    assert hasattr(widget, '_saved_pos')
    
    # Check methods
    assert hasattr(widget, '_get_drag_offset')
    assert hasattr(widget, '_request_system_move')
    assert hasattr(widget, '_persist_position')
    assert hasattr(widget, '_restore_position')
    
    print("✓ DraggableWidget has all required attributes and methods")


if __name__ == "__main__":
    test_draggable_widget_import()
    test_draggable_widget_attributes()
    print("\nAll tests passed!")
