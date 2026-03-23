"""
QA-005: Tests for Arabic Text Normalizer.

This module tests the normalization functions in backend/alignment/normalizer.py:
- Diacritic removal
- Alef normalization
- Hamza normalization
- Tokenization
- Word matching
"""

import pytest
from backend.alignment.normalizer import ArabicTextNormalizer


class TestDiacriticRemoval:
    """Test suite for diacritic (tashkeel) removal."""

    def test_remove_fatha(self, normalizer: ArabicTextNormalizer):
        """Test removal of fatha diacritic."""
        # Fatha (U+064E) on ba
        text_with_diacritic = "بَ"
        expected = "ب"
        assert normalizer.normalize(text_with_diacritic) == expected

    def test_remove_damma(self, normalizer: ArabicTextNormalizer):
        """Test removal of damma diacritic."""
        # Damma (U+064F) on ba
        text_with_diacritic = "بُ"
        expected = "ب"
        assert normalizer.normalize(text_with_diacritic) == expected

    def test_remove_kasra(self, normalizer: ArabicTextNormalizer):
        """Test removal of kasra diacritic."""
        # Kasra (U+0650) on ba
        text_with_diacritic = "بِ"
        expected = "ب"
        assert normalizer.normalize(text_with_diacritic) == expected

    def test_remove_shadda(self, normalizer: ArabicTextNormalizer):
        """Test removal of shadda diacritic."""
        # Shadda (U+0651) on ra
        text_with_diacritic = "رَّ"
        expected = "ر"
        assert normalizer.normalize(text_with_diacritic) == expected

    def test_remove_sukun(self, normalizer: ArabicTextNormalizer):
        """Test removal of sukun diacritic."""
        # Sukun (U+0652) on lam
        text_with_diacritic = "لْ"
        expected = "ل"
        assert normalizer.normalize(text_with_diacritic) == expected

    def test_remove_tanween_fath(self, normalizer: ArabicTextNormalizer):
        """Test removal of tanween fath (fathatan)."""
        text_with_diacritic = "كِتَابًا"
        # Should remove all diacritics
        result = normalizer.normalize(text_with_diacritic)
        assert "ً" not in result  # No fathatan

    def test_remove_multiple_diacritics(self, normalizer: ArabicTextNormalizer):
        """Test removal of multiple diacritics."""
        text_with_diacritics = "بِسْمِ اللَّهِ"
        result = normalizer.normalize(text_with_diacritics)
        # Should have no diacritics
        assert "ِ" not in result
        assert "ْ" not in result
        assert "ّ" not in result

    def test_remove_diacritics_method(self, normalizer: ArabicTextNormalizer):
        """Test the remove_diacritics method specifically."""
        text = "بِسْمِ"
        result = normalizer.remove_diacritics(text)
        assert result == "بسم"


class TestAlefNormalization:
    """Test suite for alef variant normalization."""

    def test_normalize_alef_with_hamza_above(self, normalizer: ArabicTextNormalizer):
        """Test normalization of alef with hamza above (أ)."""
        text = "أحمد"
        result = normalizer.normalize(text)
        assert result[0] == "ا"  # Should be bare alef

    def test_normalize_alef_with_hamza_below(self, normalizer: ArabicTextNormalizer):
        """Test normalization of alef with hamza below (إ)."""
        text = "إسلام"
        result = normalizer.normalize(text)
        assert result[0] == "ا"

    def test_normalize_alef_with_madda(self, normalizer: ArabicTextNormalizer):
        """Test normalization of alef with madda (آ)."""
        text = "آمن"
        result = normalizer.normalize(text)
        assert result[0] == "ا"

    def test_normalize_alef_wasla(self, normalizer: ArabicTextNormalizer):
        """Test normalization of alef wasla (ٱ)."""
        text = "ٱلرَّحْمَٰنِ"
        result = normalizer.normalize(text)
        assert result[0] == "ا"

    def test_normalize_alef_method(self, normalizer: ArabicTextNormalizer):
        """Test the normalize_alef method specifically."""
        text = "أإآٱ"
        result = normalizer.normalize_alef(text)
        assert result == "اااا"

    def test_preserve_bare_alef(self, normalizer: ArabicTextNormalizer):
        """Test that bare alef is preserved."""
        text = "الله"
        result = normalizer.normalize(text)
        assert "ا" in result


class TestHamzaNormalization:
    """Test suite for hamza normalization (optional feature)."""

    def test_hamza_not_normalized_by_default(self, normalizer: ArabicTextNormalizer):
        """Test that hamza is NOT normalized by default."""
        text = "مؤمن"
        result = normalizer.normalize(text)
        assert "ؤ" in result  # Should be preserved

    def test_hamza_normalized_when_enabled(self, normalizer_with_hamza: ArabicTextNormalizer):
        """Test that hamza IS normalized when enabled."""
        text = "مؤمن"
        result = normalizer_with_hamza.normalize(text)
        assert "ؤ" not in result  # Should be converted to و

    def test_yeh_hamza_normalized_when_enabled(self, normalizer_with_hamza: ArabicTextNormalizer):
        """Test that yeh with hamza is normalized when enabled."""
        text = "رئيس"
        result = normalizer_with_hamza.normalize(text)
        assert "ئ" not in result  # Should be converted to ي


