import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from mva.webapp.server import _free_port, create_app


def test_settings_and_stations(tmp_path):
    c = TestClient(create_app(tmp_path))
    s = c.get("/api/settings").json()
    assert s["default_takt_seconds"] == 42 and s["dataset_step"] == 5
    s.update(author="Everton", default_takt_seconds=38.5)
    assert c.put("/api/settings", json=s).status_code == 200
    assert c.get("/api/settings").json()["author"] == "Everton"
    assert c.get("/api/stations").json() == {"stations": []}
    st = {"stations": [{"station_id": "P03", "name": "Montagem tampa", "takt_time_seconds": 42, "standard_cycle_time_seconds": 39}]}
    assert c.put("/api/stations", json=st).status_code == 200
    assert c.get("/api/stations").json()["stations"][0]["name"] == "Montagem tampa"
    assert c.put("/api/stations", json={"stations": st["stations"] * 2}).status_code == 422
    assert c.get("/api/info").json()["version"]
    assert c.get("/").headers["cache-control"] == "no-store"


def test_demo_seeded_once_with_results(tmp_path):
    c = TestClient(create_app(tmp_path, seed_demo=True))
    items = c.get("/api/analyses").json()
    assert len(items) == 1 and items[0]["demo"] and items[0]["analyzed"]
    m = c.get(f"/api/analyses/{items[0]['id']}/results").json()
    assert m["statistics"]["n"] == 8
    kinds = {a["anomaly_type"] for a in m["anomalies"]}
    assert {"excessive_search", "excessive_waiting", "rework_debug"} <= kinds
    assert set(m["yamazumi_average"]) == {"VA", "NNVA", "NVA"}
    pytest.importorskip("cv2")
    c.app.state.demo_video_thread.join(timeout=120)
    assert c.get(f"/api/analyses/{items[0]['id']}").json()["has_video"]
    c.delete(f"/api/analyses/{items[0]['id']}")
    c2 = TestClient(create_app(tmp_path, seed_demo=True))  # deleted demo is not recreated
    assert c2.get("/api/analyses").json() == []
    assert c2.post("/api/demo").json()["analyzed"]
    # O vídeo da demonstração é gravado numa thread; esperar evita abortar o OpenCV na saída do Python.
    c2.app.state.demo_video_thread.join(timeout=120)


def test_free_port_skips_busy_port():
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); s.listen()
        busy = s.getsockname()[1]
        assert _free_port("127.0.0.1", busy) != busy
