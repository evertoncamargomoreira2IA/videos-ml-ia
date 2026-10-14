from pathlib import Path
from mva.cli import analyze

def test_cli_generates_report_and_metrics(tmp_path):
    root=Path(__file__).parents[1]
    report=tmp_path/"report.md"
    analyze(str(root/"examples"/"sample_events.csv"),25200,600,str(report))
    assert report.exists()
    assert "Yamazumi" in report.read_text(encoding="utf-8")
    assert (tmp_path/"metrics.json").exists()
