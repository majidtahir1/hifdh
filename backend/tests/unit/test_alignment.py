"""
QA-006: Tests for Continuation Alignment Engine.

This module tests the alignment/position tracking in backend/alignment/engine.py:
- Word matching and position tracking
- Skip detection
- Repetition detection
- Stability and confirmation logic
"""

import pytest
from backend.alignment.engine import (
    ContinuationAlignmentEngine,
    TranscribedWord,
    PositionState,
)
from backend.models.events import AlignmentEventType
from backend.models import AyahText


class TestTranscribedWord:
    """Test suite for TranscribedWord dataclass."""

    def test_transcribed_word_creation(self):
        """Test basic TranscribedWord creation."""
        word = TranscribedWord(
            text="الحمد",
            confidence=0.95,
            timestamp_ms=1000,
            is_final=True,
        )
        assert word.text == "الحمد"
        assert word.confidence == 0.95
        assert word.is_final is True

    def test_transcribed_word_defaults(self):
        """Test TranscribedWord default values."""
        word = TranscribedWord(
            text="test",
            confidence=0.9,
            timestamp_ms=0,
        )
        assert word.is_final is False


class TestPositionState:
    """Test suite for PositionState dataclass."""

    def test_position_state_defaults(self):
        """Test PositionState default values."""
        state = PositionState()
        assert state.confirmed_index == 0
        assert state.tentative_index == 0
        assert state.last_stable_index == 0
        assert state.consecutive_matches == 0


class TestAlignmentEngineInitialization:
    """Test suite for alignment engine initialization."""

    def test_engine_creation(self, sample_ayahs):
        """Test basic engine creation."""
        engine = ContinuationAlignmentEngine(expected_ayahs=sample_ayahs)
        assert engine is not None
        assert len(engine.expected_tokens) > 0

    def test_engine_flattens_tokens(self, sample_ayahs):
        """Test that engine correctly flattens tokens from ayahs."""
        engine = ContinuationAlignmentEngine(expected_ayahs=sample_ayahs)
        # Count tokens manually
        expected_count = sum(len(a.text_tokens) for a in sample_ayahs)
        assert len(engine.expected_tokens) == expected_count

    def test_engine_builds_ayah_map(self, sample_ayahs):
        """Test that engine builds correct token-to-ayah mapping."""
        engine = ContinuationAlignmentEngine(expected_ayahs=sample_ayahs)
        assert len(engine.token_to_ayah_map) == len(engine.expected_tokens)

    def test_engine_normalizes_expected_tokens(self, sample_ayahs):
        """Test that engine normalizes expected tokens."""
        engine = ContinuationAlignmentEngine(expected_ayahs=sample_ayahs)
        assert len(engine.expected_normalized) == len(engine.expected_tokens)


class TestWordMatching:
    """Test suite for word matching functionality."""

    def test_match_first_word(self, alignment_engine, make_word):
        """Test matching the first expected word."""
        words = [make_word("الحمد")]
        events = alignment_engine.process_words(words)

        assert len(events) == 1
        assert events[0].event_type == AlignmentEventType.MATCH
        assert events[0].word_index == 0

    def test_match_sequence(self, alignment_engine, make_word):
        """Test matching a sequence of words."""
        words = [
            make_word("الحمد"),
            make_word("لله"),
            make_word("رب"),
        ]
        events = alignment_engine.process_words(words)

        assert len(events) == 3
        for i, event in enumerate(events):
            assert event.event_type == AlignmentEventType.MATCH
            assert event.word_index == i

    def test_match_with_diacritics(self, alignment_engine, make_word):
        """Test matching works with diacritics in input."""
        # Input with diacritics should match normalized expected
        words = [make_word("الْحَمْدُ")]
        events = alignment_engine.process_words(words)

        assert len(events) == 1
        assert events[0].event_type == AlignmentEventType.MATCH


