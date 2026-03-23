"""
QA-003: Tests for juz mapping accuracy.

This module verifies:
- juz_mapping.json has exactly 30 entries
- Each entry has required fields (juz, start, end)
- Juz numbers are sequential 1-30
- Ayah ranges are valid and non-overlapping
- Start and end references are valid
"""

import pytest
from pathlib import Path


class TestJuzMappingAccuracy:
    """Test suite for juz_mapping.json accuracy."""

    # Number of juz in the Quran
    EXPECTED_JUZ_COUNT = 30

    # Required fields for each juz entry
    REQUIRED_FIELDS = ["juz", "start", "end"]

    # Required fields for start/end
    REQUIRED_POSITION_FIELDS = ["surah", "ayah"]

    def test_juz_mapping_file_exists(self, juz_mapping_path: Path):
        """Verify juz_mapping.json file exists."""
        assert juz_mapping_path.exists(), f"juz_mapping.json not found at {juz_mapping_path}"

    def test_juz_mapping_has_30_entries(self, juz_mapping: list[dict]):
        """Verify juz_mapping.json contains exactly 30 entries."""
        assert len(juz_mapping) == self.EXPECTED_JUZ_COUNT, (
            f"Expected {self.EXPECTED_JUZ_COUNT} juz entries, got {len(juz_mapping)}"
        )

    def test_all_required_fields_present(self, juz_mapping: list[dict]):
        """Verify each juz entry has all required fields."""
        for idx, entry in enumerate(juz_mapping):
            for field in self.REQUIRED_FIELDS:
                assert field in entry, (
                    f"Juz entry at index {idx} missing required field '{field}'"
                )

            # Check start has required fields
            start = entry.get("start", {})
            for field in self.REQUIRED_POSITION_FIELDS:
                assert field in start, (
                    f"Juz {entry.get('juz')}: start missing '{field}'"
                )

            # Check end has required fields
            end = entry.get("end", {})
            for field in self.REQUIRED_POSITION_FIELDS:
                assert field in end, (
                    f"Juz {entry.get('juz')}: end missing '{field}'"
                )

    def test_juz_numbers_sequential(self, juz_mapping: list[dict]):
        """Verify juz numbers are 1, 2, 3, ..., 30 in order."""
        for idx, entry in enumerate(juz_mapping):
            expected_juz = idx + 1
            actual_juz = entry.get("juz")
            assert actual_juz == expected_juz, (
                f"Juz at index {idx} should be {expected_juz}, got {actual_juz}"
            )

    def test_surah_numbers_valid(self, juz_mapping: list[dict]):
        """Verify all surah numbers are between 1 and 114."""
        for entry in juz_mapping:
            juz = entry.get("juz")
            start_surah = entry["start"]["surah"]
            end_surah = entry["end"]["surah"]

            assert 1 <= start_surah <= 114, (
                f"Juz {juz}: start surah {start_surah} out of range"
            )
            assert 1 <= end_surah <= 114, (
                f"Juz {juz}: end surah {end_surah} out of range"
            )

    def test_ayah_numbers_valid(self, juz_mapping: list[dict]):
        """Verify all ayah numbers are positive."""
        for entry in juz_mapping:
            juz = entry.get("juz")
            start_ayah = entry["start"]["ayah"]
            end_ayah = entry["end"]["ayah"]

            assert start_ayah >= 1, (
                f"Juz {juz}: start ayah {start_ayah} invalid"
            )
            assert end_ayah >= 1, (
                f"Juz {juz}: end ayah {end_ayah} invalid"
            )

    def test_start_before_or_equal_end(self, juz_mapping: list[dict]):
        """Verify start position is before or equal to end position within each juz."""
        for entry in juz_mapping:
            juz = entry.get("juz")
            start_surah = entry["start"]["surah"]
            start_ayah = entry["start"]["ayah"]
            end_surah = entry["end"]["surah"]
            end_ayah = entry["end"]["ayah"]

            # Start surah should be <= end surah
            assert start_surah <= end_surah, (
                f"Juz {juz}: start surah {start_surah} > end surah {end_surah}"
            )

            # If same surah, start ayah should be <= end ayah
            if start_surah == end_surah:
                assert start_ayah <= end_ayah, (
                    f"Juz {juz}: start ayah {start_ayah} > end ayah {end_ayah}"
                )

    def test_juz_boundaries_continuous(self, juz_mapping: list[dict]):
        """Verify juz boundaries are continuous (no gaps or overlaps)."""
        for i in range(len(juz_mapping) - 1):
            current = juz_mapping[i]
            next_juz = juz_mapping[i + 1]

            current_end_surah = current["end"]["surah"]
            current_end_ayah = current["end"]["ayah"]
            next_start_surah = next_juz["start"]["surah"]
            next_start_ayah = next_juz["start"]["ayah"]

            # Next juz should start where current ends
            if current_end_surah == next_start_surah:
                # Same surah: next should start at current_end + 1
                assert next_start_ayah == current_end_ayah + 1, (
                    f"Gap/overlap between juz {current['juz']} and {next_juz['juz']}: "
                    f"juz {current['juz']} ends at {current_end_surah}:{current_end_ayah}, "
                    f"juz {next_juz['juz']} starts at {next_start_surah}:{next_start_ayah}"
                )
            else:
                # Different surah: next should be the next surah, ayah 1
                assert next_start_surah == current_end_surah + 1, (
                    f"Gap/overlap between juz {current['juz']} and {next_juz['juz']}: "
                    f"juz {current['juz']} ends in surah {current_end_surah}, "
                    f"juz {next_juz['juz']} starts in surah {next_start_surah}"
                )
                assert next_start_ayah == 1, (
                    f"Juz {next_juz['juz']} should start at ayah 1 of new surah, "
                    f"got ayah {next_start_ayah}"
                )

    def test_first_juz_starts_at_quran_beginning(self, juz_mapping: list[dict]):
        """Verify juz 1 starts at Surah 1, Ayah 1."""
        first_juz = juz_mapping[0]
        assert first_juz["juz"] == 1, f"First entry is not juz 1: {first_juz['juz']}"
        assert first_juz["start"]["surah"] == 1, (
            f"Juz 1 should start at surah 1, got {first_juz['start']['surah']}"
        )
        assert first_juz["start"]["ayah"] == 1, (
            f"Juz 1 should start at ayah 1, got {first_juz['start']['ayah']}"
        )

    def test_last_juz_ends_at_quran_end(self, juz_mapping: list[dict]):
        """Verify juz 30 ends at Surah 114, Ayah 6."""
        last_juz = juz_mapping[-1]
        assert last_juz["juz"] == 30, f"Last entry is not juz 30: {last_juz['juz']}"
        assert last_juz["end"]["surah"] == 114, (
            f"Juz 30 should end at surah 114, got {last_juz['end']['surah']}"
        )
        assert last_juz["end"]["ayah"] == 6, (
            f"Juz 30 should end at ayah 6, got {last_juz['end']['ayah']}"
        )

    def test_juz_data_types(self, juz_mapping: list[dict]):
        """Verify all numeric fields are integers."""
        for entry in juz_mapping:
            juz = entry.get("juz")

            assert isinstance(entry["juz"], int), (
                f"Juz number should be int, got {type(entry['juz']).__name__}"
            )
            assert isinstance(entry["start"]["surah"], int), (
                f"Juz {juz}: start surah should be int"
            )
            assert isinstance(entry["start"]["ayah"], int), (
                f"Juz {juz}: start ayah should be int"
            )
            assert isinstance(entry["end"]["surah"], int), (
                f"Juz {juz}: end surah should be int"
            )
            assert isinstance(entry["end"]["ayah"], int), (
                f"Juz {juz}: end ayah should be int"
            )

    def test_juz_mapping_matches_quran_data(self, juz_mapping: list[dict], quran_data: list[dict]):
        """Verify juz mapping accurately reflects ayahs in quran.json."""
        # Build a lookup for quran data
        ayah_to_juz = {}
        for ayah in quran_data:
            key = (ayah["surah"], ayah["ayah"])
            ayah_to_juz[key] = ayah["juz"]

        for entry in juz_mapping:
            juz = entry["juz"]
            start_key = (entry["start"]["surah"], entry["start"]["ayah"])
            end_key = (entry["end"]["surah"], entry["end"]["ayah"])

            # Verify start ayah exists and is in correct juz
            assert start_key in ayah_to_juz, (
                f"Juz {juz} start {start_key} not found in quran data"
            )
            assert ayah_to_juz[start_key] == juz, (
                f"Juz {juz} start {start_key} has juz {ayah_to_juz[start_key]} in quran data"
            )

            # Verify end ayah exists and is in correct juz
            assert end_key in ayah_to_juz, (
                f"Juz {juz} end {end_key} not found in quran data"
            )
            assert ayah_to_juz[end_key] == juz, (
                f"Juz {juz} end {end_key} has juz {ayah_to_juz[end_key]} in quran data"
            )
