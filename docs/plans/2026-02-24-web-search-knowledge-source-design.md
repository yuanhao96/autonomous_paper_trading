# Web Search as Knowledge Source for Learning Pipeline

**Date:** 2026-02-24
**Status:** Approved

## Problem

The nightly learning pipeline currently draws from two sources per topic:
1. Pre-ingested book chunks (BM25 search over 1036 chunks in `discovered/`)
2. Wikipedia summaries (live fetch per topic)

This misses current articles, tutorials, and educational content available on the broader web. Adding general web search would supplement the book-heavy knowledge base with diverse, up-to-date perspectives.

## Decision

Add a `fetch_web_search()` function to `knowledge/ingestion.py` using DuckDuckGo (free, no API key). Integrate it as an additional source in the learning pipeline alongside books and Wikipedia.

## Design

### New function: `fetch_web_search()`

Location: `knowledge/ingestion.py`

```python
def fetch_web_search(
    topic: str,
    max_results: int = 5,
    fetch_top_articles: int = 2,
) -> list[Document]:
```

Behavior:
- Builds search query: `"{topic} trading finance"` for domain relevance
- Calls `duckduckgo_search.DDGS().text()` for search snippets
- Creates a Document per snippet (title, snippet text, URL, tags=`["web_search", topic]`)
- Fetches full article content for top N results via existing `fetch_article()`
- Returns `[]` gracefully on any error (rate limit, network, missing package)

### Learning pipeline integration

```
Step 1: BM25 search over books       → 5 documents
Step 2: Wikipedia summary             → 1 document
Step 2b: Web search (NEW)             → 3-7 documents
Step 3: Synthesize all via LLM
Step 4: Store in curriculum/
Step 5: Assess mastery
```

### Configuration

In `config/settings.yaml` under `data:`:
```yaml
web_search_max_results: 5
web_search_fetch_articles: 2
```

### Dependency

Add `duckduckgo_search` to `requirements.txt`. Soft dependency: if not installed, logs warning and returns empty list.

### Error handling

- Package not installed → warn, return `[]`
- DDG rate limit / network error → warn, return `[]`
- Article fetch failure → skip article, return snippet Documents
- 1-second delay between article fetches for rate-limit respect

No learning session ever fails due to web search unavailability. Purely additive.

## Files to modify

1. `knowledge/ingestion.py` — add `fetch_web_search()`
2. `scripts/simulate_learning.py` — add web search step between Wikipedia and synthesis
3. `config/settings.yaml` — add web search config keys
4. `requirements.txt` — add `duckduckgo_search`
5. `tests/test_ingestion.py` — add tests for new function (if test file exists)
