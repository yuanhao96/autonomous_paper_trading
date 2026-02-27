"""Tests for Wikipedia universe scraper."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.universe.wikipedia import (
    _normalize_ticker,
    fetch_nasdaq100,
    fetch_sp500,
    get_cached_or_fetch,
)

# ── Minimal HTML fixtures ────────────────────────────────────────────

SP500_HTML = """
<html><body>
<table id="constituents" class="wikitable">
<tr><th>Symbol</th><th>Security</th></tr>
<tr><td>AAPL</td><td>Apple Inc.</td></tr>
<tr><td>MSFT</td><td>Microsoft Corp.</td></tr>
<tr><td>BRK.B</td><td>Berkshire Hathaway</td></tr>
</table>
</body></html>
"""

NASDAQ100_HTML = """
<html><body>
<table id="constituents" class="wikitable">
<tr><th>Company</th><th>Ticker</th></tr>
<tr><td>Apple Inc.</td><td>AAPL</td></tr>
<tr><td>Microsoft</td><td> MSFT </td></tr>
</table>
</body></html>
"""


class TestNormalizeTicker:
    def test_strip_whitespace(self):
        assert _normalize_ticker("  AAPL  ") == "AAPL"

    def test_dot_to_dash(self):
        assert _normalize_ticker("BRK.B") == "BRK-B"

    def test_already_clean(self):
        assert _normalize_ticker("MSFT") == "MSFT"


class TestFetchSp500:
    @patch("src.universe.wikipedia.requests.get")
    def test_parses_table(self, mock_get: MagicMock):
        # Build a large enough table to pass the >= 400 check
        rows = "\n".join(
            f"<tr><td>SYM{i:04d}</td><td>Company {i}</td></tr>" for i in range(500)
        )
        html = (
            '<html><body><table id="constituents" class="wikitable">'
            "<tr><th>Symbol</th><th>Security</th></tr>"
            f"{rows}</table></body></html>"
        )
        mock_get.return_value = MagicMock(status_code=200, text=html)
        mock_get.return_value.raise_for_status = MagicMock()

        result = fetch_sp500()
        assert result is not None
        assert len(result) == 500
        assert result[0] == "SYM0000"

    @patch("src.universe.wikipedia.requests.get")
    def test_returns_none_on_network_error(self, mock_get: MagicMock):
        import requests

        mock_get.side_effect = requests.ConnectionError("no network")
        assert fetch_sp500() is None

    @patch("src.universe.wikipedia.requests.get")
    def test_returns_none_on_too_few_tickers(self, mock_get: MagicMock):
        mock_get.return_value = MagicMock(status_code=200, text=SP500_HTML)
        mock_get.return_value.raise_for_status = MagicMock()
        # Only 3 rows in SP500_HTML — below 400 threshold
        assert fetch_sp500() is None


class TestFetchNasdaq100:
    @patch("src.universe.wikipedia.requests.get")
    def test_returns_none_on_too_few_tickers(self, mock_get: MagicMock):
        mock_get.return_value = MagicMock(status_code=200, text=NASDAQ100_HTML)
        mock_get.return_value.raise_for_status = MagicMock()
        # Only 2 rows — below 80 threshold
        assert fetch_nasdaq100() is None

    @patch("src.universe.wikipedia.requests.get")
    def test_parses_table(self, mock_get: MagicMock):
        rows = "\n".join(
            f"<tr><td>Company {i}</td><td>SYM{i:04d}</td></tr>" for i in range(100)
        )
        html = (
            '<html><body><table id="constituents" class="wikitable">'
            "<tr><th>Company</th><th>Ticker</th></tr>"
            f"{rows}</table></body></html>"
        )
        mock_get.return_value = MagicMock(status_code=200, text=html)
        mock_get.return_value.raise_for_status = MagicMock()

        result = fetch_nasdaq100()
        assert result is not None
        assert len(result) == 100


class TestCaching:
    def test_writes_and_reads_cache(self, tmp_path: Path):
        fetcher = MagicMock(return_value=["AAPL", "MSFT"])
        result = get_cached_or_fetch("test", fetcher, cache_dir=tmp_path)
        assert result == ["AAPL", "MSFT"]
        fetcher.assert_called_once()

        # Second call should use cache
        fetcher.reset_mock()
        result2 = get_cached_or_fetch("test", fetcher, cache_dir=tmp_path)
        assert result2 == ["AAPL", "MSFT"]
        fetcher.assert_not_called()

    def test_refetches_after_expiry(self, tmp_path: Path):
        # Write a stale cache entry
        cache_file = tmp_path / "universe_test.json"
        stale_time = "2020-01-01T00:00:00+00:00"
        cache_file.write_text(json.dumps({"symbols": ["OLD"], "fetched_at": stale_time}))

        fetcher = MagicMock(return_value=["NEW1", "NEW2"])
        result = get_cached_or_fetch("test", fetcher, cache_dir=tmp_path)
        assert result == ["NEW1", "NEW2"]
        fetcher.assert_called_once()

    def test_falls_back_to_stale_cache_on_failure(self, tmp_path: Path):
        cache_file = tmp_path / "universe_test.json"
        stale_time = "2020-01-01T00:00:00+00:00"
        cache_file.write_text(json.dumps({"symbols": ["STALE"], "fetched_at": stale_time}))

        fetcher = MagicMock(return_value=None)
        result = get_cached_or_fetch("test", fetcher, cache_dir=tmp_path)
        assert result == ["STALE"]

    def test_returns_none_when_no_cache_and_fetch_fails(self, tmp_path: Path):
        fetcher = MagicMock(return_value=None)
        result = get_cached_or_fetch("test", fetcher, cache_dir=tmp_path)
        assert result is None
