"""Central configuration: environment variables, models and output paths."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    manager_model: str
    agent_model: str
    search_provider: str
    output_dir: Path
    default_csv: Path

    # ---- derived paths -------------------------------------------------
    @property
    def metrics_csv(self) -> Path:
        return self.output_dir / "metrics.csv"

    @property
    def benchmarks_path(self) -> Path:
        return self.output_dir / "benchmarks.json"

    @property
    def report_pdf(self) -> Path:
        return self.output_dir / "market_report.pdf"

    @property
    def report_md(self) -> Path:
        return self.output_dir / "market_report.md"

    # ---- validation ----------------------------------------------------
    def missing_keys(self) -> list[str]:
        """Return the names of required API keys that are not configured."""
        missing: list[str] = []
        models = {self.manager_model, self.agent_model}
        if any(not m.startswith("anthropic/") for m in models) and not os.getenv("OPENAI_API_KEY"):
            missing.append("OPENAI_API_KEY")
        if any(m.startswith("anthropic/") for m in models) and not os.getenv("ANTHROPIC_API_KEY"):
            missing.append("ANTHROPIC_API_KEY")
        if not (os.getenv("TAVILY_API_KEY") or os.getenv("SERPER_API_KEY")):
            missing.append("TAVILY_API_KEY or SERPER_API_KEY")
        return missing


def get_settings(output_dir: str | Path | None = None) -> Settings:
    out = Path(output_dir) if output_dir else PROJECT_ROOT / "output"
    out.mkdir(parents=True, exist_ok=True)
    return Settings(
        manager_model=os.getenv("MANAGER_MODEL", "gpt-4o"),
        agent_model=os.getenv("AGENT_MODEL", "gpt-4o-mini"),
        search_provider=os.getenv("SEARCH_PROVIDER", "tavily").lower(),
        output_dir=out,
        default_csv=PROJECT_ROOT / "data" / "sample_metrics.csv",
    )
