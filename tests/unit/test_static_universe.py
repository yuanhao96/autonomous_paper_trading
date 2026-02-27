"""Tests for static universe definitions."""

import pytest

from src.universe.static import (
    STATIC_UNIVERSES,
    get_static_universe,
    list_static_universes,
)


class TestStaticUniverses:
    def test_sp500_has_symbols(self):
        symbols = get_static_universe("sp500")
        assert len(symbols) >= 50  # at least fallback size
        assert "AAPL" in symbols

    def test_nasdaq100_has_symbols(self):
        symbols = get_static_universe("nasdaq100")
        assert len(symbols) >= 40  # at least fallback size
        assert "MSFT" in symbols

    def test_sector_etfs(self):
        symbols = get_static_universe("sector_etfs")
        assert "XLK" in symbols

    def test_g10_forex(self):
        symbols = get_static_universe("g10_forex")
        assert len(symbols) >= 10

    def test_unknown_universe(self):
        with pytest.raises(ValueError, match="Unknown static universe"):
            get_static_universe("nonexistent")

    def test_list_universes(self):
        names = list_static_universes()
        assert "sp500" in names
        assert "g10_forex" in names
        assert len(names) == len(STATIC_UNIVERSES)

    def test_returns_copy(self):
        """Ensure get_static_universe returns a copy, not a reference."""
        s1 = get_static_universe("sp500")
        s2 = get_static_universe("sp500")
        s1.append("FAKE")
        assert "FAKE" not in s2
