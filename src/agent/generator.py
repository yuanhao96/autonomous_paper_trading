"""Strategy generator — LLM-driven StrategySpec creation from knowledge base.

Two modes:
  EXPLORE: Pick a new template from the knowledge base, generate parameters
  EXPLOIT: Take an existing strategy and refine it based on diagnostics

The generator reads strategy documentation from the knowledge base and
produces valid StrategySpec objects with bounded parameters. The LLM never
generates arbitrary code — only structured specs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.agent.reviewer import (
    format_failure_analysis,
    format_history_for_llm,
    format_result_for_llm,
)
from src.core.config import PROJECT_ROOT, Settings
from src.core.llm import LLMClient
from src.screening.translator import get_optimization_bounds
from src.strategies.spec import RiskParams, StrategyResult, StrategySpec

logger = logging.getLogger(__name__)

# Knowledge base root
KB_ROOT = PROJECT_ROOT / "knowledge" / "strategies"

# Templates currently supported by the screening translator
SUPPORTED_TEMPLATES = [
    # ── Momentum (10) ─────────────────────────────────────────
    "momentum/momentum-effect-in-stocks",
    "momentum/time-series-momentum",
    "momentum/time-series-momentum-effect",
    "momentum/dual-momentum",
    "momentum/sector-momentum",
    "momentum/asset-class-momentum",
    "momentum/asset-class-trend-following",
    "momentum/momentum-and-reversal-combined-with-volatility-effect-in-stocks",
    "momentum/residual-momentum",
    "momentum/combining-momentum-effect-with-volume",
    # ── Mean Reversion & Pairs Trading (7) ────────────────────
    "mean-reversion/mean-reversion-rsi",
    "mean-reversion/mean-reversion-bollinger",
    "mean-reversion/pairs-trading",
    "mean-reversion/short-term-reversal",
    "mean-reversion/short-term-reversal-strategy-in-stocks",
    "mean-reversion/mean-reversion-statistical-arbitrage-in-stocks",
    "mean-reversion/pairs-trading-with-stocks",
    # ── Technical (6) ─────────────────────────────────────────
    "technical/moving-average-crossover",
    "technical/breakout",
    "technical/trend-following",
    "technical/ichimoku-clouds-in-energy-sector",
    "technical/dual-thrust-trading-algorithm",
    "technical/paired-switching",
    # ── Factor Investing (5) ──────────────────────────────────
    "factor/fama-french-five-factors",
    "factor/beta-factors-in-stocks",
    "factor/liquidity-effect-in-stocks",
    "factor/accrual-anomaly",
    "factor/earnings-quality-factor",
    # ── Value & Fundamental (5) ───────────────────────────────
    "value/value-factor",
    "value/price-earnings-anomaly",
    "value/book-to-market-value-anomaly",
    "value/small-capitalization-stocks-premium-anomaly",
    "value/g-score-investing",
    # ── Calendar Anomalies (5) ────────────────────────────────
    "calendar/turn-of-the-month-in-equity-indexes",
    "calendar/january-effect-in-stocks",
    "calendar/pre-holiday-effect",
    "calendar/overnight-anomaly",
    "calendar/seasonality-effect-same-calendar-month",
    # ── Volatility (4) ────────────────────────────────────────
    "volatility/volatility-effect-in-stocks",
    "volatility/volatility-risk-premium-effect",
    "volatility/vix-predicts-stock-index-returns",
    "volatility/leveraged-etfs-with-systematic-risk-management",
    # ── Forex (2) ─────────────────────────────────────────────
    "forex/forex-carry-trade",
    "forex/combining-mean-reversion-and-momentum-in-forex",
    # ── Commodities (2) ───────────────────────────────────────
    "commodities/term-structure-effect-in-commodities",
    "commodities/gold-market-timing",
    # ── Category A: Asset-class/universe variations (13) ──────
    "momentum/momentum-effect-in-country-equity-indexes",
    "momentum/momentum-effect-in-reits",
    "momentum/momentum-effect-in-stocks-in-small-portfolios",
    "momentum/momentum-in-mutual-fund-returns",
    "momentum/momentum-effect-in-commodities-futures",
    "commodities/commodities-futures-trend-following",
    "forex/forex-momentum",
    "forex/momentum-strategy-low-frequency-forex",
    "mean-reversion/mean-reversion-effect-in-country-equity-indexes",
    "mean-reversion/pairs-trading-with-country-etfs",
    "mean-reversion/short-term-reversal-with-futures",
    "factor/beta-factor-in-country-equity-indexes",
    "value/value-effect-within-countries",
    # ── Category B: New signal functions (28) ─────────────────
    # Calendar
    "calendar/january-barometer",
    "calendar/12-month-cycle-cross-section",
    "calendar/lunar-cycle-in-equity-market",
    "calendar/option-expiration-week-effect",
    # Momentum variants
    "momentum/momentum-and-state-of-market-filters",
    "momentum/momentum-and-style-rotation-effect",
    "momentum/momentum-short-term-reversal-strategy",
    "commodities/improved-momentum-strategy-on-commodities-futures",
    "commodities/momentum-effect-combined-with-term-structure-in-commodities",
    "momentum/intraday-etf-momentum",
    "momentum/price-and-earnings-momentum",
    "momentum/sentiment-and-style-rotation-effect-in-stocks",
    # Pairs / Mean-Reversion
    "mean-reversion/intraday-dynamic-pairs-trading",
    "mean-reversion/optimal-pairs-trading",
    "mean-reversion/pairs-trading-copula-vs-cointegration",
    "mean-reversion/intraday-arbitrage-between-index-etfs",
    # Cross-Asset / Spread
    "commodities/can-crude-oil-predict-equity-returns",
    "commodities/trading-with-wti-brent-spread",
    # Technical
    "technical/dynamic-breakout-ii-strategy",
    # Factor / Fundamental
    "factor/capm-alpha-ranking-dow-30",
    "factor/expected-idiosyncratic-skewness",
    "factor/asset-growth-effect",
    "factor/roa-effect-within-stocks",
    "factor/standardized-unexpected-earnings",
    "factor/fundamental-factor-long-short-strategy",
    "factor/stock-selection-based-on-fundamental-factors",
    # Volatility
    "volatility/exploiting-term-structure-of-vix-futures",
    # Forex
    "forex/risk-premia-in-forex-markets",
]

# Default universes the generator can pick from
# Must match keys in src/universe/static.py STATIC_UNIVERSES
AVAILABLE_UNIVERSES = [
    "sp500",
    "nasdaq100",
    "sector_etfs",
    "broad_etfs",
    "g10_forex",
    "crypto_top",
]

# System prompt for strategy generation
_SYSTEM_PROMPT = """\
You are a quantitative trading strategy researcher. Your job is to generate \
trading strategy specifications as structured JSON.

