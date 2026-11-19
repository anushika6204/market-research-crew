"""Tool that lets the researcher persist extracted metrics as a CSV for the analyst."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from crewai.tools import tool


def parse_rows(rows_json: str) -> list[dict]:
    """Parse a JSON list of records (tolerates markdown code fences and {"rows": [...]})."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", rows_json.strip(), flags=re.MULTILINE).strip()
    data = json.loads(cleaned)
    if isinstance(data, dict):
        data = data.get("rows", data.get("data"))
    if not isinstance(data, list) or not data or not all(isinstance(r, dict) for r in data):
        raise ValueError("Expected a non-empty JSON list of objects, e.g. [{\"company\": \"X\", \"revenue_billion\": 1.2}]")
    return data


def write_metrics_csv(rows: list[dict], path: str | Path) -> Path:
    """Write records to CSV with Pandas, coercing numeric-looking columns."""
    df = pd.DataFrame(rows)
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() == df[col].notna().sum():
            df[col] = converted
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def build_csv_writer_tool(csv_path: str | Path):
    """Factory: returns a tool bound to a specific output path."""
    target = Path(csv_path)

    @tool("Save Metrics to CSV")
    def save_metrics_csv(rows_json: str) -> str:
        """Save collected company metrics to a CSV file for the data analyst.
        Input: rows_json - a JSON list of objects, one per company, with a name column and
        numeric metric columns, e.g. [{"company": "Acme", "revenue_billion": 12.5, "yoy_growth_pct": 8.1}].
        Use the same keys in every object. Returns the CSV path."""
        try:
            path = write_metrics_csv(parse_rows(rows_json), target)
            return f"Saved {len(parse_rows(rows_json))} rows to {path}"
        except Exception as exc:
            return f"ERROR: could not save metrics: {exc}"

    return save_metrics_csv
