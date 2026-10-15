"""Servidor local da interface de validação (FastAPI).

Cada análise vive em <data>/analyses/<id>/ com arquivos simples, legíveis e versionáveis:
analysis.json (configuração), video.*, events.csv, metrics.json, relatorio.md e feedback.json.
"""
from __future__ import annotations

import json
import re
import shutil
import threading
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from ..catalog import DEFAULT_CATALOG, ROLES, VALUE_CLASSES, Catalog, load_catalog, save_catalog
from .. import __version__
from ..io import load_events
from ..models import EVENT_TYPES, TaktInput
from ..pipeline import Thresholds, run_analysis

STATIC = Path(__file__).parent / "static"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


class AnalysisSettings(BaseModel):
    name: str = Field(min_length=1)
    station_id: str = "ST01"
    operator_id: str = ""
    product_id: str = ""
    takt_time_seconds: float = Field(default=42, gt=0)
    standard_cycle_time_seconds: float | None = Field(default=None, gt=0)
    video_fps: float | None = Field(default=None, gt=0)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    notes: str = ""


class SettingsPatch(BaseModel):
    name: str | None = None
    station_id: str | None = None
    operator_id: str | None = None
    product_id: str | None = None
    takt_time_seconds: float | None = Field(default=None, gt=0)
    standard_cycle_time_seconds: float | None = Field(default=None, gt=0)
    clear_standard_cycle_time: bool = False
    video_fps: float | None = Field(default=None, gt=0)
    thresholds: Thresholds | None = None
    notes: str | None = None


class AppSettings(BaseModel):
    """Preferências da tela Configurações (data/settings.json)."""
    author: str = ""
    default_station_id: str = "ST01"
    default_takt_seconds: float = Field(default=42, gt=0)
    default_standard_ct_seconds: float | None = Field(default=None, gt=0)
    default_fps: float = Field(default=30, gt=0)
    dataset_step: int = Field(default=5, ge=1)
    dataset_width: int = Field(default=320, ge=0)
    thresholds: Thresholds = Field(default_factory=Thresholds)


class Station(BaseModel):
    station_id: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,30}$")
    name: str = ""
    line: str = ""
    takt_time_seconds: float | None = Field(default=None, gt=0)
    standard_cycle_time_seconds: float | None = Field(default=None, gt=0)
    notes: str = ""


class StationList(BaseModel):
    stations: list[Station] = Field(default_factory=list)


class Feedback(BaseModel):
    target_type: str = Field(pattern="^(anomaly|cycle|event|manual_ct|general)$")
    target_id: str = ""
    verdict: str = Field(default="", pattern="^(|confirmado|rejeitado|corrigir)$")
    value: float | None = None
    comment: str = ""
    author: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _write_json(path: Path, data) -> None:
    # Write-then-rename so a crash never leaves half a JSON file behind.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def takt_input(settings: dict) -> TaktInput:
    # Análises antigas guardavam tempo disponível e demanda em vez do takt.
    if not settings.get("takt_time_seconds") and settings.get("available_time_seconds"):
        settings["takt_time_seconds"] = settings["available_time_seconds"] / settings["customer_demand_units"]
    return TaktInput(takt_time_seconds=settings["takt_time_seconds"],
                     standard_cycle_time_seconds=settings.get("standard_cycle_time_seconds"))


def _video_meta(path: Path) -> dict:
    """fps e nº de frames via OpenCV; vazio se o OpenCV não estiver instalado ou não abrir."""
    try:
        import cv2
    except ImportError:
        return {}
    cap = cv2.VideoCapture(str(path))
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS)) if cap.isOpened() else 0
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if cap.isOpened() else 0
    finally:
        cap.release()
    return {"video_fps": fps, "video_frame_count": count} if fps > 0 else {}


NO_STORE = {"Cache-Control": "no-store"}


