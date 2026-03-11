"""Unit tests for stratgen.allocator module."""

import numpy as np
import pandas as pd

from stratgen.allocator import allocate_alpha_proportional


class TestAllocateAlphaProportional:
    def test_basic_allocation(self):
        scores = pd.Series({"A": 2.0, "B": 1.0, "C": 0.5}, name="alpha")
        weights = allocate_alpha_proportional(scores, top_n=3, max_position=1.0)

        assert len(weights) == 3
        assert abs(weights.sum() - 1.0) < 1e-6
        # A has highest score, should have highest weight
        assert weights["A"] > weights["B"] > weights["C"]

    def test_position_cap(self):
        scores = pd.Series({"A": 10.0, "B": 1.0, "C": 1.0}, name="alpha")
        weights = allocate_alpha_proportional(scores, top_n=3, max_position=0.40)

        assert weights["A"] <= 0.40 + 1e-6
        assert abs(weights.sum() - 1.0) < 1e-4

    def test_top_n_filtering(self):
        scores = pd.Series({"A": 3.0, "B": 2.0, "C": 1.0, "D": 0.5}, name="alpha")
        weights = allocate_alpha_proportional(scores, top_n=2, max_position=1.0)

        assert len(weights) == 2
        assert "A" in weights.index
        assert "B" in weights.index
        assert "C" not in weights.index

    def test_negative_scores_excluded(self):
        scores = pd.Series({"A": 2.0, "B": -1.0, "C": 0.5}, name="alpha")
        weights = allocate_alpha_proportional(scores, top_n=10, max_position=1.0)

        assert "B" not in weights.index
        assert len(weights) == 2

    def test_empty_scores(self):
        scores = pd.Series({"A": -1.0, "B": -2.0}, name="alpha")
        weights = allocate_alpha_proportional(scores, top_n=10, max_position=1.0)

        assert weights.empty

    def test_weights_sum_to_one(self):
        rng = np.random.default_rng(42)
        scores = pd.Series(
            rng.uniform(0.1, 5.0, 50),
            index=[f"T{i}" for i in range(50)],
        )
        weights = allocate_alpha_proportional(scores, top_n=20, max_position=0.10)

        assert len(weights) == 20
        assert abs(weights.sum() - 1.0) < 1e-3
        assert (weights <= 0.10 + 1e-4).all()

    def test_single_stock(self):
        scores = pd.Series({"A": 1.0}, name="alpha")
        weights = allocate_alpha_proportional(scores, top_n=10, max_position=1.0)

        assert len(weights) == 1
        assert abs(weights["A"] - 1.0) < 1e-6

    def test_sorted_descending(self):
        scores = pd.Series({"A": 1.0, "B": 3.0, "C": 2.0}, name="alpha")
        weights = allocate_alpha_proportional(scores, top_n=3, max_position=1.0)

        # Should be sorted by weight descending
        assert list(weights.index) == ["B", "C", "A"]
