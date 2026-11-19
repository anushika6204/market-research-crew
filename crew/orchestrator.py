"""Hierarchical CrewAI orchestration with a manager LLM, plus benchmarking."""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from crewai import LLM, Crew, Process

from crew.agents import build_analyst, build_researcher, build_writer
from crew.benchmarking import BenchmarkLogger
from crew.config import Settings
from crew.tasks import build_tasks
from crew.tools.csv_writer import build_csv_writer_tool
from crew.tools.financial_parser import calculate_financial_metrics
from crew.tools.web_scraper import web_research

log = logging.getLogger("orchestrator")


@dataclass
class CrewRunResult:
    markdown: str
    metrics_csv: Path
    benchmark: dict


class MarketResearchCrew:
    def __init__(self, settings: Settings):
        self.settings = settings

    def run(self, query: str) -> CrewRunResult:
        s = self.settings
        metrics_csv = s.metrics_csv
        metrics_csv.unlink(missing_ok=True)  # make sure stale data is never analysed

        manager_llm = LLM(model=s.manager_model, temperature=0.1)
        worker_llm = LLM(model=s.agent_model, temperature=0.2)

        benchmark = BenchmarkLogger(s.benchmarks_path, query, manager_model=s.manager_model)

        researcher = build_researcher(worker_llm, [web_research, build_csv_writer_tool(metrics_csv)])
        analyst = build_analyst(worker_llm, [calculate_financial_metrics])
        writer = build_writer(worker_llm)
        tasks = build_tasks(query, metrics_csv, benchmark)

        crew = Crew(
            agents=[researcher, analyst, writer],
            tasks=tasks,
            process=Process.hierarchical,  # manager delegates tasks dynamically
            manager_llm=manager_llm,
            verbose=True,
        )

        log.info("Manager LLM '%s' initialising hierarchical workflow for query: %s", s.manager_model, query)
        benchmark.start()
        try:
            result = crew.kickoff()
        except Exception as exc:
            benchmark.finish(status="failed", error=str(exc))
            raise
        run_record = benchmark.finish()

        if not metrics_csv.exists():
            log.warning("Researcher did not save metrics.csv; falling back to sample dataset %s", s.default_csv)
            shutil.copy(s.default_csv, metrics_csv)

        markdown = getattr(result, "raw", None) or str(result)
        return CrewRunResult(markdown=markdown, metrics_csv=metrics_csv, benchmark=run_record)
