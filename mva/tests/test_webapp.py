from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from mva.webapp.server import create_app

SAMPLE = Path(__file__).parents[1] / "examples" / "sample_events.csv"


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path))


def create(client, **files):
    data = {"name": "Posto 3", "station_id": "ST03", "takt_time_seconds": "42", "standard_cycle_time_seconds": ""}
    r = client.post("/api/analyses", data=data, files=files)
    assert r.status_code == 200, r.text
    return r.json()


def test_full_flow_events_run_feedback(client):
    a = create(client, events=("ev.csv", SAMPLE.read_bytes(), "text/csv"))
    assert a["event_count"] == 48 and a["takt_time_seconds"] == 42 and not a["analyzed"]
    m = client.post(f"/api/analyses/{a['id']}/run").json()
    assert m["statistics"]["n"] == 7
    assert {x["anomaly_type"] for x in m["anomalies"]} >= {"above_takt", "excessive_search", "rework_debug", "incomplete_cycle"}
    fb = client.post(f"/api/analyses/{a['id']}/feedback", json={"target_type": "manual_ct", "target_id": "cycle_001", "value": 41.2, "author": "Everton"})
    assert fb.status_code == 200
    client.post(f"/api/analyses/{a['id']}/feedback", json={"target_type": "anomaly", "target_id": "rework_debug@cycle_006", "verdict": "confirmado"})
    assert len(client.get(f"/api/analyses/{a['id']}/feedback").json()) == 2
    assert "Yamazumi" in client.get(f"/api/analyses/{a['id']}/report").text
    assert client.get("/api/analyses").json()[0]["feedback_count"] == 2


def test_thresholds_change_results(client):
    a = create(client, events=("ev.csv", SAMPLE.read_bytes(), "text/csv"))
    client.patch(f"/api/analyses/{a['id']}", json={"takt_time_seconds": 50, "thresholds": {"search_seconds": 20}})
    m = client.post(f"/api/analyses/{a['id']}/run").json()
    assert m["takt"]["takt_time_seconds"] == 50
    assert "excessive_search" not in {x["anomaly_type"] for x in m["anomalies"]}


def test_events_roundtrip_validation_and_stale_flag(client):
    a = create(client)
    assert client.get(f"/api/analyses/{a['id']}/events").text == ""
    assert client.post(f"/api/analyses/{a['id']}/run").status_code == 400
    bad = "event_id,video_id,station_id,start_time,end_time,duration,event_type,category,value_class,confidence,source,human_verified\nx,v,s,3,2,1,assemble,x,x,1,manual,true\n"
    r = client.put(f"/api/analyses/{a['id']}/events", content=bad)
    assert r.status_code == 422 and "linha 2" in r.json()["detail"]
    assert client.put(f"/api/analyses/{a['id']}/events", content=SAMPLE.read_text(encoding="utf-8")).json()["event_count"] == 48
    client.post(f"/api/analyses/{a['id']}/run")
    assert not client.get(f"/api/analyses/{a['id']}").json()["result_stale"]
    client.put(f"/api/analyses/{a['id']}/events", content=SAMPLE.read_text(encoding="utf-8"))
    assert client.get(f"/api/analyses/{a['id']}").json()["result_stale"]


def test_video_upload_and_range_request(client):
    a = create(client, video=("clip.mp4", b"0123456789" * 100, "video/mp4"))
    assert a["has_video"] and a["video_filename"] == "clip.mp4"
    r = client.get(f"/api/analyses/{a['id']}/video", headers={"Range": "bytes=10-19"})
    assert r.status_code == 206 and r.content == b"0123456789"
    assert client.post("/api/analyses", data={"name": "x"}, files={"video": ("a.txt", b"x", "text/plain")}).status_code == 400
    assert len(client.get("/api/analyses").json()) == 1  # failed upload leaves no half-created analysis


def test_labeler_served_in_server_mode_and_bad_ids(client):
    a = create(client)
    html = client.get(f"/labeler/{a['id']}").text
    assert "window.MVA_SERVER" in html and a["id"] in html
    assert client.get("/labeler/../../etc").status_code == 404
    assert client.get("/api/analyses/nao_existe_123").status_code == 404
    assert "MVA" in client.get("/").text


def test_standard_cycle_time_comparisons(client):
    a = create(client, events=("ev.csv", SAMPLE.read_bytes(), "text/csv"))
    client.patch(f"/api/analyses/{a['id']}", json={"standard_cycle_time_seconds": 40})
    m = client.post(f"/api/analyses/{a['id']}/run").json()
    assert m["takt"]["standard_cycle_time_seconds"] == 40
    slow = {c["cycle_id"]: c["vs_standard"] for c in m["cycles"] if c["vs_standard"]}
    assert slow["cycle_005"]["deviation_seconds"] == 15 and slow["cycle_001"]["deviation_seconds"] == 0
    assert {x["cycle_ids"][0] for x in m["anomalies"] if x["anomaly_type"] == "above_standard_ct"} == {"cycle_005", "cycle_006"}
    assert round(m["summary"]["mean_ct_vs_standard_seconds"], 2) == 3.57
    client.patch(f"/api/analyses/{a['id']}", json={"clear_standard_cycle_time": True})
    m = client.post(f"/api/analyses/{a['id']}/run").json()
    assert m["takt"]["standard_cycle_time_seconds"] is None and "above_standard_ct" not in {x["anomaly_type"] for x in m["anomalies"]}


def test_old_analysis_with_available_time_still_runs(client, tmp_path):
    import json
    a = create(client, events=("ev.csv", SAMPLE.read_bytes(), "text/csv"))
    cfg = tmp_path / "analyses" / a["id"] / "analysis.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    data.pop("takt_time_seconds"); data.update(available_time_seconds=25200, customer_demand_units=500)
    cfg.write_text(json.dumps(data), encoding="utf-8")
    assert client.post(f"/api/analyses/{a['id']}/run").json()["takt"]["takt_time_seconds"] == 50.4
