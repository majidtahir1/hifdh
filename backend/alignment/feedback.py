"""
Feedback Policy Engine for the Hifdh Review App.

This module decides when and how to surface feedback to the user.
It implements:
- Confidence gating: only emit if ASR confidence > threshold
- Persistence filtering: wait for mistake to persist across windows
- Timing policy: immediate vs delayed feedback
- Feedback modes: immediate, gentle, post_ayah, post_session
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import time

from models.events import (
    AlignmentEvent,
    AlignmentEventType,
    FeedbackDecision,
    FeedbackAction,
    FeedbackConfig,
    FeedbackMode,
)
from models.mistake import Mistake, MistakeType


@dataclass
class PendingIssue:
    """
    Tracks a potential mistake awaiting confirmation.

    Used for persistence filtering - we wait for issues to persist
    across multiple transcription windows before surfacing them.
    """
    mistake: Mistake
    first_seen_ms: int
    last_seen_ms: int
    occurrences: int = 1
    is_confirmed: bool = False


class FeedbackPolicyEngine:
    """
    Decides when and how to surface feedback to the user.

    This engine acts as a filter between the mistake classifier
    and the user interface. It implements various policies to
    reduce false positives and improve user experience.

    Policies:
    1. Confidence gating: Only surface if ASR confidence > threshold
    2. Persistence filter: Wait for mistake to persist across windows
    3. Timing policy: When to show feedback (immediate, delayed, etc.)
    4. Self-correction window: Give time for user to self-correct

    Feedback modes:
    - immediate: Show mistakes as soon as detected
    - gentle: Highlight inline but don't interrupt
    - post_ayah: Show feedback after each ayah
    - post_session: Only show summary at the end
    """

    def __init__(self, config: Optional[FeedbackConfig] = None):
        """
        Initialize the feedback policy engine.

        Args:
            config: Feedback configuration. Uses defaults if None.
        """
        self.config = config or FeedbackConfig()

        # Track pending issues awaiting confirmation
        self.pending_issues: Dict[int, PendingIssue] = {}

        # Collected feedback for deferred modes
        self.deferred_feedback: List[FeedbackDecision] = []

        # Track current ayah for post_ayah mode
        self.current_ayah: Optional[Tuple[int, int]] = None

        # Track confirmed correct words
        self.confirmed_correct_count: int = 0

        # Track emitted mistakes to avoid duplicates
        self.emitted_mistakes: set = set()

    def process_mistakes(
        self,
        mistakes: List[Mistake],
    ) -> List[FeedbackDecision]:
        """
        Process mistakes and decide which to surface as feedback.

        This is the main entry point. It applies all configured
        policies to filter and transform mistakes into feedback decisions.

        Args:
            mistakes: List of mistakes from the classifier

        Returns:
            List of feedback decisions to send to the client
        """
        decisions: List[FeedbackDecision] = []
        current_time = int(time.time() * 1000)

        for mistake in mistakes:
            decision = self._evaluate_mistake(mistake, current_time)
            if decision:
                decisions.append(decision)

        # Apply mode-specific processing
        decisions = self._apply_mode_policy(decisions)

        # Cleanup old pending issues
        self._cleanup_pending(current_time)

        return decisions

    def process_event(self, event: AlignmentEvent) -> Optional[FeedbackDecision]:
        """
        Process a single alignment event and return a feedback decision.

        Used for streaming feedback - processes events one at a time
        as they come from the alignment engine.

        Args:
            event: Alignment event to process

        Returns:
            Feedback decision, or None if no feedback needed
        """
        current_time = int(time.time() * 1000)

        if event.event_type == AlignmentEventType.MATCH:
            # Clear any pending issue at this position
            if event.word_index in self.pending_issues:
                del self.pending_issues[event.word_index]

            self.confirmed_correct_count += 1

            return FeedbackDecision(
                action=FeedbackAction.CONFIRM_CORRECT,
                event=event,
            )

        elif event.event_type == AlignmentEventType.MISMATCH:
            return self._handle_mismatch(event, current_time)

        elif event.event_type == AlignmentEventType.SKIPPED:
            return self._handle_skipped(event, current_time)

        elif event.event_type == AlignmentEventType.REPETITION:
            # Repetitions don't need immediate feedback
            return None

        elif event.event_type == AlignmentEventType.INSERTION:
            # Extra words - usually don't interrupt
            if self.config.mode == "immediate":
                return FeedbackDecision(
                    action=FeedbackAction.EMIT_MISTAKE,
                    event=event,
                    reason="insertion_detected",
                )
            return None

        return None

    def _evaluate_mistake(
        self,
        mistake: Mistake,
        current_time: int,
    ) -> Optional[FeedbackDecision]:
        """
        Evaluate a mistake and decide on feedback.

        Applies confidence gating and persistence filtering.

        Args:
            mistake: The mistake to evaluate
            current_time: Current timestamp

        Returns:
            Feedback decision, or None if holding
        """
        # Create a synthetic event for the decision
        event = AlignmentEvent(
            event_type=self._mistake_type_to_event_type(mistake.mistake_type),
            word_index=mistake.word_index,
            received_word=mistake.received,
            confidence=mistake.confidence,
            timestamp_ms=mistake.timestamp_ms,
        )

        # Check if already emitted
        mistake_key = (mistake.word_index, mistake.timestamp_ms)
        if mistake_key in self.emitted_mistakes:
            return None

        # Non-penalty mistakes (repetition, self-corrected, low-confidence)
        # don't need feedback in most modes
        if not mistake.is_penalty:
            if mistake.mistake_type == MistakeType.SELF_CORRECTED:
                # Optionally acknowledge self-correction
                if self.config.mode == "immediate":
                    self.emitted_mistakes.add(mistake_key)
                    return FeedbackDecision(
                        action=FeedbackAction.CLEAR_PENDING,
                        event=event,
                        reason="self_corrected",
                    )
            return None

        # Confidence gating
        if mistake.confidence < self.config.min_confidence:
            return FeedbackDecision(
                action=FeedbackAction.HOLD,
                event=event,
                reason="low_confidence",
            )

        # Persistence filtering
        if self.config.require_persistence:
            pending = self.pending_issues.get(mistake.word_index)

            if pending:
                # Update existing pending issue
                pending.occurrences += 1
                pending.last_seen_ms = current_time

                if pending.occurrences >= self.config.persistence_windows:
                    # Confirmed - emit mistake
                    pending.is_confirmed = True
                    self.emitted_mistakes.add(mistake_key)
                    return FeedbackDecision(
                        action=FeedbackAction.EMIT_MISTAKE,
                        event=event,
                        reason="persistence_confirmed",
                    )
                else:
                    # Still waiting for persistence
                    return FeedbackDecision(
                        action=FeedbackAction.HOLD,
                        event=event,
                        reason="awaiting_persistence",
                    )
            else:
                # New pending issue
                self.pending_issues[mistake.word_index] = PendingIssue(
                    mistake=mistake,
                    first_seen_ms=current_time,
                    last_seen_ms=current_time,
                )
                return FeedbackDecision(
                    action=FeedbackAction.HOLD,
                    event=event,
                    reason="first_occurrence",
                )

        # No persistence required - emit immediately
        self.emitted_mistakes.add(mistake_key)
        return FeedbackDecision(
            action=FeedbackAction.EMIT_MISTAKE,
            event=event,
        )

    def _handle_mismatch(
        self,
        event: AlignmentEvent,
        current_time: int,
    ) -> Optional[FeedbackDecision]:
        """
        Handle a mismatch event.

        Args:
            event: The mismatch event
            current_time: Current timestamp

        Returns:
            Feedback decision
        """
        # Confidence gating
        if event.confidence < self.config.min_confidence:
            return FeedbackDecision(
                action=FeedbackAction.HOLD,
                event=event,
                reason="low_confidence",
            )

        # Persistence filtering
        if self.config.require_persistence:
            pending = self.pending_issues.get(event.word_index)

            if pending:
                pending.occurrences += 1
                pending.last_seen_ms = current_time

                if pending.occurrences >= self.config.persistence_windows:
                    return FeedbackDecision(
                        action=FeedbackAction.EMIT_MISTAKE,
                        event=event,
                    )
                else:
                    return FeedbackDecision(
                        action=FeedbackAction.HOLD,
                        event=event,
                        reason="awaiting_persistence",
                    )
            else:
                # Create new pending issue (need a Mistake object)
                self.pending_issues[event.word_index] = PendingIssue(
                    mistake=Mistake(
                        mistake_type=MistakeType.WRONG_WORD,
                        ayah=(0, 0),
                        word_index=event.word_index or 0,
                        expected="",
                        received=event.received_word,
                        confidence=event.confidence,
                        is_penalty=True,
                        timestamp_ms=event.timestamp_ms,
                    ),
                    first_seen_ms=current_time,
                    last_seen_ms=current_time,
                )
                return FeedbackDecision(
                    action=FeedbackAction.HOLD,
                    event=event,
                    reason="first_occurrence",
                )

        # No persistence - immediate feedback
        return FeedbackDecision(
            action=FeedbackAction.EMIT_MISTAKE,
            event=event,
        )

    def _handle_skipped(
        self,
        event: AlignmentEvent,
        current_time: int,
    ) -> Optional[FeedbackDecision]:
        """
        Handle a skipped word event.

        Args:
            event: The skip event
            current_time: Current timestamp

        Returns:
            Feedback decision
        """
        # Skips are high confidence (we know a word was missed)
        # but we might want to wait briefly in case it's a self-correction

        if self.config.require_persistence:
            pending = self.pending_issues.get(event.word_index)

            if pending:
                pending.occurrences += 1
                pending.last_seen_ms = current_time

                if pending.occurrences >= self.config.persistence_windows:
                    return FeedbackDecision(
                        action=FeedbackAction.EMIT_MISTAKE,
                        event=event,
                    )
                return FeedbackDecision(
                    action=FeedbackAction.HOLD,
                    event=event,
                    reason="awaiting_persistence",
                )
            else:
                self.pending_issues[event.word_index] = PendingIssue(
                    mistake=Mistake(
                        mistake_type=MistakeType.SKIPPED,
                        ayah=(0, 0),
                        word_index=event.word_index or 0,
                        expected="",
                        received=None,
                        confidence=1.0,
                        is_penalty=True,
                        timestamp_ms=event.timestamp_ms,
                    ),
                    first_seen_ms=current_time,
                    last_seen_ms=current_time,
                )
                return FeedbackDecision(
                    action=FeedbackAction.HOLD,
                    event=event,
                    reason="first_occurrence",
                )

        return FeedbackDecision(
            action=FeedbackAction.EMIT_MISTAKE,
            event=event,
        )

    def _apply_mode_policy(
        self,
        decisions: List[FeedbackDecision],
    ) -> List[FeedbackDecision]:
        """
        Apply mode-specific feedback policy.

        Different modes handle feedback differently:
        - immediate: Return all decisions
        - gentle: Return all but mark for gentle display
        - post_ayah: Defer until ayah boundary
        - post_session: Defer until session end

        Args:
            decisions: List of feedback decisions

        Returns:
            Filtered/modified list of decisions
        """
        if self.config.mode == "immediate":
            return decisions

        elif self.config.mode == "gentle":
            # Add delay to mistake emissions
            for decision in decisions:
                if decision.action == FeedbackAction.EMIT_MISTAKE:
                    decision.delay_ms = 500  # Half second delay
            return decisions

        elif self.config.mode == "post_ayah":
            # Defer mistakes, keep confirmations
            result = []
            for decision in decisions:
                if decision.action == FeedbackAction.CONFIRM_CORRECT:
                    result.append(decision)
                elif decision.action == FeedbackAction.EMIT_MISTAKE:
                    self.deferred_feedback.append(decision)
            return result

        elif self.config.mode == "post_session":
            # Defer everything except confirmations
            result = []
            for decision in decisions:
                if decision.action == FeedbackAction.CONFIRM_CORRECT:
                    result.append(decision)
                else:
                    self.deferred_feedback.append(decision)
            return result

        return decisions

    def _cleanup_pending(self, current_time: int) -> None:
        """
        Remove old pending issues.

        Issues that haven't been seen within the self-correction window
        are removed.

        Args:
            current_time: Current timestamp
        """
        expired_keys = []
        for key, pending in self.pending_issues.items():
            if current_time - pending.last_seen_ms > self.config.self_correction_window_ms:
                expired_keys.append(key)

        for key in expired_keys:
            del self.pending_issues[key]

    def _mistake_type_to_event_type(
        self,
        mistake_type: MistakeType,
    ) -> AlignmentEventType:
        """
        Convert a mistake type to an alignment event type.

        Args:
            mistake_type: The mistake type

        Returns:
            Corresponding event type
        """
        mapping = {
            MistakeType.WRONG_WORD: AlignmentEventType.MISMATCH,
            MistakeType.SKIPPED: AlignmentEventType.SKIPPED,
            MistakeType.ADDED: AlignmentEventType.INSERTION,
            MistakeType.REPETITION: AlignmentEventType.REPETITION,
            MistakeType.OUT_OF_ORDER: AlignmentEventType.MISMATCH,
            MistakeType.JUMPED_AHEAD: AlignmentEventType.SKIPPED,
            MistakeType.EARLY_STOP: AlignmentEventType.SKIPPED,
            MistakeType.SELF_CORRECTED: AlignmentEventType.MATCH,
            MistakeType.LOW_CONFIDENCE: AlignmentEventType.MISMATCH,
        }
        return mapping.get(mistake_type, AlignmentEventType.MISMATCH)

    def flush_deferred(self) -> List[FeedbackDecision]:
        """
        Flush all deferred feedback.

        Call this at ayah boundaries (for post_ayah mode) or
        session end (for post_session mode).

        Returns:
            List of deferred feedback decisions
        """
        deferred = self.deferred_feedback
        self.deferred_feedback = []
        return deferred

    def on_ayah_complete(
        self,
        ayah: Tuple[int, int],
    ) -> List[FeedbackDecision]:
        """
        Called when an ayah is completed.

        For post_ayah mode, this flushes deferred feedback.

        Args:
            ayah: (surah, ayah) that was completed

        Returns:
            List of feedback decisions (empty for non-post_ayah modes)
        """
        if self.config.mode == "post_ayah":
            return self.flush_deferred()
        return []

    def on_session_complete(self) -> List[FeedbackDecision]:
        """
        Called when the session is complete.

        For post_session mode, this flushes all deferred feedback.

        Returns:
            List of feedback decisions
        """
        if self.config.mode in ("post_ayah", "post_session"):
            return self.flush_deferred()
        return []

    def get_statistics(self) -> Dict:
        """
        Get statistics about the feedback processing.

        Returns:
            Dictionary with feedback statistics
        """
        return {
            "confirmed_correct": self.confirmed_correct_count,
            "pending_issues": len(self.pending_issues),
            "deferred_feedback": len(self.deferred_feedback),
            "emitted_mistakes": len(self.emitted_mistakes),
        }

    def reset(self) -> None:
        """Reset the engine state."""
        self.pending_issues = {}
        self.deferred_feedback = []
        self.current_ayah = None
        self.confirmed_correct_count = 0
        self.emitted_mistakes = set()

    def update_config(self, config: FeedbackConfig) -> None:
        """
        Update the feedback configuration.

        Args:
            config: New configuration
        """
        self.config = config
