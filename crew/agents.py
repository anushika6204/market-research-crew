"""The three specialised agents. The manager is configured on the Crew, not here."""
from __future__ import annotations

from crewai import Agent


def build_researcher(llm, tools: list) -> Agent:
    return Agent(
        role="Market Research Specialist",
        goal="Query search networks, locate financial data and scrape company metrics for the requested market topic.",
        backstory=(
            "You are a veteran equity-research associate who knows where reliable financial figures live. "
            "You always cite the source URL for numbers, never invent data, and record findings as structured rows."
        ),
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


def build_analyst(llm, tools: list) -> Agent:
    return Agent(
        role="Financial Data Analyst",
        goal="Parse data matrices with Pandas, compute averages and statistics, and verify numeric consistency.",
        backstory=(
            "You are a quantitative analyst who trusts only verified numbers. You always run the Financial Metrics "
            "Calculator on the collected CSV, flag anomalies and explain what the statistics mean."
        ),
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


def build_writer(llm) -> Agent:
    return Agent(
        role="Technical Reports Writer",
        goal="Synthesise research and analysis into a clear, well-structured report with accurate copy.",
        backstory=(
            "You are a senior technical writer for an investment-research firm. You write concise, factual "
            "Markdown reports, use only data provided by your colleagues and never fabricate figures."
        ),
        tools=[],
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )
