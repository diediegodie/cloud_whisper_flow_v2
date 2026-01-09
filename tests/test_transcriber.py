import os

import numpy as np
import pytest

from src.utils.paths import get_model_path

from src.core.transcriber import Transcriber, TranscriberError


def test_imports_and_instantiation() -> None:
    t = Transcriber()
    assert not t.is_model_loaded()


def test_transcribe_without_model_raises() -> None:
    t = Transcriber()
    with pytest.raises(TranscriberError):
        t.transcribe(np.array([0], dtype=np.int16))


@pytest.mark.skipif(not get_model_path().exists(), reason="Vosk model not available")
def test_model_loading_and_empty_audio(tmp_path) -> None:
    t = Transcriber()
    t.load_model()
    assert t.is_model_loaded()

    # empty audio returns empty string
    out = t.transcribe(np.array([], dtype=np.int16))
    assert isinstance(out, str)
    assert out == ""


@pytest.mark.skipif(not get_model_path().exists(), reason="Vosk model not available")
def test_silent_and_float_audio_handling() -> None:
    t = Transcriber()
    t.load_model()

    # silent int16 audio
    silent = np.zeros(16000, dtype=np.int16)
    res = t.transcribe(silent)
    assert isinstance(res, str)

    # float audio (silence) should be converted and processed
    silent_f = np.zeros(16000, dtype=np.float32)
    res2 = t.transcribe(silent_f)
    assert isinstance(res2, str)
