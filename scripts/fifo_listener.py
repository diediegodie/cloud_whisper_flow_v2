#!/usr/bin/env python3
"""Simple CLI that listens on a named pipe and forwards incoming WAV/raw PCM
into a local RecordingWorker via process_pcm.

Usage examples:
  # create a FIFO and listen
  python scripts/fifo_listener.py --pipe /tmp/cloud_whisper.pipe

  # from another shell, write a WAV into the FIFO (ffmpeg example):
  ffmpeg -f dshow -i audio="Microphone" -ac 1 -ar 16000 -f wav - | \
    python -c "import sys,shutil; open('/tmp/cloud_whisper.pipe','wb').write(sys.stdin.buffer.read())"

Note: the helper instantiates a Transcriber and RecordingWorker locally; if the
main application is already running and exposing a FIFO consumer hook, prefer
using that integration instead.
"""
import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="FIFO listener that feeds a Transcriber")
    parser.add_argument(
        "--pipe",
        "-p",
        default="/tmp/cloud_whisper_pipe",
        help="Path to FIFO (named pipe) to listen on",
    )
    args = parser.parse_args()

    try:
        # Local imports to avoid importing heavy dependencies when not used
        from src.core.transcriber import Transcriber
        from src.core.workers import RecordingWorker
        from src.core.fifo_consumer import listen_and_forward
    except Exception as e:
        print(f"Failed to import application modules: {e}")
        return 2

    transcriber = Transcriber()
    worker = RecordingWorker(transcriber)

    try:
        listen_and_forward(args.pipe, worker)
    except KeyboardInterrupt:
        print("Interrupted by user")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
