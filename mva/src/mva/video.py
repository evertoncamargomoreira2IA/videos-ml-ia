"""Ferramentas de ingestão de vídeo para revisão de processos."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import cv2
from pydantic import BaseModel, ConfigDict, Field


class VideoInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    size_bytes: int = Field(ge=0)
    container: str
    extension: str
    fps: float = Field(gt=0)
    frame_count: int = Field(gt=0)
    duration_seconds: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    codec: str


class FrameRef(BaseModel):
    timestamp_seconds: float = Field(ge=0)
    path: str


def probe_video(path: str | Path) -> VideoInfo:
    source = Path(path)
    ext = source.suffix.lower()
    if ext not in {".mp4", ".mov", ".avi", ".mkv"}:
        raise ValueError(f"Extensão de vídeo não aceita: {ext or '(sem extensão)'}. Use .mp4, .mov, .avi ou .mkv.")
    if not source.is_file():
        raise ValueError(f"Arquivo de vídeo não encontrado: {source}")

    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        cap.release()
        raise ValueError(f"Não foi possível abrir o vídeo: {source}")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc_num = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc_cv = "".join(chr((fourcc_num >> (8 * i)) & 0xFF) for i in range(4)).strip("\x00 ")
    cv_duration = count / fps if fps > 0 and count > 0 else 0.0
    cap.release()
    if fps <= 0:
        raise ValueError("FPS do vídeo deve ser maior que zero.")
    if count <= 0:
        raise ValueError("O vídeo não contém quadros válidos (frame_count deve ser maior que zero).")

    duration, codec = cv_duration, fourcc_cv or "desconhecido"
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            result = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "format=duration:stream=codec_name", "-of", "json", str(source)], capture_output=True, text=True, check=True, timeout=30)
            data = json.loads(result.stdout)
            probed_duration = float(data.get("format", {}).get("duration", 0))
            streams = data.get("streams", [])
            probed_codec = streams[0].get("codec_name") if streams else None
            if probed_duration > 0:
                duration = probed_duration
            if probed_codec:
                codec = probed_codec
        except (subprocess.SubprocessError, ValueError, KeyError, json.JSONDecodeError):
            pass
    try:
        return VideoInfo(path=str(source.resolve()), size_bytes=source.stat().st_size, container=ext.lstrip("."), extension=ext, fps=fps, frame_count=count, duration_seconds=duration, width=width, height=height, codec=codec)
    except Exception as exc:
        raise ValueError(f"Metadados de vídeo inválidos: {exc}") from exc


def video_id_for(path: str | Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ValueError(f"Não foi possível ler o arquivo de vídeo: {exc}") from exc
    return "vid_" + digest.hexdigest()[:12]


def extract_frames(path: str | Path, out_dir: str | Path, every_seconds: float = 1.0, max_frames: int | None = None, width: int | None = None) -> list[FrameRef]:
    if every_seconds <= 0:
        raise ValueError("every_seconds deve ser maior que zero.")
    if max_frames is not None and max_frames <= 0:
        raise ValueError("max_frames deve ser maior que zero.")
    if width is not None and width <= 0:
        raise ValueError("width deve ser maior que zero.")
    info = probe_video(path)
    frames_dir = Path(out_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(path))
    refs: list[FrameRef] = []
    target = 0.0
    index = 0
    try:
        while max_frames is None or len(refs) < max_frames:
            # grab() skips decoding; only frames we keep are retrieved.
            if not cap.grab():
                break
            # Container timestamps stay correct for variable-frame-rate phone videos.
            pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            timestamp = pos_ms / 1000 if pos_ms > 0 or index == 0 else index / info.fps
            if timestamp + 1e-9 >= target:
                ok, frame = cap.retrieve()
                if not ok:
                    break
                stamp_ms = round(timestamp * 1000)
                if width is not None and frame.shape[1] != width:
                    height = max(1, round(frame.shape[0] * width / frame.shape[1]))
                    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                dest = frames_dir / f"frame_{stamp_ms:09d}.jpg"
                if not cv2.imwrite(str(dest), frame):
                    raise ValueError(f"Não foi possível salvar o quadro: {dest}")
                refs.append(FrameRef(timestamp_seconds=timestamp, path=str(dest.resolve())))
                target += every_seconds
            index += 1
    finally:
        cap.release()
    if not refs:
        raise ValueError(f"Nenhum quadro pôde ser extraído de: {path}")
    return refs


def contact_sheet(frames: list[FrameRef], out_path: str | Path, cols: int = 6) -> Path:
    if cols <= 0:
        raise ValueError("cols deve ser maior que zero.")
    if not frames:
        raise ValueError("A lista de quadros está vazia.")
    thumb_w, thumb_h, label_h = 240, 180, 28
    tiles = []
    for ref in frames:
        image = cv2.imread(ref.path)
        if image is None:
            raise ValueError(f"Não foi possível abrir o quadro: {ref.path}")
        thumb = cv2.resize(image, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
        tile = cv2.copyMakeBorder(thumb, 0, label_h, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(tile, f"{ref.timestamp_seconds:.3f}s", (8, thumb_h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
        tiles.append(tile)
    rows = (len(tiles) + cols - 1) // cols
    import numpy as np
    sheet = np.full((rows * (thumb_h + label_h), cols * thumb_w, 3), 255, dtype=np.uint8)
    for i, tile in enumerate(tiles):
        y, x = divmod(i, cols)
        sheet[y * (thumb_h + label_h):(y + 1) * (thumb_h + label_h), x * thumb_w:(x + 1) * thumb_w] = tile
    dest = Path(out_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(dest), sheet):
        raise ValueError(f"Não foi possível salvar a contact sheet: {dest}")
    return dest


def write_manifest(video_info: VideoInfo, frames: list[FrameRef], out_dir: str | Path) -> Path:
    dest = Path(out_dir) / "manifest.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"video_id": video_id_for(video_info.path), "video": video_info.model_dump(), "frames": [f.model_dump() for f in frames]}
    dest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest
