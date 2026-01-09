"""Manual end-to-end test: record audio and transcribe.

This test is marked 'manual' by default and will be skipped in automated runs.
Run it locally when you have a microphone and Vosk model installed.
"""

import pytest
import numpy as np

from src.core.recorder import AudioRecorder, AudioRecorderError
from src.core.transcriber import Transcriber


@pytest.mark.skip(reason="Manual e2e test: requires microphone and Vosk model")
def test_e2e_record_and_transcribe() -> None:
    rec = AudioRecorder()
    try:
        rec.start()
    except AudioRecorderError:
        pytest.skip("No audio input device available")

    # record ~2 seconds
    import time

    time.sleep(2.0)
    audio = rec.stop()

    t = Transcriber()
    t.load_model()
    text = t.transcribe(audio)
    print("Transcribed:", text)
    assert isinstance(text, str)
