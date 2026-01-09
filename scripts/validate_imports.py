"""Validation script for runtime dependencies (run only after installing runtime requirements)."""


def validate() -> None:
    try:
        import PySide6  # type: ignore
        import vosk  # type: ignore
        import sounddevice  # type: ignore
        import numpy  # type: ignore
        import translators  # type: ignore
        import keyboard  # type: ignore

        print("All runtime libraries imported successfully!")
    except Exception as e:
        print("Import validation failed:", type(e).__name__, e)


if __name__ == "__main__":
    validate()
