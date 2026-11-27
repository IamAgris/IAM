# IAM — Voice & Hearing System Specification

**Document:** 30 (Voice & Hearing System; companion to Documents 04 and 12)  
**Version:** 1.0 · 27 November 2026  
**Status:** FROZEN — capability scope only; **not** an implementation claim  
**Parent:** `ARCHITECTURE_INDEX.md`, `IAM_FINAL_CONSOLIDATION.md`  
**Related:** `IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md` (Doc 12 / OD-28), `IAM_MEDIA_AND_RESEARCH.md`, `IAM_API_CONTRACTS.md`, `canonical/IAM_DOC_04_UI_GLOBAL_ACCESS.md`, `IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md` (OD-46)  
**Confirmed decision:** OD-50 (Voice & Hearing System capability scope — **CONFIRMED** 27 November 2026). Extends the existing voice/media scope without changing the system count or any earlier decision.

> **Source note.** This document captures the submitted Voice & Hearing System specification. Substantive text is preserved. Inline tracking/favicon image links and HTML non-breaking-space artefacts from the source draft were removed. Section numbering follows the source draft (there is no section 7).

---

## 0. Purpose

For IAM, the objective is a complete **Human-Like Voice and Listening System**, not simply adding a text-to-speech library.

The goal is for IAM to:

- Listen to you through a microphone.
- Understand normal human speech, including different accents.
- Respond using a natural, realistic human-sounding voice.
- Speak with emotion, expression and appropriate pauses.
- Recognise when you interrupt it and stop speaking.
- Have natural conversations without requiring you to press a button for every sentence.
- Remember the context of the conversation.
- Switch between listening, thinking and speaking naturally.

Since IAM is designed to run primarily on your own infrastructure with Qwen2.5-3B as its primary LLM, the recommendation is a **local-first voice architecture**.

---

## 1. Recommended dependencies

These are the technologies considered for IAM.

### A. Listening — Speech-to-Text (STT)

**1. Whisper / faster-whisper — recommended**

- Converts your voice into text.
- Supports multiple languages and accents.
- Handles normal conversational speech.
- Can run locally using CPU or GPU.

Package: `faster-whisper` — <https://github.com/SYSTRAN/faster-whisper>

**2. Silero VAD**

Detects when somebody starts and stops speaking.

- Avoids processing silence.
- Helps identify natural speaking pauses.
- Supports continuous listening.

Package: `silero-vad` — <https://github.com/snakers4/silero-vad>

**3. openWakeWord**

Allows IAM to respond to a wake phrase, such as:

- "Hey IAM"
- "Hello IAM"
- "IAM, listen"

Package: `openwakeword` — <https://github.com/dscripka/openWakeWord>

### B. Speaking — Text-to-Speech (TTS)

This is particularly important because you don't want IAM to sound like a traditional computer assistant.

**1. Kokoro-82M — recommended starting engine**

- Natural-sounding neural voices.
- Relatively small model.
- Multiple voice choices.
- Local inference.
- Suitable for everyday conversations.

<https://github.com/hexgrad/kokoro>

**2. F5-TTS**

- Creates a personalised voice from reference recordings.
- Can produce more individual-sounding voices.
- Useful for developing IAM's distinctive voice.

<https://github.com/SWivid/F5-TTS>

**3. Qwen3-TTS**

- Voice design and custom voices.
- Multiple languages.
- More advanced voice-personality possibilities.
- Worth evaluating for expressive speech.

<https://github.com/QwenLM/Qwen3-TTS>

**Recommendation:** Start with Kokoro for fast everyday speech, then evaluate F5-TTS and Qwen3-TTS for IAM's permanent voice. These are separate engines; expose them through one TTS interface and switch between them.

Kokoro's voice catalog and F5-TTS's reference-voice approach provide different ways to develop IAM's sound.

### C. Audio capture and processing

| Dependency | Purpose |
|------------|---------|
| `sounddevice` | Microphone input and audio playback in Python |
| `PyAudio` | Audio recording and streaming |
| `FFmpeg` | Audio conversion, resampling and encoding |
| `WebRTC` | Real-time audio transport between browser and IAM |
| `WebSockets` | Continuous two-way audio communication |
| `soundfile` | Reading and writing audio files |
| `numpy` | Audio signal processing |

For the browser, use its native microphone APIs (`getUserMedia`) and WebRTC rather than requiring users to install microphone software.

---

## 2. What will actually make IAM sound human?

The TTS engine alone isn't enough. IAM needs a speech-personality layer.

| Capability | What it does |
|------------|--------------|
| Emotional prosody | Changes vocal expression according to context |
| Natural pauses | Pauses at appropriate moments |
| Dynamic pitch | Avoids a monotonous voice |
| Speaking speed | Speeds up or slows down naturally |
| Conversational fillers | Uses occasional natural expressions such as "Well..." |
| Sentence variation | Avoids sounding like it is reading a script |
| Contextual emphasis | Emphasises important words |
| Breathing simulation | Adds subtle, optional breathing characteristics |
| Interrupt handling | Stops speaking when you start talking |
| Conversational turn-taking | Knows when to listen and when to respond |

