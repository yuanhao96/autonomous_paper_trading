"""Tests for knowledge.store — ChromaDB-backed semantic knowledge store."""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.store import Document, KnowledgeStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> KnowledgeStore:
    """Create a KnowledgeStore backed by a temporary directory."""
    return KnowledgeStore(persist_dir=str(tmp_path / "chroma_test"))


# ---------------------------------------------------------------------------
# Tests — add_document and query
# ---------------------------------------------------------------------------


class TestAddAndQuery:
    def test_add_document_returns_id(self, store: KnowledgeStore) -> None:
        doc = Document(
            title="Test doc",
            content="Moving averages are a popular technical indicator.",
            source="unit_test",
            topic_tags=["technical_analysis"],
        )
        doc_id = store.add_document(doc, collection_name="general")
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0

    def test_query_returns_added_document(self, store: KnowledgeStore) -> None:
        doc = Document(
            title="RSI Explanation",
            content="The Relative Strength Index measures momentum of price changes.",
            source="textbook",
            topic_tags=["momentum", "indicators"],
        )
        store.add_document(doc, collection_name="general")

        results = store.query("What is RSI?", collection_name="general", n_results=5)
        assert len(results) >= 1
        assert "id" in results[0]
        assert "content" in results[0]
        assert "metadata" in results[0]
        assert "distance" in results[0]
        assert "momentum" in results[0]["content"].lower() or "rsi" in results[0]["content"].lower()

    def test_query_empty_collection(self, store: KnowledgeStore) -> None:
        results = store.query("anything", collection_name="empty_collection")
        assert results == []


# ---------------------------------------------------------------------------
# Tests — list_by_topic
# ---------------------------------------------------------------------------


class TestListByTopic:
    def test_list_by_topic_filters(self, store: KnowledgeStore) -> None:
        doc_a = Document(
            title="Momentum Intro",
            content="Momentum is about buying winners.",
            source="test",
            topic_tags=["momentum"],
        )
        doc_b = Document(
            title="Value Intro",
            content="Value investing focuses on cheap stocks.",
            source="test",
            topic_tags=["value"],
        )
        store.add_document(doc_a, collection_name="general")
        store.add_document(doc_b, collection_name="general")

        momentum_docs = store.list_by_topic("momentum", collection_name="general")
        assert len(momentum_docs) >= 1
        # All returned docs should have "momentum" in topic_tags.
        for d in momentum_docs:
            assert "momentum" in d["metadata"]["topic_tags"]

    def test_list_by_topic_empty(self, store: KnowledgeStore) -> None:
        results = store.list_by_topic("nonexistent_topic", collection_name="general")
        assert results == []


# ---------------------------------------------------------------------------
# Tests — count
# ---------------------------------------------------------------------------


class TestCount:
    def test_count_empty(self, store: KnowledgeStore) -> None:
        assert store.count("general") == 0

    def test_count_after_adds(self, store: KnowledgeStore) -> None:
        for i in range(3):
            doc = Document(
                title=f"Doc {i}",
                content=f"Content for document number {i}.",
                source="test",
                topic_tags=["test"],
            )
            store.add_document(doc, collection_name="general")
        assert store.count("general") == 3

    def test_count_nonexistent_collection(self, store: KnowledgeStore) -> None:
        assert store.count("does_not_exist") == 0


# ---------------------------------------------------------------------------
# Tests — multiple collections
# ---------------------------------------------------------------------------


class TestMultipleCollections:
    def test_documents_in_different_collections(self, store: KnowledgeStore) -> None:
        doc_a = Document(title="A", content="Content A", source="test", topic_tags=["a"])
        doc_b = Document(title="B", content="Content B", source="test", topic_tags=["b"])

        store.add_document(doc_a, collection_name="stage_1_foundations")
        store.add_document(doc_b, collection_name="stage_2_strategies")

        assert store.count("stage_1_foundations") == 1
        assert store.count("stage_2_strategies") == 1
        assert store.count("general") == 0
