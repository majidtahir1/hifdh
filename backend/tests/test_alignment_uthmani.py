"""
Unit tests for alignment engine with Uthmani script handling.

Tests word alignment logic with mock transcription data - no audio needed.
"""

import pytest
from backend.alignment.engine import ContinuationAlignmentEngine, TranscribedWord, AlignmentEventType
from backend.models import AyahText


def make_ayah(surah: int, ayah: int, text: str, juz: int = 1) -> AyahText:
    """Helper to create AyahText for testing."""
    tokens = text.split()
    return AyahText(
        surah=surah,
        ayah=ayah,
        juz=juz,
        text_uthmani=text,
        text_normalized=text,
        text_tokens=tokens,
        audio_url=None,
    )


class TestUthmaniAlignment:
    """Test alignment with Uthmani script differences."""

    def test_uthmani_kitab(self, make_word):
        """كتب (Uthmani) should match كتاب (ASR output)."""
        ayah = make_ayah(83, 9, "كتب مرقوم")  # Simplified Uthmani
        engine = ContinuationAlignmentEngine([ayah])

        words = [
            make_word("كِتَابٌ"),  # ASR outputs standard Arabic
            make_word("مَرْقُومٌ"),
        ]

        events = engine.process_words(words)

        matches = [e for e in events if e.event_type == AlignmentEventType.MATCH]
        assert len(matches) == 2, f"Expected 2 matches, got {len(matches)}"

    def test_uthmani_with_marks(self, make_word):
        """Handle Uthmani special marks like ۭ (small high meem)."""
        ayah = make_ayah(83, 9, "كتبۭ مرقومۭ")
        engine = ContinuationAlignmentEngine([ayah])

        words = [
            make_word("كِتَابٌ"),
            make_word("مَرْقُومٌ"),
        ]

        events = engine.process_words(words)

        matches = [e for e in events if e.event_type == AlignmentEventType.MATCH]
        assert len(matches) == 2, f"Expected 2 matches, got {len(matches)}"

    def test_alam_tara(self, make_word):
        """Test الم تر matching with diacritics."""
        ayah = make_ayah(105, 1, "الم تر كيف فعل ربك")
        engine = ContinuationAlignmentEngine([ayah])

        words = [
            make_word("أَلَمْ"),
            make_word("تَرَ"),
            make_word("كَيْفَ"),
            make_word("فَعَلَ"),
            make_word("رَبُّكَ"),
        ]

        events = engine.process_words(words)

        matches = [e for e in events if e.event_type == AlignmentEventType.MATCH]
        assert len(matches) == 5, f"Expected 5 matches, got {len(matches)}"


class TestRestartBehavior:
    """Test pause/restart handling."""

    def test_restart_from_earlier(self, make_word):
        """User pauses and restarts from earlier point."""
        ayah = make_ayah(1, 1, "بسم الله الرحمن الرحيم")
        engine = ContinuationAlignmentEngine([ayah])

        # First pass - recite first 3 words
        words1 = [
            make_word("بِسْمِ"),
            make_word("اللَّهِ"),
            make_word("الرَّحْمَنِ"),
        ]
        engine.process_words(words1)
        assert engine.position.tentative_index == 3

        # Restart from word 1 (الله)
        words2 = [make_word("اللَّهِ")]
        events = engine.process_words(words2)

        # Should detect as repetition, not mismatch
        reps = [e for e in events if e.event_type == AlignmentEventType.REPETITION]
        assert len(reps) == 1, "Should detect restart as repetition"

    def test_restart_resets_confirmed(self, make_word):
        """Restart should reset confirmed position if going back past it."""
        ayah = make_ayah(1, 1, "بسم الله الرحمن الرحيم")
        engine = ContinuationAlignmentEngine([ayah])

        # Recite first 3 words
        words = [
            make_word("بِسْمِ"),
            make_word("اللَّهِ"),
            make_word("الرَّحْمَنِ"),
        ]
        engine.process_words(words)
        engine.force_commit()

        # Now restart from word 0
        restart_words = [make_word("بِسْمِ")]
        events = engine.process_words(restart_words)

        # Should detect repetition and reset confirmed
        reps = [e for e in events if e.event_type == AlignmentEventType.REPETITION]
        assert len(reps) == 1, "Should detect restart"
        assert engine.position.confirmed_index == 0, "Confirmed should reset on restart"


class TestProgressTracking:
    """Test progress reporting."""

    def test_force_commit(self, make_word):
        """Force commit should finalize all tentative."""
        ayah = make_ayah(1, 1, "بسم الله")
        engine = ContinuationAlignmentEngine([ayah])

        words = [make_word("بِسْمِ")]
        engine.process_words(words)

        engine.force_commit()

        # After force commit, tentative becomes confirmed
        assert engine.position.confirmed_index == engine.position.tentative_index
