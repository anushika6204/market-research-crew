import pandas as pd
import pytest
from pypdf import PdfReader

from crew.analysis import compute_summary_statistics, load_metrics
from crew.report_generator import (
    ReportMetadata,
    build_pdf_report,
    build_styles,
    generate_report,
    inline_markup,
    markdown_to_flowables,
)
from reportlab.platypus import ListFlowable, Table

SAMPLE_MD = """# Title

## Summary
Text with **bold**, *italic*, `code`, R&D <tags> & a [link](https://example.com).

- one
- two

1. first
2. second

| Col A | Col B |
|---|---|
| 1 | 2 |
"""


@pytest.fixture
def summary(mock_csv):
    return compute_summary_statistics(load_metrics(mock_csv))


def test_pdf_is_written_and_valid(tmp_path, summary):
    out = build_pdf_report(SAMPLE_MD, summary, tmp_path / "r.pdf", ReportMetadata(title="T", query="Q"))
    data = out.read_bytes()
    assert data.startswith(b"%PDF") and b"%%EOF" in data[-1024:]
    assert len(PdfReader(out).pages) >= 1


def test_pdf_has_banner_stats_table_and_page_numbers(tmp_path, summary):
    out = build_pdf_report(SAMPLE_MD, summary, tmp_path / "r.pdf", ReportMetadata(title="My Banner", query="Q1"))
    text = PdfReader(out).pages[0].extract_text()
    assert "My Banner" in text and "Query: Q1" in text
    assert "Financial Metrics Summary" in text and "Revenue" in text
    assert "Page 1 of 1" in text


def test_multi_page_numbering(tmp_path, summary):
    long_md = "# Long\n\n" + "\n\n".join(f"## Section {i}\n" + "Lorem ipsum dolor sit amet. " * 60 for i in range(12))
    out = build_pdf_report(long_md, summary, tmp_path / "long.pdf")
    reader = PdfReader(out)
    n = len(reader.pages)
    assert n > 1
    assert f"Page {n} of {n}" in reader.pages[-1].extract_text()


def test_a4_page_size(tmp_path, summary):
    page = PdfReader(build_pdf_report(SAMPLE_MD, summary, tmp_path / "a4.pdf")).pages[0]
    assert round(float(page.mediabox.width)) == 595 and round(float(page.mediabox.height)) == 842


def test_special_characters_do_not_break_styling(tmp_path, summary):
    md = "# A & B <x>\n\nPrice < 5 & growth > 3 ** unmatched * star\n\n| a | b |\n|--|--|\n| <1> | & |"
    assert build_pdf_report(md, summary, tmp_path / "s.pdf").exists()


def test_empty_markdown_rejected(tmp_path, summary):
    with pytest.raises(ValueError):
        build_pdf_report("   ", summary, tmp_path / "x.pdf")


def test_markdown_conversion_types():
    flow = markdown_to_flowables(SAMPLE_MD, build_styles())
    assert sum(isinstance(f, ListFlowable) for f in flow) == 2
    assert sum(isinstance(f, Table) for f in flow) == 1


def test_inline_markup_escapes_and_formats():
    out = inline_markup("R&D **b** <x>")
    assert "R&amp;D" in out and "<b>b</b>" in out and "&lt;x&gt;" in out


def test_generate_report_end_to_end(tmp_path, mock_csv):
    out = generate_report(SAMPLE_MD, mock_csv, tmp_path / "e2e.pdf", query="demo")
    assert "Underlying Dataset" in " ".join(p.extract_text() for p in PdfReader(out).pages)
