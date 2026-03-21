# Hifdh Review App - Architecture Document (v2)

## Overview

A web-based application for Quran memorization (hifdh) review. The app tests students by playing a random ayah from their memorized range, then listening to their recitation and providing real-time feedback on mistakes.

### Problem Statement

Existing Quran apps (like Tarteel) offer memorization assistance and mistake detection, but lack the "random recall test" feature that teachers use:

> "Here's a random ayah from Juz 25-30 — continue reciting from there."

This tests true memorization recall from arbitrary starting points, not just following along.

### Goals

- **Primary**: Real-time mistake detection during recitation with ~1-2 second feedback delay
- **Secondary**: Simple, distraction-free interface optimized for hifdh review sessions
- **Tertiary**: Track progress and common mistakes over time (Phase 2)

### Core Challenge

The hardest problem is **not transcription** — it's reliably determining **where the student is in the expected continuation** while handling:
- Hesitations and pauses
- Self-corrections
- Repetitions
- Chunk boundary artifacts
- Jumps forward/backward

This requires a **Continuation Alignment Engine**, not just text comparison.

---

## User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. SELECT RANGE                                                │
│     User chooses: "Test me on Juz 25-30"                        │
│     Optional: specific surahs, # of ayahs to recite             │
│                              │                                  │
│                              ▼                                  │
│  2. RECEIVE PROMPT                                              │
│     App picks random ayah from range                            │
│     App PLAYS audio of that ayah (user listens)                 │
│     App shows text of prompt ayah                               │
│                              │                                  │
│                              ▼                                  │
│  3. RECITE                                                      │
│     User clicks "Start" → mic begins recording                  │
│     User recites the NEXT N ayahs from memory                   │
│     App transcribes in rolling windows                          │
│     App aligns against expected continuation                    │
│     App shows real-time feedback (confirmed words only)         │
│                              │                                  │
│                              ▼                                  │
│  4. REVIEW                                                      │
│     Session summary: X/Y ayahs correct                          │
│     Mistakes highlighted with corrections                       │
│     Option: Retry / Next Test / End Session                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND                               │
│                        (Lite React)                             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Audio     │  │  Recording  │  │      UI Components      │  │
│  │   Player    │  │   Manager   │  │  - Ayah display (RTL)   │  │
│  │             │  │             │  │  - Word highlighting    │  │
│  │  - Play     │  │  - Mic      │  │    (tentative/confirmed)│  │
│  │    prompt   │  │    access   │  │  - Mistake banners      │  │
│  │    ayah     │  │  - Chunk    │  │  - Session controls     │  │
│  │             │  │    & send   │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│         │                │                     ▲                │
│         │                │ WebSocket           │                │
│         │                ▼                     │                │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          │    ┌───────────┴─────────────────────┘
          │    │
          ▼    ▼
