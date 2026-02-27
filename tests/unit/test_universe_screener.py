"""Tests for universe screener filter logic."""

from __future__ import annotations

import logging

import pandas as pd

from src.universe.screener import _apply_filter
from src.universe.spec import Filter


class TestApplyFilterWarning:
    """Bug #8: Missing filter columns should emit a warning, not silently no-op."""

    def test_missing_column_emits_warning(self, caplog):
        data = pd.DataFrame({"price": [100, 200, 300]}, index=["A", "B", "C"])
        filt = Filter(field="market_cap", operator="greater_than", value=1e9)

        with caplog.at_level(logging.WARNING, logger="src.universe.screener"):
            result = _apply_filter(data, filt)

        # Data should be returned unchanged
        assert len(result) == 3
        # Warning should have been logged
        assert any("market_cap" in record.message for record in caplog.records)
        assert any("skipped" in record.message.lower() for record in caplog.records)

    def test_present_column_no_warning(self, caplog):
        data = pd.DataFrame({"price": [100, 200, 300]}, index=["A", "B", "C"])
        filt = Filter(field="price", operator="greater_than", value=150)

        with caplog.at_level(logging.WARNING, logger="src.universe.screener"):
            result = _apply_filter(data, filt)

        assert len(result) == 2  # 200, 300
        assert not any("skipped" in record.message.lower() for record in caplog.records)
