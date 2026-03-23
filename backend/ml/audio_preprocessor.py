"""
Audio Preprocessor for Hifdh Review App.

Handles conversion of various audio formats to the format required by
the Whisper model: 16kHz mono float32 numpy array.
"""

import io
import logging
import subprocess
import tempfile
import os
from typing import Optional

import numpy as np
import soundfile as sf
import librosa

logger = logging.getLogger(__name__)


class AudioPreprocessor:
    """
    Preprocesses audio chunks for transcription.

    Converts various input formats (webm, wav, etc.) to 16kHz mono float32
    numpy arrays suitable for the Whisper model.
    """

    # Target sample rate for Whisper models
    TARGET_SAMPLE_RATE = 16000

    # Target audio format
    TARGET_DTYPE = np.float32

    def __init__(
        self,
        target_sample_rate: int = TARGET_SAMPLE_RATE,
        normalize_audio: bool = True,
        target_db: float = -20.0,
    ):
        """
        Initialize the audio preprocessor.

        Args:
            target_sample_rate: Target sample rate for output (default 16kHz for Whisper)
            normalize_audio: Whether to normalize audio levels
            target_db: Target dB level for normalization (default -20 dB)
        """
        self.target_sample_rate = target_sample_rate
        self.normalize_audio = normalize_audio
        self.target_db = target_db

    def process(self, audio_bytes: bytes) -> np.ndarray:
        """
        Process audio bytes into a numpy array suitable for transcription.

        Args:
            audio_bytes: Raw audio data in any supported format (webm, wav, ogg, mp3, etc.)

        Returns:
            numpy array of shape (samples,) with dtype float32, resampled to target rate

        Raises:
            ValueError: If audio cannot be decoded
        """
        if not audio_bytes:
            raise ValueError("Empty audio data provided")

        # Try to load audio using soundfile first (faster, supports many formats)
        audio_array, sample_rate = self._load_audio(audio_bytes)

        # Convert to mono if stereo
        audio_array = self._to_mono(audio_array)

        # Resample to target rate if needed
        if sample_rate != self.target_sample_rate:
            audio_array = self._resample(audio_array, sample_rate)

        # Normalize audio levels if enabled
        if self.normalize_audio:
            audio_array = self._normalize(audio_array)

        # Ensure float32 dtype
        audio_array = audio_array.astype(self.TARGET_DTYPE)

        return audio_array

    def _load_audio(self, audio_bytes: bytes) -> tuple[np.ndarray, int]:
        """
        Load audio from bytes using soundfile, ffmpeg, or librosa as fallback.

        Returns:
            Tuple of (audio_array, sample_rate)
        """
        audio_buffer = io.BytesIO(audio_bytes)

        # Try soundfile first (faster, handles wav, flac, ogg)
        try:
            audio_array, sample_rate = sf.read(audio_buffer)
            logger.debug(f"Loaded audio with soundfile: {len(audio_array)} samples at {sample_rate}Hz")
            return audio_array.astype(np.float32), sample_rate
        except Exception as e:
            logger.debug(f"soundfile failed: {e}")

        # Try ffmpeg directly for WebM/Opus support
        try:
            audio_array, sample_rate = self._load_with_ffmpeg(audio_bytes)
            logger.info(f"Loaded audio with ffmpeg: {len(audio_array)} samples at {sample_rate}Hz")
            return audio_array, sample_rate
        except Exception as e:
            logger.warning(f"ffmpeg failed: {e}")

        # Fallback to librosa
        audio_buffer.seek(0)
        try:
            audio_array, sample_rate = librosa.load(
                audio_buffer,
                sr=None,  # Preserve original sample rate
                mono=False,  # Handle mono conversion ourselves
            )
            logger.debug(f"Loaded audio with librosa: {audio_array.shape} at {sample_rate}Hz")
            return audio_array, sample_rate
        except Exception as e:
            logger.error(f"Failed to load audio: {e}")
            raise ValueError(f"Could not decode audio data: {e}")

    def _load_with_ffmpeg(self, audio_bytes: bytes) -> tuple[np.ndarray, int]:
        """
        Load audio using ffmpeg subprocess for WebM/Opus support.

        Returns:
            Tuple of (audio_array, sample_rate)
        """
        # Create temp file for input
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
            f.write(audio_bytes)
            input_path = f.name

        output_path = input_path.replace('.webm', '.wav')

        try:
            # Convert to WAV using ffmpeg
            result = subprocess.run(
                [
                    'ffmpeg', '-y', '-i', input_path,
                    '-ar', '16000',  # 16kHz sample rate
                    '-ac', '1',       # Mono
                    '-f', 'wav',
                    output_path
                ],
                capture_output=True,
                timeout=10
            )

            if result.returncode != 0:
                raise ValueError(f"ffmpeg error: {result.stderr.decode()}")

            # Read the WAV file
            audio_array, sample_rate = sf.read(output_path)
            return audio_array.astype(np.float32), sample_rate

        finally:
            # Clean up temp files
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def _to_mono(self, audio_array: np.ndarray) -> np.ndarray:
        """
        Convert stereo audio to mono.

        Args:
            audio_array: Input array, shape (samples,) or (channels, samples) or (samples, channels)

        Returns:
            Mono audio array of shape (samples,)
        """
        if audio_array.ndim == 1:
            # Already mono
            return audio_array

        if audio_array.ndim == 2:
            # Could be (channels, samples) or (samples, channels)
            # librosa uses (channels, samples), soundfile uses (samples, channels)
            if audio_array.shape[0] in (1, 2):
                # Likely (channels, samples)
                return np.mean(audio_array, axis=0)
            else:
                # Likely (samples, channels)
                return np.mean(audio_array, axis=1)

        raise ValueError(f"Unexpected audio array shape: {audio_array.shape}")

    def _resample(self, audio_array: np.ndarray, original_rate: int) -> np.ndarray:
        """
        Resample audio to target sample rate.

        Uses librosa for high-quality resampling.
        """
        logger.debug(f"Resampling from {original_rate}Hz to {self.target_sample_rate}Hz")

        resampled = librosa.resample(
            audio_array,
            orig_sr=original_rate,
            target_sr=self.target_sample_rate,
        )

        return resampled

    def _normalize(self, audio_array: np.ndarray) -> np.ndarray:
        """
        Normalize audio levels to target dB.

        This helps ensure consistent input levels for the model.
        """
        # Calculate current RMS
        rms = np.sqrt(np.mean(audio_array ** 2))

        if rms < 1e-10:
            # Audio is essentially silent
            logger.debug("Audio is silent, skipping normalization")
            return audio_array

        # Calculate current dB
        current_db = 20 * np.log10(rms)

        # Calculate gain needed
        gain_db = self.target_db - current_db
        gain_linear = 10 ** (gain_db / 20)

        # Apply gain
        normalized = audio_array * gain_linear

        # Clip to prevent clipping
        normalized = np.clip(normalized, -1.0, 1.0)

        logger.debug(f"Normalized audio from {current_db:.1f}dB to {self.target_db:.1f}dB")

        return normalized

    def get_duration(self, audio_array: np.ndarray) -> float:
        """
        Calculate duration of audio array in seconds.

        Args:
            audio_array: Processed audio array

        Returns:
            Duration in seconds
        """
        return len(audio_array) / self.target_sample_rate

    def process_with_info(self, audio_bytes: bytes) -> dict:
        """
        Process audio and return both the array and metadata.

        Returns:
            Dictionary with:
                - audio: numpy array
                - duration: float (seconds)
                - sample_rate: int
                - samples: int
        """
        audio_array = self.process(audio_bytes)

        return {
            "audio": audio_array,
            "duration": self.get_duration(audio_array),
            "sample_rate": self.target_sample_rate,
            "samples": len(audio_array),
        }
