# Web Search Knowledge Source — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add DuckDuckGo web search as an additional knowledge source in the nightly learning pipeline.

**Architecture:** New `fetch_web_search()` function in `knowledge/ingestion.py` that queries DuckDuckGo for topic-relevant content, creates snippet Documents, and optionally fetches full article text via the existing `fetch_article()`. Integrated into the learning script as a step between Wikipedia and synthesis.

**Tech Stack:** `duckduckgo_search` Python package (free, no API key), existing `urllib`-based `fetch_article()`.

---

### Task 1: Add `duckduckgo_search` dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add the dependency**

Append `duckduckgo_search>=6.0.0` to `requirements.txt` after the existing dependencies (line 14):

```
duckduckgo_search>=6.0.0
```

**Step 2: Install it**

Run: `pip install duckduckgo_search>=6.0.0`
Expected: Successfully installed

**Step 3: Verify import works**

Run: `python -c "from duckduckgo_search import DDGS; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add duckduckgo_search dependency for web search knowledge source"
```

---

### Task 2: Add web search config to settings.yaml

**Files:**
- Modify: `config/settings.yaml:14-28` (under `data:` section)

**Step 1: Add config keys**

Add these two lines at the end of the `data:` block in `config/settings.yaml` (after line 28, `book_skip_chars: 3000`):

```yaml
  # Web search settings for nightly learning.
  web_search_max_results: 5
  web_search_fetch_articles: 2
```

**Step 2: Verify YAML is valid**

Run: `python -c "import yaml; yaml.safe_load(open('config/settings.yaml')); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add config/settings.yaml
git commit -m "feat: add web search config keys to settings.yaml"
```

---

### Task 3: Write the test for `fetch_web_search()`

**Files:**
- Create: `tests/test_web_search.py`

**Step 1: Write the test file**

```python
"""Tests for fetch_web_search() in knowledge.ingestion."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

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
            with patch("knowledge.ingestion.fetch_article", return_value=full_article) as mock_fetch:
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_web_search.py -v`
Expected: FAIL — `_ddgs_text_search` does not exist yet in `knowledge.ingestion`

**Step 3: Commit the test file**

```bash
git add tests/test_web_search.py
git commit -m "test: add tests for fetch_web_search (red phase)"
```

---

### Task 4: Implement `fetch_web_search()` in `knowledge/ingestion.py`

**Files:**
- Modify: `knowledge/ingestion.py` (insert after `fetch_arxiv`, before `fetch_alpaca_news` — after line 553)

**Step 1: Add the helper and main function**

Insert the following after `fetch_arxiv` (line 553) and before `fetch_alpaca_news` (line 556):

```python


def _ddgs_text_search(query: str, max_results: int = 5) -> list[dict]:
    """Run a DuckDuckGo text search via the ``duckduckgo_search`` package.

    Isolated into its own function so tests can mock it without touching
    the third-party import.

    Returns a list of result dicts with keys ``title``, ``body``, ``href``.
    Raises ``ImportError`` if the package is not installed.
    """
    from duckduckgo_search import DDGS  # soft import

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return results


def fetch_web_search(
    topic: str,
    max_results: int = 5,
    fetch_top_articles: int = 2,
) -> list[Document]:
    """Fetch web search results for a trading/finance topic via DuckDuckGo.

    Creates ``Document`` objects from search snippets.  Optionally fetches
    full article content for the top results via :func:`fetch_article`.

    Parameters
    ----------
    topic:
        Topic name to search for (e.g. ``"Market Microstructure"``).
    max_results:
        Maximum number of search snippets to return.
    fetch_top_articles:
        Number of top results to fetch as full articles (default 2).
        Set to 0 to skip article fetching.

    Returns
    -------
    list[Document]
        Snippet documents, plus any successfully fetched full articles.
        Returns an empty list if the search fails or the package is
        not installed.
    """
    search_query = f"{topic} trading finance"
    topic_tag = topic.lower()

    try:
        raw_results = _ddgs_text_search(search_query, max_results=max_results)
    except ImportError:
        logger.warning(
            "duckduckgo_search is not installed; skipping web search for '%s'. "
            "Install with: pip install duckduckgo_search",
            topic,
        )
        return []
    except Exception as exc:
        logger.warning("Web search failed for '%s': %s", topic, exc)
        return []

    documents: list[Document] = []
    article_urls: list[str] = []

    for result in raw_results:
        title = (result.get("title") or "").strip()
        body = (result.get("body") or "").strip()
        href = (result.get("href") or "").strip()

        if not title or not body:
            continue

        documents.append(
            Document(
                title=title,
                content=body,
                source=href,
                timestamp=_utcnow_iso(),
                topic_tags=["web_search", topic_tag],
            )
        )

        if href and len(article_urls) < fetch_top_articles:
            article_urls.append(href)

    # Fetch full article content for the top results.
    for url in article_urls:
        try:
            import time
            time.sleep(1)  # Rate-limit respect.
            article_doc = fetch_article(url)
            if article_doc is not None:
                article_doc.topic_tags = ["web_search", "full_article", topic_tag]
                documents.append(article_doc)
        except Exception as exc:
            logger.warning("Failed to fetch full article '%s': %s", url, exc)

    logger.info(
        "Web search: %d snippet(s) + %d article(s) for topic '%s'.",
        len(documents) - len([d for d in documents if "full_article" in d.topic_tags]),
        len([d for d in documents if "full_article" in d.topic_tags]),
        topic,
    )
    return documents
```