class TestMismatchDetection:
    """Test suite for mismatch detection."""

    def test_detect_mismatch(self, alignment_engine, make_word):
        """Test detecting a mismatched word."""
        words = [make_word("كلمة")]  # Wrong word
        events = alignment_engine.process_words(words)

        assert len(events) == 1
        assert events[0].event_type == AlignmentEventType.MISMATCH
        assert events[0].received_word == "كلمة"

    def test_mismatch_advances_position(self, alignment_engine, make_word):
        """Test that mismatch advances tentative position."""
        initial_pos = alignment_engine.position.tentative_index

        words = [make_word("خطأ")]
        alignment_engine.process_words(words)

        # Position should advance even on mismatch
        assert alignment_engine.position.tentative_index == initial_pos + 1


class TestSkipDetection:
    """Test suite for skip detection."""

    def test_detect_single_skip(self, alignment_engine, make_word):
        """Test detecting a single skipped word."""
        # Skip first word, say second word
        words = [make_word("لله")]  # Second word, skipping "الحمد"
        events = alignment_engine.process_words(words)

        # Should have skip event then match event
        assert len(events) == 2
        assert events[0].event_type == AlignmentEventType.SKIPPED
        assert events[0].word_index == 0  # Skipped first word
        assert events[1].event_type == AlignmentEventType.MATCH
        assert events[1].word_index == 1  # Matched second word

    def test_detect_multiple_skips(self, alignment_engine, make_word):
        """Test detecting multiple skipped words."""
        # Skip first two words, say third word
        words = [make_word("رب")]  # Third word
        events = alignment_engine.process_words(words)

        # Should have 2 skip events then match event
        assert len(events) == 3
        assert events[0].event_type == AlignmentEventType.SKIPPED
        assert events[1].event_type == AlignmentEventType.SKIPPED
        assert events[2].event_type == AlignmentEventType.MATCH


class TestRepetitionDetection:
    """Test suite for repetition detection."""

    def test_detect_repetition(self, alignment_engine, make_word):
        """Test detecting a repetition (going back)."""
        # First, match some words
        words = [
            make_word("الحمد"),
            make_word("لله"),
            make_word("رب"),
        ]
        alignment_engine.process_words(words)

        # Now repeat an earlier word
        repeat_words = [make_word("لله")]
        events = alignment_engine.process_words(repeat_words)

        assert len(events) == 1
        assert events[0].event_type == AlignmentEventType.REPETITION

    def test_repetition_does_not_advance_position(self, alignment_engine, make_word):
        """Test that repetition doesn't advance position."""
        # Match first three words
        words = [
            make_word("الحمد"),
            make_word("لله"),
            make_word("رب"),
        ]
        alignment_engine.process_words(words)

        position_before = alignment_engine.position.tentative_index

        # Repeat
        repeat_words = [make_word("لله")]
        alignment_engine.process_words(repeat_words)

        # Position should not have advanced
        assert alignment_engine.position.tentative_index == position_before


class TestInsertionDetection:
    """Test suite for insertion detection."""

    def test_detect_insertion_at_end(self, alignment_engine, make_word):
        """Test detecting insertion after all expected words."""
        # Match all expected words first
        total_tokens = len(alignment_engine.expected_tokens)

        # Process all expected words
        for token in alignment_engine.expected_tokens:
            words = [make_word(token)]
            alignment_engine.process_words(words)

        # Now say an extra word
        extra_words = [make_word("كلمة")]
        events = alignment_engine.process_words(extra_words)

        assert len(events) == 1
        assert events[0].event_type == AlignmentEventType.INSERTION


class TestPositionTracking:
    """Test suite for position tracking."""

    def test_initial_position(self, alignment_engine):
        """Test initial position is at start."""
        assert alignment_engine.position.confirmed_index == 0
        assert alignment_engine.position.tentative_index == 0

    def test_tentative_advances_on_match(self, alignment_engine, make_word):
        """Test tentative position advances on match."""
        words = [make_word("الحمد")]
        alignment_engine.process_words(words)

        assert alignment_engine.position.tentative_index == 1

    def test_get_current_position(self, alignment_engine, make_word):
        """Test getting current position as ayah coordinates."""
        # Match first word
        words = [make_word("الحمد")]
        alignment_engine.process_words(words)

        ayah_idx, word_idx = alignment_engine.get_current_position()
        assert ayah_idx == 0  # Still in first ayah
        assert word_idx == 1  # At second word

    def test_get_confirmed_position(self, alignment_engine, make_word):
        """Test getting confirmed position."""
        # Initially at start
        ayah_idx, word_idx = alignment_engine.get_confirmed_position()
        assert ayah_idx == 0
        assert word_idx == 0


