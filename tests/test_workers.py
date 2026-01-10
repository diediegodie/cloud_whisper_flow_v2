"""Test worker threads.

This test exercises the `RecordingWorker` lifecycle using a Qt
`QApplication` event loop and the global `signals` instance.
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from src.core.transcriber import Transcriber
from src.core.workers import RecordingWorker
from src.utils.signals import signals


def test_recording_worker():
    """Test RecordingWorker thread lifecycle."""
    app = QApplication.instance() or QApplication(sys.argv)

    # Load transcriber
    transcriber = Transcriber()
    transcriber.load_model()

    worker = RecordingWorker(transcriber)

    results = {"started": False, "stopped": False, "text": None, "error": None}

    def on_started():
        results["started"] = True
        print("Recording started signal received")

    def on_stopped():
        results["stopped"] = True
        print("Recording stopped signal received")

    def on_complete(text):
        results["text"] = text
        print(f"Transcription complete: '{text}'")
        app.quit()

    def on_error(error):
        results["error"] = error
        print(f"Error: {error}")
        app.quit()

    signals.recording_started.connect(on_started)
    signals.recording_stopped.connect(on_stopped)
    signals.transcription_complete.connect(on_complete)
    signals.transcription_error.connect(on_error)

    # Start worker
    worker.start()

    # Stop after 1 second
    QTimer.singleShot(1000, worker.stop_recording)

    # Timeout after 10 seconds
    QTimer.singleShot(10000, app.quit)

    app.exec()

    # Wait for thread to finish
    worker.wait()

    assert results["started"], "Recording should have started"
    assert results["stopped"], "Recording should have stopped"
    print("Worker test completed!")


if __name__ == "__main__":
    test_recording_worker()
