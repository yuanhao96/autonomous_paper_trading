"""Bulk ingestion script: load all books listed in config/books.yaml into
the MarkdownMemory knowledge base.

Stores raw book chunks in ``knowledge/memory/trading/discovered/`` tagged
with their curriculum topics.  No LLM calls are made — this is pure file I/O.
Synthesis happens during nightly learning sessions.

Usage:
    python scripts/ingest_books.py [--chunks N] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Project root is one level up from this script.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

import yaml

from knowledge.ingestion import fetch_book_text
from knowledge.store import MarkdownMemory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _get_books_dir() -> Path:
    env_dir = os.getenv("BOOKS_DIR", "")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    try:
        with open(_PROJECT_ROOT / "config" / "settings.yaml") as fh:
            settings = yaml.safe_load(fh) or {}
        d = settings.get("data", {}).get("books_dir", "")
        if d:
            return Path(d).expanduser().resolve()
    except Exception:
        pass
    return Path("~/projects/investment-books-text").expanduser().resolve()


def _load_books_config() -> dict[str, list[str]]:
    cfg_path = _PROJECT_ROOT / "config" / "books.yaml"
    with open(cfg_path) as fh:
        data = yaml.safe_load(fh) or {}
    return {k: v for k, v in data.items() if isinstance(v, list)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk-ingest investment books into knowledge base.")
    parser.add_argument("--chunks", type=int, default=10,
                        help="Max chunks to load per book (default: 10)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be ingested without writing anything.")
    args = parser.parse_args()

    books_dir = _get_books_dir()
    books_map = _load_books_config()
    memory = MarkdownMemory(memory_root=str(_PROJECT_ROOT / "knowledge" / "memory" / "trading"))

    # Build unique book → [topic_ids] mapping (books appear in multiple topics).
    book_topics: dict[str, list[str]] = {}
    for topic_id, filenames in books_map.items():
        for fname in filenames:
            book_topics.setdefault(fname, []).append(topic_id)

    total_books = len(book_topics)
    total_chunks_stored = 0
    skipped = 0
    failed = 0

    logger.info("Books directory : %s", books_dir)
    logger.info("Books to ingest : %d unique books across %d topics", total_books, len(books_map))
    logger.info("Chunks per book : %d", args.chunks)
    if args.dry_run:
        logger.info("DRY RUN — no files will be written.\n")

    for i, (filename, topic_ids) in enumerate(sorted(book_topics.items()), start=1):
        book_path = books_dir / filename
        topic_hint = topic_ids[0]  # primary topic for tagging
        tags = ["book"] + topic_ids

        logger.info("[%d/%d] %s", i, total_books, filename[:70])

        if not book_path.exists():
            logger.warning("  ⚠ File not found, skipping: %s", book_path)
            skipped += 1
            continue

        docs = fetch_book_text(
            str(book_path),
            topic_hint=topic_hint,
            chunk_size=3000,
            skip_chars=3000,
            max_chunks=args.chunks,
        )

        if not docs:
            logger.warning("  ⚠ No content extracted (scanned PDF?), skipping.")
            skipped += 1
            continue

        if args.dry_run:
            logger.info("  → Would store %d chunk(s) tagged: %s", len(docs), topic_ids)
            total_chunks_stored += len(docs)
            continue

        # Store each chunk as a discovered topic entry.
        book_slug = filename.replace(".txt", "").replace(" ", "_").lower()[:60]
        for j, doc in enumerate(docs):
            # Override tags to include all topic_ids this book maps to.
            doc.topic_tags = tags
            topic_name = f"{Path(filename).stem[:50]} — part {j + 1}"
            entry_key = f"{book_slug}_p{j + 1}"
            try:
                path = memory.store_discovered(
                    topic_name=topic_name,
                    content=doc.content,
                    source=str(book_path),
                    tags=tags,
                )
                total_chunks_stored += 1
                logger.debug("    ✅ chunk %d → %s", j + 1, path.name)
            except Exception as exc:
                logger.error("    ❌ Failed to store chunk %d: %s", j + 1, exc)
                failed += 1

        logger.info("  ✅ Stored %d chunk(s) | topics: %s", len(docs), ", ".join(topic_ids))

    print()
    logger.info("=" * 60)
    logger.info("Ingestion complete!")
    logger.info("  Books processed : %d", total_books - skipped)
    logger.info("  Books skipped   : %d (missing / scanned)", skipped)
    logger.info("  Chunks stored   : %d", total_chunks_stored)
    logger.info("  Errors          : %d", failed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