┌─────────────────────────────────────────────────────────────────┐
│                          BACKEND                                │
│                    (Python - FastAPI)                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 WebSocket Session Handler                │   │
│  │         - Manage connection lifecycle                    │   │
│  │         - Route audio to pipeline                        │   │
│  │         - Emit feedback events to client                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Audio Preprocessor                     │   │
│  │         - Resample to 16kHz mono                         │   │
│  │         - Normalize chunk format                         │   │
│  │         - Smooth chunk joins                             │   │
│  │         - Maintain rolling audio buffer                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Streaming Transcriber                    │   │
│  │         - faster-whisper + Quran model                   │   │
│  │         - Transcribe overlapping windows                 │   │
│  │         - Output: tentative + confirmed words            │   │
│  │         - Word-level confidence scores                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │             Continuation Alignment Engine                │   │
│  │                   [CORE COMPONENT]                       │   │
│  │                                                          │   │
│  │  Inputs:                                                 │   │
│  │    - Known prompt ayah (anchor point)                    │   │
│  │    - Expected ayah window (next N ayahs)                 │   │
│  │    - Streaming transcription (tentative + confirmed)     │   │
│  │                                                          │   │
│  │  Responsibilities:                                       │   │
│  │    - Track position in expected continuation             │   │
│  │    - Rolling word alignment against expected window      │   │
│  │    - Detect: where recitation most likely resumed        │   │
│  │    - Distinguish: true mistake vs chunk artifact         │   │
│  │    - Recognize: self-corrections, repetitions            │   │
│  │    - Maintain: confirmed vs tentative alignment          │   │
│  │                                                          │   │
│  │  Outputs:                                                │   │
│  │    - Current position in expected text                   │   │
│  │    - Alignment events (match, mismatch, skip, etc.)      │   │
│  │    - Confidence level for each alignment decision        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Mistake Classifier                     │   │
│  │         - Categorize alignment events                    │   │
│  │         - Types: wrong_word, skipped, repetition,        │   │
│  │           out_of_order, jumped_ahead, self_corrected,    │   │
│  │           early_stop, low_confidence                     │   │
│  │         - Attach severity and context                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Feedback Policy Engine                   │   │
│  │         - Confidence gating (only surface if certain)    │   │
│  │         - Timing policy (immediate vs delayed)           │   │
│  │         - Emit events, let frontend decide display       │   │
│  │         - Filter: tentative issues vs confirmed mistakes │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Session Store                         │   │
│  │         - Interface-based (swap impl later)              │   │
│  │         - MVP: in-memory                                 │   │
│  │         - Future: Redis/Postgres                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Quran Data Service                     │   │
│  │         - Ayah text (3 forms: uthmani, normalized, tokens)│  │
│  │         - Juz/Surah/Ayah mappings                        │   │
│  │         - Audio file URLs                                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | **FastAPI** | Async support, WebSockets built-in, fast |
| ML Model | **faster-whisper** | 4x faster than openai-whisper, same accuracy |
| Quran Model | **tarteel-ai/whisper-base-ar-quran** | 5.7% WER, Quran-tuned |
| Audio Processing | **librosa** / **soundfile** | Resampling, normalization |
| WebSocket | **FastAPI WebSockets** | Real-time bidirectional communication |

### Frontend

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | **Lite React** (Vite) | Stateful UI: WS state, recording, streaming transcript, highlights |
| Audio Playback | **HTML5 Audio API** | Native, simple |
| Recording | **Web Audio API + MediaRecorder** | Mic access, chunking |
| Styling | **Tailwind CSS** | Fast styling, RTL support |

### Data Sources

