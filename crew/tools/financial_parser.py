"""Financial Data Parser tool: CSV -> Pandas -> Markdown summary table."""
from crewai.tools import tool

from crew.analysis import build_metrics_report


@tool("Financial Metrics Calculator")
def calculate_financial_metrics(csv_path: str) -> str:
    """Load corporate metrics from a CSV file with Pandas and return summary statistics
    (count, mean, std, min, max) as a Markdown table, plus numeric consistency checks.
    Input: csv_path - the filesystem path of the CSV file."""
    try:
        return build_metrics_report(csv_path)
    except Exception as exc:  # returned to the agent so it can recover instead of crashing the crew
        return f"ERROR: could not analyse '{csv_path}': {exc}"
