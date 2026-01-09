import numpy as np

from src.core.recorder import AudioRecorder


class FakeInputStream:
    def __init__(self, samplerate, device, channels, dtype, callback):
        self.samplerate = samplerate
        self.device = device
        self.channels = channels
        self.dtype = dtype
        self.callback = callback

    def start(self):
        # Simulate a few callback invocations with int16 data
        for _ in range(3):
            frames = 160
            data = np.ones((frames, self.channels), dtype=np.int16) * 1234
            self.callback(data, frames, None, None)

    def stop(self):
        return None

    def close(self):
        return None


def test_mocked_recording(monkeypatch):
    import sounddevice as sd

    # Mock device list
    monkeypatch.setattr(
        sd,
        "query_devices",
        lambda: [
            {"name": "FakeIn", "max_input_channels": 1, "default_samplerate": 16000}
        ],
    )

    # Replace InputStream with our fake
    monkeypatch.setattr(sd, "InputStream", FakeInputStream)

    r = AudioRecorder()
    devices = r.list_devices()
    assert devices and devices[0]["name"] == "FakeIn"

    r.start()
    data = r.stop()

    assert isinstance(data, np.ndarray)
    assert data.dtype == np.int16
    assert data.size > 0
