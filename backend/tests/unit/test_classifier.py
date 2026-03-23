"""
QA-008: Tests for Mistake Classifier.

This module tests the mistake detection logic in backend/alignment/classifier.py:
- Mismatch classification
- Skip classification
- Repetition handling
- Self-correction detection
- Severity levels
"""

import pytest
from backend.alignment.classifier import MistakeClassifier, Severity, ClassifiedMistake
from backend.models.events import AlignmentEvent, AlignmentEventType
from backend.models.mistake import Mistake, MistakeType


class TestMistakeClassifierInitialization:
    """Test suite for MistakeClassifier initialization."""

    def test_classifier_creation(self):
        """Test basic classifier creation."""
        classifier = MistakeClassifier()
        assert classifier is not None

    def test_classifier_default_values(self):
        """Test classifier default configuration values."""
        classifier = MistakeClassifier()
        assert classifier.min_confidence == 0.7
        assert classifier.self_correction_window_ms == 2000
        assert classifier.jump_threshold == 3

    def test_classifier_custom_values(self):
        """Test classifier with custom configuration."""
        classifier = MistakeClassifier(
            min_confidence=0.8,
            self_correction_window_ms=3000,
            jump_threshold=5,
        )
        assert classifier.min_confidence == 0.8
        assert classifier.self_correction_window_ms == 3000
        assert classifier.jump_threshold == 5


class TestMismatchClassification:
    """Test suite for mismatch event classification."""

    def test_classify_mismatch_high_confidence(self, classifier: MistakeClassifier):
        """Test classifying high-confidence mismatch as WRONG_WORD."""
        events = [
            AlignmentEvent(
                event_type=AlignmentEventType.MISMATCH,
                word_index=0,
                received_word="خطأ",
                confidence=0.9,
                timestamp_ms=1000,
            )
        ]

        # Mock lookup functions
        def ayah_lookup(idx):
            return (1, 2)

        def uthmani_lookup(idx):
            return "الحمد"

        mistakes = classifier.classify(events, ayah_lookup, uthmani_lookup)

        assert len(mistakes) == 1
        assert mistakes[0].mistake_type == MistakeType.WRONG_WORD
        assert mistakes[0].is_penalty is True
        assert mistakes[0].expected == "الحمد"
        assert mistakes[0].received == "خطأ"

    def test_classify_mismatch_low_confidence(self, classifier: MistakeClassifier):
        """Test classifying low-confidence mismatch as LOW_CONFIDENCE."""
        events = [
            AlignmentEvent(
                event_type=AlignmentEventType.MISMATCH,
                word_index=0,
                received_word="كلمة",
                confidence=0.5,  # Below min_confidence
                timestamp_ms=1000,
            )
        ]

        mistakes = classifier.classify(events)

        assert len(mistakes) == 1
        assert mistakes[0].mistake_type == MistakeType.LOW_CONFIDENCE
        assert mistakes[0].is_penalty is False  # No penalty for low confidence


class TestSkipClassification:
    """Test suite for skip event classification."""

    def test_classify_single_skip(self, classifier: MistakeClassifier):
        """Test classifying single skip as SKIPPED."""
        events = [
            AlignmentEvent(
                event_type=AlignmentEventType.SKIPPED,
                word_index=0,
                received_word=None,
                confidence=0.0,
                timestamp_ms=1000,
            ),
            AlignmentEvent(
                event_type=AlignmentEventType.MATCH,
                word_index=1,
                received_word="لله",
                confidence=0.95,
                timestamp_ms=1100,
            ),
        ]

        mistakes = classifier.classify(events)

        # Should have one SKIPPED mistake
        skip_mistakes = [m for m in mistakes if m.mistake_type == MistakeType.SKIPPED]
        assert len(skip_mistakes) == 1
        assert skip_mistakes[0].is_penalty is True

    def test_classify_multiple_skips_as_jump(self, classifier: MistakeClassifier):
        """Test classifying multiple skips as JUMPED_AHEAD."""
        # Create 3+ consecutive skips (default threshold)
        events = [
            AlignmentEvent(
                event_type=AlignmentEventType.SKIPPED,
                word_index=0,
                received_word=None,
                confidence=0.0,
                timestamp_ms=1000,
            ),
            AlignmentEvent(
                event_type=AlignmentEventType.SKIPPED,
                word_index=1,
                received_word=None,
                confidence=0.0,
                timestamp_ms=1000,
            ),
            AlignmentEvent(
                event_type=AlignmentEventType.SKIPPED,
                word_index=2,
                received_word=None,
                confidence=0.0,
                timestamp_ms=1000,
            ),
            AlignmentEvent(
                event_type=AlignmentEventType.MATCH,
                word_index=3,
                received_word="العالمين",
                confidence=0.95,
                timestamp_ms=1100,
            ),
        ]

        mistakes = classifier.classify(events)

        # Should have one JUMPED_AHEAD mistake
        jump_mistakes = [m for m in mistakes if m.mistake_type == MistakeType.JUMPED_AHEAD]
        assert len(jump_mistakes) == 1
        assert jump_mistakes[0].is_penalty is True


