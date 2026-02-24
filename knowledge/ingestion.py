"""Content fetcher module for the knowledge system.

Fetches financial news, SEC filings, and generic web articles, returning
normalised ``Document`` objects suitable for storage in the knowledge base.

Only stdlib dependencies are used (urllib, xml.etree, re, logging, json).
"""

from __future__ import annotations

import json
import logging
import re
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

_REQUEST_TIMEOUT: Final[int] = 10  # seconds

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
