#!/usr/bin/env python3
"""Simple CLI to replay a 16kHz mono WAV into Transcriber.feed_pcm for manual testing.

Usage: python scripts/replay_wav.py path/to/file.wav

The WAV must be PCM 16-bit mono at 16000 Hz. If not, resample/convert with ffmpeg:
  ffmpeg -i input.wav -ac 1 -ar 16000 -f wav output_16k_mono.wav

For WSL mic forwarding see docs/WSL_MIC_FORWARDING.md
"""
import argparse
import sys
import wave
from src.core.transcriber import Transcriber, TranscriberError


def main():
    p = argparse.ArgumentParser()
    p.add_argument("wavfile", help="Path to 16kHz mono 16-bit WAV file")
    args = p.parse_args()

    try:
        wf = wave.open(args.wavfile, "rb")
    except Exception as e:
        print(f"Failed to open WAV: {e}")
        sys.exit(2)

    if wf.getnchannels() != 1:
        print("WAV must be mono (1 channel)")
        sys.exit(2)
    if wf.getsampwidth() != 2:
        print("WAV must be 16-bit PCM (sampwidth=2)")
        sys.exit(2)
    if wf.getframerate() != 16000:
        print("WAV must be 16000 Hz; resample with ffmpeg if needed")
        sys.exit(2)

    data = wf.readframes(wf.getnframes())
    wf.close()

    t = Transcriber()
    try:
        t.load_model()
    except TranscriberError as e:
        print(f"Unable to load model: {e}")
        print("If running locally for debugging, ensure Vosk model installed or use mocked tests.")
        sys.exit(2)

    print("Feeding WAV to Transcriber...")
    try:
        text = t.feed_pcm(data)
        print("Transcribed:", text)
    except TranscriberError as e:
        print(f"Transcription failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
