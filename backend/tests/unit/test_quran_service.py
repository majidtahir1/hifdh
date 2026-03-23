"""
QA-007: Tests for Quran Data Service.

This module tests the quran data loading and queries in backend/services/quran_data.py:
- Data loading from JSON files
- Random ayah selection
- Expected continuation retrieval
- Ayah lookup by reference
- Juz boundary retrieval
"""

import pytest
from backend.services.quran_data import QuranDataService, get_quran_service


class TestQuranDataServiceInitialization:
    """Test suite for QuranDataService initialization."""

    def test_service_creation(self, quran_service: QuranDataService):
        """Test basic service creation."""
        assert quran_service is not None

    def test_service_loads_data(self, quran_service: QuranDataService):
        """Test that service loads Quran data on initialization."""
        total = quran_service.get_total_ayahs()
        assert total == 6236

    def test_service_builds_indices(self, quran_service: QuranDataService):
        """Test that service builds lookup indices."""
        # Check ayah lookup
        ayah = quran_service.get_ayah_by_ref(1, 1)
        assert ayah is not None

        # Check juz lookup
        ayahs_in_juz = quran_service.get_ayahs_in_juz(1)
        assert len(ayahs_in_juz) > 0


class TestGetRandomAyah:
    """Test suite for random ayah selection."""

    def test_get_random_ayah_single_juz(self, quran_service: QuranDataService):
        """Test getting random ayah from single juz."""
        ayah = quran_service.get_random_ayah(1, 1)
        assert ayah is not None
        assert ayah.juz == 1

    def test_get_random_ayah_range(self, quran_service: QuranDataService):
        """Test getting random ayah from juz range."""
        ayah = quran_service.get_random_ayah(1, 5)
        assert ayah is not None
        assert 1 <= ayah.juz <= 5

    def test_get_random_ayah_full_quran(self, quran_service: QuranDataService):
        """Test getting random ayah from full Quran."""
        ayah = quran_service.get_random_ayah(1, 30)
        assert ayah is not None
        assert 1 <= ayah.juz <= 30

    def test_get_random_ayah_invalid_juz_start_low(self, quran_service: QuranDataService):
        """Test error for juz_start < 1."""
        with pytest.raises(ValueError, match="Invalid juz_start"):
            quran_service.get_random_ayah(0, 5)

    def test_get_random_ayah_invalid_juz_start_high(self, quran_service: QuranDataService):
        """Test error for juz_start > 30."""
        with pytest.raises(ValueError, match="Invalid juz_start"):
            quran_service.get_random_ayah(31, 31)

    def test_get_random_ayah_invalid_juz_end_low(self, quran_service: QuranDataService):
        """Test error for juz_end < 1."""
        with pytest.raises(ValueError, match="Invalid juz_end"):
            quran_service.get_random_ayah(1, 0)

    def test_get_random_ayah_invalid_juz_end_high(self, quran_service: QuranDataService):
        """Test error for juz_end > 30."""
        with pytest.raises(ValueError, match="Invalid juz_end"):
            quran_service.get_random_ayah(1, 31)

    def test_get_random_ayah_invalid_range(self, quran_service: QuranDataService):
        """Test error for juz_start > juz_end."""
        with pytest.raises(ValueError, match="cannot be greater than"):
            quran_service.get_random_ayah(5, 1)

    def test_get_random_ayah_returns_valid_ayah(self, quran_service: QuranDataService):
        """Test that returned ayah has all required fields."""
        ayah = quran_service.get_random_ayah(1, 1)
        assert ayah.surah >= 1
        assert ayah.ayah >= 1
        assert ayah.juz >= 1
        assert len(ayah.text_uthmani) > 0
        assert len(ayah.text_normalized) > 0
        assert len(ayah.text_tokens) > 0


class TestGetExpectedContinuation:
    """Test suite for expected continuation retrieval."""

    def test_get_continuation_simple(self, quran_service: QuranDataService):
        """Test getting continuation ayahs."""
        # Get first ayah of surah 1
        first_ayah = quran_service.get_ayah_by_ref(1, 1)
        continuation = quran_service.get_expected_continuation(first_ayah, 3)

        assert len(continuation) == 3
        # Should be ayahs 2, 3, 4 of surah 1
        assert continuation[0].ayah == 2
        assert continuation[1].ayah == 3
        assert continuation[2].ayah == 4

    def test_get_continuation_single_ayah(self, quran_service: QuranDataService):
        """Test getting single continuation ayah."""
        ayah = quran_service.get_ayah_by_ref(1, 1)
        continuation = quran_service.get_expected_continuation(ayah, 1)

        assert len(continuation) == 1
        assert continuation[0].ayah == 2

    def test_get_continuation_invalid_num_ayahs(self, quran_service: QuranDataService):
        """Test error for num_ayahs < 1."""
        ayah = quran_service.get_ayah_by_ref(1, 1)
        with pytest.raises(ValueError, match="num_ayahs must be at least 1"):
            quran_service.get_expected_continuation(ayah, 0)

    def test_get_continuation_at_end_of_quran(self, quran_service: QuranDataService):
        """Test getting continuation near end of Quran."""
        # Get last ayah
        last_ayah = quran_service.get_ayah_by_ref(114, 6)
        continuation = quran_service.get_expected_continuation(last_ayah, 5)

        # Should return empty list - no more ayahs after last
        assert len(continuation) == 0

    def test_get_continuation_partial_at_end(self, quran_service: QuranDataService):
        """Test getting partial continuation near end of Quran."""
        # Get ayah near end
        near_end = quran_service.get_ayah_by_ref(114, 4)
        continuation = quran_service.get_expected_continuation(near_end, 5)

        # Should return only remaining ayahs
        assert len(continuation) == 2  # Ayahs 5 and 6

    def test_get_continuation_crosses_surah(self, quran_service: QuranDataService):
        """Test continuation crossing surah boundaries."""
        # Last ayah of surah 1
        last_ayah_s1 = quran_service.get_ayah_by_ref(1, 7)
        continuation = quran_service.get_expected_continuation(last_ayah_s1, 3)

        # Should include first ayahs of surah 2
        assert len(continuation) == 3
        assert continuation[0].surah == 2
        assert continuation[0].ayah == 1


