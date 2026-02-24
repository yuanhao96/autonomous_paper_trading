"""Topic learning state — tracks evidence, gaps, conflicts and confidence
across multiple retrieval rounds for a single curriculum topic.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from knowledge.store import Document


@dataclass
class TopicLearningState:
    topic_id: str
    round_idx: int = 0
    sub_questions: list[str] = field(default_factory=list)
    evidence_pool: list[Document] = field(default_factory=list)
    claims: list[dict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    prev_confidence: float = 0.0
    budget_used: int = 0  # approximate token count

    # Per-round audit trail: list of dicts with round, tools, n_docs, confidence
    round_log: list[dict] = field(default_factory=list)

    def add_evidence(self, docs: list[Document]) -> int:
        """Add new documents to the evidence pool, deduplicating by content hash.

        Returns the number of newly added (non-duplicate) documents.
        """
        existing_hashes = {_content_hash(d) for d in self.evidence_pool}
        added = 0
        for doc in docs:
            h = _content_hash(doc)
            if h not in existing_hashes:
                self.evidence_pool.append(doc)
                existing_hashes.add(h)
                added += 1
        return added

    def update_confidence(self, new_score: float) -> None:
        """Update confidence, preserving the previous value for marginal_gain."""
        self.prev_confidence = self.confidence
        self.confidence = max(0.0, min(1.0, new_score))

    def add_gap(self, gap: str) -> None:
        if gap and gap not in self.gaps:
            self.gaps.append(gap)

    def add_conflict(self, conflict: dict) -> None:
        """Add a detected conflict if not already recorded."""
        key = (conflict.get("claim_a", ""), conflict.get("claim_b", ""))
        existing = {(c.get("claim_a", ""), c.get("claim_b", "")) for c in self.conflicts}
        if key not in existing:
            self.conflicts.append(conflict)

    def log_round(self, tools_used: list[str], n_docs: int) -> None:
        self.round_log.append({
            "round": self.round_idx,
            "tools": tools_used,
            "docs_retrieved": n_docs,
            "confidence": round(self.confidence, 3),
            "gaps": list(self.gaps),
            "conflicts": len(self.conflicts),
        })

    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    def source_diversity(self) -> int:
        """Number of distinct tool_name values in the evidence pool."""
        names = set()
        for doc in self.evidence_pool:
            meta = getattr(doc, "meta", None) or {}
            name = meta.get("tool_name", "unknown")
            names.add(name)
        return len(names)


def _content_hash(doc: Document) -> str:
    text = (doc.content or "")[:500]
    return hashlib.md5(text.encode("utf-8")).hexdigest()