| Data | Source | Format |
|------|--------|--------|
| Ayah Text | [quran-json](https://github.com/risan/quran-json) or API | JSON |
| Juz Mapping | Static JSON | Juz → Surah:Ayah ranges |
| Audio Files | [everyayah.com](https://everyayah.com) | MP3 per ayah |

---

## Data Models

### Quran Text (Three Forms)

```python
@dataclass
class AyahText:
    surah: int
    ayah: int
    juz: int
    audio_url: str

    # Three forms for different purposes
    text_uthmani: str      # Display: "وَعِبَادُ الرَّحْمَٰنِ"
    text_normalized: str   # Comparison: "وعباد الرحمن" (diacritics removed, alef normalized)
    text_tokens: list[str] # Alignment: ["وعباد", "الرحمن"]
```

**Why three forms?**
- Compare on normalized/tokenized form
- Display feedback using Uthmani text
- Avoid over-normalization hiding real mistakes

### Session State Machine

```python
from enum import Enum
from dataclasses import dataclass, field

class SessionState(Enum):
    WAITING_FOR_PROMPT_PLAYBACK = "waiting_for_prompt_playback"
    RECORDING = "recording"
    ALIGNING = "aligning"
    USER_PAUSED = "user_paused"
    COMPLETE = "complete"

@dataclass
class ReviewSession:
    id: str
    state: SessionState

    # Configuration
    juz_range: tuple[int, int]
    num_ayahs_to_recite: int

    # Prompt and expectation
    prompt_ayah: AyahText
    expected_ayahs: list[AyahText]
    expected_tokens: list[str]  # Flattened token list for alignment

    # Position tracking
    confirmed_word_index: int = 0       # Last word we're certain about
    tentative_word_index: int = 0       # Current best guess position
    last_stable_alignment: int = 0      # Last high-confidence alignment

    # Transcript state
    confirmed_transcript: list[str] = field(default_factory=list)
    tentative_transcript: list[str] = field(default_factory=list)

    # Mistake tracking
    mistakes: list[Mistake] = field(default_factory=list)

    # Confidence tracking
    low_confidence_counter: int = 0
    self_correction_window_ms: int = 2000  # Time to allow self-correction

    # Timing
    recording_started_at: float | None = None
    last_chunk_at: float | None = None
```

### Mistake Model (Extended)

```python
class MistakeType(Enum):
    WRONG_WORD = "wrong_word"           # Said different word
    SKIPPED = "skipped"                 # Missed a word
    ADDED = "added"                     # Said extra word not in text
    REPETITION = "repetition"           # Repeated a phrase
    OUT_OF_ORDER = "out_of_order"       # Words in wrong sequence
    JUMPED_AHEAD = "jumped_ahead"       # Skipped multiple words/ayahs
    EARLY_STOP = "early_stop"           # Stopped before expected end
    SELF_CORRECTED = "self_corrected"   # Made mistake but fixed it (no penalty)
    LOW_CONFIDENCE = "low_confidence"   # ASR uncertain, needs review

@dataclass
class Mistake:
    mistake_type: MistakeType
    ayah: tuple[int, int]  # (surah, ayah)
    word_index: int
    expected: str          # Uthmani form for display
    received: str | None   # What was said (None if skipped)
    confidence: float      # ASR confidence
    is_penalty: bool       # False for self_corrected, low_confidence
    timestamp_ms: int
```

---

## Core Component: Continuation Alignment Engine

This is the heart of the system. It maintains position in expected text and handles messy recitation.

### Conceptual Model

```
Expected tokens:  [w0] [w1] [w2] [w3] [w4] [w5] [w6] [w7] [w8] ...
                        ↑              ↑
                   confirmed      tentative
                   position       position

Incoming transcript:  "w1 w2 w2 w3"
                           ↑
                      repetition detected
                      (not a mistake)
```

### Algorithm Sketch

```python
class ContinuationAlignmentEngine:
    def __init__(self, expected_tokens: list[str], normalizer: ArabicNormalizer):
        self.expected = expected_tokens
        self.normalizer = normalizer
        self.confirmed_idx = 0
        self.tentative_idx = 0
        self.pending_words: list[tuple[str, float, int]] = []  # (word, confidence, timestamp)

    def process_transcription(
        self,
        new_words: list[str],
        confidences: list[float],
        is_final: bool
    ) -> list[AlignmentEvent]:
        """
        Process new transcription output.
        Returns alignment events (matches, mismatches, skips, etc.)
        """
        events = []

        for word, conf in zip(new_words, confidences):
            norm_word = self.normalizer.normalize(word)

            # Look ahead in expected tokens for best match
            match_idx = self._find_best_match(norm_word, self.tentative_idx)

            if match_idx == self.tentative_idx:
                # Perfect sequential match
                events.append(AlignmentEvent("match", self.tentative_idx, word, conf))
                self.tentative_idx += 1

            elif match_idx is not None and match_idx > self.tentative_idx:
                # Jumped ahead - mark skipped words
                for skip_idx in range(self.tentative_idx, match_idx):
                    events.append(AlignmentEvent("skipped", skip_idx, None, 0.0))
                events.append(AlignmentEvent("match", match_idx, word, conf))
                self.tentative_idx = match_idx + 1

            elif match_idx is not None and match_idx < self.tentative_idx:
                # Repetition - went back
                events.append(AlignmentEvent("repetition", match_idx, word, conf))

            else:
                # No match - wrong word or insertion
                events.append(AlignmentEvent("mismatch", self.tentative_idx, word, conf))

        # Commit confirmed words if stable
        if is_final or self._is_stable():
            self._commit_tentative()

        return events

    def _find_best_match(self, word: str, start_idx: int, window: int = 5) -> int | None:
        """Find best matching position within a look-ahead window."""
        for i in range(start_idx, min(start_idx + window, len(self.expected))):
            if self.normalizer.normalize(self.expected[i]) == word:
                return i
        return None

    def _is_stable(self) -> bool:
        """Check if current alignment is stable enough to commit."""
        # Stable if tentative has advanced and matches are consistent
        return self.tentative_idx > self.confirmed_idx + 2

    def _commit_tentative(self):
        """Move confirmed position forward."""
        self.confirmed_idx = self.tentative_idx
```

### Handling Edge Cases

| Scenario | How Engine Handles It |
|----------|----------------------|
| Student pauses mid-ayah | No new words, position unchanged, state → USER_PAUSED |
| Student repeats phrase | Detect match behind current position → emit "repetition", no penalty |
| Student self-corrects | Wrong word followed by correct word within window → mark self_corrected |
| Chunk boundary splits word | Rolling buffer with overlap, only commit stable words |
| Student jumps ahead | Match found ahead of position → emit "skipped" for gap |
| ASR hallucinates word | Low confidence + no match → emit low_confidence, don't penalize |

---

## Transcription Strategy: Confirmed vs Tentative

### Rolling Buffer Approach

```python
class StreamingTranscriber:
    def __init__(self, model: WhisperModel):
        self.model = model
        self.audio_buffer = RollingAudioBuffer(max_duration=10.0)
        self.last_confirmed_text = ""

    def process_chunk(self, audio_chunk: bytes) -> TranscriptionResult:
        self.audio_buffer.append(audio_chunk)

        # Transcribe full buffer (with overlap)
        full_audio = self.audio_buffer.get_audio()
        segments, info = self.model.transcribe(
            full_audio,
            language="ar",
            word_timestamps=True
        )

        words = []
        for segment in segments:
            for word_info in segment.words:
                words.append(WordWithMeta(
                    text=word_info.word,
                    confidence=word_info.probability,
                    start_time=word_info.start,
                    end_time=word_info.end
                ))

        # Determine confirmed vs tentative
        # Words from earlier in buffer = more stable
        confirmed, tentative = self._split_by_stability(words)

        return TranscriptionResult(
            confirmed_words=confirmed,
            tentative_words=tentative
        )

    def _split_by_stability(self, words: list[WordWithMeta]) -> tuple[list, list]:
        """
        Words that appeared in previous transcription runs = confirmed
        New words at the end of buffer = tentative
        """
        # Compare with last_confirmed_text
        # Words matching prefix = confirmed
        # New words = tentative
        ...
```

### Visual Feedback

```
Frontend display:

  Expected:  وَإِذَا خَاطَبَهُمُ الْجَاهِلُونَ قَالُوا سَلَامًا

  Your recitation:
             ───────── ─────────── ───────────
             وَإِذَا   خَاطَبَهُمُ   ال...
             ✓ confirmed  ✓ confirmed  ⋯ tentative (gray)
```

---

## Feedback Policy Engine

### Confidence Gating

Only surface a mistake if:
1. ASR confidence > threshold (e.g., 0.7), OR
2. Mismatch persists across 2+ transcription windows, OR
3. Alignment engine has high position confidence

```python
class FeedbackPolicyEngine:
    def __init__(self, config: FeedbackConfig):
        self.min_confidence = config.min_confidence  # 0.7
        self.require_persistence = config.require_persistence  # True
        self.persistence_windows = config.persistence_windows  # 2
        self.pending_issues: dict[int, PendingIssue] = {}

    def evaluate(self, event: AlignmentEvent) -> FeedbackDecision:
        if event.type == "match":
            # Clear any pending issue at this position
            self.pending_issues.pop(event.word_index, None)
            return FeedbackDecision("confirm_correct", event)

        if event.type == "mismatch":
            if event.confidence < self.min_confidence:
                return FeedbackDecision("hold", event, reason="low_confidence")

            if self.require_persistence:
                pending = self.pending_issues.get(event.word_index)
                if pending and pending.occurrences >= self.persistence_windows:
                    return FeedbackDecision("emit_mistake", event)
                else:
                    self._track_pending(event)
                    return FeedbackDecision("hold", event, reason="awaiting_persistence")

            return FeedbackDecision("emit_mistake", event)

        # Handle other event types...
```

### Feedback Modes (Configurable)

| Mode | Behavior | Use Case |
|------|----------|----------|
| `immediate` | Show mistakes as detected | Strict practice |
| `gentle` | Highlight inline, no interruption | Flow-focused review |
| `post_ayah` | Feedback after each ayah | Less disruptive |
| `post_session` | Only show summary at end | Test mode |

```python
class FeedbackConfig:
    mode: Literal["immediate", "gentle", "post_ayah", "post_session"]
    min_confidence: float = 0.7
    require_persistence: bool = True
    persistence_windows: int = 2
    self_correction_window_ms: int = 2000
```

---

## API Design

### REST Endpoints

```
POST /api/session/start
    Request:  { "juz_start": 25, "juz_end": 30, "num_ayahs": 3, "feedback_mode": "gentle" }
    Response: { "session_id": "abc123", "prompt_ayah": {...}, "expected_ayahs": [...] }

GET /api/session/{session_id}
    Response: { "session": {...}, "mistakes": [...], "state": "recording" }

POST /api/session/{session_id}/complete
    Response: { "summary": { "total_words": 45, "correct": 42, "mistakes": [...] } }

GET /api/quran/ayah/{surah}/{ayah}
    Response: { "text_uthmani": "...", "text_normalized": "...", "audio_url": "..." }
```

### WebSocket Protocol

```
Connect: ws://localhost:8000/ws/session/{session_id}

# Client → Server: Audio chunk
{
    "type": "audio_chunk",
    "data": "<base64 encoded 16kHz mono PCM>",
    "timestamp_ms": 1234567890,
    "is_final": false
}

# Client → Server: Recording control
{ "type": "start_recording" }
{ "type": "pause_recording" }
{ "type": "stop_recording" }

# Server → Client: Transcription update
{
    "type": "transcription",
    "confirmed_words": [
        {"word": "وَإِذَا", "status": "correct", "index": 0},
        {"word": "خَاطَبَهُمُ", "status": "correct", "index": 1}
    ],
    "tentative_words": [
        {"word": "ال", "index": 2}
    ]
}

# Server → Client: Mistake detected (after confidence gating)
{
    "type": "mistake",
    "mistake_type": "wrong_word",
    "word_index": 5,
    "expected": "الْجَاهِلُونَ",
    "received": "الجاهلين",
    "confidence": 0.85,
    "is_penalty": true
}

# Server → Client: Self-correction detected (no penalty)
{
    "type": "self_correction",
    "word_index": 5,
    "message": "You corrected yourself - no penalty"
}

# Server → Client: Ayah complete
{
    "type": "ayah_complete",
    "ayah": {"surah": 25, "ayah": 63},
    "status": "correct",
    "words_correct": 8,
    "words_total": 8
}

# Server → Client: Session complete
{
    "type": "session_complete",
    "summary": {
        "ayahs_tested": 3,
        "ayahs_correct": 2,
        "total_words": 24,
        "words_correct": 22,
        "mistakes": [...]
    }
}
```

---

## Arabic Text Normalization

### Strategy: Careful, Not Aggressive

```python
import regex

class ArabicNormalizer:
    """
    Normalize Arabic text for comparison.
    Be careful not to over-normalize and hide real mistakes.
    """

    # Diacritics (tashkeel) - remove for comparison
    DIACRITICS = regex.compile(r'[\u064B-\u065F\u0670]')

    # Alef variants - normalize to bare alef
    ALEF_VARIANTS = regex.compile(r'[أإآٱ]')

    def normalize(self, text: str) -> str:
        """Normalize for comparison purposes."""
        text = self.DIACRITICS.sub('', text)
        text = self.ALEF_VARIANTS.sub('ا', text)
        # Note: NOT normalizing ta marbuta (ة) to ha (ه) - that can hide real mistakes
        return text

    def tokenize(self, text: str) -> list[str]:
        """Split into words for alignment."""
        return [w for w in text.split() if w]

    def normalize_for_comparison(self, text: str) -> list[str]:
        """Full pipeline: normalize then tokenize."""
        return self.tokenize(self.normalize(text))
```

### What We Normalize (MVP)
- Tashkeel (diacritics): فَتْحَة، ضَمَّة، كَسْرَة، etc.
- Alef variants: أ إ آ ٱ → ا

### What We DON'T Normalize (to catch real mistakes)
- Ta marbuta ة vs Ha ه
- Alef maqsura ى vs Ya ي
- These differences often indicate actual memorization errors

---

## File Structure

```
hifdh/
├── backend/
│   ├── main.py                     # FastAPI app entry
│   ├── api/
│   │   ├── routes.py               # REST endpoints
│   │   └── websocket.py            # WebSocket handler
│   ├── core/
│   │   ├── alignment.py            # Continuation Alignment Engine
│   │   ├── transcriber.py          # Streaming Transcriber
│   │   ├── classifier.py           # Mistake Classifier
│   │   ├── feedback.py             # Feedback Policy Engine
│   │   └── audio.py                # Audio Preprocessor
│   ├── services/
│   │   ├── quran.py                # Quran Data Service
│   │   └── session.py              # Session Store (interface + impl)
│   ├── models/
│   │   ├── session.py              # Session, SessionState
│   │   ├── mistake.py              # Mistake, MistakeType
│   │   ├── quran.py                # AyahText
│   │   └── events.py               # AlignmentEvent, FeedbackDecision
│   ├── data/
│   │   ├── quran.json              # Ayah text (3 forms)
│   │   └── juz_mapping.json        # Juz boundaries
│   ├── config.py                   # App configuration
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── App.jsx                 # Main app component
│   │   ├── components/
│   │   │   ├── AyahDisplay.jsx     # RTL ayah text with highlighting
│   │   │   ├── RecordingControls.jsx
│   │   │   ├── TranscriptDisplay.jsx  # Confirmed/tentative words
│   │   │   ├── MistakeBanner.jsx
│   │   │   └── SessionSummary.jsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.js
│   │   │   ├── useAudioRecorder.js
│   │   │   └── useSession.js
│   │   └── utils/
│   │       └── audio.js            # Chunking, base64 encoding
│   ├── package.json
│   └── vite.config.js
│
├── ARCHITECTURE.md                 # This document
└── README.md
```

---

## MVP Scope

### Phase 1: MVP

**Backend**
- [ ] FastAPI project setup with WebSocket support
- [ ] Quran Data Service (load JSON, 3 text forms)
- [ ] Audio Preprocessor (16kHz mono, rolling buffer)
- [ ] Streaming Transcriber (faster-whisper, confirmed/tentative split)
- [ ] Continuation Alignment Engine (core position tracking)
- [ ] Mistake Classifier (basic types: correct, wrong, skipped)
- [ ] Feedback Policy Engine (confidence gating)
- [ ] Session Store (in-memory, interface-based)

**Frontend**
- [ ] React + Vite setup with Tailwind
- [ ] Juz range selector
- [ ] Audio playback for prompt ayah
- [ ] Mic recording with chunking (2s chunks)
- [ ] WebSocket connection + state management
- [ ] Real-time word display (confirmed=normal, tentative=gray)
- [ ] Mistake highlighting
- [ ] Session summary view

**Data**
- [ ] Quran text JSON (all 3 forms)
- [ ] Juz boundary mapping
- [ ] Audio URLs (everyayah.com)

### Phase 2: Polish

- [ ] Self-correction detection
- [ ] Repetition handling (no penalty)
- [ ] Feedback mode configuration
- [ ] Improved Arabic normalization (test edge cases)
- [ ] Better word alignment algorithm
- [ ] Session history persistence

### Phase 3: Scale

- [ ] User accounts
- [ ] Progress tracking over time
- [ ] Common mistake analysis
- [ ] Multiple reciters for audio
- [ ] Mobile-responsive design
- [ ] PWA support

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| ASR accuracy on diverse recitation styles | Start with Quran-tuned model; collect feedback; fine-tune if needed |
| False positives erode user trust | Confidence gating + persistence requirement before showing mistakes |
| Chunk boundary artifacts | Rolling buffer with overlap; only commit stable words |
| Over-normalization hides real mistakes | Conservative normalization; test with real users |
| Latency too high for "real-time" feel | Target <2s feedback; use faster-whisper; optimize buffer sizes |

---

## References

- [Tarteel Whisper Model](https://huggingface.co/tarteel-ai/whisper-base-ar-quran)
- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [everyayah.com](https://everyayah.com)
