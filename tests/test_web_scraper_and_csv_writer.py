import json

import pandas as pd
import pytest

pytest.importorskip("crewai")  # these modules import the @tool decorator

from crew.tools import csv_writer, web_scraper  # noqa: E402


class FakeResponse:
    def __init__(self, payload=None, text=""):
        self._payload, self.text = payload, text

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_provider_resolution(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("SERPER_API_KEY", "k")
    assert web_scraper.resolve_provider("tavily") == "serper"  # falls back
    monkeypatch.delenv("SERPER_API_KEY")
    with pytest.raises(RuntimeError):
        web_scraper.resolve_provider()


def test_tavily_and_serper_normalisation(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "t")
    monkeypatch.setenv("SERPER_API_KEY", "s")
    monkeypatch.setattr(web_scraper.requests, "post", lambda *a, **k: FakeResponse(
        {"results": [{"title": "T", "url": "http://x", "content": "c"}]}))
    assert web_scraper.search_web("q", provider="tavily") == [{"title": "T", "url": "http://x", "snippet": "c"}]
    monkeypatch.setattr(web_scraper.requests, "post", lambda *a, **k: FakeResponse(
        {"organic": [{"title": "S", "link": "http://y", "snippet": "sn"}]}))
    assert web_scraper.search_web("q", provider="serper")[0]["url"] == "http://y"


def test_extract_text_strips_scripts():
    html = "<html><script>evil()</script><nav>menu</nav><body><p>Revenue  rose\n 10%</p></body></html>"
    assert web_scraper.extract_text(html) == "Revenue rose 10%"


def test_search_and_scrape_digest(monkeypatch):
    monkeypatch.setattr(web_scraper, "search_web", lambda q, max_results=3: [
        {"title": "T", "url": "http://x", "snippet": "snip"}])
    monkeypatch.setattr(web_scraper, "scrape_url", lambda u, n=2500: "page body")
    digest = web_scraper.search_and_scrape("q")
    assert "URL: http://x" in digest and "page body" in digest


def test_csv_writer_roundtrip(tmp_path):
    rows = csv_writer.parse_rows('```json\n[{"company": "A", "revenue": "10.5"}, {"company": "B", "revenue": 20}]\n```')
    path = csv_writer.write_metrics_csv(rows, tmp_path / "m.csv")
    df = pd.read_csv(path)
    assert df["revenue"].tolist() == [10.5, 20.0]


def test_csv_writer_tool_reports_errors(tmp_path):
    tool = csv_writer.build_csv_writer_tool(tmp_path / "m.csv")
    assert tool.run(rows_json="not json").startswith("ERROR")
    ok = tool.run(rows_json=json.dumps([{"company": "A", "revenue": 1}]))
    assert ok.startswith("Saved") and (tmp_path / "m.csv").exists()
