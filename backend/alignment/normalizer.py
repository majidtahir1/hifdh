"""
Arabic Text Normalizer for the Hifdh Review App.

This module provides text normalization for comparing Arabic text,
specifically optimized for Quran recitation comparison.

Strategy: Careful, not aggressive normalization.
- Remove diacritics (tashkeel) for comparison
- Normalize alef variants to bare alef
- Keep ta marbuta (ة) distinct from ha (ه) to catch real mistakes
- Handle hamza on different carriers
"""

import re
from typing import List


class ArabicTextNormalizer:
    """
    Normalizes Arabic text for comparison purposes.

    This normalizer is designed specifically for Quran recitation comparison.
    It balances the need to handle ASR variations while not over-normalizing
    to the point where real memorization mistakes are hidden.

    What we normalize (to handle ASR variations):
    - Tashkeel (diacritics): fatha, damma, kasra, shadda, sukun, etc.
    - Alef variants: أ إ آ ٱ → ا
    - Hamza on different carriers (in some contexts)
    - Tatweel (kashida): ـ

    What we DON'T normalize (to catch real mistakes):
    - Ta marbuta ة vs Ha ه
    - Alef maqsura ى vs Ya ي (these are sometimes legitimate mistakes)
    """

    # Diacritics (tashkeel) - remove for comparison
    # U+064B FATHATAN to U+065F WAVY HAMZA BELOW, plus U+0670 SUPERSCRIPT ALEF
    # Also include Quranic annotation marks U+06D6 to U+06ED
    DIACRITICS_PATTERN = re.compile(r'[\u064B-\u065F\u0670\u06D6-\u06ED]')

    # Alef variants - normalize to bare alef (ا)
    # أ (U+0623) - ALEF WITH HAMZA ABOVE
    # إ (U+0625) - ALEF WITH HAMZA BELOW
    # آ (U+0622) - ALEF WITH MADDA ABOVE
    # ٱ (U+0671) - ALEF WASLA
    ALEF_VARIANTS_PATTERN = re.compile(r'[أإآٱ]')

    # Alef maksura (ى U+0649) vs Yeh (ي U+064A)
    # These look identical in many fonts but are different characters
    # ASR often outputs yeh when the Quran text has alef maksura
    ALEF_MAKSURA_PATTERN = re.compile(r'\u0649')

    # Tatweel (kashida) - the elongation character used for justification
    TATWEEL_PATTERN = re.compile(r'\u0640')

    # Various hamza forms that can be normalized
    # ء (U+0621) - ARABIC LETTER HAMZA (standalone)
    # ؤ (U+0624) - WAW WITH HAMZA ABOVE
    # ئ (U+0626) - YEH WITH HAMZA ABOVE
    # These are kept separate as they may indicate real pronunciation differences

    # Zero-width characters and other invisible characters
    INVISIBLE_CHARS_PATTERN = re.compile(r'[\u200B-\u200F\u202A-\u202E\uFEFF]')

    def __init__(self, normalize_hamza: bool = False):
        """
        Initialize the normalizer.

        Args:
            normalize_hamza: If True, normalize hamza on different carriers
                            to standalone hamza. Default False to catch
                            potential memorization mistakes.
        """
        self.normalize_hamza = normalize_hamza

    def normalize(self, text: str) -> str:
        """
        Normalize Arabic text for comparison purposes.

        This removes diacritics, normalizes alef variants, and cleans up
        invisible characters while preserving meaningful distinctions.

        Args:
            text: The Arabic text to normalize

        Returns:
            Normalized text suitable for comparison
        """
        # Remove invisible characters first
        text = self.INVISIBLE_CHARS_PATTERN.sub('', text)

        # Remove tatweel (elongation character)
        text = self.TATWEEL_PATTERN.sub('', text)

        # Remove diacritics (tashkeel) and Quranic marks
        text = self.DIACRITICS_PATTERN.sub('', text)

        # Normalize alef variants to bare alef
        text = self.ALEF_VARIANTS_PATTERN.sub('ا', text)

        # Normalize alef maksura to yeh (they look identical, ASR often confuses them)
        text = self.ALEF_MAKSURA_PATTERN.sub('ي', text)

        # Optionally normalize hamza on different carriers
        if self.normalize_hamza:
            text = self._normalize_hamza(text)

        # Normalize whitespace (collapse multiple spaces, strip)
        text = ' '.join(text.split())

        return text

    def _normalize_hamza(self, text: str) -> str:
        """
        Normalize hamza on different carriers to standalone hamza.

        This is optional and disabled by default, as hamza placement
        can indicate real pronunciation differences in some contexts.

        Args:
            text: The text to normalize

        Returns:
            Text with normalized hamza
        """
        # ؤ (waw with hamza) -> و + ء or just keep as is
        # ئ (yeh with hamza) -> ي + ء or just keep as is
        # For now, we just remove the hamza from carriers
        # This is aggressive and should only be used if ASR
        # frequently confuses these
        text = text.replace('ؤ', 'و')
        text = text.replace('ئ', 'ي')
        return text

    def tokenize(self, text: str) -> List[str]:
        """
        Split Arabic text into tokens (words).

        This tokenizes on whitespace, which is generally sufficient
        for Quran text. Does NOT normalize the text first - call
        normalize() before tokenize() if needed.

        Args:
            text: The text to tokenize

        Returns:
            List of word tokens
        """
        return [w for w in text.split() if w]

    def normalize_and_tokenize(self, text: str) -> List[str]:
        """
        Normalize text and then tokenize it.

        Convenience method that combines normalize() and tokenize().

        Args:
            text: The text to normalize and tokenize

        Returns:
            List of normalized word tokens
        """
        return self.tokenize(self.normalize(text))

    def words_match(self, word1: str, word2: str, fuzzy: bool = True) -> bool:
        """
        Check if two words match after normalization.

        Args:
            word1: First word to compare
            word2: Second word to compare
            fuzzy: If True, allow fuzzy matching for common ASR errors

        Returns:
            True if the normalized forms match
        """
        norm1 = self.normalize(word1)
        norm2 = self.normalize(word2)

        # Exact match
        if norm1 == norm2:
            return True

        if not fuzzy:
            return False

        # Fuzzy matching for common ASR errors:

        # 0. Uthmani script comparison - remove alifs and compare
        # Uthmani script often omits alifs that appear in standard Arabic
        # e.g., كتب (Uthmani) = كتاب (standard), الصلحت = الصالحات
        norm1_no_alif = norm1.replace('ا', '')
        norm2_no_alif = norm2.replace('ا', '')
        if norm1_no_alif == norm2_no_alif and len(norm1_no_alif) >= 2:
            return True

        # 1. One word is a suffix of the other (dropped initial alif/hamza)
        # e.g., اعوذ vs عوذ, or اذهب vs ذهب
        if norm1.endswith(norm2) or norm2.endswith(norm1):
            # Only allow if the difference is 1-2 characters (prefix)
            diff = abs(len(norm1) - len(norm2))
            if diff <= 2:
                return True

        # 2. One word starts with the other (extra suffix from ASR)
        if len(norm1) >= 2 and len(norm2) >= 2:
            if norm1.startswith(norm2) or norm2.startswith(norm1):
                diff = abs(len(norm1) - len(norm2))
                if diff <= 1:
                    return True

        # 3. Small edit distance for LONGER words only
        # This handles other Uthmani script differences
        # But avoid matching completely different short words like ما and في
        min_len = min(len(norm1), len(norm2))

        # Only use fuzzy edit distance for words with 3+ characters
        if min_len >= 3 and abs(len(norm1) - len(norm2)) <= 2:
            edit_dist = self._levenshtein_distance(norm1, norm2)
            # Allow edit distance of 2 for longer words, 1 for shorter
            max_edit = 2 if min_len >= 4 else 1
            if edit_dist <= max_edit:
                return True

        return False

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def remove_diacritics(self, text: str) -> str:
        """
        Remove only diacritics from text, keeping everything else.

        This is a more minimal normalization that only strips tashkeel.

        Args:
            text: The text to process

        Returns:
            Text with diacritics removed
        """
        return self.DIACRITICS_PATTERN.sub('', text)

    def normalize_alef(self, text: str) -> str:
        """
        Normalize only alef variants, keeping everything else.

        This normalizes أ إ آ ٱ to bare ا.

        Args:
            text: The text to process

        Returns:
            Text with alef variants normalized
        """
        return self.ALEF_VARIANTS_PATTERN.sub('ا', text)
