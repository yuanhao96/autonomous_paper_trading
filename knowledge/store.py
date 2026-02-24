"""Markdown-based knowledge memory with BM25 search.

Replaces the former ChromaDB vector store with structured markdown files
that use YAML front-matter for metadata.  Each topic is a `.md` file that
the agent can review, refine, and that is fully git-versionable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter
from rank_bm25 import BM25Okapi


@dataclass
class Document:
    """A knowledge document (kept for backward compatibility with ingestion/synthesizer)."""

    title: str
    content: str
    source: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    topic_tags: list[str] = field(default_factory=list)


def _slugify(text: str) -> str:
    """Convert *text* to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "_", slug)
    slug = slug.strip("_")
    return slug or "untitled"


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer for BM25."""
    return re.findall(r"[a-z0-9]+", text.lower())


class MarkdownMemory:
    """Persistent knowledge store backed by markdown files with YAML front-matter.

    Directory layout::

        <memory_root>/
            curriculum/
                stage_1/ ... stage_4/
                    <topic_id>.md
            discovered/
                <slugified_name>.md
            daily_log/
                <YYYY-MM-DD>.md
            connections.md

    Parameters
    ----------
    memory_root:
        Root directory for all memory files.  Created if it does not exist.
    """

    def __init__(self, memory_root: str = "knowledge/memory/trading") -> None:
        self._root = Path(memory_root)
        # Ensure directory structure exists.
        for stage in range(1, 5):
            (self._root / "curriculum" / f"stage_{stage}").mkdir(parents=True, exist_ok=True)
        (self._root / "discovered").mkdir(parents=True, exist_ok=True)
        (self._root / "daily_log").mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Curriculum knowledge
    # ------------------------------------------------------------------

    def _topic_path(self, topic_id: str, stage_number: int) -> Path:
        return self._root / "curriculum" / f"stage_{stage_number}" / f"{topic_id}.md"

    def store_curriculum_knowledge(
        self,
        topic_id: str,
        stage_number: int,
        doc: Document,
        synthesized_content: str,
        mastery_score: float = 0.0,
        mastery_reasoning: str = "",
        mastery_gaps: list[str] | None = None,
    ) -> Path:
        """Create or append synthesized knowledge to a curriculum topic file.

        YAML front-matter tracks metadata; the markdown body accumulates
        dated entries (never overwrites previous content).

        Returns the path to the written file.
        """
        path = self._topic_path(topic_id, stage_number)
        now = datetime.now(timezone.utc).isoformat()

        if path.exists():
            post = frontmatter.load(str(path))
        else:
            post = frontmatter.Post("")
            post.metadata["topic_id"] = topic_id
            post.metadata["stage"] = stage_number
            post.metadata["mastery_score"] = mastery_score
            post.metadata["mastery_reasoning"] = mastery_reasoning
            post.metadata["mastery_gaps"] = mastery_gaps or []
            post.metadata["sources"] = []
            post.metadata["created"] = now

        # Update timestamps and sources.
        post.metadata["updated"] = now
        sources: list[str] = post.metadata.get("sources", [])
        source_entry = f"{doc.title} ({doc.source})"
        if source_entry not in sources:
            sources.append(source_entry)
        post.metadata["sources"] = sources

        # Append new content under a dated heading.
        date_heading = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        new_section = f"\n\n## {date_heading} — {doc.title}\n\n{synthesized_content}"
        post.content = post.content.rstrip() + new_section

        path.write_text(frontmatter.dumps(post), encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # Daily log
    # ------------------------------------------------------------------

    def append_daily_log(self, doc: Document) -> Path:
        """Append a raw document entry to today's daily log file."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self._root / "daily_log" / f"{today}.md"

        if path.exists():
            post = frontmatter.load(str(path))
        else:
            post = frontmatter.Post("")
            post.metadata["date"] = today
            post.metadata["entry_count"] = 0

        post.metadata["entry_count"] = post.metadata.get("entry_count", 0) + 1

        entry = (
            f"\n\n### {doc.title}\n\n"
            f"**Source:** {doc.source}  \n"
            f"**Tags:** {', '.join(doc.topic_tags)}  \n"
            f"**Time:** {doc.timestamp}\n\n"
            f"{doc.content[:2000]}"
        )
        post.content = post.content.rstrip() + entry

        path.write_text(frontmatter.dumps(post), encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # Discovered topics
    # ------------------------------------------------------------------

    def store_discovered(
        self,
        topic_name: str,
        content: str,
        source: str = "",
        tags: list[str] | None = None,
    ) -> Path:
        """Store a discovered (emergent) knowledge topic."""
        slug = _slugify(topic_name)
        path = self._root / "discovered" / f"{slug}.md"
        now = datetime.now(timezone.utc).isoformat()

        if path.exists():
            post = frontmatter.load(str(path))
        else:
            post = frontmatter.Post("")
            post.metadata["topic"] = topic_name
            post.metadata["tags"] = tags or []
            post.metadata["created"] = now

        post.metadata["updated"] = now
        if source:
            sources: list[str] = post.metadata.get("sources", [])
            if source not in sources:
                sources.append(source)
            post.metadata["sources"] = sources

        date_heading = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        new_section = f"\n\n## {date_heading}\n\n{content}"
        post.content = post.content.rstrip() + new_section

        path.write_text(frontmatter.dumps(post), encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # Mastery accessors
    # ------------------------------------------------------------------

    def get_mastery(self, topic_id: str, stage_number: int) -> float:
        """Read mastery_score from front-matter; returns 0.0 if file missing."""
        path = self._topic_path(topic_id, stage_number)
        if not path.exists():
            return 0.0
        post = frontmatter.load(str(path))
        try:
            return float(post.metadata.get("mastery_score", 0.0))
        except (TypeError, ValueError):
            return 0.0

    def set_mastery(
        self,
        topic_id: str,
        stage_number: int,
        score: float,
        reasoning: str = "",
        gaps: list[str] | None = None,
    ) -> None:
        """Update mastery metadata in front-matter (creates stub if missing)."""
        path = self._topic_path(topic_id, stage_number)
        now = datetime.now(timezone.utc).isoformat()

        if path.exists():
            post = frontmatter.load(str(path))
        else:
            post = frontmatter.Post("")
            post.metadata["topic_id"] = topic_id
            post.metadata["stage"] = stage_number
            post.metadata["sources"] = []
            post.metadata["created"] = now

        post.metadata["mastery_score"] = round(score, 3)
        post.metadata["mastery_reasoning"] = reasoning
        post.metadata["mastery_gaps"] = gaps or []
        post.metadata["updated"] = now

        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    # ------------------------------------------------------------------
    # Topic content
    # ------------------------------------------------------------------

    def get_topic_content(self, topic_id: str, stage_number: int) -> str:
        """Return full markdown body of a curriculum topic (empty string if missing)."""
        path = self._topic_path(topic_id, stage_number)
        if not path.exists():
            return ""
        post = frontmatter.load(str(path))
        return post.content

    # ------------------------------------------------------------------
    # BM25 search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        subdirectory: str | None = None,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """BM25-ranked full-text search over markdown files.

        Parameters
        ----------
        query:
            Natural-language query string.
        subdirectory:
            Restrict search to a sub-path under memory_root (e.g. ``"curriculum"``
            or ``"discovered"``).  ``None`` searches everything.
        n_results:
            Maximum number of results to return.

        Returns
        -------
        list[dict]
            Each dict has keys: ``path``, ``metadata``, ``content``, ``score``.
        """
        search_root = self._root / subdirectory if subdirectory else self._root
        if not search_root.exists():
            return []

        md_files = sorted(search_root.rglob("*.md"))
        if not md_files:
            return []

        # Parse all files.
        corpus: list[list[str]] = []
        file_data: list[dict[str, Any]] = []
        for fp in md_files:
            try:
                post = frontmatter.load(str(fp))
            except Exception:
                continue
            tokens = _tokenize(post.content)
            if not tokens:
                continue
            corpus.append(tokens)
            file_data.append(
                {
                    "path": str(fp),
                    "metadata": dict(post.metadata),
                    "content": post.content,
                }
            )

        if not corpus:
            return []

        bm25 = BM25Okapi(corpus)
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = bm25.get_scores(query_tokens)

        # Pair scores with file data and sort descending.
        ranked = sorted(
            zip(scores, file_data),
            key=lambda pair: pair[0],
            reverse=True,
        )

        results: list[dict[str, Any]] = []
        for score_val, data in ranked[:n_results]:
            results.append(
                {
                    "path": data["path"],
                    "metadata": data["metadata"],
                    "content": data["content"][:1000],
                    "score": float(score_val),
                }
            )
        return results
