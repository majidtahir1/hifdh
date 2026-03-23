"""
Mistake classification models for the Hifdh Review App.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MistakeType(Enum):
    """Types of mistakes that can occur during recitation."""
    WRONG_WORD = "wrong_word"           # Said different word
    SKIPPED = "skipped"                 # Missed a word
    ADDED = "added"                     # Said extra word not in text
    REPETITION = "repetition"           # Repeated a phrase
    OUT_OF_ORDER = "out_of_order"       # Words in wrong sequence
    JUMPED_AHEAD = "jumped_ahead"       # Skipped multiple words/ayahs
    EARLY_STOP = "early_stop"           # Stopped before expected end
    SELF_CORRECTED = "self_corrected"   # Made mistake but fixed it (no penalty)
    LOW_CONFIDENCE = "low_confidence"   # ASR uncertain, needs review


@dataclass
class Mistake:
    """
    Represents a single mistake detected during recitation.

    Attributes:
        mistake_type: The category of mistake
        ayah: Tuple of (surah, ayah) where the mistake occurred
        word_index: Index of the word within the expected tokens
        expected: The expected word in Uthmani form (for display)
        received: What was actually said (None if skipped)
        confidence: ASR confidence score (0.0 to 1.0)
        is_penalty: Whether this counts against the user
        timestamp_ms: When the mistake was detected
    """
    mistake_type: MistakeType
    ayah: tuple[int, int]  # (surah, ayah)
    word_index: int
    expected: str          # Uthmani form for display
    received: str | None   # What was said (None if skipped)
    confidence: float      # ASR confidence
    is_penalty: bool       # False for self_corrected, low_confidence
    timestamp_ms: int

    def __post_init__(self):
        """Validate mistake data after initialization."""
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        if self.word_index < 0:
            raise ValueError(f"Word index must be non-negative, got {self.word_index}")

    def is_self_corrected(self) -> bool:
        """Check if this was a self-corrected mistake."""
        return self.mistake_type == MistakeType.SELF_CORRECTED

    def should_display_immediately(self) -> bool:
        """Check if this mistake should be shown to the user immediately."""
        # Don't immediately show self-corrections or low-confidence detections
        return self.is_penalty and self.mistake_type not in (
            MistakeType.SELF_CORRECTED,
            MistakeType.LOW_CONFIDENCE,
        )
