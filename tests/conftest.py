import os
import sys
import types
import json
import importlib

# By default, avoid importing/loading the heavy Vosk model during unit tests.
# Set `VOSK_TEST_FULL=1` in the environment to run the real-model tests.
if not os.environ.get("VOSK_TEST_FULL"):
    fake_vosk = types.ModuleType("vosk")

    class FakeModel:
        def __init__(self, path: str):
            # pretend model exists; keep minimal state
            self.path = path

    class FakeKaldiRecognizer:
        def __init__(self, model, sample_rate: int):
            self._buf = bytearray()

        def AcceptWaveform(self, data: bytes) -> bool:
            self._buf.extend(data)
            return True

        def FinalResult(self) -> str:
            return json.dumps({"text": ""})

        def Result(self) -> str:
            return json.dumps({"text": ""})

    setattr(fake_vosk, "Model", FakeModel)
    setattr(fake_vosk, "KaldiRecognizer", FakeKaldiRecognizer)

    # Make `import vosk` return the fake module for the whole test session.
    sys.modules["vosk"] = fake_vosk

    # Also ensure the already-imported transcriber module (if imported later)
    # sees these fakes on its attributes. Importlib used to avoid circulars.
    try:
        trans_mod = importlib.import_module("src.core.transcriber")
    except Exception:
        trans_mod = None

    if trans_mod is not None:
        setattr(trans_mod, "Model", FakeModel)
        setattr(trans_mod, "KaldiRecognizer", FakeKaldiRecognizer)


def pytest_report_header(config):
    if os.environ.get("VOSK_TEST_FULL"):
        return "VOSK_TEST_FULL=1: running real Vosk model tests"
    return "VOSK_TEST_FULL not set: using fake Vosk module for fast tests"
