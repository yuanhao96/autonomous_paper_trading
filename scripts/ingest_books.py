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

from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

import yaml  # noqa: E402

from knowledge.ingestion import fetch_book_text  # noqa: E402
from knowledge.store import MarkdownMemory, _slugify  # noqa: E402

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
    parser = argparse.ArgumentParser(
        description="Bulk-ingest investment books into knowledge base.",
    )
    parser.add_argument("--chunks", type=int, default=10,
                        help="Max chunks to load per book (default: 10)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be ingested without writing anything.")
    parser.add_argument("--skip-existing", action="store_true", default=True,
                        help="Skip books whose first chunk already exists (default: True).")
    parser.add_argument("--force", action="store_true",
                        help="Re-ingest all books even if already present.")
    args = parser.parse_args()
    skip_existing = args.skip_existing and not args.force

    books_dir = _get_books_dir()
    books_map = _load_books_config()
    memory = MarkdownMemory(memory_root=str(_PROJECT_ROOT / "knowledge" / "memory" / "trading"))

    # Build book → [topic_ids] mapping from books.yaml.
    book_topics: dict[str, list[str]] = {}
    for topic_id, filenames in books_map.items():
        for fname in filenames:
            book_topics.setdefault(fname, []).append(topic_id)

    # Discover ALL .txt files in books_dir, not just those in books.yaml.
    all_book_files = sorted(books_dir.glob("*.txt"))
    total_books = len(all_book_files)
    total_chunks_stored = 0
    skipped_empty = 0
    skipped_existing = 0
    failed = 0

    logger.info("Books directory  : %s", books_dir)
    logger.info("Total book files : %d", total_books)
    logger.info("Mapped in YAML   : %d unique books", len(book_topics))
    logger.info("Chunks per book  : %d", args.chunks)
    logger.info("Skip existing    : %s", skip_existing)
    if args.dry_run:
        logger.info("DRY RUN — no files will be written.\n")

    for i, book_path in enumerate(all_book_files, start=1):
        filename = book_path.name
        topic_ids = book_topics.get(filename, [])
        topic_hint = topic_ids[0] if topic_ids else "trading"
        tags = ["book"] + (topic_ids if topic_ids else ["trading", "investment"])

        # Check if already ingested using the same slug formula as store_discovered.
        # topic_name = f"{stem[:50]} — part 1" → _slugify → filename
        stem50 = Path(filename).stem[:50]
        first_chunk_slug = _slugify(f"{stem50} \u2014 part 1")
        existing_path = (
            _PROJECT_ROOT / "knowledge" / "memory" / "trading" / "discovered"
            / f"{first_chunk_slug}.md"
        )
        if skip_existing and existing_path.exists():
            logger.debug("[%d/%d] ⏭  Already ingested: %s", i, total_books, filename[:60])
            skipped_existing += 1
            continue

        logger.info("[%d/%d] %s", i, total_books, filename[:70])

        docs = fetch_book_text(
            str(book_path),
            topic_hint=topic_hint,
            chunk_size=3000,
            skip_chars=3000,
            max_chunks=args.chunks,
        )

        if not docs:
            logger.warning("  ⚠  No content extracted (scanned PDF?), skipping.")
            skipped_empty += 1
            continue

        if args.dry_run:
            label = ", ".join(topic_ids) if topic_ids else "(unmapped)"
            logger.info("  → Would store %d chunk(s) | topics: %s", len(docs), label)
            total_chunks_stored += len(docs)
            continue

        for j, doc in enumerate(docs):
            doc.topic_tags = tags
            topic_name = f"{Path(filename).stem[:50]} — part {j + 1}"
            try:
                memory.store_discovered(
                    topic_name=topic_name,
                    content=doc.content,
                    source=str(book_path),
                    tags=tags,
                )
                total_chunks_stored += 1
            except Exception as exc:
                logger.error("    ❌ Failed to store chunk %d: %s", j + 1, exc)
                failed += 1

        label = ", ".join(topic_ids) if topic_ids else "(unmapped — tagged: trading, investment)"
        logger.info("  ✅ Stored %d chunk(s) | %s", len(docs), label)

    print()
    logger.info("=" * 60)
    logger.info("Ingestion complete!")
    logger.info("  Books processed   : %d", total_books - skipped_empty - skipped_existing)
    logger.info("  Already existed   : %d (skipped)", skipped_existing)
    logger.info("  Scanned/empty     : %d (skipped)", skipped_empty)
    logger.info("  Chunks stored     : %d", total_chunks_stored)
    logger.info("  Errors            : %d", failed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
