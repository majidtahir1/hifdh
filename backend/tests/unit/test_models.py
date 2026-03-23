"""
QA-004: Tests for Python dataclass models.

This module tests all models in backend/models/:
- AyahText
- SessionState, ReviewSession
- MistakeType, Mistake
- AlignmentEvent, FeedbackDecision
"""

import pytest
from backend.models import (
    AyahText,
    SessionState,
    ReviewSession,
    MistakeType,
    Mistake,
    AlignmentEvent,
    FeedbackDecision,
)
from backend.models.events import (
    AlignmentEventType,
    FeedbackAction,
    FeedbackConfig,
)


class TestAyahText:
    """Test suite for AyahText dataclass."""

    def test_ayah_text_creation(self):
        """Test basic AyahText creation with valid data."""
        ayah = AyahText(
            surah=1,
            ayah=1,
            juz=1,
            audio_url="https://example.com/audio.mp3",
            text_uthmani="بِسْمِ اللَّهِ",
            text_normalized="بسم الله",
            text_tokens=["بسم", "الله"],
        )
        assert ayah.surah == 1
        assert ayah.ayah == 1
        assert ayah.juz == 1
        assert len(ayah.text_tokens) == 2

    def test_ayah_text_invalid_surah_low(self):
        """Test that surah < 1 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid surah number"):
            AyahText(
                surah=0,
                ayah=1,
                juz=1,
                audio_url="https://example.com/audio.mp3",
                text_uthmani="test",
                text_normalized="test",
                text_tokens=["test"],
            )

    def test_ayah_text_invalid_surah_high(self):
        """Test that surah > 114 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid surah number"):
            AyahText(
                surah=115,
                ayah=1,
                juz=1,
                audio_url="https://example.com/audio.mp3",
                text_uthmani="test",
                text_normalized="test",
                text_tokens=["test"],
            )

    def test_ayah_text_invalid_ayah(self):
        """Test that ayah < 1 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ayah number"):
            AyahText(
                surah=1,
                ayah=0,
                juz=1,
                audio_url="https://example.com/audio.mp3",
                text_uthmani="test",
                text_normalized="test",
                text_tokens=["test"],
            )

    def test_ayah_text_invalid_juz_low(self):
        """Test that juz < 1 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid juz number"):
            AyahText(
                surah=1,
                ayah=1,
                juz=0,
                audio_url="https://example.com/audio.mp3",
                text_uthmani="test",
                text_normalized="test",
                text_tokens=["test"],
            )

    def test_ayah_text_invalid_juz_high(self):
        """Test that juz > 30 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid juz number"):
            AyahText(
                surah=1,
                ayah=1,
                juz=31,
                audio_url="https://example.com/audio.mp3",
                text_uthmani="test",
                text_normalized="test",
                text_tokens=["test"],
            )


class TestSessionState:
    """Test suite for SessionState enum."""

    def test_session_state_values(self):
        """Test all SessionState enum values exist."""
        assert SessionState.WAITING_FOR_PROMPT_PLAYBACK.value == "waiting_for_prompt_playback"
        assert SessionState.RECORDING.value == "recording"
        assert SessionState.ALIGNING.value == "aligning"
        assert SessionState.USER_PAUSED.value == "user_paused"
        assert SessionState.COMPLETE.value == "complete"

    def test_session_state_count(self):
        """Test SessionState has expected number of states."""
        assert len(SessionState) == 5


class TestReviewSession:
    """Test suite for ReviewSession dataclass."""

    def test_review_session_creation(self, sample_ayah, sample_ayahs):
        """Test basic ReviewSession creation."""
        session = ReviewSession(
            id="test-session-123",
            state=SessionState.WAITING_FOR_PROMPT_PLAYBACK,
            juz_range=(1, 2),
            num_ayahs_to_recite=3,
            prompt_ayah=sample_ayah,
            expected_ayahs=sample_ayahs,
            expected_tokens=["الحمد", "لله", "رب", "العالمين"],
        )
        assert session.id == "test-session-123"
        assert session.state == SessionState.WAITING_FOR_PROMPT_PLAYBACK
        assert session.confirmed_word_index == 0
        assert session.tentative_word_index == 0

    def test_review_session_get_current_expected_word(self, sample_ayah, sample_ayahs):
        """Test getting current expected word."""
        session = ReviewSession(
            id="test",
            state=SessionState.RECORDING,
            juz_range=(1, 1),
            num_ayahs_to_recite=3,
            prompt_ayah=sample_ayah,
            expected_ayahs=sample_ayahs,
            expected_tokens=["الحمد", "لله", "رب"],
        )
        assert session.get_current_expected_word() == "الحمد"

        session.tentative_word_index = 1
        assert session.get_current_expected_word() == "لله"

        session.tentative_word_index = 10  # Beyond list
        assert session.get_current_expected_word() is None

    def test_review_session_advance_confirmed_position(self, sample_ayah, sample_ayahs):
        """Test advancing confirmed position."""
        session = ReviewSession(
            id="test",
            state=SessionState.RECORDING,
            juz_range=(1, 1),
            num_ayahs_to_recite=3,
            prompt_ayah=sample_ayah,
            expected_ayahs=sample_ayahs,
            expected_tokens=["الحمد", "لله", "رب"],
        )
        assert session.confirmed_word_index == 0

        session.advance_confirmed_position(2)
        assert session.confirmed_word_index == 2

        # Should not go backwards
        session.advance_confirmed_position(1)
        assert session.confirmed_word_index == 2

    def test_review_session_is_complete(self, sample_ayah, sample_ayahs):
        """Test completion detection."""
        session = ReviewSession(
            id="test",
            state=SessionState.RECORDING,
            juz_range=(1, 1),
            num_ayahs_to_recite=3,
            prompt_ayah=sample_ayah,
            expected_ayahs=sample_ayahs,
            expected_tokens=["الحمد", "لله", "رب"],
        )
        assert not session.is_complete()

        session.confirmed_word_index = 3
        assert session.is_complete()


class TestMistakeType:
    """Test suite for MistakeType enum."""

    def test_mistake_type_values(self):
        """Test all MistakeType enum values exist."""
        expected_types = [
            "wrong_word", "skipped", "added", "repetition",
            "out_of_order", "jumped_ahead", "early_stop",
            "self_corrected", "low_confidence"
        ]
        actual_values = [mt.value for mt in MistakeType]
        for expected in expected_types:
            assert expected in actual_values, f"Missing MistakeType: {expected}"


class TestMistake:
    """Test suite for Mistake dataclass."""

    def test_mistake_creation(self):
        """Test basic Mistake creation."""
        mistake = Mistake(
            mistake_type=MistakeType.WRONG_WORD,
            ayah=(1, 2),
            word_index=0,
            expected="الحمد",
            received="الحامد",
            confidence=0.85,
            is_penalty=True,
            timestamp_ms=1000,
        )
        assert mistake.mistake_type == MistakeType.WRONG_WORD
        assert mistake.ayah == (1, 2)
        assert mistake.is_penalty is True

    def test_mistake_invalid_confidence_low(self):
        """Test that confidence < 0 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            Mistake(
                mistake_type=MistakeType.WRONG_WORD,
                ayah=(1, 2),
                word_index=0,
                expected="test",
                received="test2",
                confidence=-0.1,
                is_penalty=True,
                timestamp_ms=1000,
            )

    def test_mistake_invalid_confidence_high(self):
        """Test that confidence > 1 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            Mistake(
                mistake_type=MistakeType.WRONG_WORD,
                ayah=(1, 2),
                word_index=0,
                expected="test",
                received="test2",
                confidence=1.5,
                is_penalty=True,
                timestamp_ms=1000,
            )

    def test_mistake_invalid_word_index(self):
        """Test that negative word_index raises ValueError."""
        with pytest.raises(ValueError, match="Word index must be non-negative"):
            Mistake(
                mistake_type=MistakeType.WRONG_WORD,
                ayah=(1, 2),
                word_index=-1,
                expected="test",
                received="test2",
                confidence=0.9,
                is_penalty=True,
                timestamp_ms=1000,
            )

    def test_mistake_is_self_corrected(self):
        """Test is_self_corrected method."""
        mistake = Mistake(
            mistake_type=MistakeType.SELF_CORRECTED,
            ayah=(1, 2),
            word_index=0,
            expected="test",
            received="test2",
            confidence=0.9,
            is_penalty=False,
            timestamp_ms=1000,
        )
        assert mistake.is_self_corrected() is True

        mistake.mistake_type = MistakeType.WRONG_WORD
        assert mistake.is_self_corrected() is False

    def test_mistake_should_display_immediately(self):
        """Test should_display_immediately method."""
        # Regular mistake with penalty - should display
        mistake = Mistake(
            mistake_type=MistakeType.WRONG_WORD,
            ayah=(1, 2),
            word_index=0,
            expected="test",
            received="test2",
            confidence=0.9,
            is_penalty=True,
            timestamp_ms=1000,
        )
        assert mistake.should_display_immediately() is True

        # Self-corrected - should not display
        mistake.mistake_type = MistakeType.SELF_CORRECTED
        mistake.is_penalty = False
        assert mistake.should_display_immediately() is False

        # Low confidence - should not display
        mistake.mistake_type = MistakeType.LOW_CONFIDENCE
        assert mistake.should_display_immediately() is False


class TestAlignmentEvent:
    """Test suite for AlignmentEvent dataclass."""

    def test_alignment_event_creation(self):
        """Test basic AlignmentEvent creation."""
        event = AlignmentEvent(
            event_type=AlignmentEventType.MATCH,
            word_index=0,
            received_word="الحمد",
            confidence=0.95,
            timestamp_ms=1000,
        )
        assert event.event_type == AlignmentEventType.MATCH
        assert event.confidence == 0.95

    def test_alignment_event_invalid_confidence(self):
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            AlignmentEvent(
                event_type=AlignmentEventType.MATCH,
                word_index=0,
                received_word="test",
                confidence=1.5,
            )

    def test_alignment_event_is_correct(self):
        """Test is_correct method."""
        event = AlignmentEvent(
            event_type=AlignmentEventType.MATCH,
            word_index=0,
            received_word="test",
            confidence=0.9,
        )
        assert event.is_correct() is True

        event.event_type = AlignmentEventType.MISMATCH
        assert event.is_correct() is False

    def test_alignment_event_is_error(self):
        """Test is_error method."""
        event = AlignmentEvent(
            event_type=AlignmentEventType.MISMATCH,
            word_index=0,
            received_word="test",
            confidence=0.9,
        )
        assert event.is_error() is True

        event.event_type = AlignmentEventType.SKIPPED
        assert event.is_error() is True

        event.event_type = AlignmentEventType.MATCH
        assert event.is_error() is False


class TestFeedbackDecision:
    """Test suite for FeedbackDecision dataclass."""

    def test_feedback_decision_creation(self):
        """Test basic FeedbackDecision creation."""
        event = AlignmentEvent(
            event_type=AlignmentEventType.MATCH,
            word_index=0,
            received_word="test",
            confidence=0.9,
        )
        decision = FeedbackDecision(
            action=FeedbackAction.CONFIRM_CORRECT,
            event=event,
            reason="Word matches expected",
        )
        assert decision.action == FeedbackAction.CONFIRM_CORRECT
        assert decision.reason == "Word matches expected"

    def test_feedback_decision_should_emit_to_client(self):
        """Test should_emit_to_client method."""
        event = AlignmentEvent(
            event_type=AlignmentEventType.MATCH,
            word_index=0,
            received_word="test",
            confidence=0.9,
        )

        # CONFIRM_CORRECT should emit
        decision = FeedbackDecision(
            action=FeedbackAction.CONFIRM_CORRECT,
            event=event,
        )
        assert decision.should_emit_to_client() is True

        # EMIT_MISTAKE should emit
        decision.action = FeedbackAction.EMIT_MISTAKE
        assert decision.should_emit_to_client() is True

        # HOLD should not emit
        decision.action = FeedbackAction.HOLD
        assert decision.should_emit_to_client() is False

    def test_feedback_decision_is_holding(self):
        """Test is_holding method."""
        event = AlignmentEvent(
            event_type=AlignmentEventType.MISMATCH,
            word_index=0,
            received_word="test",
            confidence=0.9,
        )
        decision = FeedbackDecision(
            action=FeedbackAction.HOLD,
            event=event,
        )
        assert decision.is_holding() is True

        decision.action = FeedbackAction.EMIT_MISTAKE
        assert decision.is_holding() is False


class TestFeedbackConfig:
    """Test suite for FeedbackConfig dataclass."""

    def test_feedback_config_defaults(self):
        """Test FeedbackConfig default values."""
        config = FeedbackConfig()
        assert config.mode == "gentle"
        assert config.min_confidence == 0.7
        assert config.require_persistence is True
        assert config.persistence_windows == 2
        assert config.self_correction_window_ms == 2000

    def test_feedback_config_invalid_min_confidence(self):
        """Test that invalid min_confidence raises ValueError."""
        with pytest.raises(ValueError, match="min_confidence must be between"):
            FeedbackConfig(min_confidence=-0.1)

        with pytest.raises(ValueError, match="min_confidence must be between"):
            FeedbackConfig(min_confidence=1.5)

    def test_feedback_config_invalid_persistence_windows(self):
        """Test that invalid persistence_windows raises ValueError."""
        with pytest.raises(ValueError, match="persistence_windows must be at least"):
            FeedbackConfig(persistence_windows=0)

    def test_feedback_config_invalid_self_correction_window(self):
        """Test that invalid self_correction_window_ms raises ValueError."""
        with pytest.raises(ValueError, match="self_correction_window_ms must be non-negative"):
            FeedbackConfig(self_correction_window_ms=-100)
