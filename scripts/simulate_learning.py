"""Simulate the nightly learning process for the first N curriculum topics.

This script exercises the full learning pipeline:
  1. Load curriculum & identify topics to learn
  2. Search the knowledge base (BM25) for relevant book chunks
  3. Fetch Wikipedia summaries as supplementary material
  4. Synthesize knowledge via LLM (or local extraction if no API key)
  5. Store synthesized knowledge in curriculum files
  6. Assess mastery

Usage:
    python scripts/simulate_learning.py [--topics N] [--dry-run] [--skip-wiki]
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import textwrap
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

from knowledge.curriculum import CurriculumTracker
from knowledge.learning_controller import LearningController
from knowledge.store import MarkdownMemory, Document
from knowledge.synthesizer import KnowledgeSynthesizer, StructuredKnowledge
from knowledge.ingestion import fetch_web_search, fetch_wikipedia

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("simulate_learning")


def _has_llm_key() -> bool:
    """Check if a Moonshot API key is available."""
    return bool(os.getenv("MOONSHOT_API_KEY"))


def _extract_sentences(text: str, keywords: list[str], max_sentences: int = 10) -> list[str]:
    """Extract sentences from text that contain any of the keywords."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    matches = []
    kw_lower = [k.lower() for k in keywords]
    for s in sentences:
        s_lower = s.lower()
        if any(kw in s_lower for kw in kw_lower):
            clean = s.strip()
            if 20 < len(clean) < 500:
                matches.append(clean)
    return matches[:max_sentences]


