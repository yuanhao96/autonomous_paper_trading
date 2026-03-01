#!/usr/bin/env python3
"""Split bundled WorldQuant alpha docs into individual factor files."""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALPHA_DIR = PROJECT_ROOT / "knowledge" / "strategies" / "alpha-factors"
FACTORS_DIR = PROJECT_ROOT / "factors"

# Source file -> target category directory
SOURCE_MAP = {
    "momentum-price-alphas.md": "momentum",
    "mean-reversion-rsi-alphas.md": "mean_reversion",
    "volume-price-alphas.md": "volume_price",
    "volatility-alphas.md": "volatility",
    "trend-directional-alphas.md": "trend",
    "price-channel-alphas.md": "price_channel",
    "composite-alphas.md": "composite",
}

# Category display names
CATEGORY_NAMES = {
    "momentum": "momentum",
    "mean_reversion": "mean_reversion",
    "volume_price": "volume_price",
    "volatility": "volatility",
    "trend": "trend",
    "price_channel": "price_channel",
    "composite": "composite",
}


def parse_alphas_from_doc(text: str, source_file: str) -> list[dict]:
    """Parse individual alpha entries from a bundled alpha doc."""
    alphas = []

    # Split on ### Alpha#NNN headers
    # Handle both formats: "### Alpha#NNN" and variations
    sections = re.split(r"### Alpha#(\d+)", text)

    # sections[0] is the preamble, then pairs of (number, content)
    for i in range(1, len(sections), 2):
        alpha_num = sections[i].strip()
        content = sections[i + 1] if i + 1 < len(sections) else ""

        alpha = parse_alpha_section(alpha_num, content, source_file)
        if alpha:
            alphas.append(alpha)

    return alphas


def parse_alpha_section(alpha_num: str, content: str, source_file: str) -> dict | None:
    """Parse a single alpha section into a structured dict."""
    # Extract formula - handle multiple formats:
    # 1. "- **Formula**: `formula`"
    # 2. "**Formula**: `formula`"
    # 3. "**Formula**:\n```\nformula\n```"
    # 4. Code block after header

    formula = None

    # Try inline format first: **Formula**: `...`
    m = re.search(r"\*\*Formula\*\*:?\s*`([^`]+)`", content)
    if m:
        formula = m.group(1).strip()
    else:
        # Try code block format: **Formula**:\n```\nformula\n```
        m = re.search(r"\*\*Formula\*\*:?\s*\n```[^\n]*\n(.*?)```", content, re.DOTALL)
        if m:
            formula = m.group(1).strip()
        else:
            # Try bare code block
            m = re.search(r"```\n(.*?)```", content, re.DOTALL)
            if m:
                formula = m.group(1).strip()

    if not formula:
        print(f"  WARNING: No formula found for Alpha#{alpha_num} in {source_file}")
        return None

    # Extract interpretation
    interpretation = ""
    # Try: **Interpretation**: text (greedy up to next ** field or ---)
    m = re.search(r"\*\*Interpretation\*\*:?\s*(.+?)(?=\n\*\*|\n---|\Z)", content, re.DOTALL)
    if m:
        interpretation = m.group(1).strip()
        # Clean up leading dashes/bullets
        interpretation = re.sub(r"^[-*]\s*", "", interpretation)
        # Remove trailing lines that look like params or notes
        interpretation = interpretation.split("\n- **Params")[0].strip()
        interpretation = interpretation.split("\n**Params")[0].strip()
        interpretation = interpretation.split("\n**Note")[0].strip()

    # Extract params
    params = {}
    m = re.search(r"\*\*Params\*\*:?\s*`(\{[^`]*\})`", content)
    if m:
        try:
            import ast
            params = ast.literal_eval(m.group(1))
        except (ValueError, SyntaxError):
            pass

    return {
        "number": alpha_num,
        "formula": formula,
        "interpretation": interpretation,
        "params": params,
    }


def build_param_table(params: dict) -> str:
    """Build a parameter table with default values and ranges."""
    if not params:
        return "None"

    lines = ["| Param | Default | Range |", "|-------|---------|-------|"]
    for name, default in params.items():
        # Generate reasonable ranges based on the parameter type
        if isinstance(default, int):
            low = max(1, default // 2)
            high = default * 2
            range_str = f"[{low}, {high}]"
        elif isinstance(default, float):
            low = max(0.01, default / 2)
            high = default * 2
            range_str = f"[{low}, {high}]"
        else:
            range_str = f"[{default}]"
        lines.append(f"| {name} | {default} | {range_str} |")
    return "\n".join(lines)


def alpha_name(alpha_num: str, interpretation: str) -> str:
    """Generate a concise name from the alpha number and interpretation."""
    interp = interpretation.strip()
    if not interp:
        return f"Alpha Factor #{alpha_num}"
    # Take first line only (skip numbered sub-items)
    first_line = interp.split("\n")[0].strip()
    # Take first sentence
    first_sentence = first_line.split(".")[0].strip()
    # Remove trailing -- or : continuation markers
    first_sentence = re.sub(r"\s*[-:]+\s*$", "", first_sentence)
    if len(first_sentence) > 60:
        first_sentence = first_sentence[:57] + "..."
    return first_sentence or f"Alpha Factor #{alpha_num}"


def write_factor_file(alpha: dict, category: str, source_file: str) -> Path:
    """Write a single factor .md file."""
    num = alpha["number"]
    formula = alpha["formula"]
    interpretation = alpha["interpretation"]
    params = alpha["params"]

    name = alpha_name(num, interpretation)
    param_table = build_param_table(params)

    content = f"""# WQ-{num}: {name}

## Formula
{formula}

## Interpretation
{interpretation}

## Parameters
{param_table}

## Category
{category}

## Source
WorldQuant Alpha#{num} (Kakushadze 2015)
"""

    out_path = FACTORS_DIR / category / f"wq_{num}.md"
    out_path.write_text(content)
    return out_path


def main():
    total = 0
    for source_name, category in SOURCE_MAP.items():
        source_path = ALPHA_DIR / source_name
        if not source_path.exists():
            print(f"WARNING: {source_path} not found, skipping")
            continue

        text = source_path.read_text()
        alphas = parse_alphas_from_doc(text, source_name)
        print(f"{source_name} -> {category}/: {len(alphas)} alphas")

        for alpha in alphas:
            out_path = write_factor_file(alpha, category, source_name)
            total += 1

    print(f"\nTotal: {total} factor files written to {FACTORS_DIR}")


if __name__ == "__main__":
    main()
