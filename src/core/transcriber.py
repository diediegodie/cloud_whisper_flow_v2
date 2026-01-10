from __future__ import annotations

import json
from typing import Optional, TYPE_CHECKING, Any

import numpy as np

from src.utils.paths import get_model_path

try:
    from vosk import Model, KaldiRecognizer
except Exception:  # Vosk may be missing in test environments
    Model = None  # type: ignore
    KaldiRecognizer = None  # type: ignore

if TYPE_CHECKING:
    from vosk import Model as VoskModel  # type: ignore
else:
    VoskModel = Any


class TranscriberError(Exception):
    """Raised when transcription operations fail."""


class Transcriber:
    """Wraps a Vosk Model for offline speech-to-text.

    Usage:
      t = Transcriber()
      t.load_model()
      text = t.transcribe(audio_array)
    """

    def __init__(
        self, model_path: Optional[str] = None, sample_rate: int = 16000
    ) -> None:
        self.sample_rate: int = int(sample_rate)
        self._model_path = str(model_path or get_model_path())
        self._model: Optional[VoskModel] = None

    def load_model(self) -> None:
        """Load the Vosk model from disk.

        Raises:
            TranscriberError: if the model cannot be loaded or vosk is not installed.
        """
        if Model is None:
            raise TranscriberError("Vosk is not installed in this environment")
        try:
            self._model = Model(self._model_path)
        except Exception as e:
            raise TranscriberError(
                f"Failed to load Vosk model from {self._model_path}: {e}"
            )

    def is_model_loaded(self) -> bool:
        """Return True if the model is loaded."""
        return self._model is not None

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe a numpy array of audio (1-D) to text.

        Args:
            audio: 1-D numpy array containing audio samples. Expected sample
                   rate is `self.sample_rate` and dtype int16, but floats are
                   accepted and converted.

        Returns:
            The transcribed text (possibly empty string).

        Raises:
            TranscriberError: if model not loaded or on processing errors.
        """
        if not self.is_model_loaded():
            raise TranscriberError("Model not loaded. Call load_model() first.")

        try:
            # Normalize and validate audio
            if audio is None:
                return ""

            arr = np.asarray(audio)

            if arr.size == 0:
                return ""

            # If float, scale to int16 range
            if np.issubdtype(arr.dtype, np.floating):
                arr = np.clip(arr, -1.0, 1.0)
                arr = (arr * 32767).astype(np.int16)
            elif arr.dtype != np.int16:
                arr = arr.astype(np.int16)

            # Ensure 1-D
            arr = arr.flatten()

            if KaldiRecognizer is None:
                raise TranscriberError(
                    "Vosk recognizer unavailable (vosk import failed)"
                )

            recognizer = KaldiRecognizer(self._model, self.sample_rate)
            # Process in chunks to avoid large-memory AcceptWaveform calls
            chunk_size = 4000
            for i in range(0, arr.size, chunk_size):
                chunk = arr[i : i + chunk_size]
                recognizer.AcceptWaveform(chunk.tobytes())

            # Final result contains JSON with 'text' field
            try:
                result_json = recognizer.FinalResult()
                data = json.loads(result_json)
                return data.get("text", "") or ""
            except Exception:
                # As a fallback, try Result() then FinalResult()
                try:
                    res = recognizer.Result()
                    parsed = json.loads(res)
                    return parsed.get("text", "") or ""
                except Exception as e:
                    raise TranscriberError(f"Failed to parse recognition result: {e}")

        except TranscriberError:
            raise
        except Exception as e:
            raise TranscriberError(f"Transcription failed: {e}")

    def feed_pcm(self, pcm_bytes: bytes) -> str:
        """Feed raw PCM int16 bytes (mono, sample_rate) and return transcription.

        This is a small injection API intended for testing and CI where a real
        microphone is unavailable. Expects raw little-endian int16 PCM bytes
        matching self.sample_rate and mono channels.
        """
        if not self.is_model_loaded():
            raise TranscriberError("Model not loaded. Call load_model() first.")
        if not pcm_bytes:
            return ""
        try:
            arr = np.frombuffer(pcm_bytes, dtype=np.int16)
            return self.transcribe(arr)
        except Exception as e:
            raise TranscriberError(f"feed_pcm failed: {e}")
