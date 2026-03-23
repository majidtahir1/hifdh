"""
Event models for alignment and feedback in the Hifdh Review App.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class AlignmentEventType(Enum):
    """Types of events emitted by the Continuation Alignment Engine."""
    MATCH = "match"             # Word matches expected
    MISMATCH = "mismatch"       # Word doesn't match expected
    SKIPPED = "skipped"         # Expected word was skipped
    REPETITION = "repetition"   # Word was repeated (went back)
    INSERTION = "insertion"     # Extra word not in expected


@dataclass
class AlignmentEvent:
    """
    Represents an event from the alignment engine.

    Emitted when the alignment engine processes transcription output
    and determines how words align with the expected continuation.

    Attributes:
        event_type: The type of alignment event
        word_index: Index in the expected tokens (None for insertions)
        received_word: The word that was transcribed (None for skipped)
        confidence: ASR confidence for the received word
        timestamp_ms: When this event was generated
    """
    event_type: AlignmentEventType
    word_index: int | None      # Position in expected tokens
    received_word: str | None   # What was said
    confidence: float           # ASR confidence (0.0-1.0)
    timestamp_ms: int = 0

    def __post_init__(self):
        """Validate event data after initialization."""
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def is_correct(self) -> bool:
        """Check if this event represents a correct match."""
        return self.event_type == AlignmentEventType.MATCH

    def is_error(self) -> bool:
        """Check if this event represents an error."""
        return self.event_type in (
            AlignmentEventType.MISMATCH,
            AlignmentEventType.SKIPPED,
        )


class FeedbackAction(Enum):
    """Actions the feedback policy engine can take."""
    CONFIRM_CORRECT = "confirm_correct"   # Mark word as correct
    EMIT_MISTAKE = "emit_mistake"         # Surface mistake to user
    HOLD = "hold"                         # Wait for more information
    CLEAR_PENDING = "clear_pending"       # Clear a pending issue


@dataclass
class FeedbackDecision:
    """
    Represents a decision made by the Feedback Policy Engine.

    The feedback engine evaluates alignment events and decides whether
    to surface feedback to the user, hold for more information, or
    clear pending issues.

    Attributes:
        action: The action to take
        event: The alignment event that triggered this decision
        reason: Optional explanation for why this decision was made
        delay_ms: Optional delay before surfacing (for gentle mode)
    """
    action: FeedbackAction
    event: AlignmentEvent
    reason: str | None = None
    delay_ms: int = 0

    def should_emit_to_client(self) -> bool:
        """Check if this decision should result in a message to the client."""
        return self.action in (
            FeedbackAction.CONFIRM_CORRECT,
            FeedbackAction.EMIT_MISTAKE,
        )

    def is_holding(self) -> bool:
        """Check if we're holding this decision for more information."""
        return self.action == FeedbackAction.HOLD


# Type alias for feedback modes
FeedbackMode = Literal["immediate", "gentle", "post_ayah", "post_session"]


@dataclass
class FeedbackConfig:
    """Configuration for the Feedback Policy Engine."""
    mode: FeedbackMode = "gentle"
    min_confidence: float = 0.7
    require_persistence: bool = True
    persistence_windows: int = 2
    self_correction_window_ms: int = 2000

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.min_confidence < 0.0 or self.min_confidence > 1.0:
            raise ValueError(f"min_confidence must be between 0.0 and 1.0, got {self.min_confidence}")
        if self.persistence_windows < 1:
            raise ValueError(f"persistence_windows must be at least 1, got {self.persistence_windows}")
        if self.self_correction_window_ms < 0:
            raise ValueError(f"self_correction_window_ms must be non-negative, got {self.self_correction_window_ms}")