def create_app(data_dir: str | Path, seed_demo: bool = False) -> FastAPI:
    catalog_path = Path(data_dir) / "catalog.json"
    settings_path = Path(data_dir) / "settings.json"
    stations_path = Path(data_dir) / "stations.json"
    root = Path(data_dir) / "analyses"
    root.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="MVA — validação local", version=__version__)

    def app_settings() -> AppSettings:
        return AppSettings.model_validate(_read_json(settings_path, {}))

    def folder(analysis_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9_]{6,40}", analysis_id):
            raise HTTPException(404, "Análise não encontrada")
        path = root / analysis_id
        if not (path / "analysis.json").exists():
            raise HTTPException(404, "Análise não encontrada")
        return path

    def video_path(path: Path) -> Path | None:
        return next((p for p in path.glob("video.*") if p.suffix.lower() in VIDEO_EXTENSIONS), None)

    def summary(path: Path) -> dict:
        data = _read_json(path / "analysis.json", {})
        metrics = _read_json(path / "metrics.json", None)
        events_file = path / "events.csv"
        video = video_path(path)
        data.update({
            "has_video": video is not None,
            "video_filename": data.get("video_original_name") if video else None,
            "has_events": events_file.exists(),
            "event_count": max(0, len(events_file.read_text(encoding="utf-8-sig").strip().splitlines()) - 1) if events_file.exists() else 0,
            "takt_time_seconds": takt_input(data).takt_time_seconds,
            "analyzed": metrics is not None,
            "result_stale": metrics is not None and data.get("events_updated_at", "") > data.get("analyzed_at", ""),
            "feedback_count": len(_read_json(path / "feedback.json", [])),
        })
        if metrics:
            data["statistics"] = metrics["statistics"]
            data["anomaly_count"] = len(metrics["anomalies"])
        return data

    def save_video(path: Path, upload: UploadFile, settings: dict) -> None:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in VIDEO_EXTENSIONS:
            raise HTTPException(400, f"Formato de vídeo não aceito: {ext or '(sem extensão)'}")
        for old in path.glob("video.*"):
            old.unlink()
        with (path / f"video{ext}").open("wb") as out:
            shutil.copyfileobj(upload.file, out, 1024 * 1024)
        settings["video_original_name"] = upload.filename
        settings.pop("video_frame_count", None)
        settings.update(_video_meta(path / f"video{ext}"))

    def save_events(path: Path, text: str, settings: dict) -> int:
        target = path / "events.csv"
        tmp = path / "events.tmp.csv"
        tmp.write_text(text, encoding="utf-8")
        try:
            count = len(load_events(tmp))
        except ValueError as exc:
            tmp.unlink()
            raise HTTPException(422, str(exc)) from exc
        tmp.replace(target)
        settings["events_updated_at"] = _now()
        return count

    def new_analysis(settings: dict) -> Path:
        analysis_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
        path = root / analysis_id
        path.mkdir()
        settings.update({"id": analysis_id, "created_at": _now()})
        return path

    def create_demo() -> dict:
        from ..demo import demo_csv, demo_events, demo_video

        settings = AnalysisSettings(name="Demonstração — posto exemplo (vídeo sintético)", station_id="DEMO-01",
                                    operator_id="OP-DEMO", product_id="PRODUTO-DEMO", takt_time_seconds=42,
                                    standard_cycle_time_seconds=40,
                                    notes="Análise de exemplo criada automaticamente para conhecer o programa.").model_dump()
        path = new_analysis(settings)
        rows = demo_events()
        save_events(path, demo_csv(rows, settings["id"], settings["station_id"]), settings)
        settings.update({"demo": True, "video_fps": 10})
        _write_json(path / "analysis.json", settings)
        run(settings["id"])

        def make_video() -> None:
            # Codificar ~5 min de vídeo leva uns 20 s: roda em segundo plano para a tela abrir logo.
            tmp = path / "demo_tmp.webm"
            try:
                if demo_video(rows, tmp, (426, 240)) and path.exists():
                    tmp.replace(path / "video.webm")
                    data = _read_json(path / "analysis.json", {})
                    data.update({"video_original_name": "demo_posto_exemplo.webm",
                                 "video_frame_count": max(r["end_frame"] for r in rows) + 10})
                    _write_json(path / "analysis.json", data)
            except Exception:  # noqa: BLE001 - sem vídeo a demonstração continua útil
                tmp.unlink(missing_ok=True)

        app.state.demo_video_thread = threading.Thread(target=make_video, daemon=True)
        app.state.demo_video_thread.start()
        return summary(path)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse((STATIC / "index.html").read_text(encoding="utf-8"), headers=NO_STORE)

    @app.get("/api/info")
    def info():
        return {"version": __version__, "data_dir": str(Path(data_dir).resolve())}

    @app.get("/api/settings")
    def get_settings():
        return app_settings().model_dump()

    @app.put("/api/settings")
    def put_settings(body: AppSettings):
        _write_json(settings_path, body.model_dump())
        return body.model_dump()

    @app.get("/api/stations")
    def get_stations():
        return StationList.model_validate(_read_json(stations_path, {})).model_dump()

    @app.put("/api/stations")
    def put_stations(body: StationList):
        ids = [s.station_id for s in body.stations]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise HTTPException(422, f"Posto repetido: {', '.join(sorted(dup))}")
        _write_json(stations_path, body.model_dump())
        return body.model_dump()

    @app.post("/api/demo")
    def demo():
        return create_demo()

    @app.get("/labeler/{analysis_id}", response_class=HTMLResponse)
    def labeler(analysis_id: str):
        folder(analysis_id)
        html = (STATIC / "labeler.html").read_text(encoding="utf-8")
        # Server mode: the labeler loads video/events from the API and saves back.
        return HTMLResponse(html.replace("<script>\n(()=>{", f"<script>window.MVA_SERVER={json.dumps({'id': analysis_id})};</script>\n<script>\n(()=>{{", 1), headers=NO_STORE)

    @app.get("/api/vocabulary")
    def vocabulary():
        return {"event_types": list(EVENT_TYPES)}

    @app.get("/api/catalog")
    def get_catalog():
        return {**load_catalog(catalog_path).model_dump(), "value_classes": VALUE_CLASSES, "roles": ROLES}

    @app.put("/api/catalog")
    def put_catalog(catalog: Catalog):
        save_catalog(catalog_path, catalog)
        return get_catalog()

    @app.post("/api/catalog/reset")
    def reset_catalog():
        save_catalog(catalog_path, DEFAULT_CATALOG)
        return get_catalog()

    @app.get("/api/analyses")
    def list_analyses():
        items = [summary(p) for p in root.iterdir() if (p / "analysis.json").exists()]
        return sorted(items, key=lambda a: a.get("created_at", ""), reverse=True)

    @app.post("/api/analyses")
    async def create_analysis(name: str = Form(...), station_id: str = Form("ST01"), operator_id: str = Form(""),
                              product_id: str = Form(""), takt_time_seconds: float = Form(42),
                              standard_cycle_time_seconds: str = Form(""), video: UploadFile | None = File(None),
                              events: UploadFile | None = File(None)):
        settings = AnalysisSettings(name=name, station_id=station_id, operator_id=operator_id, product_id=product_id,
                                    takt_time_seconds=takt_time_seconds,
                                    standard_cycle_time_seconds=float(standard_cycle_time_seconds) if standard_cycle_time_seconds.strip() else None
                                    ).model_dump()
        path = new_analysis(settings)
        try:
            if video is not None and video.filename:
                save_video(path, video, settings)
            if events is not None and events.filename:
                save_events(path, (await events.read()).decode("utf-8-sig"), settings)
        except HTTPException:
            shutil.rmtree(path)
            raise
        _write_json(path / "analysis.json", settings)
        return summary(path)

    @app.get("/api/analyses/{analysis_id}")
    def get_analysis(analysis_id: str):
        return summary(folder(analysis_id))

    @app.patch("/api/analyses/{analysis_id}")
    def update_analysis(analysis_id: str, patch: SettingsPatch):
        path = folder(analysis_id)
        settings = _read_json(path / "analysis.json", {})
        settings.update(patch.model_dump(exclude_none=True, exclude={"clear_standard_cycle_time"}, mode="json"))
        if patch.clear_standard_cycle_time:
            settings["standard_cycle_time_seconds"] = None
        AnalysisSettings.model_validate(settings)
        _write_json(path / "analysis.json", settings)
        return summary(path)

    @app.delete("/api/analyses/{analysis_id}")
    def delete_analysis(analysis_id: str):
        shutil.rmtree(folder(analysis_id))
        return {"deleted": analysis_id}

    @app.put("/api/analyses/{analysis_id}/video")
    def upload_video(analysis_id: str, video: UploadFile = File(...)):
        path = folder(analysis_id)
        settings = _read_json(path / "analysis.json", {})
        save_video(path, video, settings)
        _write_json(path / "analysis.json", settings)
        return summary(path)

    @app.get("/api/analyses/{analysis_id}/video")
    def get_video(analysis_id: str):
        video = video_path(folder(analysis_id))
        if video is None:
            raise HTTPException(404, "Esta análise ainda não tem vídeo")
        return FileResponse(video)  # Starlette answers Range requests, so the player can seek.

    @app.get("/api/analyses/{analysis_id}/events", response_class=PlainTextResponse)
    def get_events(analysis_id: str):
        events = folder(analysis_id) / "events.csv"
        return events.read_text(encoding="utf-8-sig") if events.exists() else ""

    @app.put("/api/analyses/{analysis_id}/events")
    async def put_events(analysis_id: str, request: Request):
        path = folder(analysis_id)
        settings = _read_json(path / "analysis.json", {})
        count = save_events(path, (await request.body()).decode("utf-8-sig"), settings)
        _write_json(path / "analysis.json", settings)
        return {"event_count": count, "saved_at": settings["events_updated_at"]}

    @app.post("/api/analyses/{analysis_id}/run")
    def run(analysis_id: str):
        path = folder(analysis_id)
        if not (path / "events.csv").exists():
            raise HTTPException(400, "Rotule ou importe eventos antes de rodar a análise")
        settings = _read_json(path / "analysis.json", {})
        try:
            events = load_events(path / "events.csv")
            takt = takt_input(settings)
            metrics, report = run_analysis(events, takt, Thresholds.model_validate(settings.get("thresholds", {})),
                                           load_catalog(catalog_path))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        _write_json(path / "metrics.json", metrics)
        (path / "relatorio.md").write_text(report, encoding="utf-8")
        settings["analyzed_at"] = _now()
        _write_json(path / "analysis.json", settings)
        return metrics

    @app.get("/api/analyses/{analysis_id}/results")
    def results(analysis_id: str):
        metrics = _read_json(folder(analysis_id) / "metrics.json", None)
        if metrics is None:
            raise HTTPException(404, "Análise ainda não executada")
        return metrics

    @app.get("/api/analyses/{analysis_id}/report")
    def report(analysis_id: str):
        path = folder(analysis_id) / "relatorio.md"
        if not path.exists():
            raise HTTPException(404, "Análise ainda não executada")
        return FileResponse(path, media_type="text/markdown", filename=f"relatorio_{analysis_id}.md")

    @app.post("/api/analyses/{analysis_id}/dataset")
    def build_dataset(analysis_id: str, step: int = 5, width: int = 320):
        path = folder(analysis_id)
        video = video_path(path)
        if video is None or not (path / "events.csv").exists():
            raise HTTPException(400, "A análise precisa de vídeo e de atividades rotuladas")
        try:
            from ..dataset import export_frame_dataset
        except ImportError as exc:
            raise HTTPException(500, "OpenCV não instalado") from exc
        try:
            result = export_frame_dataset(video, load_events(path / "events.csv"), path / "dataset", step=step,
                                          width=width or None, catalog=load_catalog(catalog_path), prefix=f"{analysis_id}_")
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        result["folder"] = str((path / "dataset").resolve())
        _write_json(path / "dataset" / "summary.json", result)
        return result

    @app.get("/api/analyses/{analysis_id}/dataset")
    def dataset_summary(analysis_id: str):
        summary_file = folder(analysis_id) / "dataset" / "summary.json"
        # 200 vazio em vez de 404: a tela consulta isso sempre que abre a análise.
        return _read_json(summary_file, {})

    @app.get("/api/analyses/{analysis_id}/dataset.zip")
    def dataset_zip(analysis_id: str):
        path = folder(analysis_id)
        if not (path / "dataset" / "summary.json").exists():
            raise HTTPException(404, "Dataset ainda não exportado")
        archive = shutil.make_archive(str(path / "dataset_export"), "zip", path / "dataset")
        return FileResponse(archive, media_type="application/zip", filename=f"dataset_{analysis_id}.zip")

    @app.get("/api/analyses/{analysis_id}/feedback")
    def get_feedback(analysis_id: str):
        return _read_json(folder(analysis_id) / "feedback.json", [])

    @app.post("/api/analyses/{analysis_id}/feedback")
    def add_feedback(analysis_id: str, item: Feedback):
        path = folder(analysis_id)
        items = _read_json(path / "feedback.json", [])
        # Append-only: earlier judgments stay as history (they become training labels later).
        record = {**item.model_dump(), "id": uuid.uuid4().hex[:10], "created_at": _now()}
        items.append(record)
        _write_json(path / "feedback.json", items)
        return record

    if seed_demo and not (Path(data_dir) / ".demo_criada").exists():
        try:
            create_demo()
        finally:
            (Path(data_dir) / ".demo_criada").write_text(_now(), encoding="utf-8")
    return app


def _free_port(host: str, port: int) -> int:
    """A porta pedida ou a próxima livre (uma janela antiga do MVA pode estar segurando a 8765)."""
    import socket

    for candidate in range(port, port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex((host, candidate)) != 0:
                return candidate
    return port


def serve(data_dir: str, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False) -> None:
    import uvicorn

    free = _free_port(host, port)
    if free != port:
        print(f"A porta {port} está ocupada (provavelmente uma janela antiga do MVA ainda aberta). Usando {free}.")
    url = f"http://{host}:{free}/"
    print(f"MVA versão {__version__} em {url}  (dados em {Path(data_dir).resolve()})  — feche esta janela para encerrar")
    app = create_app(data_dir, seed_demo=True)
    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=free, log_level="warning")
