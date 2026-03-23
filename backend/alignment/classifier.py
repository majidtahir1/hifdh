"""
Mistake Classifier for the Hifdh Review App.

This module classifies alignment events into mistake types with
appropriate severity levels. It also handles detection of patterns
like self-corrections and jumped sequences.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
import time

from models.events import AlignmentEvent, AlignmentEventType
from models.mistake import Mistake, MistakeType


class Severity(Enum):
    """Severity levels for mistakes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ClassifiedMistake:
    """
    A mistake with additional classification metadata.

    Extends the base Mistake with severity and other classifier-specific info.
    """
    mistake: Mistake
    severity: Severity
    is_recoverable: bool = True  # Can be recovered by self-correction


class MistakeClassifier:
    """
    Classifies alignment events into mistake types.

    This classifier takes raw alignment events from the engine and
    categorizes them into specific mistake types with severity levels.
    It also detects patterns like self-corrections by analyzing
    sequences of events.

    Mistake types and their severity:
    - WRONG_WORD: High - said different word
    - SKIPPED: Medium - missed a word (Low if just 1 word)
    - REPETITION: Low - repeated a phrase (not a penalty)
    - OUT_OF_ORDER: High - words in wrong sequence
    - JUMPED_AHEAD: Medium/High - skipped multiple words
    - SELF_CORRECTED: Low - made mistake but fixed it (no penalty)
    - EARLY_STOP: High - stopped before expected end
    - LOW_CONFIDENCE: Low - ASR uncertain (no penalty)
    """

    # Minimum ASR confidence to consider a detection reliable
    MIN_RELIABLE_CONFIDENCE = 0.7

    # Number of consecutive skips that constitute a "jump"
    JUMP_THRESHOLD = 3

    # Time window for self-correction detection (ms)
    SELF_CORRECTION_WINDOW_MS = 2000

    def __init__(
        self,
        min_confidence: float = MIN_RELIABLE_CONFIDENCE,
        self_correction_window_ms: int = SELF_CORRECTION_WINDOW_MS,
        jump_threshold: int = JUMP_THRESHOLD,
    ):
        """
        Initialize the classifier.

        Args:
            min_confidence: Minimum ASR confidence for reliable detection
            self_correction_window_ms: Time window for self-correction
            jump_threshold: Number of skips that constitute a jump
        """
        self.min_confidence = min_confidence
        self.self_correction_window_ms = self_correction_window_ms
        self.jump_threshold = jump_threshold

        # Track recent events for pattern detection
        self.recent_events: List[AlignmentEvent] = []
        self.max_recent_events = 50

        # Track pending mistakes that might be self-corrected
        self.pending_mistakes: List[Tuple[Mistake, int]] = []  # (mistake, timestamp)

    def classify(
        self,
        events: List[AlignmentEvent],
        ayah_lookup: Optional[callable] = None,
        uthmani_lookup: Optional[callable] = None,
    ) -> List[Mistake]:
        """
        Classify alignment events into mistakes.

        Args:
            events: List of alignment events to classify
            ayah_lookup: Function to get (surah, ayah) for token index
            uthmani_lookup: Function to get Uthmani text for token index

        Returns:
            List of classified mistakes
        """
        mistakes: List[Mistake] = []
        current_time = int(time.time() * 1000)

        # Track consecutive skips for jump detection
        consecutive_skips: List[AlignmentEvent] = []

        for event in events:
            self._track_event(event)

            # Check for self-corrections of pending mistakes
            if event.event_type == AlignmentEventType.MATCH:
                self._check_self_corrections(event, current_time, mistakes)
                consecutive_skips = []  # Reset skip counter
                continue

            if event.event_type == AlignmentEventType.SKIPPED:
                consecutive_skips.append(event)
                # Don't emit mistake yet - might be part of a jump
                continue

            if event.event_type == AlignmentEventType.MISMATCH:
                # Process any pending skips first
                if consecutive_skips:
                    skip_mistakes = self._process_skips(
                        consecutive_skips, ayah_lookup, uthmani_lookup
                    )
                    mistakes.extend(skip_mistakes)
                    consecutive_skips = []

                # Create mismatch mistake
                mistake = self._create_mismatch_mistake(
                    event, ayah_lookup, uthmani_lookup
                )
                if mistake:
                    # Add to pending for possible self-correction
                    self.pending_mistakes.append((mistake, event.timestamp_ms))
                    mistakes.append(mistake)

            elif event.event_type == AlignmentEventType.REPETITION:
                # Repetitions are not mistakes, but we track them
                mistake = self._create_repetition_record(
                    event, ayah_lookup, uthmani_lookup
                )
                if mistake:
                    mistakes.append(mistake)

            elif event.event_type == AlignmentEventType.INSERTION:
                # Extra words not in expected text
                mistake = self._create_insertion_mistake(event)
                if mistake:
                    mistakes.append(mistake)

        # Process any remaining skips
        if consecutive_skips:
            skip_mistakes = self._process_skips(
                consecutive_skips, ayah_lookup, uthmani_lookup
            )
            mistakes.extend(skip_mistakes)

        # Clean up old pending mistakes
        self._cleanup_pending(current_time)

        return mistakes

    def _create_mismatch_mistake(
        self,
        event: AlignmentEvent,
        ayah_lookup: Optional[callable],
        uthmani_lookup: Optional[callable],
    ) -> Optional[Mistake]:
        """
        Create a WRONG_WORD mistake from a mismatch event.

        Args:
            event: The mismatch event
            ayah_lookup: Function to get (surah, ayah) for token index
            uthmani_lookup: Function to get Uthmani text for token index

        Returns:
            Mistake object, or None if low confidence
        """
        # Check if confidence is too low
        if event.confidence < self.min_confidence:
            return Mistake(
                mistake_type=MistakeType.LOW_CONFIDENCE,
                ayah=self._get_ayah(event.word_index, ayah_lookup),
                word_index=event.word_index or 0,
                expected=self._get_uthmani(event.word_index, uthmani_lookup) or "",
                received=event.received_word,
                confidence=event.confidence,
                is_penalty=False,  # Low confidence = no penalty
                timestamp_ms=event.timestamp_ms,
            )

        return Mistake(
            mistake_type=MistakeType.WRONG_WORD,
            ayah=self._get_ayah(event.word_index, ayah_lookup),
            word_index=event.word_index or 0,
            expected=self._get_uthmani(event.word_index, uthmani_lookup) or "",
            received=event.received_word,
            confidence=event.confidence,
            is_penalty=True,
            timestamp_ms=event.timestamp_ms,
        )

    def _process_skips(
        self,
        skip_events: List[AlignmentEvent],
        ayah_lookup: Optional[callable],
        uthmani_lookup: Optional[callable],
    ) -> List[Mistake]:
        """
        Process consecutive skip events.

        If there are many skips, classify as JUMPED_AHEAD.
        Otherwise, classify individual SKIPPED mistakes.

        Args:
            skip_events: List of skip events
            ayah_lookup: Function to get (surah, ayah) for token index
            uthmani_lookup: Function to get Uthmani text for token index

        Returns:
            List of skip/jump mistakes
        """
        mistakes: List[Mistake] = []

        if len(skip_events) >= self.jump_threshold:
            # This is a jump - create single JUMPED_AHEAD mistake
            first_event = skip_events[0]
            last_event = skip_events[-1]

            mistake = Mistake(
                mistake_type=MistakeType.JUMPED_AHEAD,
                ayah=self._get_ayah(first_event.word_index, ayah_lookup),
                word_index=first_event.word_index or 0,
                expected=f"[{len(skip_events)} words skipped]",
                received=None,
                confidence=1.0,  # High confidence in skip detection
                is_penalty=True,
                timestamp_ms=first_event.timestamp_ms,
            )
            mistakes.append(mistake)

        else:
            # Individual skips
            for event in skip_events:
                mistake = Mistake(
                    mistake_type=MistakeType.SKIPPED,
                    ayah=self._get_ayah(event.word_index, ayah_lookup),
                    word_index=event.word_index or 0,
                    expected=self._get_uthmani(event.word_index, uthmani_lookup) or "",
                    received=None,
                    confidence=1.0,
                    is_penalty=True,
                    timestamp_ms=event.timestamp_ms,
                )
                mistakes.append(mistake)

        return mistakes

    def _create_repetition_record(
        self,
        event: AlignmentEvent,
        ayah_lookup: Optional[callable],
        uthmani_lookup: Optional[callable],
    ) -> Optional[Mistake]:
        """
        Create a REPETITION record (not a penalty).

        Args:
            event: The repetition event
            ayah_lookup: Function to get (surah, ayah) for token index
            uthmani_lookup: Function to get Uthmani text for token index

        Returns:
            Mistake object with is_penalty=False
        """
        return Mistake(
            mistake_type=MistakeType.REPETITION,
            ayah=self._get_ayah(event.word_index, ayah_lookup),
            word_index=event.word_index or 0,
            expected=self._get_uthmani(event.word_index, uthmani_lookup) or "",
            received=event.received_word,
            confidence=event.confidence,
            is_penalty=False,  # Repetitions are not penalized
            timestamp_ms=event.timestamp_ms,
        )

    def _create_insertion_mistake(self, event: AlignmentEvent) -> Optional[Mistake]:
        """
        Create an ADDED mistake for inserted words.

        Args:
            event: The insertion event

        Returns:
            Mistake object
        """
        return Mistake(
            mistake_type=MistakeType.ADDED,
            ayah=(0, 0),  # No specific ayah for insertions
            word_index=-1,  # No position in expected
            expected="",
            received=event.received_word,
            confidence=event.confidence,
            is_penalty=True,
            timestamp_ms=event.timestamp_ms,
        )

    def _check_self_corrections(
        self,
        match_event: AlignmentEvent,
        current_time: int,
        mistakes: List[Mistake],
    ) -> None:
        """
        Check if a match event represents a self-correction.

        If a previous mismatch at the same position is now matched,
        and it's within the correction window, mark it as self-corrected.

        Args:
            match_event: The match event
            current_time: Current timestamp
            mistakes: List of mistakes to potentially update
        """
        new_pending: List[Tuple[Mistake, int]] = []

        for mistake, timestamp in self.pending_mistakes:
            time_diff = match_event.timestamp_ms - timestamp

            # Check if this match corrects a pending mistake
            if (
                mistake.word_index == match_event.word_index
                and time_diff <= self.self_correction_window_ms
            ):
                # This is a self-correction
                # Find and update the mistake in the list
                for i, m in enumerate(mistakes):
                    if (
                        m.word_index == mistake.word_index
                        and m.timestamp_ms == mistake.timestamp_ms
                    ):
                        # Replace with self-corrected version
                        mistakes[i] = Mistake(
                            mistake_type=MistakeType.SELF_CORRECTED,
                            ayah=mistake.ayah,
                            word_index=mistake.word_index,
                            expected=mistake.expected,
                            received=mistake.received,
                            confidence=mistake.confidence,
                            is_penalty=False,  # No penalty for self-correction
                            timestamp_ms=mistake.timestamp_ms,
                        )
                        break
            else:
                # Keep in pending if not corrected yet
                new_pending.append((mistake, timestamp))

        self.pending_mistakes = new_pending

    def _cleanup_pending(self, current_time: int) -> None:
        """
        Remove old pending mistakes that are past the correction window.

        Args:
            current_time: Current timestamp
        """
        self.pending_mistakes = [
            (m, t) for m, t in self.pending_mistakes
            if current_time - t <= self.self_correction_window_ms
        ]

    def _track_event(self, event: AlignmentEvent) -> None:
        """
        Track an event for pattern detection.

        Args:
            event: Event to track
        """
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events.pop(0)

    def _get_ayah(
        self,
        word_index: Optional[int],
        ayah_lookup: Optional[callable],
    ) -> Tuple[int, int]:
        """
        Get (surah, ayah) for a word index.

        Args:
            word_index: Index in expected tokens
            ayah_lookup: Function to get ayah info

        Returns:
            Tuple of (surah, ayah), or (0, 0) if unknown
        """
        if word_index is None or ayah_lookup is None:
            return (0, 0)
        result = ayah_lookup(word_index)
        return result if result else (0, 0)

    def _get_uthmani(
        self,
        word_index: Optional[int],
        uthmani_lookup: Optional[callable],
    ) -> Optional[str]:
        """
        Get Uthmani text for a word index.

        Args:
            word_index: Index in expected tokens
            uthmani_lookup: Function to get Uthmani text

        Returns:
            Uthmani text, or None if unknown
        """
        if word_index is None or uthmani_lookup is None:
            return None
        return uthmani_lookup(word_index)

    def get_severity(self, mistake: Mistake) -> Severity:
        """
        Get the severity level for a mistake.

        Args:
            mistake: The mistake to evaluate

        Returns:
            Severity level
        """
        severity_map = {
            MistakeType.WRONG_WORD: Severity.HIGH,
            MistakeType.SKIPPED: Severity.MEDIUM,
            MistakeType.ADDED: Severity.MEDIUM,
            MistakeType.REPETITION: Severity.LOW,
            MistakeType.OUT_OF_ORDER: Severity.HIGH,
            MistakeType.JUMPED_AHEAD: Severity.HIGH,
            MistakeType.EARLY_STOP: Severity.HIGH,
            MistakeType.SELF_CORRECTED: Severity.LOW,
            MistakeType.LOW_CONFIDENCE: Severity.LOW,
        }
        return severity_map.get(mistake.mistake_type, Severity.MEDIUM)

    def create_early_stop_mistake(
        self,
        word_index: int,
        ayah_lookup: Optional[callable] = None,
        uthmani_lookup: Optional[callable] = None,
    ) -> Mistake:
        """
        Create an EARLY_STOP mistake when recitation ends prematurely.

        Args:
            word_index: Index where recitation stopped
            ayah_lookup: Function to get (surah, ayah) for token index
            uthmani_lookup: Function to get Uthmani text for token index

        Returns:
            EARLY_STOP mistake
        """
        return Mistake(
            mistake_type=MistakeType.EARLY_STOP,
            ayah=self._get_ayah(word_index, ayah_lookup),
            word_index=word_index,
            expected=self._get_uthmani(word_index, uthmani_lookup) or "[continued]",
            received=None,
            confidence=1.0,
            is_penalty=True,
            timestamp_ms=int(time.time() * 1000),
        )

    def reset(self) -> None:
        """Reset the classifier state."""
        self.recent_events = []
        self.pending_mistakes = []