**Step 2: Run the tests**

Run: `pytest tests/test_web_search.py -v`
Expected: All 6 tests PASS

**Step 3: Run the full test suite to check for regressions**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add knowledge/ingestion.py
git commit -m "feat: add fetch_web_search() using DuckDuckGo"
```

---

### Task 5: Integrate web search into the learning script

**Files:**
- Modify: `scripts/simulate_learning.py`

**Step 1: Add the import**

At line 33, after the `fetch_wikipedia` import, add:

```python
from knowledge.ingestion import fetch_web_search
```

**Step 2: Add `--skip-web` CLI flag**

In the `main()` function (around line 364), after the `--skip-wiki` argument, add:

```python
    parser.add_argument("--skip-web", action="store_true",
                        help="Skip web search (use only books + Wikipedia).")
```

**Step 3: Add `skip_web` parameter to `simulate_topic_learning()`**

Update the function signature (line 195-202) to add `skip_web: bool = False`:

```python
def simulate_topic_learning(
    topic,
    memory: MarkdownMemory,
    synthesizer: KnowledgeSynthesizer,
    tracker: CurriculumTracker,
    *,
    skip_wiki: bool = False,
    skip_web: bool = False,
    dry_run: bool = False,
) -> dict:
```

**Step 4: Add the web search step**

Insert after the Wikipedia block (after line 249, `logger.info("[Step 2] Skipping Wikipedia (--skip-wiki).")`) and before the `if not documents:` check (line 251):

```python

    # ------------------------------------------------------------------
    # Step 2b: Web search (supplementary)
    # ------------------------------------------------------------------
    if not skip_web:
        logger.info("[Step 2b] Web searching for '%s'...", topic.name)
        web_docs = fetch_web_search(topic.name, max_results=5, fetch_top_articles=2)
        if web_docs:
            snippet_count = len([d for d in web_docs if "full_article" not in d.topic_tags])
            article_count = len(web_docs) - snippet_count
            logger.info("  Got %d snippet(s) + %d full article(s) from web search.",
                        snippet_count, article_count)
            documents.extend(web_docs)
        else:
            logger.info("  No web search results found.")
    else:
        logger.info("[Step 2b] Skipping web search (--skip-web).")
```

**Step 5: Pass `skip_web` from `main()` to the function call**

Update the call in `main()` (around line 391-394):

```python
        result = simulate_topic_learning(
            topic, memory, synthesizer, tracker,
            skip_wiki=args.skip_wiki,
            skip_web=args.skip_web,
            dry_run=args.dry_run,
        )
```

**Step 6: Verify with a dry run**

Run: `python scripts/simulate_learning.py --dry-run --topics 1`
Expected: Output shows `[Step 2b] Web searching for '...'` and reports snippet/article counts, followed by a higher total document count than before.

**Step 7: Verify skip flag works**

Run: `python scripts/simulate_learning.py --dry-run --skip-web --topics 1`
Expected: Output shows `[Step 2b] Skipping web search (--skip-web).`

**Step 8: Commit**

```bash
git add scripts/simulate_learning.py
git commit -m "feat: integrate web search into learning pipeline"
```

---

### Task 6: End-to-end test with one topic

**Step 1: Run the full learning pipeline for 1 topic**

Run: `python scripts/simulate_learning.py --topics 1 --skip-wiki`
Expected: The pipeline runs through all steps including web search. Web search adds documents. The summary shows web search contributing to the total document count.

Note: This uses the local extraction synthesizer (no MOONSHOT_API_KEY). The web search Documents will be incorporated into the keyword extraction.

**Step 2: Verify the curriculum file was updated**

Run: `ls knowledge/memory/trading/curriculum/stage_1/`
Expected: Topic markdown files exist and have been updated with new content.

**Step 3: Commit any generated knowledge files if desired, or leave them gitignored**

No commit needed for generated knowledge files — they are session artifacts.

---

## Summary of commits

1. `feat: add duckduckgo_search dependency`
2. `feat: add web search config keys to settings.yaml`
3. `test: add tests for fetch_web_search (red phase)`
4. `feat: add fetch_web_search() using DuckDuckGo`
5. `feat: integrate web search into learning pipeline`
