# Multi-Agent Market Research & Report Generator (CrewAI)

- **Repository**: https://github.com/anushika6204/market-research-crew

A hierarchical CrewAI team researches a market topic, analyses the collected metrics with Pandas, writes a report,
and a ReportLab post-processor compiles a styled A4 PDF. Each run is benchmarked to `benchmarks.json`.

## Architecture

```
main.py  ->  MarketResearchCrew (crew/orchestrator.py)
                 Manager LLM (Process.hierarchical, delegates dynamically)
                    |- Market Research Specialist  [Web scraper tool, CSV writer tool]
                    |- Financial Data Analyst      [Financial Metrics Calculator (Pandas)]
                    '- Technical Reports Writer    [no tools]
             -> report Markdown + metrics.csv
             -> crew/report_generator.py (ReportLab) -> market_report.pdf
             -> crew/benchmarking.py -> benchmarks.json
```

```
crew/
  config.py            settings, env loading, output paths
  analysis.py          pure Pandas stats + consistency checks (no CrewAI dependency)
  tools/
    web_scraper.py     @tool: Tavily/SerperDev search + page scraping
    financial_parser.py @tool: CSV -> Pandas -> Markdown summary table
    csv_writer.py      tool factory: researcher saves extracted metrics to CSV
  agents.py            the three agents
  tasks.py             tasks (no fixed agent: the manager assigns them)
  orchestrator.py      Crew(process=Process.hierarchical, manager_llm=...)
  benchmarking.py      per-task timings + routing history
  report_generator.py  Markdown -> styled A4 PDF (banner, tables, Page X of Y)
tests/                 pytest suite
data/                  sample CSV + demo report (illustrative, fictional data)
sample_outputs/        sample market_report.md / market_report.pdf
```

## Installation

1. Python 3.10-3.13 recommended. Create a virtualenv and install dependencies:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Configure secrets:
   ```bash
   cp .env.example .env     # then edit .env
   ```
   | Variable | Purpose |
   |---|---|
   | `OPENAI_API_KEY` | Manager and agent LLMs (default `gpt-4o` / `gpt-4o-mini`) |
   | `TAVILY_API_KEY` / `SERPER_API_KEY` | Search provider (at least one) |
   | `SEARCH_PROVIDER` | `tavily` or `serper`; falls back to whichever key exists |
   | `MANAGER_MODEL`, `AGENT_MODEL` | Override models. For Claude use e.g. `anthropic/claude-3-5-sonnet-latest` and set `ANTHROPIC_API_KEY` |

## Usage

```bash
python main.py --query 'Tech Sector Q3 Analysis'   # full multi-agent run
python main.py --demo                              # no API keys: PDF from bundled sample data
python main.py --query 'EV Market 2025' --output-dir out/ev
```

Outputs in `output/` (or `--output-dir`): `market_report.pdf`, `market_report.md`, `metrics.csv`, `benchmarks.json`.

## Running the tests

```bash
pytest
```

The suite covers the Pandas maths (mean/min/max/std on a mock CSV), PDF validity, banner/table/page numbering,
Markdown conversion, benchmark logging, search-provider normalisation and the CSV writer. Tests that need
`crewai` are skipped automatically if it is not installed. No test calls an LLM or a network API.

## Verifying the three test cases

1. **Hierarchical execution** - run `python main.py --query 'Tech Sector Q3 Analysis'`. The console shows
   `Manager LLM 'gpt-4o' initialising hierarchical workflow`, CrewAI's verbose agent trace, and routing lines such as
   `[Routing] step 1: Manager -> 'Market Research Specialist' | task 'collect_market_data' finished in 41.20s`.
2. **PDF** - `output/market_report.pdf` has a header banner, the writer's styled sections, the Pandas statistics grid
   and `Page X of Y` footers (see `sample_outputs/`).
3. **Tests** - `pytest`.

## benchmarks.json schema

```json
{"runs": [{
  "run_id": "a1b2c3d4", "query": "...", "manager_model": "gpt-4o", "status": "completed",
  "started_at": "...", "finished_at": "...", "total_seconds": 95.4,
  "tasks": [{"order": 1, "task": "collect_market_data", "agent": "Market Research Specialist",
             "duration_seconds": 41.2, "completed_at": "...", "output_chars": 3120}],
  "routing_history": [{"step": 1, "task": "collect_market_data",
                       "delegated_by": "Crew Manager", "assigned_to": "Market Research Specialist"}]
}]}
```

Runs are appended, so the file accumulates history. Task duration is the time since the previous task finished
(tasks execute sequentially in the hierarchical process).

## Design notes

- **Dynamic delegation**: tasks are created without an `agent`; the manager LLM picks the worker for each.
- **Tool import**: `from crewai.tools import tool` (the older `crewai_tools.tool` import in the brief is deprecated).
- **Data hand-off**: the researcher saves rows via *Save Metrics to CSV*; the analyst runs the Pandas tool on that
  file; the PDF statistics table is computed from the same CSV. If the researcher fails to save one, the run falls
  back to `data/sample_metrics.csv` and logs a warning.
- **Tools never crash the crew**: errors are returned as strings so agents can retry.
- **Sample data is fictional** and only used by `--demo` and tests.
- Financial output is generated by LLMs from web data: verify figures before relying on them.
