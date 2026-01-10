WSL microphone forwarding and FFmpeg notes

Secondary path: forwarding Windows microphone into WSL for manual end-to-end debugging.

FFmpeg TCP streaming example (run on Windows):

  ffmpeg -f dshow -i audio="Microphone" -ac 1 -ar 16000 -f wav tcp://0.0.0.0:9999

Consume in WSL (replace WINDOWS_HOST with your Windows IP):

  ffmpeg -i tcp://WINDOWS_HOST:9999 -f wav - | python scripts/replay_wav.py -

Alternative approaches:

- Use VB-Cable (virtual audio cable) on Windows and expose input via PulseAudio/WSLg.
- Use ffmpeg to save to a local WAV and then replay into the app with scripts/replay_wav.py.

Prefer the injected PCM approach (Transcriber.feed_pcm) for CI and deterministic tests; use the FFmpeg path for manual troubleshooting only.
