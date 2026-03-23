"""
Integration tests using pre-recorded audio files.

To use these tests:
1. Create a tests/fixtures/audio/ directory
2. Add .wav or .mp3 files of Quran recitations
3. Create corresponding .json files with expected results

Example fixture structure:
  tests/fixtures/audio/
    surah_112_ayah_1.wav      # Audio file
    surah_112_ayah_1.json     # Expected: {"text": "قل هو الله احد", "words": [...]}
"""

import pytest
import json
import os
from pathlib import Path

# Skip all tests if no fixtures available
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "audio"


def get_audio_fixtures():
    """Get list of available audio test fixtures."""
    if not FIXTURES_DIR.exists():
        return []

    fixtures = []
    for audio_file in FIXTURES_DIR.glob("*.wav"):
        json_file = audio_file.with_suffix(".json")
        if json_file.exists():
            fixtures.append((audio_file, json_file))

    for audio_file in FIXTURES_DIR.glob("*.mp3"):
        json_file = audio_file.with_suffix(".json")
        if json_file.exists():
            fixtures.append((audio_file, json_file))

    return fixtures


@pytest.mark.skipif(
    not FIXTURES_DIR.exists() or len(get_audio_fixtures()) == 0,
    reason="No audio fixtures available. Add .wav/.mp3 files to tests/fixtures/audio/"
)
class TestAudioIntegration:
    """Integration tests with real audio files."""

    @pytest.fixture
    def transcriber(self):
        """Load the transcriber (expensive - cached)."""
        from ml.transcriber import StreamingTranscriber
        return StreamingTranscriber()

    @pytest.fixture
    def preprocessor(self):
        """Audio preprocessor."""
        from ml.audio_preprocessor import AudioPreprocessor
        return AudioPreprocessor()

    @pytest.mark.parametrize("audio_file,expected_file", get_audio_fixtures())
    def test_transcription_accuracy(self, transcriber, preprocessor, audio_file, expected_file):
        """Test transcription against expected text."""
        # Load expected results
        with open(expected_file) as f:
            expected = json.load(f)

        # Load and process audio
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()

        audio_array = preprocessor.process(audio_bytes)
        result = transcriber.transcribe_with_context(audio_array)

        # Check transcription
        assert result.full_text.strip(), "Transcription should not be empty"

        # If expected words provided, check word-level accuracy
        if "words" in expected:
            expected_words = expected["words"]
            transcribed_words = [w.text for w in result.words]

            # Calculate word accuracy
            matches = sum(1 for e, t in zip(expected_words, transcribed_words)
                         if e.strip() == t.strip())
            accuracy = matches / len(expected_words) if expected_words else 0

            assert accuracy >= 0.7, f"Word accuracy {accuracy:.1%} below threshold"


@pytest.mark.skipif(
    not FIXTURES_DIR.exists(),
    reason="Fixtures directory not found"
)
class TestEndToEnd:
    """End-to-end tests simulating full session flow."""

    @pytest.fixture
    def test_audio_path(self):
        """Path to a test audio file."""
        # Look for any available test audio
        for ext in ["*.wav", "*.mp3"]:
            files = list(FIXTURES_DIR.glob(ext))
            if files:
                return files[0]
        pytest.skip("No test audio files available")

    def test_full_session_flow(self, test_audio_path):
        """Test complete session: audio -> transcription -> alignment."""
        from ml.audio_preprocessor import AudioPreprocessor
        from ml.transcriber import StreamingTranscriber
        from alignment.engine import ContinuationAlignmentEngine, TranscribedWord
        from models.quran import AyahText

        # Setup
        preprocessor = AudioPreprocessor()
        transcriber = StreamingTranscriber()

        # Create a simple expected ayah (adjust based on your test audio)
        expected_ayah = AyahText(
            surah=112,
            ayah=1,
            juz=30,
            text_uthmani="قل هو الله احد",
            text_normalized="قل هو الله احد",
            text_tokens=["قل", "هو", "الله", "احد"],
            audio_url=None,
        )
        engine = ContinuationAlignmentEngine([expected_ayah])

        # Process audio
        with open(test_audio_path, "rb") as f:
            audio_bytes = f.read()

        audio_array = preprocessor.process(audio_bytes)
        result = transcriber.transcribe_with_context(audio_array)

        # Convert to alignment input
        words = [
            TranscribedWord(
                text=w.text,
                confidence=w.confidence,
                timestamp_ms=int(w.start * 1000),
                is_final=True,
            )
            for w in result.confirmed
        ]

        # Run alignment
        if words:
            events = engine.process_words(words)
            engine.force_commit()

            # Check we got some progress
            confirmed, total = engine.get_progress()
            assert confirmed > 0, "Should have confirmed at least some words"


# Helper to create test fixtures
def create_fixture_template():
    """Create template fixture files for manual population."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    template = {
        "surah": 112,
        "ayah": 1,
        "text": "قل هو الله احد",
        "words": ["قل", "هو", "الله", "احد"],
        "notes": "Record this ayah and save as surah_112_ayah_1.wav"
    }

    template_path = FIXTURES_DIR / "TEMPLATE.json"
    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    print(f"Created template at {template_path}")
    print("To create a test fixture:")
    print("1. Record the ayah and save as .wav or .mp3")
    print("2. Copy TEMPLATE.json and rename to match audio file")
    print("3. Update the JSON with correct surah/ayah/words")


if __name__ == "__main__":
    create_fixture_template()
