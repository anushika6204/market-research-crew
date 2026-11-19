"""Task definitions. Tasks have no fixed agent: the hierarchical manager assigns them dynamically."""
from __future__ import annotations

from pathlib import Path

from crewai import Task

from crew.benchmarking import BenchmarkLogger


def build_tasks(query: str, csv_path: str | Path, benchmark: BenchmarkLogger) -> list[Task]:
    research = Task(
        description=(
            f"Research the topic: '{query}'.\n"
            "1. Use the Web Market Research Scraper with several focused queries to find financial metrics "
            "(revenue, net income, margins, R&D spend, growth) for 5-8 relevant companies.\n"
            "2. Record every company as one row with identical keys, e.g. company, revenue_billion, "
            "net_income_billion, operating_margin_pct, rd_spend_billion, yoy_growth_pct (use numbers only, no units in values).\n"
            f"3. Save the rows with the Save Metrics to CSV tool (it writes to {csv_path}).\n"
            "4. Summarise key market context and list the source URLs used."
        ),
        expected_output=(
            "A research brief with market context, the table of collected metrics, confirmation that the CSV "
            "was saved, and a list of source URLs."
        ),
        callback=benchmark.task_callback("collect_market_data"),
    )

    analysis = Task(
        description=(
            f"Analyse the metrics CSV at '{csv_path}'. Run the Financial Metrics Calculator on that exact path, "
            "review the summary statistics (mean, min, max, standard deviation) and the consistency checks, "
            "and interpret what they say about '" + query + "'."
        ),
        expected_output=(
            "The Markdown statistics table exactly as produced by the tool, the consistency-check results, and "
            "3-5 numbered analytical insights grounded in those statistics."
        ),
        context=[research],
        callback=benchmark.task_callback("analyze_metrics"),
    )

    writing = Task(
        description=(
            f"Write the final market research report for '{query}' using ONLY the research brief and the analysis "
            "provided as context. Do not invent numbers. Output clean Markdown with exactly these sections: "
            "'# <Report Title>', '## Executive Summary', '## Market Overview', '## Key Findings' (bullet list), "
            "'## Financial Analysis' (refer to the statistics table that is appended automatically to the PDF; "
            "do not reproduce the full table), '## Risks and Outlook', '## Sources' (URLs)."
        ),
        expected_output="A complete, well-structured Markdown report with the seven sections listed in the description.",
        context=[research, analysis],
        callback=benchmark.task_callback("write_report"),
    )
    return [research, analysis, writing]
