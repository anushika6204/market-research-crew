"""CLI entry point.

Usage:
    python main.py --query 'Tech Sector Q3 Analysis'      # full multi-agent run (needs API keys)
    python main.py --demo                                  # no LLM/search: renders the PDF from sample data
"""
from __future__ import annotations

import argparse
import logging
import sys

from crew.config import get_settings
from crew.report_generator import generate_report

log = logging.getLogger("main")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Multi-agent market research & PDF report generator (CrewAI)")
    p.add_argument("--query", default="Tech Sector Q3 Analysis", help="Research topic")
    p.add_argument("--output-dir", default=None, help="Directory for market_report.pdf/.md and benchmarks.json")
    p.add_argument("--demo", action="store_true", help="Skip the crew and compile a PDF from bundled sample data")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)-12s | %(message)s", datefmt="%H:%M:%S")
    settings = get_settings(args.output_dir)

    if args.demo:
        from crew.config import PROJECT_ROOT

        log.info("DEMO mode: using bundled sample data (no LLM or search calls).")
        markdown = (PROJECT_ROOT / "data" / "sample_report.md").read_text(encoding="utf-8")
        csv_path = settings.default_csv
    else:
        missing = settings.missing_keys()
        if missing:
            log.error("Missing configuration in .env: %s (see .env.example)", ", ".join(missing))
            return 2
        from crew.orchestrator import MarketResearchCrew  # imported lazily so --demo and tests do not need crewai

        result = MarketResearchCrew(settings).run(args.query)
        markdown, csv_path = result.markdown, result.metrics_csv

    settings.report_md.write_text(markdown, encoding="utf-8")
    pdf_path = generate_report(markdown, csv_path, settings.report_pdf, query=args.query)
    log.info("Markdown report: %s", settings.report_md)
    log.info("PDF report:      %s", pdf_path)
    if not args.demo:
        log.info("Benchmarks:      %s", settings.benchmarks_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
