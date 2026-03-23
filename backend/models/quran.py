"""
Quran data models for the Hifdh Review App.
"""

from dataclasses import dataclass


@dataclass
class AyahText:
    """
    Represents a single ayah (verse) with multiple text representations.

    Three forms are maintained for different purposes:
    - text_uthmani: Display form with full diacritics
    - text_normalized: Comparison form (diacritics removed, alef normalized)
    - text_tokens: Tokenized form for word-by-word alignment
    """
    surah: int
    ayah: int
    juz: int
    audio_url: str

    # Three forms for different purposes
    text_uthmani: str       # Display: "وَعِبَادُ الرَّحْمَٰنِ"
    text_normalized: str    # Comparison: "وعباد الرحمن" (diacritics removed, alef normalized)
    text_tokens: list[str]  # Alignment: ["وعباد", "الرحمن"]

    def __post_init__(self):
        """Validate ayah data after initialization."""
        if self.surah < 1 or self.surah > 114:
            raise ValueError(f"Invalid surah number: {self.surah}")
        if self.ayah < 1:
            raise ValueError(f"Invalid ayah number: {self.ayah}")
        if self.juz < 1 or self.juz > 30:
            raise ValueError(f"Invalid juz number: {self.juz}")
