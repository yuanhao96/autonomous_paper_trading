"""Path constants for the stratgen package."""

from pathlib import Path

# src/stratgen/ → src/ → repo root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
STRATEGIES_DIR = KNOWLEDGE_DIR / "strategies"

RESULTS_DISCOVER = PROJECT_ROOT / "results_v4.json"
RESULTS_OPTIMIZE = PROJECT_ROOT / "results_v5.json"
RUNS_TRADE = PROJECT_ROOT / "runs_v6.json"


def resolve_knowledge_doc(ref: str) -> Path:
    """Resolve a knowledge doc path (absolute or relative to KNOWLEDGE_DIR)."""
    path = Path(ref)
    if path.exists():
        return path
    candidate = KNOWLEDGE_DIR / ref
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Knowledge doc not found: {ref}")
