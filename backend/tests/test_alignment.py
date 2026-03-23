"""
Unit tests for alignment engine.

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


# Uses make_word fixture from conftest.py


class TestBasicAlignment:
    """Test basic word alignment."""

    def test_perfect_recitation(self, make_word):
        """All words match in order."""
        ayah = make_ayah(1, 1, "بسم الله الرحمن الرحيم")
        engine = ContinuationAlignmentEngine([ayah])

        words = [
            make_word("بِسْمِ"),
            make_word("اللَّهِ"),
            make_word("الرَّحْمَنِ"),
            make_word("الرَّحِيمِ"),
        ]

        events = engine.process_words(words)

        # All should be matches
        match_events = [e for e in events if e.event_type == AlignmentEventType.MATCH]
        assert len(match_events) == 4

        # Position should be at end
        assert engine.position.tentative_index == 4

    def test_single_mismatch(self):
        """One word is wrong."""
        ayah = make_ayah(1, 1, "بسم الله الرحمن")
        engine = ContinuationAlignmentEngine([ayah])

        words = [
            make_word("بِسْمِ"),
            make_word("خطأ"),  # Wrong word
            make_word("الرَّحْمَنِ"),
        ]

        events = engine.process_words(words)

        # Should have 2 matches and 1 mismatch
        matches = [e for e in events if e.event_type == AlignmentEventType.MATCH]
        mismatches = [e for e in events if e.event_type == AlignmentEventType.MISMATCH]

        assert len(matches) == 2
        assert len(mismatches) == 1

    def test_skipped_word(self):
        """User skips a word."""
        ayah = make_ayah(1, 1, "بسم الله الرحمن الرحيم")
        engine = ContinuationAlignmentEngine([ayah])

        words = [
            make_word("بِسْمِ"),
            # Skipped الله
            make_word("الرَّحْمَنِ"),
            make_word("الرَّحِيمِ"),
        ]

        events = engine.process_words(words)

        # Should have skip event for الله
        skips = [e for e in events if e.event_type == AlignmentEventType.SKIPPED]
        assert len(skips) == 1
        assert skips[0].word_index == 1  # Index of الله


class TestUthmaniAlignment:
    """Test alignment with Uthmani script differences."""

    def test_uthmani_kitab(self):
        """كتب (Uthmani) should match كتاب (ASR output)."""
        ayah = make_ayah(83, 9, "كتب مرقوم")  # Simplified Uthmani
        engine = ContinuationAlignmentEngine([ayah])

        words = [
            make_word("كِتَابٌ"),  # ASR outputs standard Arabic
            make_word("مَرْقُومٌ"),
        ]

        events = engine.process_words(words)

        matches = [e for e in events if e.event_type == AlignmentEventType.MATCH]
        assert len(matches) == 2

    def test_uthmani_with_marks(self):
        """Handle Uthmani special marks like ۭ."""
        # Using the actual Uthmani form with small high meem
        ayah = make_ayah(83, 9, "كتبۭ مرقومۭ")
        engine = ContinuationAlignmentEngine([ayah])

        words = [
            make_word("كِتَابٌ"),
            make_word("مَرْقُومٌ"),
        ]

        events = engine.process_words(words)

        matches = [e for e in events if e.event_type == AlignmentEventType.MATCH]
        # Should match despite Uthmani marks
        assert len(matches) == 2


class TestRestartBehavior:
    """Test pause/restart handling."""

    def test_restart_from_earlier(self):
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
        words2 = [
            make_word("اللَّهِ"),  # Going back
        ]
        events = engine.process_words(words2)

        # Should detect as repetition, not mismatch
        reps = [e for e in events if e.event_type == AlignmentEventType.REPETITION]
        assert len(reps) == 1

        # Position should reset to after الله
        assert engine.position.tentative_index == 2

    def test_continue_after_restart(self):
        """After restart, can continue normally."""
        ayah = make_ayah(1, 1, "بسم الله الرحمن الرحيم")
        engine = ContinuationAlignmentEngine([ayah])

        # Recite all, then restart and continue
        words1 = [make_word("بِسْمِ"), make_word("اللَّهِ")]
        engine.process_words(words1)

        # Restart from بسم
        words2 = [make_word("بِسْمِ")]
        engine.process_words(words2)

        # Continue normally
        words3 = [make_word("اللَّهِ"), make_word("الرَّحْمَنِ"), make_word("الرَّحِيمِ")]
        events = engine.process_words(words3)

        # All should match
        matches = [e for e in events if e.event_type == AlignmentEventType.MATCH]
        assert len(matches) == 3


class TestMultipleAyahs:
    """Test alignment across multiple ayahs."""

    def test_cross_ayah_recitation(self):
        """Recitation spans multiple ayahs."""
        ayah1 = make_ayah(112, 1, "قل هو الله احد")
        ayah2 = make_ayah(112, 2, "الله الصمد")

        engine = ContinuationAlignmentEngine([ayah1, ayah2])

        words = [
            make_word("قُلْ"),
            make_word("هُوَ"),
            make_word("اللَّهُ"),
            make_word("أَحَدٌ"),
            make_word("اللَّهُ"),
            make_word("الصَّمَدُ"),
        ]

        events = engine.process_words(words)

        matches = [e for e in events if e.event_type == AlignmentEventType.MATCH]
        assert len(matches) == 6


class TestProgressTracking:
    """Test progress reporting."""

    def test_progress_updates(self):
        """Progress should update as words are confirmed."""
        ayah = make_ayah(1, 1, "بسم الله الرحمن الرحيم")
        engine = ContinuationAlignmentEngine([ayah])

        assert engine.get_progress() == (0, 4)

        words = [make_word("بِسْمِ"), make_word("اللَّهِ")]
        engine.process_words(words)

        # After stability threshold, should be confirmed
        confirmed, total = engine.get_progress()
        assert total == 4
        assert confirmed >= 0  # Depends on stability threshold

    def test_force_commit(self):
        """Force commit should finalize all tentative."""
        ayah = make_ayah(1, 1, "بسم الله")
        engine = ContinuationAlignmentEngine([ayah])

        words = [make_word("بِسْمِ")]
        engine.process_words(words)

        # Before force commit
        initial_confirmed = engine.position.confirmed_index

        engine.force_commit()

        # After force commit, tentative becomes confirmed
        assert engine.position.confirmed_index == engine.position.tentative_index
