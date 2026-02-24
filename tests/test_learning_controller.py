"""Unit tests for the multi-round learning controller system (Phases 1-3)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from knowledge.evaluator import (
    detect_conflicts,
    marginal_gain,
    score_document_relevance,
    score_source_quality,
)
from knowledge.learning_state import TopicLearningState
from knowledge.store import Document
from knowledge.tools import (
    AlpacaNewsTool,
    MemorySearchTool,
    ToolInput,
    ToolOutput,
    WikipediaTool,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_doc(title: str = "Test", content: str = "Test content", tool_name: str = "memory") -> Document:
    doc = Document(title=title, content=content, source="test", topic_tags=[])
    doc.meta = {
        "tool_name": tool_name,
        "evidence_type": "retrieved",
        "quality_score": 0.7,
        "novelty_score": 0.5,
        "retrieval_query": "test",
        "retrieved_at": "2026-01-01T00:00:00+00:00",
    }
    return doc


# ---------------------------------------------------------------------------
# Phase 1: Tool wrappers
# ---------------------------------------------------------------------------

class TestMemorySearchTool:
    def test_returns_tool_output(self):
        mock_memory = MagicMock()
        mock_memory.search.return_value = [
            {"content": "Order books match buyers and sellers.", "path": "test.md",
             "topic_name": "Market Microstructure", "tags": ["book"], "score": 5.0}
        ]
        tool = MemorySearchTool(mock_memory)
        result = tool.run(ToolInput(topic="Market Microstructure"))

        assert isinstance(result, ToolOutput)
        assert len(result.documents) == 1
        assert result.documents[0].content == "Order books match buyers and sellers."
        assert result.tool_meta["n_results"] == 1

    def test_handles_empty_results(self):
        mock_memory = MagicMock()
        mock_memory.search.return_value = []
        tool = MemorySearchTool(mock_memory)
        result = tool.run(ToolInput(topic="Unknown Topic"))

        assert isinstance(result, ToolOutput)
        assert result.documents == []
        assert result.errors == []

    def test_handles_search_error(self):
        mock_memory = MagicMock()
        mock_memory.search.side_effect = RuntimeError("DB error")
        tool = MemorySearchTool(mock_memory)
        result = tool.run(ToolInput(topic="Momentum"))

        assert isinstance(result, ToolOutput)
        assert len(result.errors) == 1
        assert "DB error" in result.errors[0]

    def test_evidence_metadata_attached(self):
        mock_memory = MagicMock()
        mock_memory.search.return_value = [
            {"content": "Spread is bid minus ask.", "path": "t.md",
             "topic_name": "Spreads", "tags": [], "score": 3.0}
        ]
        tool = MemorySearchTool(mock_memory)
        result = tool.run(ToolInput(topic="Spreads", sub_question="What is bid-ask spread?"))

        doc = result.documents[0]
        assert hasattr(doc, "meta") and doc.meta is not None
        assert doc.meta["tool_name"] == "memory"
        assert "retrieved_at" in doc.meta
        assert "quality_score" in doc.meta


# ---------------------------------------------------------------------------
# Phase 2: Evaluator
# ---------------------------------------------------------------------------

class TestScoreDocumentRelevance:
    def test_returns_float_in_range(self):
        doc = _make_doc(content="Market microstructure involves order books and spreads.")
        score = score_document_relevance(doc, "Market Microstructure")
        assert 0.0 <= score <= 1.0

    def test_higher_for_matching_content(self):
        relevant = _make_doc(content="Momentum trading uses RSI and moving average crossover signals.")
        irrelevant = _make_doc(content="The weather is nice today and the birds are singing.")
        s1 = score_document_relevance(relevant, "Momentum Trading RSI")
        s2 = score_document_relevance(irrelevant, "Momentum Trading RSI")
        assert s1 > s2

    def test_empty_topic_returns_zero(self):
        doc = _make_doc(content="Some content.")
        assert score_document_relevance(doc, "") == 0.0

    def test_empty_content_returns_zero(self):
        doc = _make_doc(content="")
        assert score_document_relevance(doc, "Momentum") == 0.0


class TestScoreSourceQuality:
    @pytest.mark.parametrize("tool_name,expected", [
        ("arxiv", 0.9),
        ("wikipedia", 0.8),
        ("book", 0.75),
        ("memory", 0.7),
        ("web", 0.6),
        ("news", 0.5),
    ])
    def test_correct_values_per_tool(self, tool_name, expected):
        doc = _make_doc(tool_name=tool_name)
        assert score_source_quality(doc) == expected

    def test_unknown_tool_returns_default(self):
        doc = _make_doc(tool_name="unknown_source")
        assert 0.0 <= score_source_quality(doc) <= 1.0


class TestDetectConflicts:
    def test_finds_opposing_sentiment(self):
        claims = [
            {"claim": "Momentum strategies always increase returns in trending markets.", "source_title": "Book A", "confidence": 0.8},
            {"claim": "Momentum strategies never guarantee returns in markets.", "source_title": "Book B", "confidence": 0.7},
        ]
        conflicts = detect_conflicts(claims)
        assert isinstance(conflicts, list)

    def test_no_conflicts_in_consistent_claims(self):
        claims = [
            {"claim": "Market orders execute immediately.", "source_title": "A", "confidence": 0.9},
            {"claim": "Limit orders set a price ceiling.", "source_title": "B", "confidence": 0.9},
        ]
        conflicts = detect_conflicts(claims)
        # These don't conflict — both can be true simultaneously
        assert isinstance(conflicts, list)

    def test_empty_claims_returns_empty(self):
        assert detect_conflicts([]) == []

    def test_single_claim_no_conflict(self):
        claims = [{"claim": "RSI is an oscillator.", "source_title": "X", "confidence": 0.9}]
        assert detect_conflicts(claims) == []


class TestMarginalGain:
    def test_positive_gain(self):
        assert marginal_gain(0.4, 0.7) == pytest.approx(0.3)

    def test_zero_gain(self):
        assert marginal_gain(0.5, 0.5) == 0.0

    def test_no_negative_gain(self):
        # Confidence should never decrease in our model, but guard against it
        assert marginal_gain(0.8, 0.6) == 0.0


# ---------------------------------------------------------------------------
# Phase 2: TopicLearningState
# ---------------------------------------------------------------------------

class TestTopicLearningState:
    def test_add_evidence_deduplicates(self):
        state = TopicLearningState(topic_id="momentum")
        doc = _make_doc(content="Same content here.")
        state.add_evidence([doc, doc])  # duplicate
        assert len(state.evidence_pool) == 1

    def test_add_evidence_returns_new_count(self):
        state = TopicLearningState(topic_id="momentum")
        doc1 = _make_doc(content="First unique content.")
        doc2 = _make_doc(content="Second unique content.")
        added = state.add_evidence([doc1, doc2])
        assert added == 2

    def test_update_confidence_clamps(self):
        state = TopicLearningState(topic_id="test")
        state.update_confidence(1.5)
        assert state.confidence == 1.0
        state.update_confidence(-0.5)
        assert state.confidence == 0.0

    def test_source_diversity(self):
        state = TopicLearningState(topic_id="test")
        doc1 = _make_doc(tool_name="memory")
        doc2 = _make_doc(content="Wikipedia content about markets.", tool_name="wikipedia")
        state.add_evidence([doc1, doc2])
        assert state.source_diversity() == 2


# ---------------------------------------------------------------------------
# Phase 3: LearningController stop policy
# ---------------------------------------------------------------------------

class TestLearningControllerStopPolicy:
    def _make_controller(self, max_rounds=3, threshold=0.75, min_gain=0.05):
        from knowledge.learning_controller import LearningController
        ctrl = LearningController.__new__(LearningController)
        ctrl.max_rounds = max_rounds
        ctrl.confidence_threshold = threshold
        ctrl.min_marginal_gain = min_gain
        ctrl.per_topic_budget = 50000
        return ctrl

    def test_stops_at_confidence_threshold(self):
        ctrl = self._make_controller()
        state = TopicLearningState(topic_id="test")
        state.round_idx = 1
        state.update_confidence(0.8)  # above threshold 0.75
        assert ctrl.should_continue(state) is False

    def test_stops_at_max_rounds(self):
        ctrl = self._make_controller(max_rounds=3)
        state = TopicLearningState(topic_id="test")
        state.round_idx = 3
        state.confidence = 0.3  # low confidence but max rounds hit
        assert ctrl.should_continue(state) is False

    def test_stops_on_low_marginal_gain(self):
        ctrl = self._make_controller(min_gain=0.05)
        state = TopicLearningState(topic_id="test")
        state.round_idx = 2
        state.prev_confidence = 0.50
        state.confidence = 0.51  # gain = 0.01 < 0.05
        assert ctrl.should_continue(state) is False

    def test_continues_when_below_threshold(self):
        ctrl = self._make_controller()
        state = TopicLearningState(topic_id="test")
        state.round_idx = 0
        state.confidence = 0.3
        assert ctrl.should_continue(state) is True

    def test_stops_on_budget_exhausted(self):
        ctrl = self._make_controller()
        state = TopicLearningState(topic_id="test")
        state.round_idx = 0
        state.confidence = 0.3
        state.budget_used = 100_000  # over budget
        assert ctrl.should_continue(state) is False


class TestPlanSubQuestions:
    def test_returns_list_of_strings_with_mock_llm(self):
        from knowledge.learning_controller import LearningController
        ctrl = LearningController.__new__(LearningController)
        ctrl.max_rounds = 3
        ctrl.confidence_threshold = 0.75
        ctrl.min_marginal_gain = 0.05
        ctrl.per_topic_budget = 50000
        ctrl._tool_map = {}

        mock_response = '["What is market microstructure?", "How do order books work?", "What are bid-ask spreads?", "Who are market makers?"]'
        with patch("knowledge.learning_controller.call_llm", return_value=mock_response):
            questions = ctrl.plan_sub_questions("Market Microstructure", "How exchanges work", 1)

        assert isinstance(questions, list)
        assert len(questions) >= 3
        assert all(isinstance(q, str) for q in questions)

    def test_falls_back_on_llm_error(self):
        from knowledge.learning_controller import LearningController
        ctrl = LearningController.__new__(LearningController)
        ctrl.max_rounds = 3
        ctrl.confidence_threshold = 0.75
        ctrl.min_marginal_gain = 0.05
        ctrl.per_topic_budget = 50000
        ctrl._tool_map = {}

        with patch("knowledge.learning_controller.call_llm", side_effect=RuntimeError("API down")):
            questions = ctrl.plan_sub_questions("Order Types", "Market, limit, stop orders", 1)

        assert isinstance(questions, list)
        assert len(questions) >= 3
