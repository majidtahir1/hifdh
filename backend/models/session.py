"""
Session state models for the Hifdh Review App.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .quran import AyahText
    from .mistake import Mistake


class SessionState(Enum):
    """Possible states for a review session."""
    WAITING_FOR_PROMPT_PLAYBACK = "waiting_for_prompt_playback"
    RECORDING = "recording"
    ALIGNING = "aligning"
    USER_PAUSED = "user_paused"
    COMPLETE = "complete"


@dataclass
class ReviewSession:
    """
    Represents an active review session with all state needed for tracking.

    A session includes:
    - Configuration (juz range, number of ayahs)
    - The prompt ayah and expected continuation
    - Position tracking (confirmed vs tentative)
    - Transcript state
    - Mistake tracking
    - Timing information
    """
    id: str
    state: SessionState

    # Configuration
    juz_range: tuple[int, int]
    num_ayahs_to_recite: int

    # Prompt and expectation
    prompt_ayah: "AyahText"
    expected_ayahs: list["AyahText"]
    expected_tokens: list[str]  # Flattened token list for alignment

    # Position tracking
    confirmed_word_index: int = 0       # Last word we're certain about
    tentative_word_index: int = 0       # Current best guess position
    last_stable_alignment: int = 0      # Last high-confidence alignment

    # Transcript state
    confirmed_transcript: list[str] = field(default_factory=list)
    tentative_transcript: list[str] = field(default_factory=list)

    # Mistake tracking
    mistakes: list["Mistake"] = field(default_factory=list)

    # Confidence tracking
    low_confidence_counter: int = 0
    self_correction_window_ms: int = 2000  # Time to allow self-correction

    # Timing
    recording_started_at: float | None = None
    last_chunk_at: float | None = None

    def get_current_expected_word(self) -> str | None:
        """Get the expected word at the current tentative position."""
        if self.tentative_word_index < len(self.expected_tokens):
            return self.expected_tokens[self.tentative_word_index]
        return None

    def advance_confirmed_position(self, new_index: int) -> None:
        """Advance the confirmed word index."""
        if new_index > self.confirmed_word_index:
            self.confirmed_word_index = new_index

    def is_complete(self) -> bool:
        """Check if the session has covered all expected tokens."""
        return self.confirmed_word_index >= len(self.expected_tokens)
