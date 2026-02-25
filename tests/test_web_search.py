"""Tests for fetch_web_search() in knowledge.ingestion."""
from __future__ import annotations

from unittest.mock import patch

from knowledge.store import Document


class TestFetchWebSearch:
    """Tests for the fetch_web_search function."""

    def test_returns_documents_from_search_results(self):
        """Happy path: DDG returns results, we get snippet Documents."""
        from knowledge.ingestion import fetch_web_search

        mock_results = [
            {
                "title": "Market Microstructure Explained",
                "body": "Market microstructure studies how exchanges facilitate trading.",
                "href": "https://example.com/microstructure",
            },
            {
                "title": "Understanding Order Books",
                "body": "An order book lists buy and sell orders for a security.",
                "href": "https://example.com/orderbook",
            },
        ]

        with patch("knowledge.ingestion._ddgs_text_search", return_value=mock_results):
            with patch("knowledge.ingestion.fetch_article", return_value=None):
                docs = fetch_web_search("Market Microstructure", fetch_top_articles=0)

        assert len(docs) == 2
        assert all(isinstance(d, Document) for d in docs)
        assert docs[0].title == "Market Microstructure Explained"
        assert "web_search" in docs[0].topic_tags
        assert "market microstructure" in docs[0].topic_tags
        assert docs[0].source == "https://example.com/microstructure"

    def test_fetches_top_articles(self):
        """When fetch_top_articles > 0, calls fetch_article for top results."""
        from knowledge.ingestion import fetch_web_search

        mock_results = [
            {
                "title": "Article One",
                "body": "Snippet one.",
                "href": "https://example.com/one",
            },
            {
                "title": "Article Two",
                "body": "Snippet two.",
                "href": "https://example.com/two",
            },
        ]

        full_article = Document(
            title="Article One (full)",
            content="Full article content here with lots of detail.",
            source="https://example.com/one",
        )

        with patch("knowledge.ingestion._ddgs_text_search", return_value=mock_results):
            with patch(
                "knowledge.ingestion.fetch_article", return_value=full_article,
            ) as mock_fetch:
                docs = fetch_web_search("test topic", max_results=2, fetch_top_articles=1)

        # 2 snippets + 1 full article = 3 documents
        assert len(docs) == 3
        mock_fetch.assert_called_once_with("https://example.com/one")

    def test_returns_empty_list_when_ddgs_not_installed(self):
        """Graceful fallback when duckduckgo_search is not installed."""
        from knowledge.ingestion import fetch_web_search

        with patch("knowledge.ingestion._ddgs_text_search", side_effect=ImportError("no module")):
            docs = fetch_web_search("some topic")

        assert docs == []

    def test_returns_empty_list_on_search_error(self):
        """Graceful fallback when DDG search raises an exception."""
        from knowledge.ingestion import fetch_web_search

        with patch("knowledge.ingestion._ddgs_text_search", side_effect=Exception("rate limited")):
            docs = fetch_web_search("some topic")

        assert docs == []

    def test_skips_results_with_missing_fields(self):
        """Results missing title or body are skipped."""
        from knowledge.ingestion import fetch_web_search

        mock_results = [
            {"title": "", "body": "no title", "href": "https://example.com/1"},
            {"title": "Has title", "body": "", "href": "https://example.com/2"},
            {"title": "Good Result", "body": "Good body.", "href": "https://example.com/3"},
        ]

        with patch("knowledge.ingestion._ddgs_text_search", return_value=mock_results):
            with patch("knowledge.ingestion.fetch_article", return_value=None):
                docs = fetch_web_search("test", fetch_top_articles=0)

        assert len(docs) == 1
        assert docs[0].title == "Good Result"

    def test_article_fetch_failure_still_returns_snippets(self):
        """If fetch_article fails, snippet Documents are still returned."""
        from knowledge.ingestion import fetch_web_search

        mock_results = [
            {"title": "Article", "body": "Snippet.", "href": "https://example.com/a"},
        ]

        with patch("knowledge.ingestion._ddgs_text_search", return_value=mock_results):
            with patch("knowledge.ingestion.fetch_article", return_value=None):
                docs = fetch_web_search("test", fetch_top_articles=1)

        # 1 snippet, 0 full articles (fetch failed)
        assert len(docs) == 1
        assert docs[0].title == "Article"
