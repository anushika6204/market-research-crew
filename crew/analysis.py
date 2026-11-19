"""Pure-Pandas analysis helpers (no CrewAI dependency, so they are easy to test)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SUMMARY_STATS = ["count", "mean", "std", "min", "max"]


def load_metrics(csv_path: str | Path) -> pd.DataFrame:
    """Load a metrics CSV, raising clear errors for missing or empty files."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"CSV file is empty: {path}")
    return df


def compute_summary_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Return count/mean/std/min/max for every numeric column (stats as rows)."""
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        raise ValueError("The dataset contains no numeric columns to summarise.")
    return numeric.agg(SUMMARY_STATS)


def dataframe_to_markdown(df: pd.DataFrame, floatfmt: str = ".2f") -> str:
    """Render a DataFrame as a clean Markdown table."""
    return df.to_markdown(floatfmt=floatfmt)


def verify_numeric_consistency(df: pd.DataFrame) -> list[str]:
    """Run sanity checks and return a list of human-readable issues (empty = clean)."""
    issues: list[str] = []
    numeric = df.select_dtypes(include="number")

    for col in numeric.columns:
        missing = int(numeric[col].isna().sum())
        if missing:
            issues.append(f"Column '{col}' has {missing} missing value(s).")
        if np.isinf(numeric[col]).any():
            issues.append(f"Column '{col}' contains infinite values.")

    dupes = int(df.duplicated().sum())
    if dupes:
        issues.append(f"Dataset contains {dupes} duplicate row(s).")

    if len(numeric) >= 8:  # z-scores are meaningless on tiny samples
        for col in numeric.columns:
            series = numeric[col].dropna()
            std = series.std()
            if std and std > 0:
                outliers = int((((series - series.mean()) / std).abs() > 3).sum())
                if outliers:
                    issues.append(f"Column '{col}' has {outliers} outlier(s) beyond 3 standard deviations.")
    return issues


def build_metrics_report(csv_path: str | Path) -> str:
    """Full Markdown analysis: summary table plus consistency findings."""
    df = load_metrics(csv_path)
    summary = compute_summary_statistics(df)
    issues = verify_numeric_consistency(df)

    parts = [
        f"### Summary Statistics ({len(df)} rows, {len(summary.columns)} numeric metrics)",
        dataframe_to_markdown(summary),
        "",
        "### Numeric Consistency Checks",
    ]
    parts += [f"- {i}" for i in issues] if issues else ["- All checks passed: no missing values, duplicates or outliers."]
    return "\n".join(parts)
