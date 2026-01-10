"""Thread-safe Qt signals for the application.

This module provides a single global `signals` instance that can be
imported throughout the application for inter-thread communication.
"""

from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    """Central signal hub for thread-safe communication.

    Only signal definitions here — no logic. A single global `signals`
    instance is exported for app-wide use.
    """

    # Recording signals
    recording_started = Signal()
    recording_stopped = Signal()
    # Signal used to toggle recording from other threads (e.g. global hotkey)
    toggle_recording = Signal()

    # Transcription signals
    transcription_started = Signal()
    transcription_complete = Signal(str)
    transcription_error = Signal(str)

    # Translation signals
    translation_started = Signal()
    translation_complete = Signal(str)
    translation_error = Signal(str)

    # Status signals
    status_update = Signal(str)

    # Audio signals
    audio_level = Signal(float)


# Single global instance for the application to import and use
signals = AppSignals()
