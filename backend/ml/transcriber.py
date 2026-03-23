"""
Streaming Transcriber for Hifdh Review App.

Uses faster-whisper with the Quran-tuned model for real-time transcription
of Arabic Quran recitation.
"""

import logging
import warnings
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from faster_whisper import WhisperModel

# Suppress numpy warnings from faster-whisper's mel spectrogram computation
# These occur with silent/quiet audio sections and are harmless
warnings.filterwarnings("ignore", message="divide by zero encountered in matmul")
warnings.filterwarnings("ignore", message="overflow encountered in matmul")
warnings.filterwarnings("ignore", message="invalid value encountered in matmul")

logger = logging.getLogger(__name__)


@dataclass
class WordInfo:
    """Information about a single transcribed word."""

    text: str
    start: float  # Start time in seconds
    end: float  # End time in seconds
    confidence: float  # Probability/confidence score (0-1)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
        }


@dataclass
class TranscriptionResult:
    """
    Result from transcribing an audio chunk.

    Contains both confirmed words (stable across multiple passes)
    and tentative words (may change with more context).
    """

    words: List[WordInfo] = field(default_factory=list)
    tentative: List[WordInfo] = field(default_factory=list)  # Last N words that may change
    confirmed: List[WordInfo] = field(default_factory=list)  # Words stable across windows
    full_text: str = ""
    language: str = "ar"
    language_probability: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "words": [w.to_dict() for w in self.words],
            "tentative": [w.to_dict() for w in self.tentative],
            "confirmed": [w.to_dict() for w in self.confirmed],
            "full_text": self.full_text,
            "language": self.language,
            "language_probability": self.language_probability,
        }


