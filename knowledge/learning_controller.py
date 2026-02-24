"""Multi-round, tool-orchestrated learning controller.

Replaces the fixed BM25 → Wikipedia → DDG sequence in simulate_learning.py
with a dynamic loop that:
  1. Plans sub-questions for the topic via LLM.
  2. Selects tools via policy (based on stage, topic type, conflict state).
  3. Runs retrieval rounds, deduplicating and scoring evidence.
  4. Synthesizes and critiques after each round.
  5. Stops when confidence target is met, budget exhausted, or max_rounds hit.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from core.llm import call_llm
from knowledge.curriculum import CurriculumTracker
from knowledge.evaluator import (
    detect_conflicts,
    marginal_gain,
    score_document_relevance,
    score_source_quality,
)
from knowledge.learning_state import TopicLearningState
from knowledge.store import Document, MarkdownMemory
from knowledge.synthesizer import KnowledgeSynthesizer, StructuredKnowledge
from knowledge.tools import (
    AlpacaNewsTool,
    ArxivTool,
    BookChunkTool,
    DuckDuckGoTool,
    KnowledgeTool,
    MemorySearchTool,
    ToolInput,
    WikipediaTool,
    default_tools,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_learning_settings() -> dict[str, Any]:
    cfg_path = _PROJECT_ROOT / "config" / "settings.yaml"
    try:
        with open(cfg_path) as fh:
            data = yaml.safe_load(fh) or {}
        return data.get("learning", {})
    except Exception:
        return {}


class LearningController:
    """Orchestrates multi-round, tool-assisted knowledge acquisition per topic."""

    def __init__(
        self,
        memory: MarkdownMemory,
        synthesizer: KnowledgeSynthesizer,
        curriculum: CurriculumTracker,
        tools: list[KnowledgeTool] | None = None,
    ) -> None:
        self._memory = memory
        self._synthesizer = synthesizer
        self._curriculum = curriculum
        self._tools: list[KnowledgeTool] = tools or default_tools(memory)

        cfg = _load_learning_settings()
        self.max_rounds: int = int(cfg.get("max_rounds", 3))
        self.confidence_threshold: float = float(cfg.get("confidence_threshold", 0.75))
        self.min_marginal_gain: float = float(cfg.get("min_marginal_gain", 0.05))
        self.per_topic_budget: int = int(cfg.get("per_topic_budget", 50000))

        # Build a name→tool mapping for quick lookup
        self._tool_map: dict[str, KnowledgeTool] = {
            t.spec.name: t for t in self._tools
        }

    # ------------------------------------------------------------------
    # Sub-question planning
    # ------------------------------------------------------------------

    def plan_sub_questions(
        self, topic_name: str, topic_desc: str, stage: int
    ) -> list[str]:
        """Ask the LLM to decompose *topic_name* into 3-5 mastery sub-questions.

        Returns a list of strings. Falls back to a simple heuristic list on error.
        """
        prompt = (
            f"You are a financial education expert designing a curriculum for an "
            f"autonomous trading agent (Stage {stage}).\n\n"
            f"Topic: {topic_name}\n"
            f"Description: {topic_desc}\n\n"
            f"Generate exactly 4 concise sub-questions whose answers together prove "
            f"mastery of this topic. Each question should be answerable from trading "
            f"literature and should cover a distinct aspect (definition, mechanism, "
            f"application, risk).\n\n"
            f'Output ONLY a JSON array of strings: ["question1", "question2", ...]'
        )
        try:
            raw = call_llm(prompt)
            # Extract JSON array
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            if match:
                questions = json.loads(match.group())
                if isinstance(questions, list) and questions:
                    logger.info(
                        "Planned %d sub-questions for '%s'.", len(questions), topic_name
                    )
                    return [str(q) for q in questions[:5]]
        except Exception:
            logger.exception("LLM sub-question planning failed; using heuristic.")

        # Heuristic fallback
        return [
            f"What is {topic_name} and why does it matter in trading?",
            f"How does {topic_name} work mechanically?",
            f"What are the main trading strategies using {topic_name}?",
            f"What are the key risks and edge cases of {topic_name}?",
        ]

    # ------------------------------------------------------------------
    # Tool selection
    # ------------------------------------------------------------------

    def select_tools(
        self,
        sub_question: str,
        state: TopicLearningState,
        stage: int,
        topic_name: str = "",
    ) -> list[KnowledgeTool]:
        """Choose tools based on stage, topic type, and current learning state."""
        selected: list[KnowledgeTool] = []

        def _get(name: str) -> KnowledgeTool | None:
            return self._tool_map.get(name)

        # Always: memory + web search (every stage, every round)
        if mem := _get("memory"):
            selected.append(mem)
        if web := _get("web"):
            selected.append(web)

        # Stage-based additions on top of the universal set
        if stage <= 2:
            if wiki := _get("wikipedia"):
                selected.append(wiki)
            if book := _get("book"):
                selected.append(book)
            if stage == 2:
                if arxiv := _get("arxiv"):
                    selected.append(arxiv)
        elif stage == 3:
            if book := _get("book"):
                selected.append(book)
            if arxiv := _get("arxiv"):
                selected.append(arxiv)
        else:  # stage 4
            if arxiv := _get("arxiv"):
                selected.append(arxiv)
            if news := _get("news"):
                selected.append(news)

        # Market/current topic override: add news + web
        market_keywords = {"market", "news", "regulatory", "earnings", "fed", "macro"}
        if any(kw in topic_name.lower() for kw in market_keywords):
            for name in ("news", "web"):
                tool = _get(name)
                if tool and tool not in selected:
                    selected.append(tool)

        # Conflict detected: ensure at least 2 independent source types
        if state.has_conflicts() and state.source_diversity() < 2:
            for name in ("wikipedia", "arxiv", "web"):
                tool = _get(name)
                if tool and tool not in selected:
                    selected.append(tool)
                    break

        logger.info(
            "Round %d — selected tools: %s",
            state.round_idx + 1,
            [t.spec.name for t in selected],
        )
        return selected

    # ------------------------------------------------------------------
    # Single round
    # ------------------------------------------------------------------

    def run_round(
        self,
        state: TopicLearningState,
        topic_name: str,
        topic_desc: str,
        stage: int,
    ) -> TopicLearningState:
        """Execute one retrieval + synthesis round, updating *state* in-place."""
        tools_used: list[str] = []

        # --- 1. Select tools for this round ---
        sub_q = (
            state.sub_questions[state.round_idx % len(state.sub_questions)]
            if state.sub_questions
            else ""
        )
        tools = self.select_tools(sub_q, state, stage, topic_name)

        # --- 2. Run tools and collect documents ---
        new_docs: list[Document] = []
        for tool in tools:
            inp = ToolInput(topic=topic_name, sub_question=sub_q)
            try:
                output = tool.run(inp)
                if output.errors:
                    logger.warning(
                        "Tool '%s' errors: %s", tool.spec.name, output.errors
                    )
                new_docs.extend(output.documents)
                tools_used.append(tool.spec.name)
            except Exception:
                logger.exception("Tool '%s' raised an exception.", tool.spec.name)

        # --- 3. Score relevance and filter ---
        scored = sorted(
            new_docs,
            key=lambda d: score_document_relevance(d, topic_name) * score_source_quality(d),
            reverse=True,
        )
        # Keep top 10 for synthesis
        top_docs = scored[:10]
        added = state.add_evidence(top_docs)
        logger.info(
            "Round %d: retrieved %d docs, %d new after dedup.",
            state.round_idx + 1, len(new_docs), added,
        )

        # --- 4. Synthesize all evidence so far ---
        if not state.evidence_pool:
            logger.warning("Round %d: evidence pool is empty, skipping synthesis.", state.round_idx + 1)
            state.log_round(tools_used, 0)
            state.round_idx += 1
            return state

        try:
            knowledge: StructuredKnowledge = self._synthesizer.synthesize(
                state.evidence_pool[:15]  # cap to avoid huge prompts
            )
        except Exception:
            logger.exception("Synthesis failed in round %d.", state.round_idx + 1)
            state.log_round(tools_used, added)
            state.round_idx += 1
            return state

        # --- 5. Extract claims and detect conflicts ---
        new_claims = getattr(knowledge, "claims", []) or []
        for c in new_claims:
            state.claims.append(c)

        if state.claims:
            new_conflicts = detect_conflicts(state.claims)
            for cf in new_conflicts:
                state.add_conflict(cf)
            if new_conflicts:
                logger.warning(
                    "Round %d: detected %d conflict(s).", state.round_idx + 1, len(new_conflicts)
                )

        # --- 6. Update gaps from synthesis ---
        for gap in getattr(knowledge, "gaps", []) or []:
            state.add_gap(gap)

        # --- 7. Update confidence ---
        # Score = average of relevance × source_quality across evidence pool
        if state.evidence_pool:
            pool_score = sum(
                score_document_relevance(d, topic_name) * score_source_quality(d)
                for d in state.evidence_pool
            ) / len(state.evidence_pool)
        else:
            pool_score = 0.0

        # Blend pool quality with synthesis richness
        n_concepts = len(getattr(knowledge, "key_concepts", []) or [])
        n_implications = len(getattr(knowledge, "trading_implications", []) or [])
        richness = min(1.0, (n_concepts + n_implications) / 20)
        new_confidence = 0.4 * pool_score + 0.6 * richness

        # Penalise for unresolved conflicts
        if state.conflicts:
            new_confidence *= max(0.5, 1.0 - 0.1 * len(state.conflicts))

        state.update_confidence(new_confidence)
        state.log_round(tools_used, added)

        logger.info(
            "Round %d complete — confidence: %.2f → %.2f | gaps: %d | conflicts: %d",
            state.round_idx + 1,
            state.prev_confidence,
            state.confidence,
            len(state.gaps),
            len(state.conflicts),
        )
        state.round_idx += 1
        return state

    # ------------------------------------------------------------------
    # Stop policy
    # ------------------------------------------------------------------

    def should_continue(self, state: TopicLearningState) -> bool:
        """Return True if another learning round should be executed."""
        if state.round_idx >= self.max_rounds:
            logger.info("Stop: max_rounds (%d) reached.", self.max_rounds)
            return False
        if state.confidence >= self.confidence_threshold:
            logger.info(
                "Stop: confidence %.2f >= threshold %.2f.",
                state.confidence, self.confidence_threshold,
            )
            return False
        if state.round_idx > 0:
            gain = marginal_gain(state.prev_confidence, state.confidence)
            if gain < self.min_marginal_gain:
                logger.info(
                    "Stop: marginal gain %.3f < %.3f.", gain, self.min_marginal_gain
                )
                return False
        if state.budget_used >= self.per_topic_budget:
            logger.info(
                "Stop: budget %d >= limit %d.", state.budget_used, self.per_topic_budget
            )
            return False
        return True

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def learn_topic(
        self, topic: Any
    ) -> tuple[StructuredKnowledge, TopicLearningState]:
        """Run the full multi-round learning loop for *topic*.

        Parameters
        ----------
        topic:
            A curriculum topic object with `.id`, `.name`, `.description`, `.stage`.

        Returns
        -------
        (StructuredKnowledge, TopicLearningState)
            Final synthesized knowledge and the full learning state for audit.
        """
        stage = getattr(topic, "stage", 1)
        topic_name = getattr(topic, "name", str(topic))
        topic_desc = getattr(topic, "description", "")

        state = TopicLearningState(topic_id=getattr(topic, "id", topic_name))

        # Plan sub-questions once at the start
        state.sub_questions = self.plan_sub_questions(topic_name, topic_desc, stage)
        logger.info(
            "Learning '%s' (stage %d) — sub-questions: %s",
            topic_name, stage, state.sub_questions,
        )

        final_knowledge: StructuredKnowledge | None = None

        while self.should_continue(state):
            state = self.run_round(state, topic_name, topic_desc, stage)

        # Final synthesis over the entire evidence pool
        if state.evidence_pool:
            try:
                final_knowledge = self._synthesizer.synthesize(state.evidence_pool[:15])
            except Exception:
                logger.exception("Final synthesis failed.")

        if final_knowledge is None:
            from knowledge.synthesizer import StructuredKnowledge as SK
            final_knowledge = SK(
                summary="Learning completed but synthesis failed.",
                key_concepts=[],
                trading_implications=[],
                risk_factors=[],
                curriculum_relevance={},
                source_documents=[],
            )

        # Log confidence trajectory
        logger.info("Learning complete for '%s':", topic_name)
        for entry in state.round_log:
            logger.info(
                "  Round %d | tools=%s | docs=%d | confidence=%.2f | gaps=%d",
                entry["round"] + 1,
                entry["tools"],
                entry["docs_retrieved"],
                entry["confidence"],
                len(entry.get("gaps", [])),
            )

        return final_knowledge, state
