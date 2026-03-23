"""
Continuation Alignment Engine for the Hifdh Review App.

This is the CORE component that tracks where the student is in the expected
text and detects mistakes. It handles the messy reality of recitation:
- Hesitations and pauses
- Self-corrections
- Repetitions
- Chunk boundary artifacts
- Jumps forward/backward

The engine maintains both confirmed and tentative positions, only committing
to alignment decisions when confidence is high enough.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import time

from models.events import AlignmentEvent, AlignmentEventType
from models.quran import AyahText
from alignment.normalizer import ArabicTextNormalizer


@dataclass
class TranscribedWord:
    """
    Represents a word from the ASR transcription.

    Attributes:
        text: The transcribed word text
        confidence: ASR confidence score (0.0 to 1.0)
        timestamp_ms: When the word was detected
        is_final: Whether this is from a finalized transcription segment
    """
    text: str
    confidence: float
    timestamp_ms: int
    is_final: bool = False


@dataclass
class PositionState:
    """
    Tracks the current position in the expected text.

    Maintains both confirmed (high confidence) and tentative (best guess)
    positions to handle uncertain alignments gracefully.
    """
    # Confirmed position - we're certain about alignment up to here
    confirmed_index: int = 0
    # Tentative position - current best guess
    tentative_index: int = 0
    # Last position where we had high confidence alignment
    last_stable_index: int = 0
    # Number of consecutive matches (for stability detection)
    consecutive_matches: int = 0


class ContinuationAlignmentEngine:
    """
    Tracks position in expected text and aligns transcribed words.

    This engine is the heart of the Hifdh Review App. It processes
    streaming transcription output and determines:
    - Where the student currently is in the expected continuation
    - Whether words match, mismatch, were skipped, or repeated
    - When to commit tentative alignments as confirmed

    The algorithm uses a sliding window approach with look-ahead matching
    to handle common recitation patterns like repetitions and self-corrections.
    """

    # Number of words to look ahead when searching for matches
    DEFAULT_LOOK_AHEAD = 5
    # Number of words to look behind for repetition detection (increased for restart after pause)
    DEFAULT_LOOK_BEHIND = 10
    # Number of consecutive matches needed for stability (set to 1 for immediate feedback)
    STABILITY_THRESHOLD = 1

    def __init__(
        self,
        expected_ayahs: List[AyahText],
        normalizer: Optional[ArabicTextNormalizer] = None,
        look_ahead: int = DEFAULT_LOOK_AHEAD,
        look_behind: int = DEFAULT_LOOK_BEHIND,
    ):
        """
        Initialize the alignment engine.

        Args:
            expected_ayahs: List of ayahs the student should recite
            normalizer: Arabic text normalizer (creates default if None)
            look_ahead: How many words ahead to search for matches
            look_behind: How many words behind to search for repetitions
        """
        self.expected_ayahs = expected_ayahs
        self.normalizer = normalizer or ArabicTextNormalizer()
        self.look_ahead = look_ahead
        self.look_behind = look_behind

        # Flatten all tokens from expected ayahs
        self.expected_tokens: List[str] = []
        # Map from token index to (ayah_list_index, word_index_in_ayah)
        self.token_to_ayah_map: List[Tuple[int, int]] = []

        for ayah_idx, ayah in enumerate(expected_ayahs):
            for word_idx, token in enumerate(ayah.text_tokens):
                self.expected_tokens.append(token)
                self.token_to_ayah_map.append((ayah_idx, word_idx))

        # Pre-normalize expected tokens for comparison
        self.expected_normalized = [
            self.normalizer.normalize(t) for t in self.expected_tokens
        ]

        # Position state
        self.position = PositionState()

        # Track recent events for self-correction detection
        self.recent_events: List[AlignmentEvent] = []
        self.max_recent_events = 20

        # Track pending words that might be part of self-correction
        self.pending_mismatch: Optional[AlignmentEvent] = None
        self.pending_mismatch_time: int = 0
        # Time window for self-correction detection (ms)
        self.self_correction_window_ms = 2000

    def process_words(
        self,
        words: List[TranscribedWord],
    ) -> List[AlignmentEvent]:
        """
        Process a batch of transcribed words and return alignment events.

        This is the main entry point for the alignment engine. It processes
        each word, determines alignment, and returns events describing
        what happened.

        Args:
            words: List of transcribed words from ASR

        Returns:
            List of alignment events (matches, mismatches, skips, etc.)
        """
        events: List[AlignmentEvent] = []

        for word in words:
            word_events = self._process_single_word(word)
            events.extend(word_events)

            # Update stability after EACH word and commit immediately if stable
            for event in word_events:
                if event.event_type == AlignmentEventType.MATCH:
                    self.position.consecutive_matches += 1
                    # Commit as soon as we reach threshold
                    if self.position.consecutive_matches >= self.STABILITY_THRESHOLD:
                        self._commit_tentative()
                else:
                    self.position.consecutive_matches = 0

        # Check for self-corrections in the event sequence
        events = self._detect_self_corrections(events)

        return events

    def _process_single_word(self, word: TranscribedWord) -> List[AlignmentEvent]:
        """
        Process a single transcribed word and determine alignment.

        Args:
            word: The transcribed word to process

        Returns:
            List of alignment events (usually 1, but may include skips)
        """
        events: List[AlignmentEvent] = []
        normalized_word = self.normalizer.normalize(word.text)

        # Check if we've reached the end of expected text
        if self.position.tentative_index >= len(self.expected_tokens):
            # Word after expected end - treat as insertion
            event = AlignmentEvent(
                event_type=AlignmentEventType.INSERTION,
                word_index=None,
                received_word=word.text,
                confidence=word.confidence,
                timestamp_ms=word.timestamp_ms,
            )
            events.append(event)
            self._track_recent_event(event)
            return events

        # Look for match starting at current position
        match_idx = self._find_best_match(
            normalized_word,
            self.position.tentative_index,
        )

        if match_idx is not None:
            # Check if this is a repetition (match behind current position)
            if match_idx < self.position.tentative_index:
                # Repetition - student went back (restart after pause)
                # This is normal in tajweed - reset position to allow continuing from restart point
                event = AlignmentEvent(
                    event_type=AlignmentEventType.REPETITION,
                    word_index=match_idx,
                    received_word=word.text,
                    confidence=word.confidence,
                    timestamp_ms=word.timestamp_ms,
                )
                events.append(event)
                self._track_recent_event(event)
                # Reset BOTH tentative and confirmed positions to restart point
                # This allows the user to continue from where they restarted
                self.position.tentative_index = match_idx + 1
                # Also reset confirmed if we're going back past it
                if match_idx < self.position.confirmed_index:
                    self.position.confirmed_index = match_idx
                    self.position.consecutive_matches = 0
                print(f"[RESTART] User restarted from word {match_idx}, positions reset (tentative={self.position.tentative_index}, confirmed={self.position.confirmed_index})")
                return events

            # Check if we skipped words
            if match_idx > self.position.tentative_index:
                # Skipped words - emit skip events for each
                for skip_idx in range(self.position.tentative_index, match_idx):
                    skip_event = AlignmentEvent(
                        event_type=AlignmentEventType.SKIPPED,
                        word_index=skip_idx,
                        received_word=None,
                        confidence=0.0,
                        timestamp_ms=word.timestamp_ms,
                    )
                    events.append(skip_event)
                    self._track_recent_event(skip_event)

            # This is a match
            event = AlignmentEvent(
                event_type=AlignmentEventType.MATCH,
                word_index=match_idx,
                received_word=word.text,
                confidence=word.confidence,
                timestamp_ms=word.timestamp_ms,
            )
            events.append(event)
            self._track_recent_event(event)

            # Advance tentative position
            self.position.tentative_index = match_idx + 1

        else:
            # No match found - mismatch
            event = AlignmentEvent(
                event_type=AlignmentEventType.MISMATCH,
                word_index=self.position.tentative_index,
                received_word=word.text,
                confidence=word.confidence,
                timestamp_ms=word.timestamp_ms,
            )
            events.append(event)
            self._track_recent_event(event)

            # Advance tentative position even on mismatch
            # (the word was said, even if wrong)
            self.position.tentative_index += 1

        return events

    def _find_best_match(
        self,
        normalized_word: str,
        start_idx: int,
    ) -> Optional[int]:
        """
        Find the best matching position for a word within the search window.

        Searches forward from start_idx up to look_ahead words,
        and backward up to look_behind words (for repetition detection).

        Args:
            normalized_word: The normalized word to match
            start_idx: Starting position for forward search

        Returns:
            Index of best match, or None if no match found
        """
        # Don't match empty words
        if not normalized_word:
            return None

        # Search forward (look_ahead words)
        end_idx = min(start_idx + self.look_ahead, len(self.expected_normalized))
        for i in range(start_idx, end_idx):
            expected = self.expected_normalized[i]
            # Use fuzzy matching from normalizer
            if self.normalizer.words_match(normalized_word, expected, fuzzy=True):
                print(f"[MATCH] Found match at idx {i}: '{normalized_word}' ~ '{expected}'")
                return i
            # Debug: log comparison for first few positions
            if i < start_idx + 3:
                print(f"[COMPARE] No match: received '{normalized_word}' vs expected '{expected}' at idx {i}")

        # Search backward for repetitions (look_behind words)
        # Allow searching back past confirmed position for restart after pause
        back_start = max(start_idx - self.look_behind, 0)
        for i in range(start_idx - 1, back_start - 1, -1):
            if self.normalizer.words_match(normalized_word, self.expected_normalized[i], fuzzy=True):
                print(f"[BACKWARD_MATCH] Found restart point at idx {i}: '{normalized_word}' ~ '{self.expected_normalized[i]}'")
                return i

        return None

    def _detect_self_corrections(
        self,
        events: List[AlignmentEvent],
    ) -> List[AlignmentEvent]:
        """
        Detect and mark self-corrections in the event sequence.

        A self-correction is when a mismatch is followed by a match
        at the same position within the correction window.

        Args:
            events: List of alignment events to process

        Returns:
            Updated events (not modified in place for clarity)
        """
        # For now, return events as-is
        # Self-correction detection is handled by the MistakeClassifier
        # which has access to the full event history
        return events

    def _update_stability(self, events: List[AlignmentEvent]) -> None:
        """
        Update stability tracking based on new events.

        Stability is measured by consecutive matches. A stable alignment
        can be committed as confirmed.

        Args:
            events: Recent alignment events
        """
        for event in events:
            if event.event_type == AlignmentEventType.MATCH:
                self.position.consecutive_matches += 1
            else:
                self.position.consecutive_matches = 0

    def _is_stable(self) -> bool:
        """
        Check if current alignment is stable enough to commit.

        Returns:
            True if alignment should be committed
        """
        return self.position.consecutive_matches >= self.STABILITY_THRESHOLD

    def _commit_tentative(self) -> None:
        """
        Commit tentative position as confirmed.

        Called when alignment is stable enough to be certain.
        """
        if self.position.tentative_index > self.position.confirmed_index:
            self.position.confirmed_index = self.position.tentative_index
            self.position.last_stable_index = self.position.tentative_index

    def _track_recent_event(self, event: AlignmentEvent) -> None:
        """
        Track recent events for self-correction detection.

        Args:
            event: Event to track
        """
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events.pop(0)

    def get_current_position(self) -> Tuple[int, int]:
        """
        Get the current position as (ayah_index, word_index).

        Returns the tentative position mapped back to ayah coordinates.

        Returns:
            Tuple of (ayah_index, word_index_in_ayah)
        """
        if self.position.tentative_index >= len(self.token_to_ayah_map):
            # Past the end
            if self.token_to_ayah_map:
                last_ayah_idx, _ = self.token_to_ayah_map[-1]
                return (last_ayah_idx, len(self.expected_ayahs[last_ayah_idx].text_tokens))
            return (0, 0)

        return self.token_to_ayah_map[self.position.tentative_index]

    def get_confirmed_position(self) -> Tuple[int, int]:
        """
        Get the confirmed position as (ayah_index, word_index).

        Returns the confirmed position mapped back to ayah coordinates.

        Returns:
            Tuple of (ayah_index, word_index_in_ayah)
        """
        if self.position.confirmed_index >= len(self.token_to_ayah_map):
            if self.token_to_ayah_map:
                last_ayah_idx, _ = self.token_to_ayah_map[-1]
                return (last_ayah_idx, len(self.expected_ayahs[last_ayah_idx].text_tokens))
            return (0, 0)

        if self.position.confirmed_index == 0:
            return (0, 0)

        return self.token_to_ayah_map[self.position.confirmed_index - 1]

    def get_expected_word(self, token_index: int) -> Optional[str]:
        """
        Get the expected word at a given token index.

        Args:
            token_index: Index in the flattened token list

        Returns:
            The expected word, or None if index is out of range
        """
        if 0 <= token_index < len(self.expected_tokens):
            return self.expected_tokens[token_index]
        return None

    def get_expected_word_uthmani(self, token_index: int) -> Optional[str]:
        """
        Get the expected word in Uthmani form at a given token index.

        Args:
            token_index: Index in the flattened token list

        Returns:
            The expected word in Uthmani form, or None if out of range
        """
        if 0 <= token_index < len(self.token_to_ayah_map):
            ayah_idx, word_idx = self.token_to_ayah_map[token_index]
            ayah = self.expected_ayahs[ayah_idx]
            # Get the Uthmani text tokens by splitting
            uthmani_tokens = ayah.text_uthmani.split()
            if word_idx < len(uthmani_tokens):
                return uthmani_tokens[word_idx]
        return None

    def get_ayah_for_token(self, token_index: int) -> Optional[Tuple[int, int]]:
        """
        Get the (surah, ayah) for a given token index.

        Args:
            token_index: Index in the flattened token list

        Returns:
            Tuple of (surah_number, ayah_number), or None if out of range
        """
        if 0 <= token_index < len(self.token_to_ayah_map):
            ayah_idx, _ = self.token_to_ayah_map[token_index]
            ayah = self.expected_ayahs[ayah_idx]
            return (ayah.surah, ayah.ayah)
        return None

    def is_complete(self) -> bool:
        """
        Check if the student has completed all expected text.

        Returns:
            True if confirmed position has reached the end
        """
        return self.position.confirmed_index >= len(self.expected_tokens)

    def force_commit(self) -> None:
        """
        Force commit tentative position as confirmed.

        Called at the end of recording to finalize alignment state
        regardless of stability threshold.
        """
        if self.position.tentative_index > self.position.confirmed_index:
            self.position.confirmed_index = self.position.tentative_index
            self.position.last_stable_index = self.position.tentative_index

    def reset(self) -> None:
        """
        Reset the engine to initial state.

        Use this to start a new recitation with the same expected ayahs.
        """
        self.position = PositionState()
        self.recent_events = []
        self.pending_mismatch = None
        self.pending_mismatch_time = 0

    def get_progress(self) -> Tuple[int, int]:
        """
        Get progress as (confirmed_words, total_words).

        Returns:
            Tuple of (number of confirmed words, total expected words)
        """
        return (self.position.confirmed_index, len(self.expected_tokens))