class StreamingTranscriber:
    """
    Streaming transcriber for Quran recitation using faster-whisper.

    Uses the tarteel-ai/whisper-base-ar-quran model which is specifically
    tuned for Quranic Arabic recitation.
    """

    # Default model for Quran transcription
    # Using the tarteel-ai/whisper-base-ar-quran model converted to CTranslate2 format
    # This model is specifically tuned for Quranic Arabic recitation
    DEFAULT_MODEL = "./models/tarteel-quran-ct2"

    # Number of words at the end to consider tentative (0 for immediate feedback)
    TENTATIVE_WORD_COUNT = 0

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = "auto",
        compute_type: str = "auto",
        tentative_word_count: int = TENTATIVE_WORD_COUNT,
    ):
        """
        Initialize the streaming transcriber.

        Args:
            model_name: Name or path of the Whisper model to use
            device: Device to run model on ("cpu", "cuda", or "auto")
            compute_type: Compute type ("float16", "int8", "auto")
            tentative_word_count: Number of trailing words to mark as tentative
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.tentative_word_count = tentative_word_count

        # Model is loaded lazily on first use
        self._model: Optional[WhisperModel] = None

        # Track previous transcription for stability comparison
        self._previous_words: List[str] = []
        self._confirmed_word_count = 0

    def _load_model(self) -> WhisperModel:
        """Load the Whisper model if not already loaded."""
        if self._model is None:
            logger.info(f"Loading model: {self.model_name}")
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("Model loaded successfully")
        return self._model

    @property
    def model(self) -> WhisperModel:
        """Get the loaded model, loading it if necessary."""
        return self._load_model()

    def transcribe_chunk(self, audio_array: np.ndarray) -> TranscriptionResult:
        """
        Transcribe an audio chunk.

        Args:
            audio_array: Numpy array of audio samples (16kHz mono float32)

        Returns:
            TranscriptionResult with words, tentative/confirmed split
        """
        if len(audio_array) == 0:
            return TranscriptionResult()

        # Ensure correct dtype
        audio_array = audio_array.astype(np.float32)

        # Transcribe with word-level timestamps
        # Using fast decoding options for near real-time performance
        segments, info = self.model.transcribe(
            audio_array,
            language="ar",
            word_timestamps=True,
            vad_filter=True,  # Filter out non-speech
            beam_size=1,  # Greedy decoding (faster)
            best_of=1,  # No sampling
            condition_on_previous_text=False,  # Don't use context (faster)
        )

        # Collect all words from segments
        words: List[WordInfo] = []
        full_text_parts: List[str] = []

        for segment in segments:
            if segment.words:
                for word_info in segment.words:
                    words.append(
                        WordInfo(
                            text=word_info.word.strip(),
                            start=word_info.start,
                            end=word_info.end,
                            confidence=word_info.probability,
                        )
                    )
                    full_text_parts.append(word_info.word.strip())

        # Determine confirmed vs tentative words
        confirmed, tentative = self._split_confirmed_tentative(words)

        return TranscriptionResult(
            words=words,
            tentative=tentative,
            confirmed=confirmed,
            full_text=" ".join(full_text_parts),
            language=info.language,
            language_probability=info.language_probability,
        )

    def _split_confirmed_tentative(
        self, words: List[WordInfo]
    ) -> tuple[List[WordInfo], List[WordInfo]]:
        """
        Split words into confirmed and tentative based on stability.

        Words are considered confirmed if they:
        1. Appeared in the previous transcription at the same position
        2. Are not in the trailing tentative_word_count words

        Args:
            words: List of transcribed words

        Returns:
            Tuple of (confirmed_words, tentative_words)
        """
        if len(words) == 0:
            return [], []

        current_texts = [w.text for w in words]

        # Find how many words match the previous transcription
        # starting from the beginning
        stable_count = 0
        for i, text in enumerate(current_texts):
            if i < len(self._previous_words) and text == self._previous_words[i]:
                stable_count = i + 1
            else:
                break

        # Update confirmed count: max of previous confirmed and current stable
        # minus the tentative buffer
        potential_confirmed = max(stable_count, self._confirmed_word_count)

        # Don't mark trailing words as confirmed
        confirmed_end = min(
            potential_confirmed,
            max(0, len(words) - self.tentative_word_count),
        )

        # Update state for next comparison
        self._previous_words = current_texts
        self._confirmed_word_count = confirmed_end

        confirmed = words[:confirmed_end]
        tentative = words[confirmed_end:]

        return confirmed, tentative

    def reset(self) -> None:
        """
        Reset the transcriber state.

        Call this when starting a new recording session to clear
        previous transcription history.
        """
        self._previous_words = []
        self._confirmed_word_count = 0
        logger.debug("Transcriber state reset")

    def transcribe_with_context(
        self,
        audio_array: np.ndarray,
        initial_prompt: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio with optional context/prompt.

        The initial_prompt can help guide the model towards expected content,
        which can be useful for Quran recitation where we know the expected text.

        Args:
            audio_array: Numpy array of audio samples (16kHz mono float32)
            initial_prompt: Optional text to condition the model on

        Returns:
            TranscriptionResult with words, tentative/confirmed split
        """
        if len(audio_array) == 0:
            return TranscriptionResult()

        audio_array = audio_array.astype(np.float32)

        # Transcribe with optional prompt
        # Using fast decoding options for near real-time performance
        segments, info = self.model.transcribe(
            audio_array,
            language="ar",
            word_timestamps=True,
            vad_filter=False,  # Disabled - process immediately without waiting for pauses
            initial_prompt=initial_prompt,
            beam_size=1,  # Greedy decoding (faster)
            best_of=1,  # No sampling
        )

        # Collect words
        words: List[WordInfo] = []
        full_text_parts: List[str] = []

        for segment in segments:
            if segment.words:
                for word_info in segment.words:
                    words.append(
                        WordInfo(
                            text=word_info.word.strip(),
                            start=word_info.start,
                            end=word_info.end,
                            confidence=word_info.probability,
                        )
                    )
                    full_text_parts.append(word_info.word.strip())

        confirmed, tentative = self._split_confirmed_tentative(words)

        return TranscriptionResult(
            words=words,
            tentative=tentative,
            confirmed=confirmed,
            full_text=" ".join(full_text_parts),
            language=info.language,
            language_probability=info.language_probability,
        )

    def unload_model(self) -> None:
        """
        Unload the model from memory.

        Call this when the transcriber is no longer needed to free GPU memory.
        """
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Model unloaded")

    def __del__(self):
        """Clean up model on deletion."""
        self.unload_model()

    def __repr__(self) -> str:
        loaded = "loaded" if self._model is not None else "not loaded"
        return f"StreamingTranscriber(model={self.model_name}, {loaded})"
