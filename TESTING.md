# Testing Strategy

This document outlines the testing approach for the Hifdh Review App, covering both automated tests and manual testing strategies for the audio/human elements.

## Overview

Testing a speech-to-text application with real-time alignment presents unique challenges:
- The ML model (Whisper) has inherent variability
- Human recitation varies in speed, accent, and clarity
- Uthmani script differs from standard Arabic orthography
- Real usage involves pauses, restarts, and self-corrections

Our strategy separates concerns into testable layers.

---

## 1. Unit Tests (No Audio Required)

These tests validate core logic without any audio processing.

### Normalizer Tests (`tests/test_normalizer.py`)

Tests Arabic text normalization:
- Diacritic removal
- Alef variant normalization
- Uthmani script mark handling
- Fuzzy matching for ASR errors

```bash
pytest tests/test_normalizer.py -v
```

**Key test cases:**
- `كِتَابٌ` (with diacritics) matches `كتاب` (without)
- `كتب` (Uthmani) matches `كتاب` (standard Arabic)
- `أَلَمْ` matches `الم` (alef variants)
- `ما` does NOT match `في` (different words shouldn't fuzzy-match)

### Alignment Tests (`tests/test_alignment_uthmani.py`)

Tests the alignment engine with mock transcription data:
- Perfect recitation (all words match)
- Single word mistakes
- Skipped words
- Restart detection (going back after pause)
- Multi-ayah progression

```bash
pytest tests/test_alignment_uthmani.py -v
```

**Key test cases:**
- Uthmani `كتبۭ` matches ASR output `كِتَابٌ`
- Restart from word 3 is detected as repetition, not mistake
- Confirmed position resets appropriately on restart

### Running All Unit Tests

```bash
cd backend
source venv/bin/activate
pytest tests/test_normalizer.py tests/test_alignment_uthmani.py -v
```

These tests run in milliseconds and should pass before any commit.

---

## 2. Pre-recorded Test Corpus

For testing the full pipeline including Whisper, use pre-recorded audio files.

### Creating Test Fixtures

1. Create the fixtures directory:
   ```bash
   mkdir -p backend/tests/fixtures/audio
   ```

2. Record yourself reciting specific scenarios:
   - **Correct recitation** of a short surah (e.g., Al-Ikhlas)
   - **Intentional mistake** (wrong word)
   - **Skipped word**
   - **Restart scenario** (pause, go back 2-3 words, continue)
   - **Different speeds** (fast, slow, with hesitation)

3. Create a JSON file for each recording with expected results:
   ```json
   {
     "surah": 112,
     "ayah": 1,
     "text": "قل هو الله احد",
     "words": ["قل", "هو", "الله", "احد"],
     "expected_accuracy": 1.0,
     "scenario": "perfect_recitation"
   }
   ```

### Using Public Quran Recordings

For baseline testing, use professional recitations:
- [QuranicAudio.com](https://quranicaudio.com/) - per-surah MP3s
- [EveryAyah.com](https://everyayah.com/) - per-ayah MP3s

These test: "If we can't accurately track Al-Husary, something's broken."

### Running Integration Tests

```bash
pytest tests/test_integration.py -v
```

Tests are skipped if no fixtures exist.

---

## 3. Virtual Audio Device Testing

Test the full end-to-end pipeline silently using a virtual microphone.

### Setup (macOS)

1. Install BlackHole:
   ```bash
   brew install blackhole-2ch
   ```

2. In System Settings → Sound → Input, select "BlackHole 2ch"

3. Route audio to BlackHole:
   - Use Audio MIDI Setup to create an aggregate device, OR
   - Use Loopback (paid) for easier routing

4. In your browser, select BlackHole as the microphone

5. Play test audio files - the app receives them as "live" mic input

### Workflow

1. Start the app normally
2. Select the test ayahs (use debug mode - see below)
3. Play the corresponding test audio file
4. Observe results

**Benefits:**
- Tests everything: browser capture, WebSocket, Whisper, alignment, UI
- Completely silent (use headphones)
- Automatable with scripted playback

---

## 4. Debug Mode for Manual Testing

When testing manually, use debug/development features to understand what's happening.

### Backend Logging

The backend prints detailed alignment info:
```
[TRANSCRIBE] Full text: أَلَمْ تُرَ كَيْفَ
[TRANSCRIBE] Confirmed words: ['أَلَمْ', 'تُرَ']
[ALIGN] Processing word: 'أَلَمْ' -> normalized: 'الم'
[MATCH] Found match at idx 0: 'الم' ~ 'الم'
[RESTART] User restarted from word 3, positions reset
```

### Forcing Specific Ayahs (TODO)

For reproducible testing, implement one of:
- URL parameters: `?surah=105&ayah=1`
- Environment variable: `TEST_AYAHS=105:1,105:2`
- Debug dropdown in UI

This ensures test audio matches expected ayahs.

### Debug UI Panel (TODO)

A collapsible panel showing:
- Raw Whisper transcription
- Normalized word comparisons
- Alignment decisions in real-time
- Confidence scores

---

## 5. Testing Scenarios Checklist

### Core Functionality
- [ ] Perfect recitation of 5+ words
- [ ] Single wrong word detection
- [ ] Multiple consecutive mistakes
- [ ] Skipped word detection
- [ ] Extra word (insertion) handling

### Uthmani Script
- [ ] `كتب` ↔ `كتاب` matching
- [ ] Words with `ۭ` (small high meem)
- [ ] Alef variants (`أ`, `إ`, `آ`, `ٱ`)
- [ ] Alef maksura vs yeh (`ى` vs `ي`)

### Pause/Restart
- [ ] Pause mid-ayah, continue normally
- [ ] Pause and restart from 2 words back
- [ ] Pause and restart from beginning
- [ ] Multiple restarts in one session

### Edge Cases
- [ ] Very fast recitation
- [ ] Very slow recitation with long pauses
- [ ] Background noise
- [ ] Whispered recitation
- [ ] Multi-ayah session crossing ayah boundaries

### UI/UX
- [ ] Words highlight in real-time
- [ ] Mistakes show red underline
- [ ] Progress percentage updates
- [ ] Session summary is accurate
- [ ] Mobile browser works (with HTTPS)

---

## 6. Continuous Integration

### Pre-commit Tests

Run unit tests before every commit:
```bash
pytest tests/test_normalizer.py tests/test_alignment_uthmani.py -v
```

### CI Pipeline (Future)

```yaml
# .github/workflows/test.yml
- Run unit tests (no audio)
- Run integration tests with fixtures (if available)
- Lint checks
```

---

## 7. Test Data Management

### What to Commit
- Unit test files
- Test fixture JSON metadata
- Integration test scaffolding

### What NOT to Commit (in .gitignore)
- Audio files (`.wav`, `.mp3`) - too large
- Model binary (`model.bin`) - 138MB

### Sharing Test Audio

For team testing, store audio fixtures in:
- Shared drive
- Cloud storage with download script
- Git LFS (if team uses it)

---

## Summary

| Layer | Tests | Audio Required | Runtime |
|-------|-------|----------------|---------|
| Unit (normalizer) | Normalization, fuzzy matching | No | <1s |
| Unit (alignment) | Word matching, restart detection | No | <1s |
| Integration | Full pipeline with Whisper | Yes (files) | ~10s |
| E2E (virtual mic) | Complete user flow | Yes (files) | Manual |
| Manual | Edge cases, UX | Yes (live) | Manual |

Start with unit tests for fast feedback, use pre-recorded fixtures for regression testing, and reserve manual testing for exploratory scenarios.