One particularly important capability is **interruption handling**.

Example:

1. You ask IAM a question.
2. IAM starts answering.
3. You interrupt and say, "Wait, that's not what I meant."
4. IAM immediately stops speaking.
5. IAM listens to your correction.
6. IAM adjusts its response.

This makes the interaction feel much more like a conversation.

---

## 3. Recommended IAM architecture

**IAM Human Voice System**

- **Microphone / Browser Audio** — continuous audio input
- **Listening Engine** — openWakeWord + Silero VAD + faster-whisper
- **IAM Primary Intelligence — Qwen2.5-3B** — understands, reasons and generates responses
- **Speech Personality Engine** — emotion, tone, pauses, emphasis and conversational delivery
- **Voice Generation** — Qwen3-TTS / Kokoro / F5-TTS
- **Natural Human-Like Voice Output** — streaming audio to the user

---

## 4. Which TTS should be IAM's main voice?

| Model | Best use |
|-------|----------|
| Kokoro-82M | Lightweight, fast everyday speech |
| Qwen3-TTS 0.6B | Smaller custom voice model |
| Qwen3-TTS 1.7B | Expressive voice design and voice cloning |
| F5-TTS | Reference-based voice generation |

**Preferred choice:** **Qwen3-TTS 1.7B for IAM's signature voice**, with Kokoro as a lightweight alternative.

Qwen3-TTS supports voice design through natural-language instructions, custom speaking styles and voice cloning. Its official repository also provides the `qwen-tts` Python package.

---

## 5. Additional features

- **Persistent voice identity:** IAM always sounds like IAM, rather than randomly changing voices.
- **Voice personality configuration:** Its own speaking characteristics, accent, pitch and conversational style.
- **Multilingual speech:** Understand and respond in different languages.
- **Accent adaptation:** Investigate South African English pronunciation as part of its voice development.
- **Voice activity awareness:** Detect when you are speaking, even while IAM is responding.
- **Voice memory:** Remember conversation context, not necessarily retain recordings.
- **Private audio processing:** Keep microphone recordings and voice data locally unless explicitly authorised otherwise.
- **Voice engine failover:** Switch to another installed TTS engine if the primary one becomes unavailable.

An important distinction: do not make IAM artificially insert "um", "uh" and breathing sounds into every sentence. Natural delivery comes from appropriate prosody and conversational timing, not simply adding noises.

---

## 6. Final dependency recommendation

| Component | Dependency |
|-----------|------------|
| Speech recognition | faster-whisper |
| Voice activity detection | Silero VAD |
| Wake-word detection | openWakeWord |
| Primary TTS | Qwen3-TTS |
| Lightweight TTS fallback | Kokoro |
| Alternative voice generation | F5-TTS |
| Microphone handling | sounddevice |
| Audio conversion | FFmpeg |
| Audio transport | WebRTC |
| Real-time communication | WebSockets |
| Audio processing | NumPy + SoundFile |

**Architectural recommendation:** Keep IAM's voice system independent of its primary intelligence. Qwen2.5-3B remains IAM's brain; speech recognition and speech synthesis become specialised services that communicate with it.

This also means IAM can eventually improve its voice, change speech models and develop a more distinctive personality without having to replace its primary LLM.

---

## 8. Advanced hearing and audio understanding

IAM should be capable of understanding more than spoken words.

| Capability | Technology to investigate |
|------------|---------------------------|
| Environmental sound recognition | YAMNet |
| General audio classification | PANNs |
| Advanced audio understanding | BEATs |
| Speech emotion recognition | emotion2vec |
| Vocal expression analysis | SpeechBrain |
| Word-level speech alignment | WhisperX |
| Multilingual speech recognition | FunASR |
| Audio question answering | Qwen2-Audio |

This would allow IAM to distinguish things such as music, applause, alarms, laughter, crying, background noise and speech.

---

## 9. Advanced voice-personality development

IAM should also have:

- A consistent individual voice identity.
- Customisable voice characteristics.
- Natural conversational rhythm.
- Different speaking styles depending on context.
- Appropriate emotional expression.
- Whispering and softer speaking styles where supported.
- Excitement, curiosity and enthusiasm.
- Serious and professional delivery.
- Different language pronunciation.
- Voice adaptation without losing its identity.

---

## 10. Advanced voice system capabilities

Long-term development:

- Multiple microphone support.
- Headset and Bluetooth audio support.
- Phone-call audio integration.
- Audio-file analysis.
- Live audio streaming.
- Voice-controlled computer operations.
- Voice-controlled browser operations.
- Spoken notifications.
- Speech transcription and searchable transcripts.
- Optional speaker profiles.
- Accessibility support.
- Local offline operation.
- Audio recording controls.
- Voice activity and system diagnostics.

---

## 11. Security, privacy and training

- Microphone permission management.
- Explicit recording indicators.
- Encrypted audio storage.
- Configurable recording retention.
- Consent-based voice cloning.
- Voice impersonation safeguards.
- Replay and synthetic voice attack detection.
- Speaker verification safeguards.
- Model integrity checks.
- Voice quality evaluation.
- Accent and language testing.
- Audio dataset management.
- Voice model fine-tuning and versioning.