class TestStabilityTracking:
    """Test suite for stability tracking."""

    def test_consecutive_matches_increase_stability(self, alignment_engine, make_word):
        """Test that consecutive matches increase stability."""
        # Process enough words to reach stability threshold
        words = [
            make_word("الحمد"),
            make_word("لله"),
            make_word("رب"),
            make_word("العالمين"),
        ]

        for word in words:
            alignment_engine.process_words([word])

        assert alignment_engine.position.consecutive_matches >= 3

    def test_mismatch_resets_stability(self, alignment_engine, make_word):
        """Test that mismatch resets consecutive match count."""
        # Get some matches
        words = [
            make_word("الحمد"),
            make_word("لله"),
        ]
        alignment_engine.process_words(words)

        # Then mismatch
        alignment_engine.process_words([make_word("خطأ")])

        assert alignment_engine.position.consecutive_matches == 0


class TestCompletionDetection:
    """Test suite for completion detection."""

    def test_is_complete_false_initially(self, alignment_engine):
        """Test is_complete returns False initially."""
        assert alignment_engine.is_complete() is False

    def test_is_complete_true_after_all_words(self, alignment_engine, make_word):
        """Test is_complete after processing all words."""
        # We need to get confirmed position to match all words
        # This requires stability (3+ consecutive matches)

        # Process all words
        for token in alignment_engine.expected_tokens:
            words = [make_word(token)]
            alignment_engine.process_words(words)

        # Force confirm position for test
        alignment_engine.position.confirmed_index = len(alignment_engine.expected_tokens)

        assert alignment_engine.is_complete() is True


class TestEngineReset:
    """Test suite for engine reset functionality."""

    def test_reset_clears_position(self, alignment_engine, make_word):
        """Test that reset clears position state."""
        # Make some progress
        words = [make_word("الحمد"), make_word("لله")]
        alignment_engine.process_words(words)

        # Reset
        alignment_engine.reset()

        assert alignment_engine.position.tentative_index == 0
        assert alignment_engine.position.confirmed_index == 0
        assert alignment_engine.position.consecutive_matches == 0

    def test_reset_clears_recent_events(self, alignment_engine, make_word):
        """Test that reset clears recent events."""
        words = [make_word("الحمد")]
        alignment_engine.process_words(words)

        alignment_engine.reset()

        assert len(alignment_engine.recent_events) == 0


class TestHelperMethods:
    """Test suite for helper methods."""

    def test_get_expected_word(self, alignment_engine):
        """Test getting expected word by index."""
        word = alignment_engine.get_expected_word(0)
        assert word is not None

        # Out of bounds
        word = alignment_engine.get_expected_word(1000)
        assert word is None

    def test_get_expected_word_uthmani(self, alignment_engine):
        """Test getting expected word in Uthmani form."""
        word = alignment_engine.get_expected_word_uthmani(0)
        assert word is not None

    def test_get_ayah_for_token(self, alignment_engine):
        """Test getting ayah reference for token index."""
        result = alignment_engine.get_ayah_for_token(0)
        assert result is not None
        surah, ayah = result
        assert surah >= 1
        assert ayah >= 1

    def test_get_progress(self, alignment_engine, make_word):
        """Test getting progress."""
        confirmed, total = alignment_engine.get_progress()
        assert confirmed == 0
        assert total == len(alignment_engine.expected_tokens)

        # Make some progress
        words = [make_word("الحمد")]
        alignment_engine.process_words(words)

        confirmed, total = alignment_engine.get_progress()
        # Confirmed won't advance until stable
        assert total == len(alignment_engine.expected_tokens)
