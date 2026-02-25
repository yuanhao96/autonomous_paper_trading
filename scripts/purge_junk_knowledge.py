"""Remove low-quality knowledge files from a MarkdownMemory directory.

A file is considered "junk" when its body content (everything after the YAML
frontmatter) is shorter than a configurable character threshold.  These are
typically PDF-conversion artifacts that contain only a table-of-contents line
such as "Chapter 5 Tails 91" rather than actual prose.

Usage:
    # Dry-run (default) — print what would be deleted
    python scripts/purge_junk_knowledge.py

    # Also remove books where ≥ BOOK_JUNK_PCT percent of parts are junk
    python scripts/purge_junk_knowledge.py --purge-bad-books

    # Actually delete
    python scripts/purge_junk_knowledge.py --execute

    # Custom directory / threshold
    python scripts/purge_junk_knowledge.py \\
        --dir knowledge/memory/trading/discovered \\
        --threshold 100 \\
        --purge-bad-books \\
        --book-junk-pct 80 \\
        --execute
"""

import argparse
import os
import re
from collections import defaultdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_body(content: str) -> str:
    """Return the markdown body with YAML frontmatter stripped."""
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            return content[end + 4:].strip()
    return content.strip()


def book_name(filename: str) -> str:
    """Extract the book slug from a partitioned filename.

    e.g. ``algorithmic_trading_part_3.md`` → ``algorithmic_trading``
    """
    return re.sub(r"_part_\d+\.md$", "", filename)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def collect_junk(
    directory: str,
    threshold: int,
    purge_bad_books: bool,
    book_junk_pct: int,
) -> list[str]:
    """Return a sorted list of absolute file paths that should be deleted."""

    md_files: list[tuple[str, str, int]] = []  # (abspath, book_slug, body_len)

    for fname in os.listdir(directory):
        if not fname.endswith(".md") or fname == ".gitkeep":
            continue
        fpath = os.path.join(directory, fname)
        with open(fpath, errors="replace") as fh:
            body = parse_body(fh.read())
        md_files.append((fpath, book_name(fname), len(body)))

    # --- Pass 1: individual junk parts ---
    junk_set: set[str] = {p for p, _, bl in md_files if bl < threshold}

    # --- Pass 2 (optional): whole-book purge ---
    if purge_bad_books:
        book_parts: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for fpath, slug, body_len in md_files:
            book_parts[slug].append((fpath, body_len))

        for slug, parts in book_parts.items():
            junk_count = sum(1 for _, bl in parts if bl < threshold)
            pct = junk_count / len(parts) * 100
            if pct >= book_junk_pct:
                for fpath, _ in parts:
                    junk_set.add(fpath)

    return sorted(junk_set)


def run(
    directory: str,
    threshold: int,
    purge_bad_books: bool,
    book_junk_pct: int,
    execute: bool,
) -> None:
    to_delete = collect_junk(directory, threshold, purge_bad_books, book_junk_pct)

    if not to_delete:
        print("Nothing to delete.")
        return

    print(f"{'Deleting' if execute else 'Would delete'} {len(to_delete)} file(s):\n")
    for path in to_delete:
        print(f"  {'DEL' if execute else 'DRY'} {os.path.basename(path)}")
        if execute:
            os.remove(path)

    print(f"\n{'Deleted' if execute else 'Dry-run complete —'} {len(to_delete)} file(s).")
    if not execute:
        print("Re-run with --execute to actually remove them.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Purge junk knowledge files from a MarkdownMemory directory."
    )
    parser.add_argument(
        "--dir",
        default="knowledge/memory/trading/discovered",
        help="Path to the knowledge directory (default: knowledge/memory/trading/discovered)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=100,
        help="Minimum body character count to keep a file (default: 100)",
    )
    parser.add_argument(
        "--purge-bad-books",
        action="store_true",
        help="Also delete all parts of books where ≥ BOOK_JUNK_PCT%% of parts are junk",
    )
    parser.add_argument(
        "--book-junk-pct",
        type=int,
        default=80,
        help="Junk-part percentage that triggers whole-book removal (default: 80)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete files (default is dry-run)",
    )
    args = parser.parse_args()

    directory = os.path.abspath(args.dir)
    if not os.path.isdir(directory):
        print(f"Error: directory not found: {directory}")
        raise SystemExit(1)

    run(
        directory=directory,
        threshold=args.threshold,
        purge_bad_books=args.purge_bad_books,
        book_junk_pct=args.book_junk_pct,
        execute=args.execute,
    )


if __name__ == "__main__":
    main()
