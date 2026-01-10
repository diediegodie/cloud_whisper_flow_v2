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
from src.core.translator import Translator, TranslatorError


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

    def process_pcm(self, pcm_bytes: bytes) -> None:
        """Process externally provided PCM bytes through the Transcriber.

        This allows piping audio into the running worker (e.g., from a FIFO or
        external tool) without using the microphone stack. Emits the same
        transcription signals as the regular recording flow.
        """
        try:
            if not pcm_bytes:
                signals.transcription_error.emit("No audio provided")
                return

            signals.transcription_started.emit()
            signals.status_update.emit("Processing...")

            # Prefer feed_pcm injection API if available
            if hasattr(self.transcriber, "feed_pcm"):
                text = self.transcriber.feed_pcm(pcm_bytes)
            else:
                # Fallback: convert bytes to numpy array and call transcribe
                arr = np.frombuffer(pcm_bytes, dtype=np.int16)
                text = self.transcriber.transcribe(arr)

            signals.transcription_complete.emit(text)
            signals.status_update.emit("Ready")
        except TranscriberError as e:
            signals.transcription_error.emit(f"Transcription error: {e}")
        except Exception as e:
            signals.transcription_error.emit(f"Unexpected error: {e}")


class TranslationWorker(QThread):
    """Worker thread to perform text translation in background.

    Emits translation-related signals via `signals`.
    """

    def __init__(
        self, translator: Translator, text: str, target_language: str = "English"
    ) -> None:
        super().__init__()
        self.translator = translator
        self.text = text
        self.target_language = target_language

    def run(self) -> None:
        try:
            signals.translation_started.emit()
            signals.status_update.emit("Translating...")

            try:
                result = self.translator.translate(self.text, self.target_language)
                signals.translation_complete.emit(result)
                signals.status_update.emit("Ready")
            except TranslatorError as e:
                signals.translation_error.emit(str(e))
            except Exception as e:
                signals.translation_error.emit(f"Unexpected error: {e}")

        except Exception as e:
            # Top-level guard: ensure any uncaught error is reported
            signals.translation_error.emit(f"Worker failure: {e}")
