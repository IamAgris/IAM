# Media and Research Services

## Autonomy reasoning

`app/workers/autonomy_worker.py` reasons through the LiteLLM gateway with a strict
action allowlist (`observe`, `respond`, `research`, `plan`, `ask_authorization`).
If the gateway is unavailable it records `model_used=False` and takes no action —
it never fabricates reasoning. The earlier "placeholder" comment was stale; the
implementation was already real.

## Text-to-speech

- ElevenLabs remains supported when configured.
- `VOICE_TTS_URL` enables a generic HTTP TTS endpoint; `VOICE_TTS_API_KEY` is read
  from the environment and sent as a bearer token.
- With no provider configured, the service returns an explicit "No TTS provider
  configured" result rather than empty audio presented as success.

## Voice activity detection

Energy-based VAD on 16-bit little-endian PCM:

- 20 ms frames, configurable `VOICE_VAD_SAMPLE_RATE` and `VOICE_VAD_THRESHOLD`.
- Returns `has_voice`, `confidence`, `frames_analyzed` and `method=pcm_energy`.
- Compressed audio must be decoded by the caller; the service does not pretend to
  understand codecs.

## Video analysis

`VisionService.sample_video_frames()` extracts JPEG frames using `ffmpeg`
(`VISION_FFMPEG_PATH`) and returns base64 frames with timestamps. `analyze_video()`
sends those frames to the multimodal model via LiteLLM. If ffmpeg is unavailable,
it returns an explicit error instead of a fabricated description. Media is never
permanently stored by this path.

## Multi-source research verification

`ResearchService.verify_knowledge_against_sources()` now:

1. Loads the knowledge item by ID.
2. Searches for supporting sources through `search_service` (Wikipedia fallback).
3. Compares claim token overlap and source credibility.
4. Marks the item `verified` with at least two credible supporting sources,
   `disputed` when contradictory language appears, otherwise `unverified`.
5. Returns the source lists, overlap scores and provider for audit.

## Verification

- 104 unit tests pass (silence/tone VAD, TTS fallback, missing ffmpeg handling).
- Postgres integration check verifies multi-source classification with mocked search.

## Remaining

None of these four services remain placeholders. ffmpeg and a TTS endpoint are
deployment configuration, not code gaps.
