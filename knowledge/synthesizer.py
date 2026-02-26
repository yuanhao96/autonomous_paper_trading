"""LLM-driven knowledge synthesis module.

Takes raw Document objects and synthesizes them into structured knowledge
using the Anthropic Claude API. Also provides mastery assessment for
curriculum progression.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from core.llm import call_llm, load_prompt_template
from knowledge.store import Document

logger = logging.getLogger(__name__)


@dataclass
class StructuredKnowledge:
    """Synthesized knowledge derived from one or more source documents."""

    summary: str
    key_concepts: list[str]
    trading_implications: list[str]
    risk_factors: list[str]
    curriculum_relevance: dict[str, float]  # topic_id -> relevance score 0-1
    source_documents: list[str]  # source URLs/titles
    claims: list[dict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


def _parse_json_response(raw: str) -> dict:
    """Attempt to parse a JSON object from an LLM response.

    The LLM may wrap the JSON in a markdown code fence or include leading/
    trailing commentary. This function tries progressively looser extraction
    strategies before giving up and returning an empty dict.
    """
    # 1. Direct parse
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. Extract from markdown code fence ```json ... ``` or ``` ... ```
    for fence_start in ("```json", "```"):
        if fence_start in raw:
            start = raw.index(fence_start) + len(fence_start)
            end = raw.find("```", start)
            if end != -1:
                try:
                    return json.loads(raw[start:end].strip())
                except (json.JSONDecodeError, TypeError):
                    pass

    # 3. Find the first { ... } block (greedy)
    brace_start = raw.find("{")
    brace_end = raw.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        try:
            return json.loads(raw[brace_start : brace_end + 1])
        except (json.JSONDecodeError, TypeError):
            pass

    logger.warning("Could not parse JSON from LLM response; returning empty dict")
    return {}


def _ensure_string_list(value: object) -> list[str]:
    """Coerce *value* into a list of strings."""
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


def _ensure_float_dict(value: object) -> dict[str, float]:
    """Coerce *value* into a dict mapping strings to floats in [0, 1]."""
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
    for k, v in value.items():
        try:
            score = float(v)
            result[str(k)] = max(0.0, min(1.0, score))
        except (TypeError, ValueError):
            continue
    return result


class KnowledgeSynthesizer:
    """Synthesizes raw documents into structured trading knowledge via LLM."""

    def __init__(self) -> None:
        pass

    def synthesize(self, documents: list[Document]) -> StructuredKnowledge:
        """Synthesize a list of raw documents into structured knowledge.

        Parameters
        ----------
        documents:
            Raw ``Document`` objects (from ``knowledge.store``) to synthesize.

        Returns
        -------
        StructuredKnowledge
            A structured representation of the synthesized content.
        """
        if not documents:
            return StructuredKnowledge(
                summary="",
                key_concepts=[],
                trading_implications=[],
                risk_factors=[],
                curriculum_relevance={},
                source_documents=[],
            )

        # Build combined document text for the prompt.
        doc_sections: list[str] = []
        source_refs: list[str] = []
        for i, doc in enumerate(documents, start=1):
            header = f"--- Document {i}: {doc.title} (source: {doc.source}) ---"
            doc_sections.append(f"{header}\n{doc.content}")
            source_refs.append(f"{doc.title} ({doc.source})")

        combined_text: str = "\n\n".join(doc_sections)

        # Load the synthesis prompt template and fill in the documents.
        template: str = load_prompt_template("synthesis")
        prompt: str = template.replace("{documents}", combined_text)

        # Call the LLM.
        raw_response: str = call_llm(prompt)

        # Parse the response.
        parsed: dict = _parse_json_response(raw_response)

        return StructuredKnowledge(
            summary=str(parsed.get("summary", "")),
            key_concepts=_ensure_string_list(parsed.get("key_concepts", [])),
            trading_implications=_ensure_string_list(
                parsed.get("trading_implications", [])
            ),
            risk_factors=_ensure_string_list(parsed.get("risk_factors", [])),
            curriculum_relevance=_ensure_float_dict(
                parsed.get("curriculum_relevance", {})
            ),
            source_documents=source_refs,
            claims=list(parsed.get("claims", [])),
            gaps=_ensure_string_list(parsed.get("gaps", [])),
        )

    def assess_mastery(
        self,
        topic_id: str,
        topic_name: str,
        topic_description: str,
        mastery_criteria: str,
        learned_content: str,
    ) -> tuple[float, str, list[str]]:
        """Assess the agent's mastery of a curriculum topic.

        Parameters
        ----------
        topic_id:
            Unique identifier for the topic (used for logging/tracking).
        topic_name:
            Human-readable name of the topic.
        topic_description:
            Description of what the topic covers.
        mastery_criteria:
            Criteria that define mastery of the topic.
        learned_content:
            Summary of what the agent has learned so far about this topic.

        Returns
        -------
        tuple[float, str, list[str]]
            A tuple of ``(score, reasoning, gaps)`` where *score* is a float
            in ``[0, 1]``, *reasoning* explains the assessment, and *gaps*
            lists remaining knowledge gaps.
        """
        template: str = load_prompt_template("mastery_assessment")
        prompt: str = (
            template.replace("{topic_name}", topic_name)
            .replace("{topic_description}", topic_description)
            .replace("{mastery_criteria}", mastery_criteria)
            .replace("{learned_content}", learned_content)
        )

        raw_response: str = call_llm(prompt)
        parsed: dict = _parse_json_response(raw_response)

        # Extract score, clamped to [0, 1].
        try:
            score = float(parsed.get("score", 0.0))
            score = max(0.0, min(1.0, score))
        except (TypeError, ValueError):
            logger.warning(
                "Invalid mastery score for topic %s; defaulting to 0.0", topic_id
            )
            score = 0.0

        reasoning: str = str(parsed.get("reasoning", ""))
        gaps: list[str] = _ensure_string_list(parsed.get("gaps", []))

        return score, reasoning, gaps
