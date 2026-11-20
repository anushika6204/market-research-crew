import math

import pandas as pd
import pytest

from crew.analysis import (
    build_metrics_report,
    compute_summary_statistics,
    dataframe_to_markdown,
    load_metrics,
    verify_numeric_consistency,
)


def test_summary_statistics_are_correct(mock_csv):
    summary = compute_summary_statistics(load_metrics(mock_csv))
    assert summary.loc["count", "revenue"] == 4
    assert summary.loc["mean", "revenue"] == pytest.approx(250.0)
    assert summary.loc["min", "revenue"] == 100
    assert summary.loc["max", "revenue"] == 400
    # sample standard deviation: sqrt(50000 / 3)
    assert summary.loc["std", "revenue"] == pytest.approx(math.sqrt(50000 / 3))
    assert summary.loc["mean", "profit"] == pytest.approx(25.0)


def test_non_numeric_columns_are_ignored(mock_csv):
    summary = compute_summary_statistics(load_metrics(mock_csv))
    assert "company" not in summary.columns


def test_markdown_table_output(mock_csv):
    md = dataframe_to_markdown(compute_summary_statistics(load_metrics(mock_csv)))
    assert md.splitlines()[0].startswith("|")
    assert "| mean" in md and "250.00" in md


def test_report_contains_table_and_clean_checks(mock_csv):
    report = build_metrics_report(mock_csv)
    assert "Summary Statistics" in report and "| max" in report
    assert "All checks passed" in report


def test_consistency_checks_flag_problems():
    df = pd.DataFrame({"x": [1.0, None, 3.0, 3.0], "y": [1, 2, 3, 3]})
    issues = " ".join(verify_numeric_consistency(df))
    assert "missing" in issues and "duplicate" in issues


def test_missing_and_empty_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_metrics(tmp_path / "nope.csv")
    empty = tmp_path / "empty.csv"
    pd.DataFrame(columns=["a"]).to_csv(empty, index=False)
    with pytest.raises(ValueError):
        load_metrics(empty)


def test_crewai_tool_wrapper(mock_csv):
    pytest.importorskip("crewai")
    from crew.tools.financial_parser import calculate_financial_metrics

    out = calculate_financial_metrics.run(csv_path=str(mock_csv))
    assert "250.00" in out
    assert calculate_financial_metrics.run(csv_path="/missing.csv").startswith("ERROR")