class TestRepetitionClassification:
    """Test suite for repetition event classification."""

    def test_classify_repetition(self, classifier: MistakeClassifier):
        """Test classifying repetition as REPETITION (no penalty)."""
        events = [
            AlignmentEvent(
                event_type=AlignmentEventType.REPETITION,
                word_index=0,
                received_word="الحمد",
                confidence=0.9,
                timestamp_ms=1000,
            )
        ]

        def uthmani_lookup(idx):
            return "الحمد"

        def ayah_lookup(idx):
            return (1, 2)

        mistakes = classifier.classify(events, ayah_lookup, uthmani_lookup)

        assert len(mistakes) == 1
        assert mistakes[0].mistake_type == MistakeType.REPETITION
        assert mistakes[0].is_penalty is False  # Repetitions are not penalized


class TestInsertionClassification:
    """Test suite for insertion event classification."""

    def test_classify_insertion(self, classifier: MistakeClassifier):
        """Test classifying insertion as ADDED."""
        events = [
            AlignmentEvent(
                event_type=AlignmentEventType.INSERTION,
                word_index=None,
                received_word="كلمة",
                confidence=0.85,
                timestamp_ms=1000,
            )
        ]

        mistakes = classifier.classify(events)

        assert len(mistakes) == 1
        assert mistakes[0].mistake_type == MistakeType.ADDED
        assert mistakes[0].is_penalty is True
        assert mistakes[0].word_index == -1  # No position in expected


class TestSelfCorrectionDetection:
    """Test suite for self-correction detection."""

    def test_self_correction_within_window(self, classifier: MistakeClassifier):
        """Test self-correction detected within time window."""
        # Mismatch followed by match at same position
        events = [
            AlignmentEvent(
                event_type=AlignmentEventType.MISMATCH,
                word_index=0,
                received_word="خطأ",
                confidence=0.8,
                timestamp_ms=1000,
            ),
            AlignmentEvent(
                event_type=AlignmentEventType.MATCH,
                word_index=0,
                received_word="الحمد",
                confidence=0.95,
                timestamp_ms=1500,  # Within 2000ms window
            ),
        ]

        mistakes = classifier.classify(events)

        # The mismatch should be converted to SELF_CORRECTED
        self_corrected = [m for m in mistakes if m.mistake_type == MistakeType.SELF_CORRECTED]
        assert len(self_corrected) == 1
        assert self_corrected[0].is_penalty is False


class TestSeverityLevels:
    """Test suite for severity level assignment."""

    def test_severity_wrong_word(self, classifier: MistakeClassifier):
        """Test WRONG_WORD has HIGH severity."""
        mistake = Mistake(
            mistake_type=MistakeType.WRONG_WORD,
            ayah=(1, 2),
            word_index=0,
            expected="الحمد",
            received="خطأ",
            confidence=0.9,
            is_penalty=True,
            timestamp_ms=1000,
        )
        severity = classifier.get_severity(mistake)
        assert severity == Severity.HIGH

    def test_severity_skipped(self, classifier: MistakeClassifier):
        """Test SKIPPED has MEDIUM severity."""
        mistake = Mistake(
            mistake_type=MistakeType.SKIPPED,
            ayah=(1, 2),
            word_index=0,
            expected="الحمد",
            received=None,
            confidence=1.0,
            is_penalty=True,
            timestamp_ms=1000,
        )
        severity = classifier.get_severity(mistake)
        assert severity == Severity.MEDIUM

    def test_severity_repetition(self, classifier: MistakeClassifier):
        """Test REPETITION has LOW severity."""
        mistake = Mistake(
            mistake_type=MistakeType.REPETITION,
            ayah=(1, 2),
            word_index=0,
            expected="الحمد",
            received="الحمد",
            confidence=0.9,
            is_penalty=False,
            timestamp_ms=1000,
        )
        severity = classifier.get_severity(mistake)
        assert severity == Severity.LOW

    def test_severity_jumped_ahead(self, classifier: MistakeClassifier):
        """Test JUMPED_AHEAD has HIGH severity."""
        mistake = Mistake(
            mistake_type=MistakeType.JUMPED_AHEAD,
            ayah=(1, 2),
            word_index=0,
            expected="[3 words skipped]",
            received=None,
            confidence=1.0,
            is_penalty=True,
            timestamp_ms=1000,
        )
        severity = classifier.get_severity(mistake)
        assert severity == Severity.HIGH

    def test_severity_self_corrected(self, classifier: MistakeClassifier):
        """Test SELF_CORRECTED has LOW severity."""
        mistake = Mistake(
            mistake_type=MistakeType.SELF_CORRECTED,
            ayah=(1, 2),
            word_index=0,
            expected="الحمد",
            received="خطأ",
            confidence=0.9,
            is_penalty=False,
            timestamp_ms=1000,
        )
        severity = classifier.get_severity(mistake)
        assert severity == Severity.LOW

    def test_severity_low_confidence(self, classifier: MistakeClassifier):
        """Test LOW_CONFIDENCE has LOW severity."""
        mistake = Mistake(
            mistake_type=MistakeType.LOW_CONFIDENCE,
            ayah=(1, 2),
            word_index=0,
            expected="الحمد",
            received="كلمة",
            confidence=0.5,
            is_penalty=False,
            timestamp_ms=1000,
        )
        severity = classifier.get_severity(mistake)
        assert severity == Severity.LOW