CONSTRAINTS:
- You can ONLY use templates from the SUPPORTED_TEMPLATES list provided.
- Parameters must stay within reasonable bounds (documented in the knowledge base).
- Universe must be one of the AVAILABLE_UNIVERSES provided.
- Risk parameters must respect: max_position_pct <= 0.10, max_positions <= 20.
- Position size method must be one of: equal_weight, volatility_target, kelly.
- You must output ONLY valid JSON matching the schema below. No explanation text.

OUTPUT SCHEMA:
{
  "template": "category/template-name",
  "parameters": {"param1": value, ...},
  "universe_id": "universe_name",
  "risk": {
    "max_position_pct": 0.10,
    "max_positions": 5,
    "stop_loss_pct": null,
    "take_profit_pct": null,
    "position_size_method": "equal_weight"
  },
  "reasoning": "Brief explanation of why this strategy and parameters were chosen"
}
"""


class StrategyGenerator:
    """LLM-driven strategy generator.

    Generates StrategySpec objects by:
    1. Reading relevant knowledge base documentation
    2. Considering evolution history and failure patterns
    3. Asking the LLM to propose a strategy with bounded parameters

    The LLM outputs structured JSON, which is parsed and validated
    into a StrategySpec.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._llm = llm_client or LLMClient()
        self._settings = settings or Settings()

    @property
    def session(self):
        return self._llm.session

    def explore(
        self,
        history: list[tuple[StrategySpec, StrategyResult]] | None = None,
        category_hint: str | None = None,
    ) -> StrategySpec:
        """EXPLORE: Generate a new strategy from the knowledge base.

        Reads strategy documentation and asks the LLM to propose a fresh
        strategy specification. Avoids templates already heavily tested.

        Args:
            history: Previous (spec, result) pairs for context.
            category_hint: Optional category to focus on (e.g., "momentum").

        Returns:
            A new StrategySpec with created_by="llm_explore".
        """
        history = history or []

        # Build context from knowledge base
        kb_context = self._build_kb_context(category_hint)

        # Build history context
        history_text = format_history_for_llm(history) if history else ""
        failure_text = format_failure_analysis(
            [(s, r) for s, r in history if not r.passed]
        ) if history else ""

        # Count templates already tried
        tried_templates = {}
        for spec, _ in history:
            t = spec.template
            tried_templates[t] = tried_templates.get(t, 0) + 1

        tried_text = ""
        if tried_templates:
            tried_text = "\nTemplates already tested (try different ones first):\n"
            for t, count in sorted(tried_templates.items(), key=lambda x: -x[1]):
                tried_text += f"  {t}: {count} times\n"

        user_msg = f"""\
Generate a NEW trading strategy specification for exploration.

SUPPORTED TEMPLATES:
{json.dumps(SUPPORTED_TEMPLATES, indent=2)}

AVAILABLE UNIVERSES:
{json.dumps(AVAILABLE_UNIVERSES, indent=2)}

KNOWLEDGE BASE CONTEXT:
{kb_context}

{history_text}

{failure_text}

{tried_text}

Pick a template that has NOT been heavily tested. Choose parameters that are \
different from previous attempts. Output ONLY the JSON spec.
"""

        response = self._llm.chat_with_system(_SYSTEM_PROMPT, user_msg)
        spec = self._parse_response(response, created_by="llm_explore")
        logger.info("EXPLORE generated: %s (params=%s)", spec.template, spec.parameters)
        return spec

    def exploit(
        self,
        parent_spec: StrategySpec,
        screen_result: StrategyResult | None = None,
        validation_result: StrategyResult | None = None,
        history: list[tuple[StrategySpec, StrategyResult]] | None = None,
    ) -> StrategySpec:
        """EXPLOIT: Refine an existing strategy based on diagnostics.

        Takes a parent strategy and its results, asks the LLM to propose
        targeted improvements (parameter tweaks, universe changes, risk tuning).

        Args:
            parent_spec: The strategy to refine.
            screen_result: Screening results (if available).
            validation_result: Validation results (if available).
            history: Previous attempts for context.

        Returns:
            A refined StrategySpec with parent_id set and created_by="llm_exploit".
        """
        history = history or []

        # Format parent's diagnostics
        diagnostics = format_result_for_llm(parent_spec, screen_result, validation_result)

        # Read the parent template's knowledge base doc
        kb_doc = self._read_template_doc(parent_spec.template)

        # Get parameter bounds for the template
        bounds = get_optimization_bounds(parent_spec)
        bounds_text = {k: str(v) for k, v in bounds.items()}

        user_msg = f"""\
Refine this strategy based on its performance diagnostics.

CURRENT STRATEGY:
{diagnostics}

KNOWLEDGE BASE DOCUMENTATION:
{kb_doc[:2000]}

PARAMETER BOUNDS (for reference):
{json.dumps(bounds_text, indent=2)}

SUPPORTED TEMPLATES:
{json.dumps(SUPPORTED_TEMPLATES, indent=2)}

AVAILABLE UNIVERSES:
{json.dumps(AVAILABLE_UNIVERSES, indent=2)}

Rules for exploitation:
1. You may adjust parameters within bounds.
2. You may change the universe.
3. You may add/change risk parameters (stop_loss, position size).
4. You may switch to a closely related template if it addresses the failure.
5. Keep the template the same unless diagnostics clearly point to a template problem.
6. Focus on addressing the specific failure reason.

Output ONLY the JSON spec for the refined strategy.
"""

        response = self._llm.chat_with_system(_SYSTEM_PROMPT, user_msg)
        spec = self._parse_response(response, created_by="llm_exploit")

        # Link to parent
        spec.parent_id = parent_spec.id
        spec.generation = parent_spec.generation + 1

        logger.info(
            "EXPLOIT refined: %s → %s (gen %d, params=%s)",
            parent_spec.template, spec.template, spec.generation, spec.parameters,
        )
        return spec

    def _build_kb_context(self, category_hint: str | None = None) -> str:
        """Build knowledge base context for the LLM prompt.

        Reads the strategy index and a sample of relevant docs.
        """
        # Always include the index
        index_path = KB_ROOT / "README.md"
        if index_path.exists():
            index_text = index_path.read_text()[:3000]
        else:
            index_text = f"Available templates: {json.dumps(SUPPORTED_TEMPLATES)}"

        # If category hint, read a relevant doc
        sample_doc = ""
        if category_hint:
            category_map = {
                "momentum": "momentum/momentum-effect-in-stocks.md",
                "mean-reversion": "mean-reversion-and-pairs-trading/short-term-reversal.md",
                "value": "value-and-fundamental/price-earnings-anomaly.md",
                "technical": "technical-and-other/ichimoku-clouds-in-energy-sector.md",
                "factor": "factor-investing/fama-french-five-factors.md",
                "volatility": "volatility-and-options/volatility-effect-in-stocks.md",
                "calendar": "calendar-anomalies/turn-of-the-month-in-equity-indexes.md",
                "forex": "forex/forex-carry-trade.md",
                "commodities": "commodities/term-structure-effect-in-commodities.md",
            }
            doc_path = category_map.get(category_hint, "")
            if doc_path:
                full_path = KB_ROOT / doc_path
                if full_path.exists():
                    sample_doc = f"\nSample strategy doc:\n{full_path.read_text()[:2000]}"

        return f"{index_text}{sample_doc}"

    def _read_template_doc(self, template: str) -> str:
        """Read the knowledge base doc for a template."""
        # template format: "category/slug" → look for slug.md in any category folder
        slug = template.split("/")[-1] if "/" in template else template

        # Search all category folders
        for category_dir in KB_ROOT.iterdir():
            if not category_dir.is_dir():
                continue
            doc_path = category_dir / f"{slug}.md"
            if doc_path.exists():
                return doc_path.read_text()

        # Try with different slug patterns
        slug_variants = [slug, slug.replace("-", "_"), slug.replace("_", "-")]
        for category_dir in KB_ROOT.iterdir():
            if not category_dir.is_dir():
                continue
            for variant in slug_variants:
                doc_path = category_dir / f"{variant}.md"
                if doc_path.exists():
                    return doc_path.read_text()

        return f"No documentation found for template: {template}"

    def _parse_response(self, response: str, created_by: str) -> StrategySpec:
        """Parse LLM JSON response into a StrategySpec.

        Handles common LLM output issues (markdown code blocks, extra text).
        """
        # Strip markdown code blocks
        text = response.strip()
        if text.startswith("```"):
            # Remove ```json and trailing ```
            lines = text.split("\n")
            text = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )
        text = text.strip()

        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON object found in LLM response: {text[:200]}")

        try:
            data = json.loads(text[start:end])
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in LLM response: {e}\n{text[start:end][:200]}")

        # Validate and build StrategySpec
        template = data.get("template", "")
        if template not in SUPPORTED_TEMPLATES:
            # Try to find closest match
            slug = template.split("/")[-1] if "/" in template else template
            matches = [t for t in SUPPORTED_TEMPLATES if slug in t]
            if matches:
                template = matches[0]
                logger.warning("Corrected template %s → %s", data["template"], template)
            else:
                logger.warning("Unknown template %s, using first supported", template)
                template = SUPPORTED_TEMPLATES[0]

        parameters = data.get("parameters", {})

        universe_id = data.get("universe_id", "sector_etfs")
        if universe_id not in AVAILABLE_UNIVERSES:
            logger.warning("Unknown universe %s, using sector_etfs", universe_id)
            universe_id = "sector_etfs"

        risk_data = data.get("risk", {})
        risk = RiskParams(
            max_position_pct=min(risk_data.get("max_position_pct", 0.10), 0.10),
            max_positions=min(risk_data.get("max_positions", 5), 20),
            stop_loss_pct=risk_data.get("stop_loss_pct"),
            take_profit_pct=risk_data.get("take_profit_pct"),
            trailing_stop_pct=risk_data.get("trailing_stop_pct"),
            position_size_method=risk_data.get("position_size_method", "equal_weight"),
        )

        reasoning = data.get("reasoning", "")
        if reasoning:
            logger.info("LLM reasoning: %s", reasoning[:200])

        return StrategySpec(
            template=template,
            parameters=parameters,
            universe_id=universe_id,
            risk=risk,
            created_by=created_by,
        )
