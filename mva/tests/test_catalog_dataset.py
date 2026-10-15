import csv
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from mva.catalog import DEFAULT_CATALOG, Catalog
from mva.webapp.server import create_app

HEAD = "event_id,video_id,cycle_id,station_id,operator_id,product_id,start_time,end_time,duration,event_type,object,category,value_class,confidence,source,human_verified,model_version,start_frame,end_frame\n"


def row(i, start_f, end_f, kind, vc, fps=10):
    s, e = start_f / fps, end_f / fps
    return f"e{i},v,,ST,,,{s},{e},{e - s},{kind},,activity,{vc},1,manual,true,,{start_f},{end_f}\n"


FRAME_EVENTS = HEAD + "".join([
    row(1, 0, 0, "cycle_start", "NA"), row(2, 0, 30, "assemble", "VA"), row(3, 30, 50, "pick_part", "NNVA"),
    row(4, 50, 120, "aguardar_lider", "NVA"), row(5, 120, 120, "cycle_end", "NA"),
])


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path))


def test_catalog_defaults_edit_and_validation(client):
    cat = client.get("/api/catalog").json()
    assert {"Montar", "Encaixar", "Esperar", "Movimentação de material"} <= {a["label"] for a in cat["activities"]}
    assert cat["value_classes"]["NNVA"] == "NVA necessário"
    new = cat["activities"] + [{"code": "aguardar_lider", "label": "Aguardar líder", "value_class": "NVA", "color": "#123456", "key": "l", "role": "wait"}]
    assert client.put("/api/catalog", json={"activities": new}).status_code == 200
    assert client.get("/api/catalog").json()["activities"][-1]["code"] == "aguardar_lider"
    dup_key = new + [{"code": "outra", "label": "Outra", "value_class": "VA", "key": "l"}]
    assert client.put("/api/catalog", json={"activities": dup_key}).status_code == 422
    reserved = [{"code": "x1", "label": "X", "value_class": "VA", "key": "s"}]
    assert client.put("/api/catalog", json={"activities": reserved}).status_code == 422
    assert len(client.post("/api/catalog/reset").json()["activities"]) == len(DEFAULT_CATALOG.activities)


def test_custom_activity_drives_yamazumi_and_wait_rule(client):
    cat = client.get("/api/catalog").json()["activities"]
    cat.append({"code": "aguardar_lider", "label": "Aguardar líder", "value_class": "NVA", "color": "#123456", "key": "l", "role": "wait"})
    client.put("/api/catalog", json={"activities": cat})
    a = client.post("/api/analyses", data={"name": "frames", "takt_time_seconds": "15"}, files={"events": ("e.csv", FRAME_EVENTS.encode(), "text/csv")}).json()
    m = client.post(f"/api/analyses/{a['id']}/run").json()
    assert m["yamazumi_average"] == pytest.approx({"VA": 3.0, "NNVA": 2.0, "NVA": 7.0})
    assert "excessive_waiting" in {x["anomaly_type"] for x in m["anomalies"]}
    acts = {x["code"]: x for x in m["activities"]}
    assert acts["aguardar_lider"]["label"] == "Aguardar líder" and acts["aguardar_lider"]["mean_per_cycle_seconds"] == pytest.approx(7.0)
    assert m["events"][1]["start_frame"] == 0 and m["events"][1]["end_frame"] == 30


def test_frame_dataset_export(client, tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    video = tmp_path / "v.avi"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    for i in range(130):
        writer.write(np.full((48, 64, 3), i, dtype=np.uint8))
    writer.release()
    a = client.post("/api/analyses", data={"name": "ds", "takt_time_seconds": "15"},
                    files={"events": ("e.csv", FRAME_EVENTS.encode(), "text/csv"), "video": ("v.avi", video.read_bytes(), "video/x-msvideo")}).json()
    assert a["video_fps"] == 10 and a["video_frame_count"] == 130
    r = client.post(f"/api/analyses/{a['id']}/dataset?step=10&width=32")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["labeled_frames"] == 120 and d["images_saved"] == 12
    assert {x["code"]: x["images"] for x in d["per_activity"]} == {"assemble": 3, "pick_part": 2, "aguardar_lider": 7}
    folder = Path(d["folder"])
    labels = list(csv.DictReader((folder / "frame_labels.csv").open(encoding="utf-8")))
    assert labels[29]["activity"] == "assemble" and labels[30]["activity"] == "pick_part" and labels[125]["activity"] == "sem_rotulo"
    assert len(list((folder / "images" / "assemble").glob("*.jpg"))) == 3
    assert client.get(f"/api/analyses/{a['id']}/dataset.zip").headers["content-type"] == "application/zip"


def test_catalog_model_rejects_marker_codes():
    with pytest.raises(ValueError):
        Catalog(activities=[{"code": "cycle_start", "label": "x", "value_class": "VA"}])
