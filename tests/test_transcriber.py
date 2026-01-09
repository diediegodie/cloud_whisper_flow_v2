import json
import os
from pathlib import Path

import numpy as np
import pytest

from src.core import transcriber as transcriber_mod
from src.core.transcriber import Transcriber, TranscriberError
from src.utils.paths import get_model_path


@pytest.fixture(autouse=True)
def mock_vosk(monkeypatch):
    """Always replace `Model` and `KaldiRecognizer` in the transcriber
    module with lightweight fakes so unit tests never load the real model.
    """

    def FakeModel(path):
        return object()

    class FakeRecognizer:
        def __init__(self, model, sample_rate):
            self._buf = bytearray()

        def AcceptWaveform(self, data: bytes) -> bool:
            # pretend to accept data
            self._buf.extend(data)
            return True

        def FinalResult(self) -> str:
            return json.dumps({"text": ""})

        def Result(self) -> str:
            return json.dumps({"text": ""})

    monkeypatch.setattr(transcriber_mod, "Model", FakeModel)
    monkeypatch.setattr(transcriber_mod, "KaldiRecognizer", FakeRecognizer)


@pytest.fixture
def transcriber_instance():
    """Return a Transcriber instance without model loaded."""
    return Transcriber()


@pytest.fixture
def transcriber_with_model():
    """Return a Transcriber instance with model loaded."""
    t = Transcriber()
    t.load_model()
    return t


def test_imports_and_instantiation(transcriber_instance) -> None:
    assert not transcriber_instance.is_model_loaded()


def test_transcribe_raises_when_model_not_loaded(transcriber_instance) -> None:
    with pytest.raises(TranscriberError):
        transcriber_instance.transcribe(np.array([], dtype=np.int16))


def test_model_loads_and_status(transcriber_instance) -> None:
    assert not transcriber_instance.is_model_loaded()
    transcriber_instance.load_model()
    assert transcriber_instance.is_model_loaded()


@pytest.mark.parametrize(
    "audio_data,expected_result",
    [
        (np.array([], dtype=np.int16), ""),  # empty array
        (np.zeros(16000, dtype=np.int16), str),  # silent int16 (1s @ 16kHz)
        (np.zeros(1600, dtype=np.float32), str),  # silent float32
    ],
    ids=["empty_int16", "silent_int16", "silent_float32"],
)
def test_transcribe_audio_handling(
    transcriber_with_model, audio_data, expected_result
) -> None:
    result = transcriber_with_model.transcribe(audio_data)
    if expected_result == str:
        assert isinstance(result, str)
    else:
        assert result == expected_result
