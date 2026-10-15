"""Exporta os frames rotulados como dataset de treino (uma pasta por atividade)."""
from __future__ import annotations

import csv
import shutil
from collections import Counter
from pathlib import Path

from .catalog import MARKER_TYPES, Catalog
from .models import Event


def _segments(events: list[Event], fps: float) -> list[tuple[int, int, Event]]:
    """[início, fim) em frames de cada atividade, ordenado pelo início."""
    out = []
    for e in events:
        if e.event_type in MARKER_TYPES:
            continue
        start = e.start_frame if e.start_frame is not None else round(e.start_time * fps)
        end = e.end_frame if e.end_frame is not None else round(e.end_time * fps)
        if end > start:
            out.append((start, end, e))
    return sorted(out, key=lambda s: s[0])


def frame_labels(events: list[Event], fps: float, frame_count: int) -> list[dict]:
    """Rótulo de cada frame do vídeo (sem_rotulo onde nenhuma atividade cobre o frame)."""
    labels = [None] * frame_count
    for start, end, e in _segments(events, fps):
        for i in range(max(0, start), min(frame_count, end)):
            labels[i] = e
    return [{"frame": i, "time_seconds": round(i / fps, 4), "activity": e.event_type if e else "sem_rotulo",
             "value_class": e.value_class if e else "", "cycle_id": (e.cycle_id or "") if e else "",
             "event_id": e.event_id if e else ""} for i, e in enumerate(labels)]


def export_frame_dataset(video_path: str | Path, events: list[Event], out_dir: str | Path, step: int = 5,
                         width: int | None = 320, catalog: Catalog | None = None, prefix: str = "") -> dict:
    """Salva 1 a cada `step` frames rotulados em out_dir/images/<atividade>/ e o CSV de rótulos.

    frame_labels.csv traz o rótulo de todos os frames; images.csv só dos frames salvos.
    """
    import cv2

    if step < 1:
        raise ValueError("step deve ser 1 ou mais")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Não foi possível abrir o vídeo: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    (out / "images").mkdir(parents=True)
    segments = _segments(events, fps)
    labels = frame_labels(events, fps, max(frame_count, segments[-1][1] if segments else 0))
    with (out / "frame_labels.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(labels[0].keys()) if labels else ["frame"])
        writer.writeheader()
        writer.writerows(labels)
    counts: Counter = Counter()
    rows = []
    index = 0
    try:
        while True:
            if not cap.grab():
                break
            label = labels[index] if index < len(labels) else None
            if label and label["activity"] != "sem_rotulo" and index % step == 0:
                ok, frame = cap.retrieve()
                if ok:
                    if width and frame.shape[1] > width:
                        frame = cv2.resize(frame, (width, max(1, round(frame.shape[0] * width / frame.shape[1]))), interpolation=cv2.INTER_AREA)
                    folder = out / "images" / label["activity"]
                    folder.mkdir(exist_ok=True)
                    name = f"{prefix}f{index:07d}.jpg"
                    cv2.imwrite(str(folder / name), frame)
                    counts[label["activity"]] += 1
                    rows.append({"file": f"images/{label['activity']}/{name}", **label})
            index += 1
    finally:
        cap.release()
    with (out / "images.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "frame", "time_seconds", "activity", "value_class", "cycle_id", "event_id"])
        writer.writeheader()
        writer.writerows(rows)
    names = {a.code: a.label for a in catalog.activities} if catalog else {}
    return {"fps": fps, "frames_in_video": index, "labeled_frames": sum(1 for r in labels if r["activity"] != "sem_rotulo"),
            "images_saved": sum(counts.values()), "step": step,
            "per_activity": [{"code": k, "label": names.get(k, k), "images": v} for k, v in counts.most_common()]}
