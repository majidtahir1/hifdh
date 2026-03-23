"""
Transcription Handler for Hifdh Review App.

Orchestrates the ML pipeline for a session:
- Accumulates audio chunks
- Transcribes using Whisper
- Aligns with expected text
- Classifies mistakes
- Emits events
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Awaitable
import numpy as np

from models import AyahText, Mistake, MistakeType
from ml.audio_preprocessor import AudioPreprocessor
from ml.transcriber import StreamingTranscriber, TranscriptionResult
from alignment.engine import ContinuationAlignmentEngine, TranscribedWord
from alignment.normalizer import ArabicTextNormalizer

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionState:
    """Tracks transcription state for a session."""
    # Accumulated raw audio bytes (WebM/Opus from browser)
    raw_audio_bytes: bytes = field(default_factory=bytes)
    # Decoded audio samples (16kHz float32) - updated after successful decode
    audio_buffer: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float32))
    # Total audio duration processed
    total_duration: float = 0.0
    # Last transcription result
    last_transcription: Optional[TranscriptionResult] = None
    # Confirmed words sent to frontend
    confirmed_word_count: int = 0
    # Bytes at last successful decode
    last_decoded_bytes: int = 0
    # Number of words already processed by alignment engine
    words_processed: int = 0


class TranscriptionHandler:
    """
    Handles transcription for a single session.

    Accumulates audio, runs transcription at intervals,
    and emits events via callbacks.
    """

    # Minimum audio duration before transcribing (seconds)
    MIN_TRANSCRIPTION_DURATION = 0.15
    # Transcribe every N seconds of new audio (aggressive for real-time feedback)
    TRANSCRIPTION_INTERVAL = 0.15

    def __init__(
        self,
        expected_ayahs: List[AyahText],
        on_transcription: Optional[Callable[[List[dict], List[dict]], Awaitable[None]]] = None,
        on_mistake: Optional[Callable[[Mistake], Awaitable[None]]] = None,
        on_ayah_complete: Optional[Callable[[AyahText, int, int], Awaitable[None]]] = None,
    ):
        """
        Initialize the transcription handler.

        Args:
            expected_ayahs: List of ayahs the student should recite
            on_transcription: Callback for transcription updates (confirmed_words, tentative_words)
            on_mistake: Callback for mistake detection
            on_ayah_complete: Callback when an ayah is completed
        """
        self.expected_ayahs = expected_ayahs
        self.on_transcription = on_transcription
        self.on_mistake = on_mistake
        self.on_ayah_complete = on_ayah_complete

        # Initialize components
        self.preprocessor = AudioPreprocessor()
        self.transcriber = StreamingTranscriber()
        self.normalizer = ArabicTextNormalizer()
        self.alignment_engine = ContinuationAlignmentEngine(
            expected_ayahs=expected_ayahs,
            normalizer=self.normalizer,
        )

        # State
        self.state = TranscriptionState()
        self.last_transcription_time = 0.0
        self.mistakes: List[Mistake] = []
        self.is_finalizing = False  # Flag to stop processing new audio

        # Track ayah completion
        self.completed_ayah_indices: set = set()

    async def process_audio_chunk(self, audio_bytes: bytes) -> None:
        """
        Process an incoming audio chunk.

        Args:
            audio_bytes: Raw audio data from the client (WebM/Opus)
        """
        if not audio_bytes:
            return

        # Don't process new audio if we're finalizing
        if self.is_finalizing:
            return

        # Accumulate raw bytes - don't try to decode individual chunks
        # WebM needs complete container structure to decode
        self.state.raw_audio_bytes += audio_bytes

        # Estimate duration based on bytes (rough: ~16KB/sec for Opus at 128kbps)
        estimated_duration = len(self.state.raw_audio_bytes) / 16000

        # Check if we should attempt transcription
        time_since_last = time.time() - self.last_transcription_time

        if (estimated_duration >= self.MIN_TRANSCRIPTION_DURATION and
            (time_since_last >= self.TRANSCRIPTION_INTERVAL or
             self.last_transcription_time == 0)):
            await self._run_transcription()

    async def _run_transcription(self) -> None:
        """Run transcription on accumulated audio."""
        try:
            # Only try to decode if we have new bytes
            if len(self.state.raw_audio_bytes) <= self.state.last_decoded_bytes:
                return

            logger.info(f"Attempting to decode {len(self.state.raw_audio_bytes)} bytes of audio")

            # Try to decode accumulated raw bytes
            try:
                audio_array = self.preprocessor.process(self.state.raw_audio_bytes)
                self.state.audio_buffer = audio_array
                self.state.last_decoded_bytes = len(self.state.raw_audio_bytes)

                # Validate audio data
                if len(audio_array) == 0:
                    logger.warning("Decoded audio is empty")
                    return

                # Check for valid audio (not all zeros/silence)
                max_amplitude = np.max(np.abs(audio_array))
                if max_amplitude < 1e-6:
                    logger.warning(f"Audio appears to be silent (max amplitude: {max_amplitude})")
                    return

                logger.info(f"Decoded {len(audio_array)} samples ({len(audio_array)/16000:.2f}s), max amplitude: {max_amplitude:.4f}")
            except Exception as e:
                logger.warning(f"Could not decode audio yet ({len(self.state.raw_audio_bytes)} bytes): {e}")
                return  # Wait for more data

            # Get expected text as prompt for better accuracy
            expected_text = " ".join(
                ayah.text_normalized for ayah in self.expected_ayahs
            )

            # Transcribe
            result = self.transcriber.transcribe_with_context(
                self.state.audio_buffer,
                initial_prompt=expected_text[:200],  # More context for accuracy
            )

            self.state.last_transcription = result
            self.state.total_duration = len(self.state.audio_buffer) / 16000
            self.last_transcription_time = time.time()

            logger.info(f"Transcription: {result.full_text[:100]}...")
            print(f"[TRANSCRIBE] Full text: {result.full_text}")
            print(f"[TRANSCRIBE] Confirmed words: {[w.text for w in result.confirmed]}")
            print(f"[TRANSCRIBE] Expected tokens: {self.alignment_engine.expected_tokens[:5]}...")

            # Process through alignment engine
            # On final pass (is_finalizing=True), include tentative words
            await self._process_alignment(result, is_final=self.is_finalizing)

        except Exception as e:
            logger.error(f"Error running transcription: {e}")
            import traceback
            traceback.print_exc()

    async def _process_alignment(self, result: TranscriptionResult, is_final: bool = False) -> None:
        """Process transcription through alignment engine.

        Args:
            result: Transcription result from Whisper
            is_final: If True, process ALL words (confirmed + tentative) as final
        """
        # Process ALL words immediately for fastest feedback
        # With TENTATIVE_WORD_COUNT=0, all words are in confirmed anyway
        words_to_process = result.confirmed + result.tentative
        
        if is_final:
            logger.info(f"Final pass: processing {len(words_to_process)} words")
            print(f"[FINAL] Processing ALL words: {[w.text for w in words_to_process]}")
        else:
            logger.info(f"Processing {len(words_to_process)} words ({len(result.confirmed)} confirmed + {len(result.tentative)} tentative)")

        all_words = []
        for word in words_to_process:
            all_words.append(TranscribedWord(
                text=word.text,
                confidence=word.confidence,
                timestamp_ms=int(word.start * 1000),
                is_final=True,
            ))

        # Process ALL words, not just confirmed ones, for immediate feedback
        # Track which words are new since last processing
        new_words = all_words[self.state.words_processed:]

        if not new_words:
            logger.debug(f"No new words to process (total: {len(all_words)}, processed: {self.state.words_processed})")
        else:
            logger.info(f"Processing {len(new_words)} new words immediately")
            for w in new_words:
                normalized = self.normalizer.normalize(w.text)
                print(f"[ALIGN] Processing word: '{w.text}' -> normalized: '{normalized}'")

            # Process new words through alignment engine immediately
            events = self.alignment_engine.process_words(new_words)
            print(f"[ALIGN] Events: {[e.event_type.value for e in events]}")
            print(f"[ALIGN] Position: confirmed={self.alignment_engine.position.confirmed_index}, tentative={self.alignment_engine.position.tentative_index}")

            # Update processed word count
            self.state.words_processed = len(all_words)

            # Process events for mistakes immediately
            for event in events:
                if event.event_type.value in ("mismatch", "skipped"):
                    mistake = Mistake(
                        mistake_type=MistakeType.WRONG_WORD if event.event_type.value == "mismatch" else MistakeType.SKIPPED,
                        ayah=self.alignment_engine.get_ayah_for_token(event.word_index) or (0, 0),
                        word_index=event.word_index or 0,
                        expected=self.alignment_engine.get_expected_word(event.word_index) or "",
                        received=event.received_word,
                        confidence=event.confidence,
                        is_penalty=True,
                        timestamp_ms=event.timestamp_ms,
                    )
                    self.mistakes.append(mistake)

                    if self.on_mistake:
                        await self.on_mistake(mistake)

        # Build word status lists for frontend display
        # Show confirmed words from alignment + tentative from transcription
        confirmed_display = []
        tentative_display = []

        # Get alignment engine position
        confirmed_idx = self.alignment_engine.position.confirmed_index
        tentative_idx = self.alignment_engine.position.tentative_index

        # Build confirmed words (up to confirmed position)
        for i in range(min(confirmed_idx, len(self.alignment_engine.expected_tokens))):
            word = self.alignment_engine.expected_tokens[i]
            confirmed_display.append({
                "word": word,
                "index": i,
                "status": "correct",
            })

        # Build tentative words (confirmed to tentative)
        for i in range(confirmed_idx, min(tentative_idx, len(self.alignment_engine.expected_tokens))):
            word = self.alignment_engine.expected_tokens[i]
            tentative_display.append({
                "word": word,
                "index": i,
                "status": "tentative",
            })

        # Emit transcription update to frontend
        logger.info(f"Sending transcription update: {len(confirmed_display)} confirmed, {len(tentative_display)} tentative")
        if self.on_transcription:
            await self.on_transcription(confirmed_display, tentative_display)

        # Check for ayah completion
        await self._check_ayah_completion()

    async def _check_ayah_completion(self) -> None:
        """Check if any ayahs have been completed."""
        current_ayah_idx, _ = self.alignment_engine.get_confirmed_position()

        # Mark previous ayahs as complete
        for i in range(current_ayah_idx):
            if i not in self.completed_ayah_indices:
                self.completed_ayah_indices.add(i)
                ayah = self.expected_ayahs[i]

                # Count correct words for this ayah
                # (simplified - could be more accurate)
                words_total = len(ayah.text_tokens)
                ayah_mistakes = sum(
                    1 for m in self.mistakes
                    if m.ayah == (ayah.surah, ayah.ayah) and m.is_penalty
                )
                words_correct = words_total - ayah_mistakes

                if self.on_ayah_complete:
                    await self.on_ayah_complete(ayah, words_correct, words_total)

    def get_summary(self) -> dict:
        """Get session summary statistics."""
        total_words = len(self.alignment_engine.expected_tokens)
        mistake_penalties = sum(1 for m in self.mistakes if m.is_penalty)
        words_correct = total_words - mistake_penalties

        return {
            "total_words": total_words,
            "words_correct": words_correct,
            "mistakes": self.mistakes,
            "ayahs_tested": len(self.expected_ayahs),
            "ayahs_correct": len(self.expected_ayahs) - len(set(
                m.ayah for m in self.mistakes if m.is_penalty
            )),
        }

    async def finalize(self) -> None:
        """
        Run final transcription on all remaining audio.

        Called when recording stops to process any accumulated audio
        that hasn't been transcribed yet.
        """
        # Set flag to prevent processing new audio chunks
        self.is_finalizing = True
        logger.info(f"Finalizing transcription: {len(self.state.raw_audio_bytes)} bytes accumulated")

        # Force transcription regardless of timing
        if len(self.state.raw_audio_bytes) > 0:
            # Temporarily disable interval check
            self.last_transcription_time = 0

            await self._run_transcription()

        # Force commit any tentative alignment state
        self.alignment_engine.force_commit()

        # Send final transcription update
        confirmed_idx = self.alignment_engine.position.confirmed_index
        confirmed_display = []
        for i in range(min(confirmed_idx, len(self.alignment_engine.expected_tokens))):
            word = self.alignment_engine.expected_tokens[i]
            confirmed_display.append({
                "word": word,
                "index": i,
                "status": "correct",
            })

        logger.info(f"Sending final transcription update: {len(confirmed_display)} confirmed words")
        if self.on_transcription:
            await self.on_transcription(confirmed_display, [])

        # Log final state
        confirmed, total = self.alignment_engine.get_progress()
        logger.info(f"Final alignment state: {confirmed}/{total} words confirmed")
        logger.info(f"Mistakes recorded: {len(self.mistakes)}")

    def reset(self) -> None:
        """Reset state for a new recording."""
        self.state = TranscriptionState()
        self.state.raw_audio_bytes = b''
        self.state.last_decoded_bytes = 0
        self.state.words_processed = 0
        self.transcriber.reset()
        self.alignment_engine.reset()
        self.mistakes = []
        self.completed_ayah_indices = set()
        self.last_transcription_time = 0.0
