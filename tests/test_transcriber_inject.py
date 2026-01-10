import json
import numpy as np
import pytest

from src.core import transcriber as transcriber_mod
from src.core.transcriber import Transcriber, TranscriberError


@pytest.fixture(autouse=True)
def mock_vosk_inject(monkeypatch):
    """Provide a lightweight fake recognizer for injected PCM tests."""

    def FakeModel(path):
        return object()

    class FakeRecognizer:
        def __init__(self, model, sample_rate):
            self._buf = bytearray()

        def AcceptWaveform(self, data: bytes) -> bool:
            self._buf.extend(data)
            return True

        def FinalResult(self) -> str:
            # Return text when any audio was fed
            text = "hello world" if len(self._buf) > 0 else ""
            return json.dumps({"text": text})

        def Result(self) -> str:
            return self.FinalResult()

    monkeypatch.setattr(transcriber_mod, "Model", FakeModel)
    monkeypatch.setattr(transcriber_mod, "KaldiRecognizer", FakeRecognizer)


def test_feed_pcm_transcribes_nonempty():
    t = Transcriber()
    t.load_model()
    # create 0.1s of non-silent audio at 16kHz: simple int16 ramp
    samples = (np.linspace(-0.1, 0.1, int(0.1 * t.sample_rate)) * 32767).astype(np.int16)
    pcm = samples.tobytes()
    text = t.feed_pcm(pcm)
    assert isinstance(text, str)
    assert text == "hello world"
