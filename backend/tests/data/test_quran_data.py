"""
QA-002: Tests for Quran data integrity.

This module verifies:
- quran.json has the correct number of ayahs (6236)
- All required fields are present in each ayah
- Data types are correct
- Juz assignments are valid (1-30)
- Surah numbers are valid (1-114)
"""

import pytest
from pathlib import Path


class TestQuranDataIntegrity:
    """Test suite for quran.json data integrity."""

    # Total number of ayahs in the Quran
    EXPECTED_TOTAL_AYAHS = 6236

    # Required fields for each ayah
    REQUIRED_FIELDS = {
        "surah": int,
        "ayah": int,
        "juz": int,
        "audio_url": str,
        "text_uthmani": str,
        "text_normalized": str,
        "text_tokens": list,
    }

    def test_quran_file_exists(self, quran_json_path: Path):
        """Verify quran.json file exists."""
        assert quran_json_path.exists(), f"quran.json not found at {quran_json_path}"

    def test_quran_has_correct_ayah_count(self, quran_data: list[dict]):
        """Verify quran.json contains exactly 6236 ayahs."""
        assert len(quran_data) == self.EXPECTED_TOTAL_AYAHS, (
            f"Expected {self.EXPECTED_TOTAL_AYAHS} ayahs, got {len(quran_data)}"
        )

    def test_all_required_fields_present(self, quran_data: list[dict]):
        """Verify each ayah has all required fields."""
        for idx, ayah in enumerate(quran_data):
            for field, expected_type in self.REQUIRED_FIELDS.items():
                assert field in ayah, (
                    f"Ayah at index {idx} missing required field '{field}'"
                )

    def test_all_fields_have_correct_types(self, quran_data: list[dict]):
        """Verify each field has the correct data type."""
        for idx, ayah in enumerate(quran_data):
            for field, expected_type in self.REQUIRED_FIELDS.items():
                if field in ayah:
                    assert isinstance(ayah[field], expected_type), (
                        f"Ayah at index {idx}: field '{field}' expected {expected_type.__name__}, "
                        f"got {type(ayah[field]).__name__}"
                    )

    def test_surah_numbers_valid(self, quran_data: list[dict]):
        """Verify all surah numbers are between 1 and 114."""
        for idx, ayah in enumerate(quran_data):
            surah = ayah.get("surah")
            assert 1 <= surah <= 114, (
                f"Ayah at index {idx} has invalid surah number: {surah}"
            )

    def test_juz_numbers_valid(self, quran_data: list[dict]):
        """Verify all juz numbers are between 1 and 30."""
        for idx, ayah in enumerate(quran_data):
            juz = ayah.get("juz")
            assert 1 <= juz <= 30, (
                f"Ayah at index {idx} has invalid juz number: {juz}"
            )

    def test_ayah_numbers_valid(self, quran_data: list[dict]):
        """Verify all ayah numbers are positive."""
        for idx, ayah in enumerate(quran_data):
            ayah_num = ayah.get("ayah")
            assert ayah_num >= 1, (
                f"Ayah at index {idx} has invalid ayah number: {ayah_num}"
            )

    def test_text_uthmani_not_empty(self, quran_data: list[dict]):
        """Verify text_uthmani is not empty for any ayah."""
        for idx, ayah in enumerate(quran_data):
            text = ayah.get("text_uthmani", "")
            assert text.strip(), (
                f"Ayah at index {idx} ({ayah.get('surah')}:{ayah.get('ayah')}) "
                f"has empty text_uthmani"
            )

    def test_text_normalized_not_empty(self, quran_data: list[dict]):
        """Verify text_normalized is not empty for any ayah."""
        for idx, ayah in enumerate(quran_data):
            text = ayah.get("text_normalized", "")
            assert text.strip(), (
                f"Ayah at index {idx} ({ayah.get('surah')}:{ayah.get('ayah')}) "
                f"has empty text_normalized"
            )

    def test_text_tokens_not_empty(self, quran_data: list[dict]):
        """Verify text_tokens is not empty for any ayah."""
        for idx, ayah in enumerate(quran_data):
            tokens = ayah.get("text_tokens", [])
            assert len(tokens) > 0, (
                f"Ayah at index {idx} ({ayah.get('surah')}:{ayah.get('ayah')}) "
                f"has empty text_tokens"
            )

    def test_audio_url_format(self, quran_data: list[dict]):
        """Verify audio URLs have proper format."""
        for idx, ayah in enumerate(quran_data):
            audio_url = ayah.get("audio_url", "")
            assert audio_url.startswith("http"), (
                f"Ayah at index {idx} ({ayah.get('surah')}:{ayah.get('ayah')}) "
                f"has invalid audio_url: {audio_url}"
            )

    def test_first_ayah_is_fatiha(self, quran_data: list[dict]):
        """Verify the first ayah is Surah Al-Fatiha verse 1."""
        first_ayah = quran_data[0]
        assert first_ayah["surah"] == 1, f"First ayah surah is not 1: {first_ayah['surah']}"
        assert first_ayah["ayah"] == 1, f"First ayah number is not 1: {first_ayah['ayah']}"

    def test_last_ayah_is_nas(self, quran_data: list[dict]):
        """Verify the last ayah is Surah An-Nas verse 6."""
        last_ayah = quran_data[-1]
        assert last_ayah["surah"] == 114, f"Last ayah surah is not 114: {last_ayah['surah']}"
        assert last_ayah["ayah"] == 6, f"Last ayah number is not 6: {last_ayah['ayah']}"

    def test_ayahs_are_in_order(self, quran_data: list[dict]):
        """Verify ayahs are in sequential order by surah and ayah number."""
        prev_surah = 0
        prev_ayah = 0

        for idx, ayah in enumerate(quran_data):
            surah = ayah["surah"]
            ayah_num = ayah["ayah"]

            if surah == prev_surah:
                # Same surah - ayah should be +1
                assert ayah_num == prev_ayah + 1, (
                    f"Ayah order incorrect at index {idx}: "
                    f"expected {surah}:{prev_ayah + 1}, got {surah}:{ayah_num}"
                )
            else:
                # New surah - should be next surah, ayah 1
                assert surah == prev_surah + 1, (
                    f"Surah order incorrect at index {idx}: "
                    f"expected surah {prev_surah + 1}, got {surah}"
                )
                assert ayah_num == 1, (
                    f"New surah should start at ayah 1, got {ayah_num} at index {idx}"
                )

            prev_surah = surah
            prev_ayah = ayah_num

    def test_all_30_juz_represented(self, quran_data: list[dict]):
        """Verify all 30 juz are represented in the data."""
        juz_set = set(ayah["juz"] for ayah in quran_data)
        expected_juz = set(range(1, 31))
        assert juz_set == expected_juz, (
            f"Missing juz: {expected_juz - juz_set}"
        )

    def test_all_114_surahs_represented(self, quran_data: list[dict]):
        """Verify all 114 surahs are represented in the data."""
        surah_set = set(ayah["surah"] for ayah in quran_data)
        expected_surahs = set(range(1, 115))
        assert surah_set == expected_surahs, (
            f"Missing surahs: {expected_surahs - surah_set}"
        )
