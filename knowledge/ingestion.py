"""Content fetcher module for the knowledge system.

Fetches financial news, SEC filings, and generic web articles, returning
normalised ``Document`` objects suitable for storage in the knowledge base.

Only stdlib dependencies are used (urllib, xml.etree, re, logging, json).
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import textwrap
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Final

from knowledge.store import Document

logger: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REQUEST_TIMEOUT: Final[int] = 15  # seconds

# SEC EDGAR requires a User-Agent that identifies the caller.
# See: https://www.sec.gov/os/accessing-edgar-data
_SEC_USER_AGENT: Final[str] = (
    "AutonomousEvolvingInvestment/1.0 (paper-trading research; contact@example.com)"
)

_DEFAULT_USER_AGENT: Final[str] = (
    "AutonomousEvolvingInvestment/1.0 (paper-trading research)"
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_request(url: str, *, user_agent: str = _DEFAULT_USER_AGENT) -> urllib.request.Request:
    """Create an HTTP GET request with the given User-Agent header."""
    return urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "*/*"},
        method="GET",
    )


def _utcnow_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _strip_html_tags(html: str) -> str:
    """Remove HTML tags from *html* using a simple regex approach.

    This intentionally avoids heavy dependencies like ``lxml`` or
    ``beautifulsoup4``.  It is good enough for extracting readable text
    from typical article pages.
    """
    # Remove script and style blocks entirely.
    text: str = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining tags.
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace.
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_rfc822_to_iso(date_str: str) -> str:
    """Best-effort conversion of an RFC-822 date string to ISO 8601.

    Falls back to the current UTC time if parsing fails.
    """
    # Common RSS date format: "Mon, 23 Feb 2026 14:30:00 +0000"
    formats: list[str] = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).isoformat()
        except ValueError:
            continue
    logger.debug("Could not parse date '%s'; using current UTC time.", date_str)
    return _utcnow_iso()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_news(query: str, max_results: int = 10) -> list[Document]:
    """Fetch financial news from Yahoo Finance RSS feed.

    Parameters
    ----------
    query:
        Search term (e.g. a ticker symbol like ``"AAPL"``).
    max_results:
        Maximum number of articles to return.

    Returns
    -------
    list[Document]
        A list of ``Document`` objects. Returns an empty list on network
        or parsing errors.
    """
    encoded_query: str = urllib.parse.quote_plus(query)
    url: str = f"https://finance.yahoo.com/rss/headline?s={encoded_query}"

    req: urllib.request.Request = _build_request(url)

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            raw_xml: bytes = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        logger.warning("Failed to fetch Yahoo Finance RSS for query '%s': %s", query, exc)
        return []

    try:
        root: ET.Element = ET.fromstring(raw_xml)
    except ET.ParseError as exc:
        logger.warning("Failed to parse RSS XML for query '%s': %s", query, exc)
        return []

    documents: list[Document] = []
    items: list[ET.Element] = root.findall(".//item")

    for item in items[:max_results]:
        title: str = (item.findtext("title") or "").strip()
        description: str = (item.findtext("description") or "").strip()
        link: str = (item.findtext("link") or "").strip()
        pub_date: str = (item.findtext("pubDate") or "").strip()

        if not title:
            continue

        # Strip any residual HTML from the description.
        content: str = _strip_html_tags(description) if description else title

        timestamp: str = _parse_rfc822_to_iso(pub_date) if pub_date else _utcnow_iso()

        documents.append(
            Document(
                title=title,
                content=content,
                source=link or url,
                timestamp=timestamp,
                topic_tags=["news", query.lower()],
            )
        )

    logger.info("Fetched %d news articles for query '%s'.", len(documents), query)
    return documents


def fetch_sec_filings(
    ticker: str,
    filing_type: str = "10-K",
    max_results: int = 5,
) -> list[Document]:
    """Fetch SEC EDGAR filings via the full-text search API.

    Parameters
    ----------
    ticker:
        Company ticker symbol (e.g. ``"AAPL"``).
    filing_type:
        SEC form type to search for (default ``"10-K"``).
    max_results:
        Maximum number of filings to return.

    Returns
    -------
    list[Document]
        A list of ``Document`` objects containing filing metadata and
        snippets. Returns an empty list on network or parsing errors.
    """
    # Build the EDGAR full-text search URL.
    params: dict[str, str] = {
        "q": f'"{ticker}" "{filing_type}"',
        "dateRange": "custom",
        "startdt": "2020-01-01",
        "enddt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "forms": filing_type,
    }
    query_string: str = urllib.parse.urlencode(params)
    url: str = f"https://efts.sec.gov/LATEST/search-index?{query_string}"

    req: urllib.request.Request = _build_request(url, user_agent=_SEC_USER_AGENT)

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            raw_json: bytes = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        logger.warning(
            "Failed to fetch SEC filings for ticker '%s' (%s): %s",
            ticker,
            filing_type,
            exc,
        )
        return []

    try:
        data: dict = json.loads(raw_json)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Failed to parse SEC JSON for ticker '%s': %s", ticker, exc)
        return []

    hits: list[dict] = data.get("hits", {}).get("hits", [])
    if not hits:
        logger.info("No SEC filings found for ticker '%s' (%s).", ticker, filing_type)
        return []

    documents: list[Document] = []

    for hit in hits[:max_results]:
        source_data: dict = hit.get("_source", {})

        file_date: str = source_data.get("file_date", "")
        display_date: str = source_data.get("period_of_report", file_date)
        entity_name: str = source_data.get("entity_name", ticker.upper())
        form_type: str = source_data.get("form_type", filing_type)
        file_num: str = source_data.get("file_num", "")

        # Build a descriptive title.
        title: str = f"{entity_name} — {form_type}"
        if display_date:
            title += f" ({display_date})"

        # Use the highlight snippets if available; otherwise fall back to
        # a short metadata summary.
        highlight: dict = hit.get("highlight", {})
        snippets: list[str] = highlight.get("content", [])
        if snippets:
            content: str = " ... ".join(_strip_html_tags(s) for s in snippets)
        else:
            content = (
                f"SEC filing {form_type} for {entity_name}. "
                f"File date: {file_date}. File number: {file_num}."
            )

        # Construct a link to the filing on EDGAR.
        file_id: str = hit.get("_id", "")
        source_url: str = (
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={urllib.parse.quote_plus(ticker)}&type={urllib.parse.quote_plus(filing_type)}"
            if not file_id
            else f"https://www.sec.gov/Archives/edgar/data/{file_id}"
        )

        # Normalise the timestamp to ISO 8601.
        timestamp: str
        if file_date:
            try:
                timestamp = datetime.strptime(file_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                ).isoformat()
            except ValueError:
                timestamp = _utcnow_iso()
        else:
            timestamp = _utcnow_iso()

        documents.append(
            Document(
                title=title,
                content=content,
                source=source_url,
                timestamp=timestamp,
                topic_tags=["sec_filing", filing_type.lower(), ticker.lower()],
            )
        )

    logger.info(
        "Fetched %d SEC %s filings for ticker '%s'.",
        len(documents),
        filing_type,
        ticker,
    )
    return documents


def fetch_article(url: str) -> Document | None:
    """Fetch a generic web article and extract its text content.

    Uses ``urllib.request`` to download the page and a simple regex-based
    approach to strip HTML tags and extract readable text.

    Parameters
    ----------
    url:
        The URL of the article to fetch.

    Returns
    -------
    Document | None
        A ``Document`` with the extracted text, or ``None`` if the fetch
        or extraction fails.
    """
    req: urllib.request.Request = _build_request(url)

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            # Attempt to detect encoding; fall back to UTF-8.
            charset: str = resp.headers.get_content_charset() or "utf-8"
            raw_html: str = resp.read().decode(charset, errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        logger.warning("Failed to fetch article at '%s': %s", url, exc)
        return None

    # --- Extract title ---------------------------------------------------
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.DOTALL | re.IGNORECASE)
    title: str = _strip_html_tags(title_match.group(1)).strip() if title_match else url

    # --- Extract body text -----------------------------------------------
    # Prefer the <article> block if present; otherwise use the full body.
    article_match = re.search(
        r"<article[^>]*>(.*?)</article>", raw_html, re.DOTALL | re.IGNORECASE
    )
    if article_match:
        body_html: str = article_match.group(1)
    else:
        body_match = re.search(
            r"<body[^>]*>(.*?)</body>", raw_html, re.DOTALL | re.IGNORECASE
        )
        body_html = body_match.group(1) if body_match else raw_html

    content: str = _strip_html_tags(body_html)

    if not content:
        logger.warning("Extracted empty content from '%s'.", url)
        return None

    return Document(
        title=title,
        content=content,
        source=url,
        timestamp=_utcnow_iso(),
        topic_tags=["article"],
    )


def fetch_wikipedia(topic: str) -> list[Document]:
    """Fetch a Wikipedia summary for a concept.

    Uses the Wikipedia REST summary API, falling back to a Wikipedia search
    when the topic name does not map directly to a page title.

    Parameters
    ----------
    topic:
        Concept name (e.g. ``"Market Microstructure"``).

    Returns
    -------
    list[Document]
        A list containing one ``Document``, or empty on failure.
    """
    _WIKIPEDIA_USER_AGENT: str = (
        "AutonomousEvolvingInvestment/1.0 "
        "(paper-trading research; contact@example.com)"
    )

    def _summary_url(title: str) -> str:
        return (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + urllib.parse.quote(title.replace(" ", "_"), safe="")
        )

    def _fetch_summary(title: str) -> dict | None:
        req = _build_request(_summary_url(title), user_agent=_WIKIPEDIA_USER_AGENT)
        try:
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            logger.warning("Wikipedia HTTP error for '%s': %s", title, exc)
            return None
        except (urllib.error.URLError, OSError) as exc:
            logger.warning("Wikipedia network error for '%s': %s", title, exc)
            return None

    def _search_title(query: str) -> str | None:
        """Use the Wikipedia search API to find the best matching page title."""
        params = urllib.parse.urlencode({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": "1",
        })
        url = f"https://en.wikipedia.org/w/api.php?{params}"
        req = _build_request(url, user_agent=_WIKIPEDIA_USER_AGENT)
        try:
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
                data = json.loads(resp.read())
            hits = data.get("query", {}).get("search", [])
            return hits[0]["title"] if hits else None
        except Exception as exc:
            logger.warning("Wikipedia search failed for '%s': %s", query, exc)
            return None

    # Try the topic name directly, then fall back to search.
    data = _fetch_summary(topic)
    if data is None:
        best_title = _search_title(topic)
        if best_title:
            logger.info(
                "Wikipedia: '%s' not found directly; using search result '%s'",
                topic, best_title,
            )
            data = _fetch_summary(best_title)

    if not data:
        logger.warning("Wikipedia: no article found for topic '%s'.", topic)
        return []

    extract: str = data.get("extract", "").strip()
    if not extract:
        logger.warning("Wikipedia: empty extract for topic '%s'.", topic)
        return []

    title: str = data.get("title", topic)
    page_url: str = (
        data.get("content_urls", {}).get("desktop", {}).get("page", "")
        or f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
    )

    logger.info("Fetched Wikipedia article '%s' for topic '%s'.", title, topic)
    return [
        Document(
            title=title,
            content=extract,
            source=page_url,
            timestamp=_utcnow_iso(),
            topic_tags=["wikipedia", topic.lower()],
        )
    ]


def fetch_arxiv(query: str, max_results: int = 5) -> list[Document]:
    """Fetch paper abstracts from arXiv in the quantitative finance (q-fin) category.

    Uses the arXiv public Atom API. Results are sorted by relevance.

    Parameters
    ----------
    query:
        Search terms (e.g. ``"Kelly Criterion optimal betting"``).
    max_results:
        Maximum number of papers to return (default 5).

    Returns
    -------
    list[Document]
        A list of ``Document`` objects, one per paper abstract.
        Returns an empty list on network or parsing errors.
    """
    # Wrap multi-word queries in quotes so arXiv treats them as phrases.
    # Search by title first (highest precision), then fall back to all-fields.
    quoted_query = f'"{query}"' if " " in query else query

    def _build_params(search_query: str) -> dict[str, str]:
        return {
            "search_query": search_query,
            "start": "0",
            "max_results": str(max_results),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

    params: dict[str, str] = _build_params(f"ti:{quoted_query}")
    def _fetch_xml(search_params: dict[str, str]) -> ET.Element | None:
        fetch_url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(search_params)
        fetch_req = _build_request(fetch_url)
        try:
            with urllib.request.urlopen(fetch_req, timeout=_REQUEST_TIMEOUT) as resp:
                return ET.fromstring(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            logger.warning("Failed to fetch arXiv for query '%s': %s", query, exc)
            return None
        except ET.ParseError as exc:
            logger.warning("Failed to parse arXiv XML for query '%s': %s", query, exc)
            return None

    root: ET.Element | None = _fetch_xml(params)
    if root is None:
        return []

    # If the title-scoped search returns nothing, retry against all fields.
    ns_os = {"os": "http://a9.com/-/spec/opensearch/1.1/"}
    total = int(root.findtext("os:totalResults", default="0", namespaces=ns_os) or 0)
    if total == 0:
        logger.info(
            "arXiv: no title matches for '%s'; retrying with all-field search.", query
        )
        fallback_params = _build_params(f"all:{quoted_query}")
        root = _fetch_xml(fallback_params)
        if root is None:
            return []

    ns: dict[str, str] = {"atom": "http://www.w3.org/2005/Atom"}
    documents: list[Document] = []

    for entry in root.findall("atom:entry", ns):
        title: str = re.sub(
            r"\s+", " ", (entry.findtext("atom:title", namespaces=ns) or "").strip()
        )
        summary: str = re.sub(
            r"\s+", " ", (entry.findtext("atom:summary", namespaces=ns) or "").strip()
        )
        arxiv_id: str = (entry.findtext("atom:id", namespaces=ns) or "").strip()
        published: str = (entry.findtext("atom:published", namespaces=ns) or "").strip()

        if not title or not summary:
            continue

        # Skip arXiv error entries (the API returns a single entry with an
        # error message in the title when the query fails).
        if "Error" in title and len(summary) < 50:
            logger.warning("arXiv returned an error entry for query '%s'.", query)
            break

        documents.append(
            Document(
                title=title,
                content=summary,
                source=arxiv_id or url,
                timestamp=_parse_rfc822_to_iso(published) if published else _utcnow_iso(),
                topic_tags=["arxiv", "q-fin", query.lower()],
            )
        )

        if len(documents) >= max_results:
            break

    logger.info("Fetched %d arXiv papers for query '%s'.", len(documents), query)
    return documents


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


def fetch_alpaca_news(
    tickers: list[str],
    max_results: int = 20,
) -> list[Document]:
    """Fetch recent market news from the Alpaca News API.

    Requires ``ALPACA_API_KEY`` and ``ALPACA_SECRET_KEY`` environment
    variables (loaded via python-dotenv if present).

    Parameters
    ----------
    tickers:
        List of ticker symbols to filter news by (e.g. ``["AAPL", "MSFT"]``).
        Pass an empty list for unfiltered market-wide news (noisier).
    max_results:
        Maximum number of articles to return (Alpaca allows up to 50 per
        request; default 20).

    Returns
    -------
    list[Document]
        Normalised ``Document`` objects. Returns an empty list when
        credentials are missing or the API call fails.
    """
    api_key: str = os.environ.get("ALPACA_API_KEY", "")
    secret_key: str = os.environ.get("ALPACA_SECRET_KEY", "")

    if not api_key or not secret_key:
        logger.warning(
            "fetch_alpaca_news: ALPACA_API_KEY / ALPACA_SECRET_KEY not set; skipping."
        )
        return []

    params: dict[str, str] = {
        "limit": str(min(max_results, 50)),
        "sort": "desc",
        "include_content": "false",  # full HTML content is rarely useful; summary suffices
    }
    if tickers:
        params["symbols"] = ",".join(t.upper() for t in tickers)

    url: str = (
        "https://data.alpaca.markets/v1beta1/news?"
        + urllib.parse.urlencode(params)
    )
    req: urllib.request.Request = urllib.request.Request(
        url,
        headers={
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "User-Agent": _DEFAULT_USER_AGENT,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            data: dict = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.warning(
            "Alpaca News API HTTP %d for tickers %s: %s", exc.code, tickers, body[:200]
        )
        return []
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("Alpaca News API network error for tickers %s: %s", tickers, exc)
        return []

    articles: list[dict] = data.get("news", [])
    documents: list[Document] = []

    for article in articles:
        headline: str = html.unescape(article.get("headline", "")).strip()
        summary: str = html.unescape(article.get("summary", "")).strip()
        source: str = article.get("url", "") or article.get("source", "")
        created_at: str = article.get("created_at", "") or _utcnow_iso()
        symbols: list[str] = article.get("symbols", [])

        if not headline:
            continue

        # Use summary as content; fall back to headline if summary is empty.
        content: str = summary if summary else headline

        documents.append(
            Document(
                title=headline,
                content=content,
                source=source,
                timestamp=created_at,
                topic_tags=["news", "alpaca"] + [s.lower() for s in symbols],
            )
        )

    logger.info(
        "Fetched %d Alpaca news articles for tickers %s.",
        len(documents),
        tickers or ["(all)"],
    )
    return documents


def fetch_book_text(
    book_path: str,
    topic_hint: str = "",
    chunk_size: int = 3000,
    skip_chars: int = 3000,
    max_chunks: int = 3,
) -> list[Document]:
    """Load a plain-text book file and return chunked ``Document`` objects.

    Designed to work with the text files produced by converting the investment
    book library (``~/projects/investment-books-text/``) from PDF via
    ``pdftotext``.

    Parameters
    ----------
    book_path:
        Absolute or ``~``-expanded path to the ``.txt`` book file.
    topic_hint:
        Optional curriculum topic name used to populate ``topic_tags``.
    chunk_size:
        Maximum characters per chunk (default 3 000).
    skip_chars:
        Characters to skip at the start of the file to bypass front matter,
        copyright pages, and TOC (default 3 000).
    max_chunks:
        Maximum number of chunks to return per call (default 3).  Keeping
        this small limits LLM token usage while still providing useful signal.

    Returns
    -------
    list[Document]
        Chunked ``Document`` objects ready for synthesis and storage.
        Returns an empty list if the file is missing or unreadable.
    """
    path = Path(book_path).expanduser().resolve()
    if not path.exists():
        logger.warning("Book file not found: %s", path)
        return []

    try:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Failed to read book '%s': %s", path, exc)
        return []

    # Skip front matter (copyright pages, publisher info, TOC, etc.)
    # If the file is shorter than skip_chars or yields no content, retry
    # with progressively smaller skips before giving up.
    content = ""
    for attempt_skip in (skip_chars, skip_chars // 2, 0):
        candidate = raw_text[attempt_skip:] if len(raw_text) > attempt_skip else raw_text
        content = " ".join(candidate.split())
        if content:
            break

    if not content:
        logger.warning("Book '%s' has no usable text content.", path.name)
        return []

    # --- Chapter-aware splitting ------------------------------------------
    # Try to find chapter boundaries first so each chunk covers a coherent topic.
    chapter_re = re.compile(
        r"(?:CHAPTER|Chapter|PART|Part|SECTION|Section)\s+(?:\d+|[IVXLCDM]+)\b",
        re.MULTILINE,
    )
    chapter_matches = list(chapter_re.finditer(content))

    chunks: list[str] = []
    if len(chapter_matches) >= 2:
        for i, match in enumerate(chapter_matches[:max_chunks]):
            start = match.start()
            # End at next chapter boundary or after chunk_size * 2 chars.
            if i + 1 < len(chapter_matches):
                end = chapter_matches[i + 1].start()
            else:
                end = start + chunk_size * 2
            chunk = content[start:end].strip()
            if chunk:
                # Truncate oversized chapters.
                chunks.append(chunk[:chunk_size * 2])
    else:
        # Fallback: plain word-count chunking.
        chunks = textwrap.wrap(content, chunk_size)[:max_chunks]

    book_title = path.stem
    tags = ["book"]
    if topic_hint:
        tags.append(re.sub(r"[^\w]+", "_", topic_hint.lower()).strip("_"))

    documents: list[Document] = []
    for i, chunk in enumerate(chunks):
        documents.append(
            Document(
                title=f"{book_title} — part {i + 1}",
                content=chunk,
                source=str(path),
                topic_tags=tags,
            )
        )

    logger.info(
        "Loaded %d chunk(s) from book '%s' (topic_hint=%r).",
        len(documents),
        book_title,
        topic_hint,
    )
    return documents
