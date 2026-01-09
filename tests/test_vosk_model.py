"""Test Vosk model loading and availability.

Validates that:
1. Model directory exists at expected location
2. Vosk can load the model without error
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vosk import Model
from src.utils.paths import get_model_path


def test_model_exists():
    """Verify model directory exists at expected location."""
    model_path = get_model_path()
    assert model_path.exists(), f"Model not found at {model_path}"
    print(f"✓ Model directory exists: {model_path}")


def test_model_loads():
    """Verify Vosk can load the model successfully."""
    model_path = get_model_path()
    model = Model(str(model_path))
    assert model is not None, "Model failed to load"
    print(f"✓ Model loaded successfully from {model_path}")


if __name__ == "__main__":
    test_model_exists()
    test_model_loads()
    print("\n✓ All Vosk model tests passed!")