class TestGetAyahByRef:
    """Test suite for ayah lookup by reference."""

    def test_get_ayah_by_ref_exists(self, quran_service: QuranDataService):
        """Test getting existing ayah."""
        ayah = quran_service.get_ayah_by_ref(1, 1)
        assert ayah is not None
        assert ayah.surah == 1
        assert ayah.ayah == 1

    def test_get_ayah_by_ref_not_found(self, quran_service: QuranDataService):
        """Test getting non-existent ayah returns None."""
        ayah = quran_service.get_ayah_by_ref(1, 999)
        assert ayah is None

    def test_get_ayah_by_ref_invalid_surah(self, quran_service: QuranDataService):
        """Test getting ayah with invalid surah returns None."""
        ayah = quran_service.get_ayah_by_ref(115, 1)
        assert ayah is None

    def test_get_ayah_by_ref_last_ayah(self, quran_service: QuranDataService):
        """Test getting last ayah of Quran."""
        ayah = quran_service.get_ayah_by_ref(114, 6)
        assert ayah is not None
        assert ayah.surah == 114
        assert ayah.ayah == 6


class TestGetJuzBoundaries:
    """Test suite for juz boundary retrieval."""

    def test_get_juz_boundaries_valid(self, quran_service: QuranDataService):
        """Test getting boundaries for valid juz."""
        boundaries = quran_service.get_juz_boundaries(1)
        assert boundaries is not None
        assert "start" in boundaries
        assert "end" in boundaries
        assert boundaries["juz"] == 1

    def test_get_juz_boundaries_all_juz(self, quran_service: QuranDataService):
        """Test getting boundaries for all 30 juz."""
        for juz in range(1, 31):
            boundaries = quran_service.get_juz_boundaries(juz)
            assert boundaries is not None, f"Missing boundaries for juz {juz}"
            assert boundaries["juz"] == juz

    def test_get_juz_boundaries_invalid_low(self, quran_service: QuranDataService):
        """Test getting boundaries for juz < 1 returns None."""
        boundaries = quran_service.get_juz_boundaries(0)
        assert boundaries is None

    def test_get_juz_boundaries_invalid_high(self, quran_service: QuranDataService):
        """Test getting boundaries for juz > 30 returns None."""
        boundaries = quran_service.get_juz_boundaries(31)
        assert boundaries is None

    def test_juz_1_starts_at_beginning(self, quran_service: QuranDataService):
        """Test juz 1 starts at Surah 1, Ayah 1."""
        boundaries = quran_service.get_juz_boundaries(1)
        assert boundaries["start"]["surah"] == 1
        assert boundaries["start"]["ayah"] == 1

    def test_juz_30_ends_at_quran_end(self, quran_service: QuranDataService):
        """Test juz 30 ends at Surah 114, Ayah 6."""
        boundaries = quran_service.get_juz_boundaries(30)
        assert boundaries["end"]["surah"] == 114
        assert boundaries["end"]["ayah"] == 6


class TestGetAyahsInJuz:
    """Test suite for getting ayahs in a juz."""

    def test_get_ayahs_in_juz_valid(self, quran_service: QuranDataService):
        """Test getting ayahs for valid juz."""
        ayahs = quran_service.get_ayahs_in_juz(1)
        assert len(ayahs) > 0
        for ayah in ayahs:
            assert ayah.juz == 1

    def test_get_ayahs_in_juz_all_juz(self, quran_service: QuranDataService):
        """Test all 30 juz have ayahs."""
        for juz in range(1, 31):
            ayahs = quran_service.get_ayahs_in_juz(juz)
            assert len(ayahs) > 0, f"Juz {juz} has no ayahs"

    def test_get_ayahs_in_juz_invalid(self, quran_service: QuranDataService):
        """Test getting ayahs for invalid juz returns empty list."""
        ayahs = quran_service.get_ayahs_in_juz(0)
        assert ayahs == []

        ayahs = quran_service.get_ayahs_in_juz(31)
        assert ayahs == []


class TestGetTotalAyahs:
    """Test suite for total ayah count."""

    def test_get_total_ayahs(self, quran_service: QuranDataService):
        """Test getting total ayah count."""
        total = quran_service.get_total_ayahs()
        assert total == 6236


class TestSingletonService:
    """Test suite for singleton service pattern."""

    def test_get_quran_service_returns_same_instance(self):
        """Test that get_quran_service returns the same instance."""
        service1 = get_quran_service()
        service2 = get_quran_service()
        assert service1 is service2

    def test_get_quran_service_is_loaded(self):
        """Test that singleton service has data loaded."""
        service = get_quran_service()
        assert service.get_total_ayahs() == 6236
