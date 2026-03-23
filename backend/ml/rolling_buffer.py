"""
Rolling Audio Buffer for Hifdh Review App.

Maintains a rolling window of audio data to support overlapping transcription
windows and smooth chunk boundaries.
"""

import logging
from collections import deque
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class RollingAudioBuffer:
    """
    Maintains a rolling buffer of audio data for streaming transcription.

    The buffer stores audio in a circular fashion, keeping approximately
    max_duration seconds of audio history. This enables:
    - Overlapping transcription windows for smoother results
    - Recovery from chunk boundary artifacts
    - Stable word confirmation across multiple passes
    """

    def __init__(
        self,
        max_duration: float = 5.0,
        sample_rate: int = 16000,
    ):
        """
        Initialize the rolling audio buffer.

        Args:
            max_duration: Maximum duration of audio to keep in buffer (seconds)
            sample_rate: Sample rate of audio data (Hz)
        """
        self.max_duration = max_duration
        self.sample_rate = sample_rate
        self.max_samples = int(max_duration * sample_rate)

        # Use deque for efficient append/pop operations
        # Store audio as a single numpy array for efficiency
        self._buffer: Optional[np.ndarray] = None
        self._total_samples_received = 0

    def add_chunk(self, audio_array: np.ndarray) -> None:
        """
        Add an audio chunk to the buffer.

        Args:
            audio_array: Numpy array of audio samples (16kHz mono float32)
        """
        if len(audio_array) == 0:
            return

        # Ensure float32
        audio_array = audio_array.astype(np.float32)

        if self._buffer is None:
            # First chunk
            self._buffer = audio_array
        else:
            # Append to existing buffer
            self._buffer = np.concatenate([self._buffer, audio_array])

        self._total_samples_received += len(audio_array)

        # Trim if buffer exceeds max size
        if len(self._buffer) > self.max_samples:
            excess = len(self._buffer) - self.max_samples
            self._buffer = self._buffer[excess:]
            logger.debug(f"Trimmed {excess} samples from buffer")

        logger.debug(
            f"Buffer now has {len(self._buffer)} samples "
            f"({self.get_duration():.2f}s)"
        )

    def get_window(self, duration_seconds: float = 2.5) -> np.ndarray:
        """
        Get the most recent audio window of specified duration.

        Args:
            duration_seconds: Duration of window to retrieve (seconds)

        Returns:
            Numpy array of audio samples, may be shorter than requested
            if buffer doesn't have enough data
        """
        if self._buffer is None or len(self._buffer) == 0:
            return np.array([], dtype=np.float32)

        samples_needed = int(duration_seconds * self.sample_rate)

        if len(self._buffer) <= samples_needed:
            # Return entire buffer
            return self._buffer.copy()
        else:
            # Return last N samples
            return self._buffer[-samples_needed:].copy()

    def get_overlap_window(self, duration_seconds: float = 0.5) -> np.ndarray:
        """
        Get an overlap window from the end of the previous transcription region.

        This is used to ensure smooth transitions between transcription windows
        and to help identify where the new audio connects.

        Args:
            duration_seconds: Duration of overlap window (seconds)

        Returns:
            Numpy array of audio samples for overlap region
        """
        if self._buffer is None or len(self._buffer) == 0:
            return np.array([], dtype=np.float32)

        # Get the region that would be the end of the "previous" window
        # This is typically used when we have a 2.5s window and want 0.5s overlap
        window_samples = int(2.5 * self.sample_rate)
        overlap_samples = int(duration_seconds * self.sample_rate)

        if len(self._buffer) < window_samples:
            # Not enough data for a full window, return what we have
            return self._buffer[:min(overlap_samples, len(self._buffer))].copy()

        # Get overlap region: samples from (window_end - overlap) to window_end
        # of the "previous" window
        start_idx = max(0, len(self._buffer) - window_samples)
        end_idx = start_idx + overlap_samples

        return self._buffer[start_idx:end_idx].copy()

    def get_full_audio(self) -> np.ndarray:
        """
        Get all audio currently in the buffer.

        Returns:
            Numpy array of all buffered audio samples
        """
        if self._buffer is None:
            return np.array([], dtype=np.float32)
        return self._buffer.copy()

    def get_duration(self) -> float:
        """
        Get the current duration of audio in the buffer.

        Returns:
            Duration in seconds
        """
        if self._buffer is None:
            return 0.0
        return len(self._buffer) / self.sample_rate

    def get_total_duration_received(self) -> float:
        """
        Get the total duration of audio received since initialization.

        Returns:
            Total duration in seconds
        """
        return self._total_samples_received / self.sample_rate

    def clear(self) -> None:
        """Clear all audio from the buffer."""
        self._buffer = None
        self._total_samples_received = 0
        logger.debug("Buffer cleared")

    def is_ready_for_transcription(self, min_duration: float = 1.0) -> bool:
        """
        Check if buffer has enough audio for transcription.

        Args:
            min_duration: Minimum duration needed (seconds)

        Returns:
            True if buffer has at least min_duration of audio
        """
        return self.get_duration() >= min_duration

    @property
    def sample_count(self) -> int:
        """Get the number of samples currently in the buffer."""
        if self._buffer is None:
            return 0
        return len(self._buffer)

    def get_audio_since(self, timestamp_seconds: float) -> np.ndarray:
        """
        Get audio received since a specific timestamp.

        This is useful for retrieving audio that arrived after a certain point.

        Args:
            timestamp_seconds: Timestamp in seconds (relative to first sample)

        Returns:
            Numpy array of audio samples since that timestamp
        """
        if self._buffer is None:
            return np.array([], dtype=np.float32)

        total_duration = self.get_total_duration_received()
        current_duration = self.get_duration()

        # Calculate how far back the timestamp is
        elapsed = total_duration - timestamp_seconds

        if elapsed <= 0:
            # Timestamp is in the future, return empty
            return np.array([], dtype=np.float32)

        if elapsed >= current_duration:
            # Timestamp is before our buffer starts, return all
            return self._buffer.copy()

        # Get samples from the appropriate point
        samples_since = int(elapsed * self.sample_rate)
        return self._buffer[-samples_since:].copy()

    def __len__(self) -> int:
        """Return the number of samples in the buffer."""
        return self.sample_count

    def __repr__(self) -> str:
        return (
            f"RollingAudioBuffer("
            f"duration={self.get_duration():.2f}s, "
            f"max_duration={self.max_duration}s, "
            f"samples={self.sample_count})"
        )
