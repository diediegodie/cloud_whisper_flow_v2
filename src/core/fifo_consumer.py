"""FIFO consumer helper to forward WAV/raw PCM bytes into a RecordingWorker.

This module provides a simple blocking loop that listens on a named pipe (FIFO)
and forwards complete payloads to the provided worker via worker.process_pcm(pcm_bytes).

The implementation expects either raw 16-bit little-endian mono PCM bytes, or a
complete WAV file (RIFF header). It performs minimal validation and raises an
error if the WAV format isn't 16-bit mono.
"""
from typing import Any
import io
import os
import wave


def _extract_pcm_from_buf(buf: bytes) -> bytes:
    """Extract raw PCM bytes from a buffer that may contain a WAV file or raw PCM.

    If `buf` starts with a RIFF header, parse it and extract frames. Otherwise
    treat `buf` as raw 16-bit PCM little-endian samples.
    """
    if not buf:
        return b""

    # WAV file
    if buf[:4] == b"RIFF":
        with wave.open(io.BytesIO(buf), "rb") as wf:
            sampwidth = wf.getsampwidth()
            channels = wf.getnchannels()
            frames = wf.readframes(wf.getnframes())
            if sampwidth != 2 or channels != 1:
                raise RuntimeError(
                    f"Unsupported WAV format: sampwidth={sampwidth}, channels={channels}; expected 16-bit mono"
                )
            return frames

    # Raw PCM (assume int16 little-endian mono)
    return buf


def listen_and_forward(pipe_path: str, worker: Any) -> None:
    """Create the FIFO if needed and forward any written payloads to worker.process_pcm.

    This function blocks and loops forever, handling one writer at a time. For
    each writer it reads until EOF (i.e., the writer closed the pipe), then
    forwards the captured bytes to the worker.
    """
    if not os.path.exists(pipe_path):
        # Create FIFO with user-only permissions
        os.mkfifo(pipe_path, 0o600)

    print(f"Listening on FIFO: {pipe_path}")

    while True:
        try:
            with open(pipe_path, "rb") as f:
                buf = f.read()  # blocks until writer closes
                if not buf:
                    # Writer closed without data; ignore
                    continue

                try:
                    pcm = _extract_pcm_from_buf(buf)
                except Exception as e:
                    print(f"Failed to parse incoming payload: {e}")
                    continue

                try:
                    worker.process_pcm(pcm)
                except Exception as e:
                    print(f"Worker failed to process PCM: {e}")
        except KeyboardInterrupt:
            print("FIFO listener interrupted, exiting")
            return
        except Exception as e:
            print(f"FIFO listener error: {e}")
            # Small sleep to avoid hot loop on persistent failures
            import time

            time.sleep(1)
