from pathlib import Path
import subprocess
import sys
import pytest
from mva.models import Event, TaktInput
from mva.io import load_events
from mva.cycles import segment_cycles
from mva.metrics import cycle_time_statistics
from mva.yamazumi import yamazumi
from mva.anomalies import detect_anomalies

ROOT = Path(__file__).parents[1]
SAMPLE = ROOT / "examples" / "sample_events.csv"


def event(eid, start, end, kind="assemble", cycle=None):
    return Event(event_id=eid, video_id="v", cycle_id=cycle, station_id="s", start_time=start, end_time=end, duration=end-start, event_type=kind, category="x", value_class="VA", confidence=.9, source="manual", human_verified=False)


def test_event_validates_duration_and_order():
    event("a", 1, 2)
    with pytest.raises(ValueError):
        Event(event_id="b", video_id="v", station_id="s", start_time=2, end_time=1, duration=1, event_type="assemble", category="x", value_class="VA", confidence=.9, source="manual", human_verified=False)
    with pytest.raises(ValueError):
        Event(event_id="c", video_id="v", station_id="s", start_time=1, end_time=2, duration=2, event_type="assemble", category="x", value_class="VA", confidence=.9, source="manual", human_verified=False)


def test_segment_complete_and_incomplete_cycles():
    source = [event("s1",0,0,"cycle_start"), event("a",0,4), event("e1",4,4,"cycle_end"), event("s2",5,5,"cycle_start"), event("b",5,9)]
    cycles, assigned = segment_cycles(source)
    assert [(c.complete, c.duration) for c in cycles] == [(True,4), (False,None)]
    assert assigned[1].cycle_id == cycles[0].cycle_id


def test_statistics_by_hand_and_takt():
    cycles, _ = segment_cycles([event("s1",0,0,"cycle_start"),event("e1",10,10,"cycle_end"),event("s2",10,10,"cycle_start"),event("e2",30,30,"cycle_end")])
    m = cycle_time_statistics(cycles)
    assert m.n == 2 and m.mean == 15 and m.median == 15 and m.min == 10 and m.max == 20
    assert m.std == 5 and m.p90 == 19 and m.p95 == 19.5
    assert TaktInput(available_time_seconds=25200, customer_demand_units=600).takt_time_seconds == 42


def test_yamazumi_reconciles_and_reports_gap_overlap():
    cycles, events = segment_cycles([event("s",0,0,"cycle_start"),event("a",0,5),event("b",5,10,"fasten"),event("e",10,10,"cycle_end")])
    row = yamazumi(cycles, events)[cycles[0].cycle_id]
    assert row["event_duration_sum"] == 10
    assert row["gap_seconds"] == 0 and row["overlap_seconds"] == 0


def test_each_rule_anomaly_and_mad():
    ev = [event("s1",0,0,"cycle_start"),event("x1",0,41),event("e1",41,41,"cycle_end"),
          event("s2",41,41,"cycle_start"),event("search",41,49,"search"),event("wait",49,56,"wait"),event("rw",56,57,"rework"),event("e2",57,57,"cycle_end"),
          event("s3",57,57,"cycle_start"),event("n3",57,58),event("e3",58,58,"cycle_end"),
          event("s4",58,58,"cycle_start"),event("n4",58,59)]
    cycles, ev = segment_cycles(ev)
    flags = detect_anomalies(cycles, ev, takt_time=40, search_threshold=5, waiting_threshold=5, mad_threshold=1)
    types = {f.anomaly_type for f in flags}
    assert {"above_takt", "excessive_search", "excessive_waiting", "rework_debug", "incomplete_cycle", "mad_outlier"} <= types
    assert all(f.cycle_ids for f in flags)


def test_cli_end_to_end(tmp_path):
    report = tmp_path / "relatorio.md"
    subprocess.run([sys.executable, "-m", "mva.cli", "analyze", "--events", str(SAMPLE), "--available-time", "25200", "--demand", "600", "--out", str(report)], cwd=ROOT, check=True)
    assert report.exists() and "Yamazumi" in report.read_text(encoding="utf-8")
    assert (tmp_path / "metrics.json").exists()


def test_csv_validation_error_has_line_number(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("event_id,video_id,station_id,start_time,end_time,duration,event_type,category,value_class,confidence,source,human_verified\nx,v,s,3,2,1,assemble,x,x,.9,manual,false\n", encoding="utf-8")
    with pytest.raises(ValueError, match="linha 2"):
        load_events(p)


def test_csv_keeps_literal_na_value(tmp_path):
    p = tmp_path / "na.csv"
    p.write_text("event_id,video_id,station_id,start_time,end_time,duration,event_type,category,value_class,confidence,source,human_verified\nx,v,s,0,0,0,cycle_start,marker,NA,1,manual,true\n", encoding="utf-8")
    assert load_events(p)[0].value_class == "NA"


def test_cycle_end_and_start_at_same_time_ignore_id_order():
    source = [event("z_end",10,10,"cycle_end"), event("a_start",10,10,"cycle_start"), event("s0",0,0,"cycle_start"), event("w",0,10), event("b",10,20), event("y_end",20,20,"cycle_end")]
    cycles, _ = segment_cycles(source)
    assert [(c.complete, c.duration) for c in cycles] == [(True,10), (True,10)]


def test_mad_falls_back_when_most_cycles_equal_median():
    ev, t = [], 0
    for i, ct in enumerate([40, 40, 40, 40, 40, 90]):
        ev += [event(f"s{i}", t, t, "cycle_start"), event(f"w{i}", t, t + ct), event(f"e{i}", t + ct, t + ct, "cycle_end")]
        t += ct
    cycles, ev = segment_cycles(ev)
    flags = [f for f in detect_anomalies(cycles, ev) if f.anomaly_type == "mad_outlier"]
    assert [f.cycle_ids for f in flags] == [[cycles[-1].cycle_id]]


def test_yamazumi_average_ignores_incomplete_cycles():
    from mva.yamazumi import yamazumi_average
    cycles, ev = segment_cycles([event("s1",0,0,"cycle_start"),event("a",0,10),event("e1",10,10,"cycle_end"),event("s2",10,10,"cycle_start"),event("b",10,12)])
    assert yamazumi_average(yamazumi(cycles, ev)) == {"VA": 10}


def test_csv_with_bom_from_labeler(tmp_path):
    p = tmp_path / "bom.csv"
    p.write_bytes("﻿event_id,video_id,station_id,start_time,end_time,duration,event_type,category,value_class,confidence,source,human_verified\r\nx,v,s,0,0,0,cycle_start,marker,NA,1,manual,true\r\n".encode("utf-8"))
    assert load_events(p)[0].event_id == "x"