class TestEarlyStopMistake:
    """Test suite for early stop mistake creation."""

    def test_create_early_stop_mistake(self, classifier: MistakeClassifier):
        """Test creating early stop mistake."""
        def ayah_lookup(idx):
            return (1, 5)

        def uthmani_lookup(idx):
            return "كلمة"

        mistake = classifier.create_early_stop_mistake(
            word_index=10,
            ayah_lookup=ayah_lookup,
            uthmani_lookup=uthmani_lookup,
        )

        assert mistake.mistake_type == MistakeType.EARLY_STOP
        assert mistake.is_penalty is True
        assert mistake.ayah == (1, 5)
        assert mistake.word_index == 10

    def test_early_stop_severity(self, classifier: MistakeClassifier):
        """Test EARLY_STOP has HIGH severity."""
        mistake = Mistake(
            mistake_type=MistakeType.EARLY_STOP,
            ayah=(1, 5),
            word_index=10,
            expected="[continued]",
            received=None,
            confidence=1.0,
            is_penalty=True,
            timestamp_ms=1000,
        )
        severity = classifier.get_severity(mistake)
        assert severity == Severity.HIGH


class TestClassifierReset:
    """Test suite for classifier reset functionality."""

    def test_reset_clears_state(self, classifier: MistakeClassifier):
        """Test that reset clears internal state."""
        # Add some events
        events = [
            AlignmentEvent(
                event_type=AlignmentEventType.MISMATCH,
                word_index=0,
                received_word="خطأ",
                confidence=0.9,
                timestamp_ms=1000,
            )
        ]
        classifier.classify(events)

        # Reset
        classifier.reset()

        assert len(classifier.recent_events) == 0
        assert len(classifier.pending_mistakes) == 0


class TestClassifiedMistake:
    """Test suite for ClassifiedMistake dataclass."""

    def test_classified_mistake_creation(self, sample_mistake):
        """Test ClassifiedMistake creation."""
        classified = ClassifiedMistake(
            mistake=sample_mistake,
            severity=Severity.HIGH,
            is_recoverable=True,
        )
        assert classified.mistake == sample_mistake
        assert classified.severity == Severity.HIGH
        assert classified.is_recoverable is True

    def test_classified_mistake_defaults(self, sample_mistake):
        """Test ClassifiedMistake default values."""
        classified = ClassifiedMistake(
            mistake=sample_mistake,
            severity=Severity.MEDIUM,
        )
        assert classified.is_recoverable is True  # Default


class TestComplexScenarios:
    """Test suite for complex classification scenarios."""

    def test_mixed_events(self, classifier: MistakeClassifier):
        """Test classifying a mix of different events."""
        events = [
            # Match
            AlignmentEvent(
                event_type=AlignmentEventType.MATCH,
                word_index=0,
                received_word="الحمد",
                confidence=0.95,
                timestamp_ms=1000,
            ),
            # Mismatch
            AlignmentEvent(
                event_type=AlignmentEventType.MISMATCH,
                word_index=1,
                received_word="خطأ",
                confidence=0.85,
                timestamp_ms=2000,
            ),
            # Skip
            AlignmentEvent(
                event_type=AlignmentEventType.SKIPPED,
                word_index=2,
                received_word=None,
                confidence=0.0,
                timestamp_ms=3000,
            ),
            # Match
            AlignmentEvent(
                event_type=AlignmentEventType.MATCH,
                word_index=3,
                received_word="العالمين",
                confidence=0.9,
                timestamp_ms=3100,
            ),
        ]

        def ayah_lookup(idx):
            return (1, 2)

        def uthmani_lookup(idx):
            return f"word{idx}"

        mistakes = classifier.classify(events, ayah_lookup, uthmani_lookup)

        # Should have a WRONG_WORD and a SKIPPED mistake
        types = [m.mistake_type for m in mistakes]
        assert MistakeType.WRONG_WORD in types
        assert MistakeType.SKIPPED in types

    def test_match_only_no_mistakes(self, classifier: MistakeClassifier):
        """Test that match-only events produce no mistakes."""
        events = [
            AlignmentEvent(
                event_type=AlignmentEventType.MATCH,
                word_index=0,
                received_word="الحمد",
                confidence=0.95,
                timestamp_ms=1000,
            ),
            AlignmentEvent(
                event_type=AlignmentEventType.MATCH,
                word_index=1,
                received_word="لله",
                confidence=0.92,
                timestamp_ms=2000,
            ),
        ]

        mistakes = classifier.classify(events)
        assert len(mistakes) == 0