class TestTatweelRemoval:
    """Test suite for tatweel (kashida) removal."""

    def test_remove_tatweel(self, normalizer: ArabicTextNormalizer):
        """Test removal of tatweel character."""
        text = "اللـــــه"  # With tatweel
        result = normalizer.normalize(text)
        assert "ـ" not in result
        assert result == "الله"


class TestInvisibleCharacters:
    """Test suite for invisible character removal."""

    def test_remove_zero_width_space(self, normalizer: ArabicTextNormalizer):
        """Test removal of zero-width space."""
        text = "الله\u200Bالرحمن"  # Zero-width space
        result = normalizer.normalize(text)
        assert "\u200B" not in result

    def test_remove_zero_width_non_joiner(self, normalizer: ArabicTextNormalizer):
        """Test removal of zero-width non-joiner."""
        text = "الله\u200Cالرحمن"
        result = normalizer.normalize(text)
        assert "\u200C" not in result


class TestWhitespaceNormalization:
    """Test suite for whitespace normalization."""

    def test_collapse_multiple_spaces(self, normalizer: ArabicTextNormalizer):
        """Test collapsing multiple spaces to single space."""
        text = "بسم    الله"
        result = normalizer.normalize(text)
        assert result == "بسم الله"

    def test_strip_leading_trailing_space(self, normalizer: ArabicTextNormalizer):
        """Test stripping leading and trailing whitespace."""
        text = "  بسم الله  "
        result = normalizer.normalize(text)
        assert result == "بسم الله"


class TestTokenization:
    """Test suite for text tokenization."""

    def test_tokenize_simple(self, normalizer: ArabicTextNormalizer):
        """Test basic tokenization."""
        text = "بسم الله الرحمن"
        tokens = normalizer.tokenize(text)
        assert tokens == ["بسم", "الله", "الرحمن"]

    def test_tokenize_empty_string(self, normalizer: ArabicTextNormalizer):
        """Test tokenizing empty string."""
        tokens = normalizer.tokenize("")
        assert tokens == []

    def test_tokenize_single_word(self, normalizer: ArabicTextNormalizer):
        """Test tokenizing single word."""
        tokens = normalizer.tokenize("الحمد")
        assert tokens == ["الحمد"]

    def test_normalize_and_tokenize(self, normalizer: ArabicTextNormalizer):
        """Test combined normalize and tokenize."""
        text = "بِسْمِ اللَّهِ"
        tokens = normalizer.normalize_and_tokenize(text)
        assert tokens == ["بسم", "الله"]


class TestWordMatching:
    """Test suite for word matching functionality."""

    def test_words_match_identical(self, normalizer: ArabicTextNormalizer):
        """Test that identical words match."""
        assert normalizer.words_match("الحمد", "الحمد") is True

    def test_words_match_with_diacritics(self, normalizer: ArabicTextNormalizer):
        """Test that words match regardless of diacritics."""
        assert normalizer.words_match("الْحَمْدُ", "الحمد") is True

    def test_words_match_alef_variants(self, normalizer: ArabicTextNormalizer):
        """Test that alef variants match."""
        assert normalizer.words_match("أحمد", "احمد") is True
        assert normalizer.words_match("إسلام", "اسلام") is True

    def test_words_no_match_different(self, normalizer: ArabicTextNormalizer):
        """Test that different words don't match."""
        assert normalizer.words_match("الحمد", "الرحمن") is False

    def test_words_match_preserves_ta_marbuta(self, normalizer: ArabicTextNormalizer):
        """Test that ta marbuta (ة) is NOT normalized to ha (ه)."""
        # This is intentional - ة vs ه is a real mistake
        assert normalizer.words_match("رحمة", "رحمه") is False


class TestComplexCases:
    """Test suite for complex normalization scenarios."""

    def test_full_ayah_normalization(self, normalizer: ArabicTextNormalizer):
        """Test normalizing a complete ayah."""
        # بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
        uthmani = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
        result = normalizer.normalize(uthmani)
        # Should have no diacritics
        assert "ِ" not in result
        assert "ّ" not in result
        # Check normalized form
        tokens = result.split()
        assert len(tokens) == 4

    def test_normalize_preserves_arabic_letters(self, normalizer: ArabicTextNormalizer):
        """Test that Arabic letters are preserved during normalization."""
        text = "قل هو الله احد"
        result = normalizer.normalize(text)
        assert result == "قل هو الله احد"

    def test_normalize_empty_string(self, normalizer: ArabicTextNormalizer):
        """Test normalizing empty string."""
        assert normalizer.normalize("") == ""

    def test_normalize_whitespace_only(self, normalizer: ArabicTextNormalizer):
        """Test normalizing whitespace-only string."""
        assert normalizer.normalize("   ") == ""
