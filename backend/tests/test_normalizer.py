"""
Unit tests for Arabic text normalizer.

Tests Uthmani vs standard Arabic matching without needing audio.
"""

import pytest

# Uses normalizer fixture from conftest.py


class TestNormalization:
    """Test basic normalization."""

    def test_removes_diacritics(self, normalizer):
        assert normalizer.normalize("كِتَابٌ") == "كتاب"
        assert normalizer.normalize("بِسْمِ") == "بسم"

    def test_normalizes_alef_variants(self, normalizer):
        assert normalizer.normalize("أَلَمْ") == "الم"
        assert normalizer.normalize("إِنَّ") == "ان"
        assert normalizer.normalize("ٱلْحَمْدُ") == "الحمد"

    def test_removes_quranic_marks(self, normalizer):
        # Small high meem (U+06ED)
        assert normalizer.normalize("كتبۭ") == "كتب"
        assert normalizer.normalize("مرقومۭ") == "مرقوم"


class TestUthmaniMatching:
    """Test Uthmani script vs standard Arabic matching."""

    def test_kitab_matches(self, normalizer):
        # كتب (Uthmani) should match كتاب (standard)
        assert normalizer.words_match("كتاب", "كتب", fuzzy=True)
        assert normalizer.words_match("كِتَابٌ", "كتبۭ", fuzzy=True)

    def test_salihaat_matches(self, normalizer):
        # الصلحت (Uthmani) should match الصالحات (standard)
        assert normalizer.words_match("الصالحات", "الصلحت", fuzzy=True)

    def test_alim_matches(self, normalizer):
        # الم with diacritics should match
        assert normalizer.words_match("أَلَمْ", "الم", fuzzy=True)

    def test_yashhaduhu_matches(self, normalizer):
        # يشهده variations
        assert normalizer.words_match("يَشْهَدُهُ", "يشهده", fuzzy=True)
        assert normalizer.words_match("يَشْهَدُ", "يشهده", fuzzy=True)

    def test_muqarraboon_matches(self, normalizer):
        # المقربون
        assert normalizer.words_match("الْمُقَرَّبُونَ", "المقربون", fuzzy=True)


class TestFuzzyMatching:
    """Test fuzzy matching for ASR errors."""

    def test_dropped_initial_alif(self, normalizer):
        # ASR sometimes drops initial alif
        assert normalizer.words_match("اعوذ", "عوذ", fuzzy=True)

    def test_extra_suffix(self, normalizer):
        # ASR sometimes adds extra sounds
        assert normalizer.words_match("رب", "ربي", fuzzy=True)

    def test_different_words_dont_match(self, normalizer):
        # Completely different words should NOT match
        assert not normalizer.words_match("ما", "في", fuzzy=True)
        assert not normalizer.words_match("هو", "هي", fuzzy=True)

    def test_similar_but_different_words(self, normalizer):
        # Words that look similar but are different
        # This is tricky - we want to catch real mistakes
        # الربون is NOT المقربون (different words)
        # But our fuzzy matching might match them - this tests current behavior
        pass  # TODO: decide on desired behavior


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_string(self, normalizer):
        assert normalizer.normalize("") == ""
        assert not normalizer.words_match("", "test", fuzzy=True)

    def test_whitespace(self, normalizer):
        assert normalizer.normalize("  كتاب  ") == "كتاب"

    def test_mixed_content(self, normalizer):
        # Should handle mixed Arabic and other content
        text = normalizer.normalize("بِسْمِ اللَّهِ")
        assert text == "بسم الله"
