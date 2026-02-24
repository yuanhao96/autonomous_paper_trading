"""Tests for knowledge.store — MarkdownMemory knowledge store."""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.store import Document, MarkdownMemory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def memory(tmp_path: Path) -> MarkdownMemory:
    """Create a MarkdownMemory backed by a temporary directory."""
    return MarkdownMemory(memory_root=str(tmp_path / "memory"))


# ---------------------------------------------------------------------------
# Tests — store_curriculum_knowledge
# ---------------------------------------------------------------------------


class TestStoreCurriculumKnowledge:
    def test_creates_file(self, memory: MarkdownMemory) -> None:
        doc = Document(
            title="Test doc",
            content="Moving averages are a popular technical indicator.",
            source="unit_test",
            topic_tags=["technical_analysis"],
        )
        path = memory.store_curriculum_knowledge(
            topic_id="market_microstructure",
            stage_number=1,
            doc=doc,
            synthesized_content="Synthesized content about market microstructure.",
        )
        assert path.exists()
        assert path.name == "market_microstructure.md"

    def test_appends_content(self, memory: MarkdownMemory) -> None:
        doc1 = Document(title="Doc1", content="First batch.", source="test")
        doc2 = Document(title="Doc2", content="Second batch.", source="test")

        memory.store_curriculum_knowledge(
            topic_id="order_types", stage_number=1, doc=doc1,
            synthesized_content="First synthesis.",
        )
        memory.store_curriculum_knowledge(
            topic_id="order_types", stage_number=1, doc=doc2,
            synthesized_content="Second synthesis.",
        )

        content = memory.get_topic_content("order_types", 1)
        assert "First synthesis" in content
        assert "Second synthesis" in content


# ---------------------------------------------------------------------------
# Tests — mastery round-trip
# ---------------------------------------------------------------------------


class TestMastery:
    def test_default_mastery_is_zero(self, memory: MarkdownMemory) -> None:
        assert memory.get_mastery("nonexistent", 1) == 0.0

    def test_set_and_get_mastery(self, memory: MarkdownMemory) -> None:
        memory.set_mastery("market_microstructure", 1, 0.65, reasoning="initial study")
        assert memory.get_mastery("market_microstructure", 1) == pytest.approx(0.65)

    def test_update_mastery(self, memory: MarkdownMemory) -> None:
        memory.set_mastery("order_types", 1, 0.3)
        memory.set_mastery("order_types", 1, 0.75, reasoning="second study")
        assert memory.get_mastery("order_types", 1) == pytest.approx(0.75)

    def test_mastery_with_gaps(self, memory: MarkdownMemory) -> None:
        memory.set_mastery(
            "order_types", 1, 0.5,
            reasoning="partial", gaps=["limit orders", "stop orders"],
        )
        assert memory.get_mastery("order_types", 1) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Tests — daily log
# ---------------------------------------------------------------------------


class TestDailyLog:
    def test_append_daily_log(self, memory: MarkdownMemory) -> None:
        doc = Document(
            title="Market news",
            content="AAPL up 2% on earnings beat.",
            source="alpaca",
            topic_tags=["earnings"],
        )
        path = memory.append_daily_log(doc)
        assert path.exists()
        text = path.read_text()
        assert "Market news" in text
        assert "AAPL up 2%" in text


# ---------------------------------------------------------------------------
# Tests — discovered
# ---------------------------------------------------------------------------


class TestDiscovered:
    def test_store_discovered(self, memory: MarkdownMemory) -> None:
        path = memory.store_discovered(
            topic_name="Gamma Squeeze Mechanics",
            content="Explanation of how gamma squeezes work.",
            source="reddit_analysis",
            tags=["options", "squeeze"],
        )
        assert path.exists()
        assert "gamma_squeeze_mechanics" in path.name
        text = path.read_text()
        assert "gamma squeezes" in text


# ---------------------------------------------------------------------------
# Tests — BM25 search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_returns_results(self, memory: MarkdownMemory) -> None:
        doc = Document(title="Momentum", content="Momentum strategies.", source="test")
        memory.store_curriculum_knowledge(
            topic_id="momentum", stage_number=2, doc=doc,
            synthesized_content="Momentum investing buys stocks with strong recent performance.",
        )
        doc2 = Document(title="Value", content="Value strategies.", source="test")
        memory.store_curriculum_knowledge(
            topic_id="value", stage_number=2, doc=doc2,
            synthesized_content="Value investing focuses on underpriced securities.",
        )

        results = memory.search("momentum performance", n_results=5)
        assert len(results) >= 1
        # The momentum doc should rank higher than the value doc.
        momentum_results = [r for r in results if "momentum" in r["content"].lower()]
        assert len(momentum_results) >= 1

    def test_search_empty_memory(self, memory: MarkdownMemory) -> None:
        results = memory.search("anything")
        assert results == []

    def test_search_with_subdirectory(self, memory: MarkdownMemory) -> None:
        memory.store_discovered(
            topic_name="Pair Trading",
            content="Statistical arbitrage between correlated pairs.",
            source="test",
        )
        results = memory.search("pair arbitrage", subdirectory="discovered")
        assert len(results) >= 1

    def test_search_nonexistent_subdirectory(self, memory: MarkdownMemory) -> None:
        results = memory.search("anything", subdirectory="nonexistent")
        assert results == []


# ---------------------------------------------------------------------------
# Tests — get_topic_content
# ---------------------------------------------------------------------------


class TestGetTopicContent:
    def test_missing_topic(self, memory: MarkdownMemory) -> None:
        assert memory.get_topic_content("missing", 1) == ""

    def test_returns_body(self, memory: MarkdownMemory) -> None:
        doc = Document(title="T", content="C", source="s")
        memory.store_curriculum_knowledge(
            topic_id="test_topic", stage_number=1, doc=doc,
            synthesized_content="Body content here.",
        )
        content = memory.get_topic_content("test_topic", 1)
        assert "Body content here" in content
