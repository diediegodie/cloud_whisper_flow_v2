import time
import numpy as np
import pytest

from src.core.recorder import AudioRecorder
from src.core.recorder import AudioRecorderError


def test_list_devices_returns_list():
    r = AudioRecorder()
    devices = r.list_devices()
    assert isinstance(devices, list)
    for d in devices:
        assert "id" in d and "name" in d


def test_start_stop_capture_or_skip():
    r = AudioRecorder()
    devices = r.list_devices()
    if not devices:
        pytest.skip("No input devices available in this environment")

    default = r.get_default_device()
    if default is not None:
        r.set_device(default)

    r.start()
    time.sleep(0.5)
    assert r.is_recording()
    data = r.stop()
    assert not r.is_recording()
    assert isinstance(data, np.ndarray)
    assert data.dtype == np.int16


"""Test audio recorder."""

import time
import numpy as np
from src.core.recorder import AudioRecorder


def test_list_devices():
    """Test device listing."""
    recorder = AudioRecorder()
    devices = recorder.list_devices()
    print(f"Found {len(devices)} input devices:")
    for d in devices:
        print(f"  [{d['id']}] {d['name']}")
    assert isinstance(devices, list)


def test_record_audio():
    """Test basic recording."""
    recorder = AudioRecorder()

    if not recorder.list_devices():
        print("No audio devices, skipping record test")
        return

    recorder.start()
    assert recorder.is_recording()

    time.sleep(0.5)  # Record 0.5 seconds

    audio = recorder.stop()
    assert not recorder.is_recording()
    assert isinstance(audio, np.ndarray)
    assert audio.dtype == np.int16
    print(f"Recorded {len(audio)} samples ({len(audio)/16000:.2f}s)")


def test_invalid_device_raises():
    recorder = AudioRecorder()
    devices = recorder.list_devices()
    if not devices:
        pytest.skip("No input devices available in this environment")

    # pick an obviously invalid device id
    recorder.set_device(9999)
    with pytest.raises(AudioRecorderError):
        recorder.start()


def test_overflow_tracking():
    recorder = AudioRecorder()
    # Use the callback directly to simulate an overflow
    recorder._overflow_count = 0
    recorder._recording = True
    indata = np.zeros((100, 1), dtype=np.int16)

    class Status:
        input_overflow = True

    recorder._audio_callback(indata, 100, None, Status())
    assert recorder._overflow_count >= 1


if __name__ == "__main__":
    test_list_devices()
    test_record_audio()
    print("All recorder tests passed!")