---

## 12. Final IAM voice architecture checklist

Complete capability structure — development specification.

**IAM Voice System — Master checklist: 0/60 capabilities reviewed**

### 1. Listening and recognition (0 of 9 reviewed)

- Speech-to-text
- Streaming speech recognition
- Wake-word detection
- Voice activity detection
- Speaker diarization
- Speaker identification
- Multilingual recognition
- Accent recognition
- Word timestamps and alignment

### 2. Audio understanding (0 of 8 reviewed)

- Environmental sound recognition
- Emotion recognition
- Vocal tone analysis
- Laughter and crying detection
- Music and sound classification
- Audio question answering
- Background noise detection
- Speech and non-speech separation

### 3. Voice generation (0 of 9 reviewed)

- Natural text-to-speech
- Voice design
- Consistent voice identity
- Voice cloning with consent
- Multilingual speech
- Expressive prosody
- Pitch and speed control
- Streaming speech generation
- Alternative voice engines

### 4. Conversation intelligence (0 of 8 reviewed)

- Natural turn-taking
- Full-duplex interaction
- Interruption handling
- Conversational context
- Speech personality
- Contextual emotional expression
- Spoken commands
- Speech translation

### 5. Audio infrastructure (0 of 10 reviewed)

- Microphone integration
- Browser audio
- WebRTC
- WebSockets
- Audio buffering
- Noise suppression
- Echo cancellation
- Audio conversion
- GPU and CPU inference
- Offline operation

### 6. Security and governance (0 of 8 reviewed)

- Microphone permissions
- Recording indicators
- Audio encryption
- Retention controls
- Voice cloning consent
- Synthetic voice safeguards
- Model evaluation
- Versioning and rollback

### 7. Development and quality (0 of 8 reviewed)

- Voice quality benchmarks
- Accent testing
- Language testing
- Latency monitoring
- Audio diagnostics
- Dataset management
- Model fine-tuning
- Automatic failover

*Reset checklist:* all counts return to zero.

---

## 13. Six final advanced areas

These extend what IAM can do with audio; they are not simply more STT or TTS dependencies.

### 1. Advanced hearing capabilities

- Multi-speaker conversations.
- Overlapping speech recognition.
- Direction-of-sound estimation with supported microphone hardware.
- Distance and proximity estimation where hardware permits.
- Acoustic scene understanding.
- Detection of unusual sounds.
- Identification of familiar environmental sounds.
- Real-time audio event monitoring.

### 2. Advanced conversational behaviour

- Recognise when someone is addressing IAM.
- Distinguish a question from a statement.
- Recognise when someone hasn't finished speaking.
- Understand conversational silence.
- Detect uncertainty in spoken communication.
- Ask for clarification naturally.
- Remember previous conversational context.
- Change its response style according to the conversation.

### 3. Personal voice identity

- A permanent signature voice.
- Consistent pronunciation of names.
- Custom vocabulary and pronunciation dictionary.
- Personalised accent and speaking style.
- Voice identity consistency across different TTS engines.
- Optional voice profiles for different interaction environments.

### 4. Advanced audio interaction

- Speech-to-speech translation.
- Real-time multilingual conversations.
- Audio summarisation.
- Audio transcription.
- Audio search.
- Voice-operated applications.
- Voice-operated browser.
- Voice-controlled accessibility features.
- Spoken notifications and alerts.

### 5. Self-improving voice intelligence

Relevant to IAM's autonomous development architecture. IAM should be able to:

- Identify weaknesses in its speech recognition.
- Evaluate different voice models.
- Benchmark naturalness and latency.
- Test pronunciation accuracy.
- Develop permitted training datasets.
- Fine-tune compatible models.
- Evaluate candidate voice models.
- Maintain model versions.
- Roll back unsuccessful upgrades.
- Improve its speech personality without changing its core identity.

It must not silently replace its production models or train on private recordings without authorisation.

### 6. Hardware and external device integration

- Desktop microphones.
- USB microphones.
- Bluetooth headsets.
- Headphones.
- Mobile-device microphones.
- Multi-microphone arrays.
- External speakers.
- Audio interfaces.
- Optional dedicated wake-word hardware.

---

## 14. Final verdict

Specification scope covered. The IAM voice system is sufficiently comprehensive to move into implementation planning.

Its complete architecture consists of:

1. Listening Intelligence.
2. Speech Recognition.
3. Audio Understanding.
4. Speaker Intelligence.
5. Voice Personality.
6. Speech Generation.
7. Conversational Intelligence.
8. Real-Time Audio Engine.
9. Audio Infrastructure.
10. Voice Security and Privacy.
11. Voice Learning and Improvement.
12. Hardware and Device Integration.

One distinction: this is a comprehensive capability specification, not a claim that every possible audio capability or dependency has been identified or implemented.

**Freeze decision (OD-50):** Stop adding features and treat this document as IAM's frozen Voice & Hearing System specification.