def _local_synthesize(
    documents: list[Document],
    topic_name: str,
    topic_description: str,
) -> StructuredKnowledge:
    """Extract knowledge from documents without an LLM call.

    Uses keyword matching to pull relevant sentences and concepts.
    Good enough to test the full pipeline end-to-end.
    """
    # Build keyword list from topic name and description.
    stop_words = {"the", "a", "an", "and", "or", "for", "to", "in", "of", "is", "are", "how", "what"}
    words = re.findall(r'[a-z]+', (topic_name + " " + topic_description).lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    all_text = " ".join(doc.content for doc in documents)
    relevant_sentences = _extract_sentences(all_text, keywords, max_sentences=20)

    # Build summary from top sentences.
    summary = " ".join(relevant_sentences[:5]) if relevant_sentences else f"Content related to {topic_name}."

    # Extract capitalized multi-word phrases as potential concepts.
    concept_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')
    concepts_found: set[str] = set()
    for doc in documents:
        for match in concept_pattern.finditer(doc.content):
            phrase = match.group(0)
            if any(kw in phrase.lower() for kw in keywords):
                concepts_found.add(phrase)
    # Also extract key terms from relevant sentences.
    for s in relevant_sentences:
        for match in concept_pattern.finditer(s):
            concepts_found.add(match.group(0))

    key_concepts = sorted(concepts_found)[:8]
    if not key_concepts:
        key_concepts = [f"{topic_name} fundamentals", f"{topic_name} in practice"]

    # Trading implications: sentences with action-oriented words.
    action_words = ["should", "must", "important", "critical", "strategy", "profit", "loss", "risk"]
    implications = _extract_sentences(all_text, action_words, max_sentences=5)
    if not implications:
        implications = [f"Understanding {topic_name} is essential for informed trading decisions."]

    # Risk factors: sentences mentioning risk.
    risk_sentences = _extract_sentences(all_text, ["risk", "danger", "loss", "caution", "warning"], max_sentences=5)
    if not risk_sentences:
        risk_sentences = [f"Insufficient knowledge of {topic_name} can lead to poor trading outcomes."]

    return StructuredKnowledge(
        summary=summary[:500],
        key_concepts=key_concepts,
        trading_implications=implications[:5],
        risk_factors=risk_sentences[:3],
        curriculum_relevance={},
        source_documents=[doc.title for doc in documents],
    )


def _local_assess_mastery(
    topic_name: str,
    topic_description: str,
    mastery_criteria: str,
    learned_content: str,
) -> tuple[float, str, list[str]]:
    """Estimate mastery without an LLM call.

    Scores based on keyword coverage from the topic description and mastery criteria.
    """
    content_lower = learned_content.lower()
    content_words = set(re.findall(r'[a-z]+', content_lower))

    # Keywords from description + criteria.
    stop_words = {"the", "a", "an", "and", "or", "for", "to", "in", "of", "is", "are",
                  "how", "what", "can", "using", "whether"}
    desc_words = set(re.findall(r'[a-z]+', (topic_description + " " + mastery_criteria).lower()))
    desc_keywords = desc_words - stop_words
    desc_keywords = {w for w in desc_keywords if len(w) > 2}

    if not desc_keywords:
        return 0.3, "Insufficient criteria keywords to assess.", [f"Deepen {topic_name} knowledge"]

    covered = desc_keywords & content_words
    coverage = len(covered) / len(desc_keywords)

    # Content volume bonus: more content = more likely to have covered the topic.
    word_count = len(content_words)
    volume_bonus = min(0.15, word_count / 5000 * 0.15)

    score = min(1.0, coverage * 0.85 + volume_bonus)

    missing = desc_keywords - covered
    gaps = [f"Need more detail on: {', '.join(sorted(missing)[:5])}"] if missing else []

    reasoning = (
        f"Keyword coverage: {len(covered)}/{len(desc_keywords)} topic keywords found "
        f"({coverage:.0%}). Content volume: {word_count} unique words."
    )

    return round(score, 3), reasoning, gaps


def _search_relevant_chunks(
    memory: MarkdownMemory,
    topic_name: str,
    topic_description: str,
    n_results: int = 8,
) -> list[dict]:
    """Search the discovered knowledge base for chunks relevant to a topic."""
    # Search with both topic name and description for better recall.
    results_by_name = memory.search(
        query=topic_name,
        subdirectory="discovered",
        n_results=n_results,
    )
    results_by_desc = memory.search(
        query=topic_description,
        subdirectory="discovered",
        n_results=n_results,
    )

    # De-duplicate by path, keeping the higher score.
    seen: dict[str, dict] = {}
    for r in results_by_name + results_by_desc:
        path = r["path"]
        if path not in seen or r["score"] > seen[path]["score"]:
            seen[path] = r

    # Sort by score descending, return top n_results.
    ranked = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
    return ranked[:n_results]


def simulate_topic_learning(
    topic,
    memory: MarkdownMemory,
    synthesizer: KnowledgeSynthesizer,
    tracker: CurriculumTracker,
    *,
    skip_wiki: bool = False,
    skip_web: bool = False,
    dry_run: bool = False,
    controller: LearningController | None = None,
) -> dict:
    """Run the full learning pipeline for a single curriculum topic.

    Returns a summary dict with results.
    """
    logger.info("=" * 70)
    logger.info("LEARNING TOPIC: %s (stage %d)", topic.name, topic.stage_number)
    logger.info("  Description: %s", topic.description)
    logger.info("  Mastery criteria: %s", topic.mastery_criteria)
    logger.info("=" * 70)

    # ------------------------------------------------------------------
    # Multi-round controller path (replaces fixed Steps 1/2/2b)
    # ------------------------------------------------------------------
    if controller is not None and not dry_run:
        logger.info("[Controller] Running multi-round learning for '%s'...", topic.name)
        knowledge, state = controller.learn_topic(topic)

        # Log confidence trajectory
        logger.info("  Confidence trajectory:")
        for entry in state.round_log:
            tools_str = ", ".join(entry["tools"])
            logger.info(
                "    Round %d | tools: %-35s | docs: %2d | confidence: %.2f | gaps: %d",
                entry["round"] + 1, tools_str, entry["docs_retrieved"],
                entry["confidence"], len(entry.get("gaps", [])),
            )
        if state.gaps:
            logger.info("  Unresolved gaps: %s", state.gaps[:3])
        if state.conflicts:
            logger.info("  Conflicts detected: %d", len(state.conflicts))
        logger.info("  Total evidence: %d docs | source diversity: %d tool(s)",
                    len(state.evidence_pool), state.source_diversity())

        documents = state.evidence_pool[:15]
        # Skip to Step 3 (synthesis already done in controller)
        # Format synthesized markdown for storage
        synthesized_md = f"### Summary\n\n{knowledge.summary}\n\n"
        if knowledge.key_concepts:
            synthesized_md += "### Key Concepts\n\n"
            for concept in knowledge.key_concepts:
                synthesized_md += f"- {concept}\n"
            synthesized_md += "\n"
        if knowledge.trading_implications:
            synthesized_md += "### Trading Implications\n\n"
            for impl in knowledge.trading_implications:
                synthesized_md += f"- {impl}\n"
            synthesized_md += "\n"
        if knowledge.risk_factors:
            synthesized_md += "### Risk Factors\n\n"
            for risk in knowledge.risk_factors:
                synthesized_md += f"- {risk}\n"
        if getattr(knowledge, "claims", None):
            synthesized_md += "\n### Evidence Trail\n\n"
            for claim in knowledge.claims[:10]:
                conf = claim.get("confidence", "?")
                src = claim.get("source_title", "unknown")
                synthesized_md += f"- [{conf}] {claim.get('claim','')} *(source: {src})*\n"

        if not documents:
            return {"topic": topic.id, "status": "no_content", "mastery": 0.0}

        ref_doc = documents[0]
        path = memory.store_curriculum_knowledge(
            topic_id=topic.id,
            stage_number=topic.stage_number,
            doc=ref_doc,
            synthesized_content=synthesized_md,
        )
        logger.info("[Step 4] Stored at: %s", path)

        logger.info("[Step 5] Assessing mastery...")
        learned_content = memory.get_topic_content(topic.id, topic.stage_number)
        score, reasoning, gaps = synthesizer.assess_mastery(
            topic_id=topic.id,
            topic_name=topic.name,
            topic_description=topic.description,
            mastery_criteria=topic.mastery_criteria,
            learned_content=learned_content[:3000],
        )
        tracker.set_mastery(topic.id, score, notes=reasoning)
        logger.info("  Mastery score: %.2f", score)
        if gaps:
            for gap in gaps:
                logger.info("    - %s", gap)

        bar = "#" * int(score * 20) + "." * (20 - int(score * 20))
        print(f"    Mastery: [{bar}] {score:.0%}")

        return {
            "topic": topic.id,
            "topic_name": topic.name,
            "status": "completed",
            "documents_used": len(documents),
            "mastery_score": score,
            "reasoning": reasoning,
            "gaps": gaps,
            "key_concepts": knowledge.key_concepts[:5],
            "rounds_used": state.round_idx,
            "source_diversity": state.source_diversity(),
        }

    # ------------------------------------------------------------------
    # Step 1: Search knowledge base for relevant book chunks (legacy path)
    # ------------------------------------------------------------------
    logger.info("[Step 1] Searching knowledge base for relevant content...")
    chunks = _search_relevant_chunks(memory, topic.name, topic.description)
    logger.info("  Found %d relevant chunks", len(chunks))

    for i, chunk in enumerate(chunks[:5], 1):
        path_short = Path(chunk["path"]).stem[:60]
        logger.info("    #%d [score=%.2f] %s", i, chunk["score"], path_short)

    # Convert search results to Document objects for the synthesizer.
    documents: list[Document] = []
    for chunk in chunks[:5]:  # Use top 5 chunks to stay within token limits.
        doc = Document(
            title=Path(chunk["path"]).stem.replace("_", " ").title(),
            content=chunk["content"],
            source=chunk["path"],
            topic_tags=[topic.id],
        )
        documents.append(doc)

    # ------------------------------------------------------------------
    # Step 2: Fetch Wikipedia summary (supplementary)
    # ------------------------------------------------------------------
    if not skip_wiki:
        logger.info("[Step 2] Fetching Wikipedia summary for '%s'...", topic.name)
        wiki_docs = fetch_wikipedia(topic.name)
        if wiki_docs:
            logger.info("  Got Wikipedia article: %s (%d chars)",
                        wiki_docs[0].title, len(wiki_docs[0].content))
            documents.extend(wiki_docs)
        else:
            logger.info("  No Wikipedia article found.")
    else:
        logger.info("[Step 2] Skipping Wikipedia (--skip-wiki).")

    # ------------------------------------------------------------------
    # Step 2b: Web search (supplementary)
    # ------------------------------------------------------------------
    if not skip_web:
        logger.info("[Step 2b] Web searching for '%s'...", topic.name)
        web_docs = fetch_web_search(topic.name, max_results=5, fetch_top_articles=2)
        if web_docs:
            snippet_count = len([d for d in web_docs if "full_article" not in d.topic_tags])
            article_count = len(web_docs) - snippet_count
            logger.info("  Got %d snippet(s) + %d full article(s) from web search.",
                        snippet_count, article_count)
            documents.extend(web_docs)
        else:
            logger.info("  No web search results found.")
    else:
        logger.info("[Step 2b] Skipping web search (--skip-web).")

    if not documents:
        logger.warning("  No documents found for topic '%s'; skipping.", topic.name)
        return {"topic": topic.id, "status": "no_content", "mastery": 0.0}

    logger.info("  Total documents for synthesis: %d", len(documents))

    if dry_run:
        logger.info("[DRY RUN] Would synthesize %d documents and assess mastery.", len(documents))
        return {"topic": topic.id, "status": "dry_run", "documents": len(documents)}

    # ------------------------------------------------------------------
    # Step 3: Synthesize knowledge
    # ------------------------------------------------------------------
    use_llm = _has_llm_key()
    mode = "LLM (Moonshot)" if use_llm else "local extraction (no MOONSHOT_API_KEY)"
    logger.info("[Step 3] Synthesizing knowledge via %s...", mode)

    if use_llm:
        knowledge = synthesizer.synthesize(documents)
    else:
        knowledge = _local_synthesize(documents, topic.name, topic.description)

    logger.info("  Summary: %s", textwrap.shorten(knowledge.summary, width=120))
    logger.info("  Key concepts (%d): %s", len(knowledge.key_concepts), knowledge.key_concepts[:5])
    logger.info("  Trading implications (%d): %s",
                len(knowledge.trading_implications), knowledge.trading_implications[:2])
    logger.info("  Risk factors (%d): %s", len(knowledge.risk_factors), knowledge.risk_factors[:2])

    # ------------------------------------------------------------------
    # Step 4: Store synthesized knowledge in curriculum file
    # ------------------------------------------------------------------
    logger.info("[Step 4] Storing synthesized knowledge...")

    # Build a readable markdown summary from the structured knowledge.
    synthesized_md = f"### Summary\n\n{knowledge.summary}\n\n"
    if knowledge.key_concepts:
        synthesized_md += "### Key Concepts\n\n"
        for concept in knowledge.key_concepts:
            synthesized_md += f"- {concept}\n"
        synthesized_md += "\n"
    if knowledge.trading_implications:
        synthesized_md += "### Trading Implications\n\n"
        for impl in knowledge.trading_implications:
            synthesized_md += f"- {impl}\n"
        synthesized_md += "\n"
    if knowledge.risk_factors:
        synthesized_md += "### Risk Factors\n\n"
        for risk in knowledge.risk_factors:
            synthesized_md += f"- {risk}\n"

    # Use the first document as the source reference.
    ref_doc = documents[0]
    path = memory.store_curriculum_knowledge(
        topic_id=topic.id,
        stage_number=topic.stage_number,
        doc=ref_doc,
        synthesized_content=synthesized_md,
    )
    logger.info("  Stored at: %s", path)

    # ------------------------------------------------------------------
    # Step 5: Assess mastery
    # ------------------------------------------------------------------
    logger.info("[Step 5] Assessing mastery via %s...", mode)

    # Read back the full topic content for assessment.
    learned_content = memory.get_topic_content(topic.id, topic.stage_number)

    if use_llm:
        score, reasoning, gaps = synthesizer.assess_mastery(
            topic_id=topic.id,
            topic_name=topic.name,
            topic_description=topic.description,
            mastery_criteria=topic.mastery_criteria,
            learned_content=learned_content[:3000],
        )
    else:
        score, reasoning, gaps = _local_assess_mastery(
            topic_name=topic.name,
            topic_description=topic.description,
            mastery_criteria=topic.mastery_criteria,
            learned_content=learned_content[:5000],
        )

    # Store the mastery assessment.
    tracker.set_mastery(topic.id, score, notes=reasoning)

    logger.info("  Mastery score: %.2f", score)
    logger.info("  Reasoning: %s", textwrap.shorten(reasoning, width=120))
    if gaps:
        logger.info("  Knowledge gaps:")
        for gap in gaps:
            logger.info("    - %s", gap)

    return {
        "topic": topic.id,
        "topic_name": topic.name,
        "status": "completed",
        "documents_used": len(documents),
        "mastery_score": score,
        "reasoning": reasoning,
        "gaps": gaps,
        "key_concepts": knowledge.key_concepts[:5],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate nightly learning for curriculum topics.")
    parser.add_argument("--topics", type=int, default=3,
                        help="Number of topics to learn (default: 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Search and find content but skip LLM calls.")
    parser.add_argument("--skip-wiki", action="store_true",
                        help="Skip Wikipedia fetches (use only book knowledge).")
    parser.add_argument("--skip-web", action="store_true",
                        help="Skip web search (use only books + Wikipedia).")
    parser.add_argument("--no-controller", action="store_true",
                        help="Use legacy fixed pipeline (Steps 1/2/2b) instead of multi-round controller.")
    args = parser.parse_args()

    tracker = CurriculumTracker(
        curriculum_path=str(_PROJECT_ROOT / "config" / "curriculum.yaml"),
        memory_root=str(_PROJECT_ROOT / "knowledge" / "memory" / "trading"),
    )
    memory = MarkdownMemory(
        memory_root=str(_PROJECT_ROOT / "knowledge" / "memory" / "trading"),
    )
    synthesizer = KnowledgeSynthesizer()

    # Get the next topics to learn.
    current_stage = tracker.get_current_stage()
    logger.info("Current stage: %d", current_stage)
    logger.info("Stage progress: %s", tracker.get_stage_progress(current_stage))

    topics = tracker.get_next_learning_tasks(max_tasks=args.topics)
    if not topics:
        logger.info("All topics in stage %d are mastered! Nothing to learn.", current_stage)
        return

    logger.info("Topics to learn: %s\n", [t.name for t in topics])

    # Build controller (multi-round mode) unless --no-controller
    controller: LearningController | None = None
    if not args.no_controller and not args.dry_run:
        controller = LearningController(memory, synthesizer, tracker)
        logger.info("Using multi-round LearningController (max_rounds=%d, threshold=%.2f)",
                    controller.max_rounds, controller.confidence_threshold)
    else:
        logger.info("Using legacy fixed pipeline%s.",
                    " [DRY RUN]" if args.dry_run else " [--no-controller]")

    # Run learning for each topic.
    results: list[dict] = []
    for topic in topics:
        result = simulate_topic_learning(
            topic, memory, synthesizer, tracker,
            skip_wiki=args.skip_wiki,
            skip_web=args.skip_web,
            dry_run=args.dry_run,
            controller=controller,
        )
        results.append(result)
        print()

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("LEARNING SESSION SUMMARY")
    print("=" * 70)
    for r in results:
        status = r.get("status", "?")
        if status == "completed":
            score = r["mastery_score"]
            bar = "#" * int(score * 20) + "." * (20 - int(score * 20))
            print(f"\n  {r['topic_name']}")
            print(f"    Mastery: [{bar}] {score:.0%}")
            print(f"    Sources: {r['documents_used']} documents")
            if r.get("rounds_used") is not None:
                print(f"    Rounds:  {r['rounds_used']} | Source diversity: {r.get('source_diversity', '?')} tool(s)")
            if r.get("gaps"):
                print(f"    Gaps: {', '.join(r['gaps'][:3])}")
            if r.get("key_concepts"):
                print(f"    Learned: {', '.join(r['key_concepts'][:3])}")
        elif status == "dry_run":
            print(f"\n  {r['topic']} — [DRY RUN] {r['documents']} documents found")
        else:
            print(f"\n  {r['topic']} — {status}")

    # Show updated stage progress.
    print(f"\nUpdated stage {current_stage} progress:")
    for tid, score in tracker.get_stage_progress(current_stage).items():
        bar = "#" * int(score * 20) + "." * (20 - int(score * 20))
        print(f"  {tid:25s} [{bar}] {score:.0%}")
    print()


if __name__ == "__main__":
    main()
