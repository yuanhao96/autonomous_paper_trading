"""Path constants for the stratgen package."""

from pathlib import Path

# src/stratgen/ → src/ → repo root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
FACTORS_DIR = PROJECT_ROOT / "factors"
XS_FACTORS_DIR = FACTORS_DIR / "cross_sectional"

DATA_DIR = PROJECT_ROOT / "data"
UNIVERSE_CACHE_DIR = DATA_DIR / "universe"

RESULTS_FACTORS = PROJECT_ROOT / "results_factors.json"
RESULTS_FACTORS_OPT = PROJECT_ROOT / "results_factors_opt.json"
RESULTS_FACTORS_XS = PROJECT_ROOT / "results_factors_xs.json"
