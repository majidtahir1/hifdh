"""
Quran Data Service for the Hifdh Review App.

Provides access to Quran ayahs with support for:
- Random ayah selection within juz ranges
- Expected continuation retrieval
- Ayah lookup by surah/ayah reference
"""

import json
import random
from pathlib import Path
from typing import Optional

from models import AyahText


class QuranDataService:
    """
    Service for accessing Quran data.

    Loads quran.json and juz_mapping.json on initialization and provides
    methods for retrieving ayahs for review sessions.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the Quran data service.

        Args:
            data_dir: Path to the data directory containing quran.json and juz_mapping.json.
                     Defaults to backend/data relative to this file.
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"

        self.data_dir = data_dir
        self._ayahs: list[AyahText] = []
        self._juz_mapping: list[dict] = []

        # Build lookup indices
        self._ayah_by_ref: dict[tuple[int, int], AyahText] = {}  # (surah, ayah) -> AyahText
        self._ayahs_by_juz: dict[int, list[AyahText]] = {}  # juz -> list of ayahs

        self._load_data()

    def _load_data(self) -> None:
        """Load and index the Quran data from JSON files."""
        # Load quran.json
        quran_path = self.data_dir / "quran.json"
        with open(quran_path, "r", encoding="utf-8") as f:
            quran_data = json.load(f)

        # Load juz_mapping.json
        juz_path = self.data_dir / "juz_mapping.json"
        with open(juz_path, "r", encoding="utf-8") as f:
            self._juz_mapping = json.load(f)

        # Convert raw data to AyahText objects and build indices
        for ayah_data in quran_data:
            ayah = AyahText(
                surah=ayah_data["surah"],
                ayah=ayah_data["ayah"],
                juz=ayah_data["juz"],
                audio_url=ayah_data["audio_url"],
                text_uthmani=ayah_data["text_uthmani"],
                text_normalized=ayah_data["text_normalized"],
                text_tokens=ayah_data["text_tokens"],
            )
            self._ayahs.append(ayah)

            # Index by reference
            self._ayah_by_ref[(ayah.surah, ayah.ayah)] = ayah

            # Index by juz
            if ayah.juz not in self._ayahs_by_juz:
                self._ayahs_by_juz[ayah.juz] = []
            self._ayahs_by_juz[ayah.juz].append(ayah)

    def get_random_ayah(self, juz_start: int, juz_end: int) -> AyahText:
        """
        Get a random ayah from the specified juz range.

        Args:
            juz_start: Starting juz number (inclusive, 1-30)
            juz_end: Ending juz number (inclusive, 1-30)

        Returns:
            A randomly selected AyahText from the range.

        Raises:
            ValueError: If juz range is invalid or no ayahs found.
        """
        if juz_start < 1 or juz_start > 30:
            raise ValueError(f"Invalid juz_start: {juz_start}. Must be 1-30.")
        if juz_end < 1 or juz_end > 30:
            raise ValueError(f"Invalid juz_end: {juz_end}. Must be 1-30.")
        if juz_start > juz_end:
            raise ValueError(f"juz_start ({juz_start}) cannot be greater than juz_end ({juz_end}).")

        # Collect all ayahs in the range
        candidates: list[AyahText] = []
        for juz in range(juz_start, juz_end + 1):
            if juz in self._ayahs_by_juz:
                candidates.extend(self._ayahs_by_juz[juz])

        if not candidates:
            raise ValueError(f"No ayahs found in juz range {juz_start}-{juz_end}.")

        return random.choice(candidates)

    def get_expected_continuation(self, ayah: AyahText, num_ayahs: int) -> list[AyahText]:
        """
        Get the expected continuation ayahs following the given ayah.

        This returns the ayahs that the student is expected to recite after
        hearing the prompt ayah.

        Args:
            ayah: The prompt ayah (starting point)
            num_ayahs: Number of ayahs to return for the continuation

        Returns:
            List of AyahText objects representing the expected continuation.
            May be shorter than num_ayahs if we reach the end of the Quran.
        """
        if num_ayahs < 1:
            raise ValueError(f"num_ayahs must be at least 1, got {num_ayahs}")

        # Find the index of the given ayah
        try:
            start_idx = self._ayahs.index(ayah)
        except ValueError:
            # Ayah not found by object reference, try by surah/ayah
            ref_ayah = self._ayah_by_ref.get((ayah.surah, ayah.ayah))
            if ref_ayah is None:
                raise ValueError(f"Ayah {ayah.surah}:{ayah.ayah} not found.")
            start_idx = self._ayahs.index(ref_ayah)

        # Return the next num_ayahs ayahs (starting AFTER the prompt)
        continuation_start = start_idx + 1
        continuation_end = min(continuation_start + num_ayahs, len(self._ayahs))

        return self._ayahs[continuation_start:continuation_end]

    def get_ayah_by_ref(self, surah: int, ayah: int) -> Optional[AyahText]:
        """
        Get an ayah by its surah and ayah number.

        Args:
            surah: Surah number (1-114)
            ayah: Ayah number within the surah

        Returns:
            The AyahText if found, None otherwise.
        """
        return self._ayah_by_ref.get((surah, ayah))

    def get_juz_boundaries(self, juz: int) -> Optional[dict]:
        """
        Get the start and end boundaries for a juz.

        Args:
            juz: Juz number (1-30)

        Returns:
            Dictionary with 'start' and 'end' keys containing surah/ayah info,
            or None if juz is invalid.
        """
        if juz < 1 or juz > 30:
            return None

        for mapping in self._juz_mapping:
            if mapping["juz"] == juz:
                return mapping
        return None

    def get_total_ayahs(self) -> int:
        """Get the total number of ayahs loaded."""
        return len(self._ayahs)

    def get_ayahs_in_juz(self, juz: int) -> list[AyahText]:
        """
        Get all ayahs in a specific juz.

        Args:
            juz: Juz number (1-30)

        Returns:
            List of AyahText objects in the juz. Empty list if juz is invalid.
        """
        return self._ayahs_by_juz.get(juz, [])


# Singleton instance for app-wide use
_quran_service: Optional[QuranDataService] = None


def get_quran_service() -> QuranDataService:
    """
    Get the singleton QuranDataService instance.

    Creates the instance on first call.
    """
    global _quran_service
    if _quran_service is None:
        _quran_service = QuranDataService()
    return _quran_service
