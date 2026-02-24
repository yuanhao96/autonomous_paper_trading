"""Evidence quality evaluation functions for the multi-round learning loop."""
from __future__ import annotations

import re

from knowledge.store import Document

# Quality scores by tool source (heuristic)
_SOURCE_QUALITY: dict[str, float] = {
    "arxiv": 0.9,
    "wikipedia": 0.8,
    "book": 0.75,
    "memory": 0.7,
    "web": 0.6,
    "news": 0.5,
}


def score_document_relevance(doc: Document, topic: str) -> float:
    """Estimate relevance of *doc* to *topic* using keyword overlap (0–1).

    Splits topic into keywords, counts how many appear in the document
    content (case-insensitive), and normalises by total keywords.
    """
    if not topic or not doc.content:
        return 0.0

    keywords = re.findall(r"\w+", topic.lower())
    keywords = [k for k in keywords if len(k) > 3]  # skip short stop words
    if not keywords:
        return 0.0

    text_lower = doc.content.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    return min(1.0, hits / len(keywords))


def score_source_quality(doc: Document) -> float:
    """Heuristic quality score (0–1) based on the tool that retrieved the doc."""
    meta = getattr(doc, "meta", None) or {}
    tool_name = meta.get("tool_name", "")
    # Check topic_tags as fallback
    if not tool_name:
        tags = doc.topic_tags or []
        for tag in tags:
            if tag in _SOURCE_QUALITY:
                return _SOURCE_QUALITY[tag]
    return _SOURCE_QUALITY.get(tool_name, 0.5)


def detect_conflicts(claims: list[dict]) -> list[dict]:
    """Find pairs of claims that assert contradictory things about the same concept.

    A conflict is detected when two claims share the same concept key but have
    different value assertions (simple heuristic: same noun phrase, opposite
    modal verbs or contradictory adjectives).

    Each claim dict should have at minimum:
        {"claim": str, "source_title": str, "confidence": float}

    Returns a list of conflict dicts:
        {"claim_a": str, "claim_b": str, "source_a": str, "source_b": str, "reason": str}
    """
    conflicts: list[dict] = []
    _OPPOSITES = [
        ({"increase", "rises", "higher", "positive", "bullish"},
         {"decrease", "falls", "lower", "negative", "bearish"}),
        ({"always", "guaranteed", "certain"},
         {"never", "impossible", "uncertain"}),
        ({"correlated", "related", "linked"},
         {"uncorrelated", "unrelated", "independent"}),
    ]

    for i, c1 in enumerate(claims):
        for c2 in claims[i + 1:]:
            text1 = (c1.get("claim") or "").lower()
            text2 = (c2.get("claim") or "").lower()

            # Check for opposing sentiment signals
            for pos_set, neg_set in _OPPOSITES:
                c1_pos = any(w in text1 for w in pos_set)
                c1_neg = any(w in text1 for w in neg_set)
                c2_pos = any(w in text2 for w in pos_set)
                c2_neg = any(w in text2 for w in neg_set)

                if (c1_pos and c2_neg) or (c1_neg and c2_pos):
                    # Check they share at least one noun (very rough)
                    words1 = set(re.findall(r"\b[a-z]{4,}\b", text1))
                    words2 = set(re.findall(r"\b[a-z]{4,}\b", text2))
                    shared = words1 & words2 - {"that", "with", "this", "from",
                                                 "when", "have", "will", "been"}
                    if shared:
                        conflicts.append({
                            "claim_a": c1.get("claim", ""),
                            "claim_b": c2.get("claim", ""),
                            "source_a": c1.get("source_title", ""),
                            "source_b": c2.get("source_title", ""),
                            "reason": f"Opposing assertions detected (shared concepts: {', '.join(list(shared)[:3])})",
                        })
                        break
    return conflicts


def marginal_gain(prev_confidence: float, new_confidence: float) -> float:
    """Return the improvement in confidence from the previous round."""
    return max(0.0, new_confidence - prev_confidence)
