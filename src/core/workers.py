"""Worker threads for background processing.

RecordingWorker implements background recording and transcription while
emitting Qt signals for UI consumption. It never updates UI directly.
"""

from typing import Optional

import numpy as np
from PySide6.QtCore import QThread, QMutex

from src.core.recorder import AudioRecorder, AudioRecorderError
from src.core.transcriber import Transcriber, TranscriberError
from src.utils.signals import signals


class RecordingWorker(QThread):
    """Worker thread for recording and transcription.

    The worker records audio using `AudioRecorder` until `stop_recording`
    is called, then transcribes using the provided `Transcriber`.
    All interactions with the UI should be done via `signals`.
    """

    def __init__(self, transcriber: Transcriber) -> None:
        super().__init__()
        self.transcriber = transcriber
        self.recorder = AudioRecorder()
        self._should_stop: bool = False
        self._mutex = QMutex()
        self._audio_data: Optional[np.ndarray] = None

    def run(self) -> None:
        """Record audio until stopped, then transcribe.

        Emits recording and transcription signals. Catches errors and emits
        `transcription_error` instead of raising.
        """
        try:
            signals.recording_started.emit()
            signals.status_update.emit("Recording...")

            self.recorder.start()

            # Poll until stop requested
            while True:
                self._mutex.lock()
                should_stop = self._should_stop
                self._mutex.unlock()
                if should_stop:
                    break
                # Qt-friendly sleep
                self.msleep(50)

            # Stop recording and collect audio
            audio = self.recorder.stop()
            self._audio_data = audio
            signals.recording_stopped.emit()

            if self._audio_data is None or len(self._audio_data) == 0:
                signals.transcription_error.emit("No audio recorded")
                return

            # Transcribe
            signals.transcription_started.emit()
            signals.status_update.emit("Processing...")

            text = self.transcriber.transcribe(self._audio_data)
            signals.transcription_complete.emit(text)
            signals.status_update.emit("Ready")

        except AudioRecorderError as e:
            signals.transcription_error.emit(f"Recording error: {e}")
        except TranscriberError as e:
            signals.transcription_error.emit(f"Transcription error: {e}")
        except Exception as e:
            signals.transcription_error.emit(f"Unexpected error: {e}")

    def stop_recording(self) -> None:
        """Signal the worker to stop recording (thread-safe).

        This method sets a flag protected by a QMutex which the running
        thread polls and reacts to.
        """
        self._mutex.lock()
        try:
            self._should_stop = True
        finally:
            self._mutex.unlock()

    def reset(self) -> None:
        """Reset worker state for reuse."""
        self._mutex.lock()
        try:
            self._should_stop = False
            self._audio_data = None
        finally:
            self._mutex.unlock()
