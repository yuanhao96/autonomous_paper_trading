"""Tool abstraction layer for the multi-round learning system.

Each tool wraps an existing ingestion function and normalizes its output
into ToolOutput objects with evidence metadata attached to every Document.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

import yaml

from knowledge.store import Document, MarkdownMemory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class ToolSpec:
    name: str
    cost_hint: str          # "low" | "medium" | "high"
    latency_hint: str       # "fast" | "medium" | "slow"
    reliability_hint: float # 0–1
    domains: list[str]
    supports_queries: bool


@dataclass
class ToolInput:
    topic: str
    sub_question: str = ""
    query: str = ""          # if empty, derived from topic + sub_question
    budget: str = "medium"   # "low" | "medium" | "high"


@dataclass
class ToolOutput:
    documents: list[Document] = field(default_factory=list)
    coverage_tags: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    tool_meta: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# KnowledgeTool protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class KnowledgeTool(Protocol):
    spec: ToolSpec

    def run(self, input: ToolInput) -> ToolOutput:
        ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enrich(doc: Document, tool_name: str, query: str, quality_score: float) -> Document:
    """Attach evidence metadata to a Document in-place and return it."""
    doc.topic_tags = list(doc.topic_tags or [])
    # Store metadata in a structured way on the document object
    if not hasattr(doc, "meta") or doc.meta is None:
        doc.meta = {}
    doc.meta.update({
        "evidence_type": "retrieved",
        "tool_name": tool_name,
        "retrieval_query": query,
        "retrieved_at": _now_iso(),
        "quality_score": quality_score,
        "novelty_score": 0.5,  # placeholder; updated by evaluator
    })
    return doc


def _effective_query(inp: ToolInput) -> str:
    if inp.query:
        return inp.query
    if inp.sub_question:
        return f"{inp.topic} {inp.sub_question}"
    return inp.topic


# ---------------------------------------------------------------------------
# Concrete tool implementations
# ---------------------------------------------------------------------------

class MemorySearchTool:
    spec = ToolSpec(
        name="memory",
        cost_hint="low",
        latency_hint="fast",
        reliability_hint=0.95,
        domains=["all"],
        supports_queries=True,
    )

    def __init__(self, memory: MarkdownMemory) -> None:
        self._memory = memory

    def run(self, inp: ToolInput) -> ToolOutput:
        query = _effective_query(inp)
        try:
            results = self._memory.search(query, n_results=8)
            docs = []
            for r in results:
                content = r.get("content", "") or r.get("synthesized_content", "")
                if not content:
                    continue
                doc = Document(
                    title=r.get("topic_name", r.get("path", "memory")),
                    content=str(content),
                    source="memory",
                    topic_tags=r.get("tags", []),
                )
                doc = _enrich(doc, "memory", query, quality_score=0.7)
                doc.meta["bm25_score"] = r.get("score", 0.0)
                docs.append(doc)
            return ToolOutput(
                documents=docs,
                coverage_tags=["existing_knowledge"],
                tool_meta={"query": query, "n_results": len(docs)},
            )
        except Exception as exc:
            logger.warning("MemorySearchTool error: %s", exc)
            return ToolOutput(errors=[str(exc)])


class WikipediaTool:
    spec = ToolSpec(
        name="wikipedia",
        cost_hint="low",
        latency_hint="fast",
        reliability_hint=0.85,
        domains=["finance", "economics", "general"],
        supports_queries=True,
    )

    def run(self, inp: ToolInput) -> ToolOutput:
        from knowledge.ingestion import fetch_wikipedia
        query = _effective_query(inp)
        try:
            docs = fetch_wikipedia(query)
            enriched = [_enrich(d, "wikipedia", query, 0.8) for d in docs]
            return ToolOutput(
                documents=enriched,
                coverage_tags=["encyclopedia", "definitions"],
                tool_meta={"query": query},
            )
        except Exception as exc:
            logger.warning("WikipediaTool error: %s", exc)
            return ToolOutput(errors=[str(exc)])


class DuckDuckGoTool:
    spec = ToolSpec(
        name="web",
        cost_hint="low",
        latency_hint="medium",
        reliability_hint=0.7,
        domains=["current", "news", "general"],
        supports_queries=True,
    )

    def run(self, inp: ToolInput) -> ToolOutput:
        from knowledge.ingestion import fetch_web_search
        query = _effective_query(inp)
        try:
            docs = fetch_web_search(query)
            enriched = [_enrich(d, "web", query, 0.6) for d in docs]
            return ToolOutput(
                documents=enriched,
                coverage_tags=["web", "current"],
                tool_meta={"query": query},
            )
        except Exception as exc:
            logger.warning("DuckDuckGoTool error: %s", exc)
            return ToolOutput(errors=[str(exc)])


class ArxivTool:
    spec = ToolSpec(
        name="arxiv",
        cost_hint="low",
        latency_hint="medium",
        reliability_hint=0.9,
        domains=["quantitative_finance", "research", "academic"],
        supports_queries=True,
    )

    def __init__(self, max_results: int = 5) -> None:
        self._max_results = max_results

    def run(self, inp: ToolInput) -> ToolOutput:
        from knowledge.ingestion import fetch_arxiv
        query = _effective_query(inp)
        try:
            docs = fetch_arxiv(query, max_results=self._max_results)
            enriched = [_enrich(d, "arxiv", query, 0.9) for d in docs]
            return ToolOutput(
                documents=enriched,
                coverage_tags=["academic", "research", "quantitative"],
                tool_meta={"query": query, "max_results": self._max_results},
            )
        except Exception as exc:
            logger.warning("ArxivTool error: %s", exc)
            return ToolOutput(errors=[str(exc)])


class BookChunkTool:
    spec = ToolSpec(
        name="book",
        cost_hint="low",
        latency_hint="fast",
        reliability_hint=0.8,
        domains=["trading", "finance", "investment"],
        supports_queries=False,
    )

    def __init__(self, books_dir: str | None = None, books_config_path: str | None = None) -> None:
        self._books_dir = books_dir
        self._books_config_path = books_config_path or "config/books.yaml"

    def _get_books_dir(self) -> Path:
        if self._books_dir:
            return Path(self._books_dir).expanduser()
        env_dir = os.getenv("BOOKS_DIR", "")
        if env_dir:
            return Path(env_dir).expanduser()
        try:
            with open("config/settings.yaml") as fh:
                settings = yaml.safe_load(fh) or {}
            d = settings.get("data", {}).get("books_dir", "")
            if d:
                return Path(d).expanduser()
        except Exception:
            pass
        return Path("~/projects/investment-books-text").expanduser()

    def _load_books_config(self) -> dict[str, list[str]]:
        try:
            with open(self._books_config_path) as fh:
                data = yaml.safe_load(fh) or {}
            return {k: v for k, v in data.items() if isinstance(v, list)}
        except Exception:
            return {}

    def run(self, inp: ToolInput) -> ToolOutput:
        from knowledge.ingestion import fetch_book_text
        books_map = self._load_books_config()
        books_dir = self._get_books_dir()

        # Match topic_id by looking for the topic keyword in keys
        topic_lower = inp.topic.lower().replace(" ", "_")
        matched_files: list[str] = []
        for key, files in books_map.items():
            if key in topic_lower or topic_lower in key:
                matched_files.extend(files)
                break

        if not matched_files:
            # Fall back to first book in any overlapping domain
            for key, files in books_map.items():
                matched_files.extend(files[:1])
                if matched_files:
                    break

        all_docs: list[Document] = []
        for fname in matched_files[:2]:  # max 2 books per round
            path = books_dir / fname
            docs = fetch_book_text(str(path), topic_hint=inp.topic, max_chunks=3)
            for d in docs:
                _enrich(d, "book", inp.topic, 0.75)
            all_docs.extend(docs)

        return ToolOutput(
            documents=all_docs,
            coverage_tags=["book", "curated"],
            tool_meta={"books_used": matched_files[:2], "chunks": len(all_docs)},
        )


class AlpacaNewsTool:
    spec = ToolSpec(
        name="news",
        cost_hint="low",
        latency_hint="fast",
        reliability_hint=0.75,
        domains=["market", "current", "news"],
        supports_queries=True,
    )

    def __init__(self, tickers: list[str] | None = None) -> None:
        self._tickers = tickers or ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    def run(self, inp: ToolInput) -> ToolOutput:
        from knowledge.ingestion import fetch_alpaca_news
        try:
            docs = fetch_alpaca_news(self._tickers)
            enriched = [_enrich(d, "news", inp.topic, 0.5) for d in docs]
            return ToolOutput(
                documents=enriched,
                coverage_tags=["news", "market", "current"],
                tool_meta={"tickers": self._tickers, "count": len(enriched)},
            )
        except Exception as exc:
            logger.warning("AlpacaNewsTool error: %s", exc)
            return ToolOutput(errors=[str(exc)])


# ---------------------------------------------------------------------------
# Default tool registry
# ---------------------------------------------------------------------------

def default_tools(memory: MarkdownMemory) -> list[KnowledgeTool]:
    """Return the standard set of tools in priority order."""
    return [
        MemorySearchTool(memory),
        WikipediaTool(),
        BookChunkTool(),
        ArxivTool(),
        DuckDuckGoTool(),
        AlpacaNewsTool(),
    ]
