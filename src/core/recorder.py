from typing import List, Optional, Dict, Any
import numpy as np

try:
    import sounddevice as sd
except Exception:  # sounddevice may not be available in headless/test env
    sd = None


class AudioRecorderError(Exception):
    """Raised when audio recording operations fail."""


class AudioRecorder:
    """Simple audio recorder wrapper for 16kHz int16 input suitable for Vosk.

    API:
      - list_devices() -> list[dict]
      - set_device(device_id: int)
      - get_default_device() -> Optional[int]
      - start() -> None
      - stop() -> numpy.ndarray | None
      - is_recording() -> bool

    Notes:
      - Uses `sounddevice.InputStream` with samplerate=16000, channels=1, dtype='int16'.
      - Keeps a simple list buffer of frames appended by callback.
      - Does not perform threading or advanced buffering responsibilities.
    """

    def __init__(
        self, sample_rate: int = 16000, block_size: int = 8000, channels: int = 1
    ) -> None:
        self._device_id: Optional[int] = None
        self._stream: Optional[Any] = None
        self._buffer: List[np.ndarray] = []
        self._samplerate = int(sample_rate)
        self.block_size = int(block_size)
        self.channels = int(channels)
        self._dtype = "int16"
        self._recording: bool = False
        self._audio_data: List[np.ndarray] = []
        self._overflow_count: int = 0

    def list_devices(self) -> List[Dict]:
        """Return list of available input devices (may be empty).

        Each entry: {id, name, channels, default_samplerate}
        """
        if sd is None:
            return []
        devices: Any = sd.query_devices()
        out: List[Dict[str, Any]] = []
        for idx, d in enumerate(devices):
            # d is usually a mapping, but guard if sounddevice returns different shapes
            if isinstance(d, dict):
                try:
                    channels = int(d.get("max_input_channels", 0))
                except Exception:
                    channels = 0
                name = d.get("name")
                try:
                    default_sr = float(d.get("default_samplerate", 0.0))
                except Exception:
                    default_sr = 0.0
            else:
                # fallback for unexpected device entry types
                try:
                    name = str(d)
                except Exception:
                    name = None
                channels = 0
                default_sr = 0.0
            out.append(
                {
                    "id": idx,
                    "name": name,
                    "channels": channels,
                    "default_samplerate": default_sr,
                }
            )
        return out

    def set_device(self, device_id: int) -> None:
        self._device_id = int(device_id)

    def get_default_device(self) -> Optional[int]:
        if sd is None:
            return None
        try:
            default = sd.default.device
            # default can be (in, out) tuple or single
            if isinstance(default, (list, tuple)):
                return int(default[0]) if default[0] is not None else None
            return int(default) if default is not None else None
        except Exception:
            return None

    @property
    def device_id(self) -> Optional[int]:
        return self._device_id

    @property
    def sample_rate(self) -> int:
        return self._samplerate

    def _audio_callback(self, indata, frames, time, status):
        # indata is shape (frames, channels); convert to 1-D int16
        if status:
            # Track input overflow events
            try:
                if getattr(status, "input_overflow", False):
                    self._overflow_count += 1
            except Exception:
                # ignore any unexpected status shape
                pass
        if indata is None:
            return
        arr = np.asarray(indata)
        if arr.dtype != np.int16:
            # sounddevice may provide float32; convert to int16 preserving scale
            # clip to [-1,1] if float
            if np.issubdtype(arr.dtype, np.floating):
                arr = np.clip(arr, -1.0, 1.0)
                arr = (arr * 32767).astype(np.int16)
            else:
                arr = arr.astype(np.int16)
        # flatten to 1-D and store
        try:
            if self._recording:
                self._audio_data.append(arr.copy())
        except Exception:
            # fallback: append flattened array
            if self._recording:
                self._audio_data.append(np.asarray(arr).flatten())

    def _validate_device(self, device_id: int) -> bool:
        """Check if device supports required sample rate and channels."""
        if sd is None:
            return False
        try:
            sd.check_input_settings(
                device=device_id, samplerate=self.sample_rate, channels=self.channels
            )
            return True
        except Exception as e:
            # If check_input_settings raised a PortAudioError, device isn't compatible
            try:
                if hasattr(sd, "PortAudioError") and isinstance(e, sd.PortAudioError):
                    return False
            except Exception:
                pass
            # In mocked or constrained test environments, fall back to checking query_devices
            try:
                devices = self.list_devices()
                return any(d.get("id") == device_id for d in devices)
            except Exception:
                return False

    def start(self) -> None:
        """Start recording audio."""
        if sd is None:
            raise AudioRecorderError("sounddevice not available")

        if self._recording:
            return

        # Prepare audio data buffer and reset overflow counter
        self._audio_data = []
        self._overflow_count = 0
        self._recording = True

        device = (
            self.device_id if self.device_id is not None else self.get_default_device()
        )

        if device is None:
            # try to pick the first available input device if query_devices is populated
            try:
                devices = self.list_devices()
                if devices:
                    device = devices[0]["id"]
                else:
                    raise AudioRecorderError("No audio input device found")
            except AudioRecorderError:
                raise
            except Exception:
                raise AudioRecorderError("No audio input device found")

        # Validate device compatibility
        if not self._validate_device(device):
            raise AudioRecorderError(
                f"Device {device} does not support {self.sample_rate}Hz sample rate"
            )

        try:
            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    device=device,
                    channels=self.channels,
                    dtype=self._dtype,
                    callback=self._audio_callback,
                    blocksize=self.block_size,
                )
            except TypeError:
                # Some mocked or older InputStream implementations may not accept blocksize
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    device=device,
                    channels=self.channels,
                    dtype=self._dtype,
                    callback=self._audio_callback,
                )
            self._stream.start()
        except Exception as e:
            # Wrap PortAudio/sounddevice errors
            raise AudioRecorderError(f"Failed to start recording: {e}")

    def stop(self) -> np.ndarray:
        """Stop recording and return audio data as 1-D numpy array of int16."""
        if not self._recording:
            return np.array([], dtype=np.int16)

        self._recording = False
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None

        if self._audio_data:
            combined = np.concatenate(self._audio_data, axis=0).flatten()
            return combined.astype(np.int16)
        return np.array([], dtype=np.int16)

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording

    def get_overflow_count(self) -> int:
        """Get number of buffer overflows detected during recording."""
        return int(self._overflow_count)
