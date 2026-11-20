import json
from types import SimpleNamespace

from crew.benchmarking import BenchmarkLogger


def test_records_timings_and_routing(tmp_path):
    path = tmp_path / "benchmarks.json"
    bench = BenchmarkLogger(path, "Q", manager_model="gpt-4o")
    bench.start()
    bench.task_callback("collect_market_data")(SimpleNamespace(agent="Market Research Specialist", raw="abc"))
    bench.task_callback("analyze_metrics")(SimpleNamespace(agent="Financial Data Analyst", raw="abcdef"))
    bench.task_callback("write_report")(SimpleNamespace(agent="Technical Reports Writer", raw="x"))
    run = bench.finish()

    saved = json.loads(path.read_text())["runs"][0]
    assert saved["run_id"] == run["run_id"] and saved["status"] == "completed"
    assert [t["task"] for t in saved["tasks"]] == ["collect_market_data", "analyze_metrics", "write_report"]
    assert all(t["duration_seconds"] >= 0 for t in saved["tasks"])
    assert saved["tasks"][1]["output_chars"] == 6
    assert [r["assigned_to"] for r in saved["routing_history"]] == [
        "Market Research Specialist", "Financial Data Analyst", "Technical Reports Writer"]
    assert saved["total_seconds"] >= sum(t["duration_seconds"] for t in saved["tasks"]) - 0.01


def test_runs_are_appended_and_corrupt_file_recovered(tmp_path):
    path = tmp_path / "b.json"
    BenchmarkLogger(path, "one").finish()
    BenchmarkLogger(path, "two").finish(status="failed", error="boom")
    runs = json.loads(path.read_text())["runs"]
    assert [r["query"] for r in runs] == ["one", "two"] and runs[1]["error"] == "boom"

    path.write_text("{not json")
    BenchmarkLogger(path, "three").finish()
    assert len(json.loads(path.read_text())["runs"]) == 1
