"""Análise de demonstração: eventos realistas de um posto + vídeo sintético que mostra a atividade.

Serve para validar a interface sem depender de vídeo real. Tudo é determinístico (semente fixa).
"""
from __future__ import annotations

import random
from pathlib import Path

from .catalog import DEFAULT_CATALOG

FPS = 10
HEADER = ("event_id,video_id,cycle_id,station_id,operator_id,product_id,start_time,end_time,duration,event_type,"
          "object,category,value_class,confidence,source,human_verified,model_version,start_frame,end_frame")

# (atividade, duração média em s) de um ciclo padrão de ~40 s; variações entram por ciclo.
STANDARD_SEQUENCE = [("pick_part", 4.0), ("fit", 6.0), ("assemble", 9.0), ("fasten", 8.0), ("move_material", 3.0),
                     ("inspect", 5.0), ("pick_part", 3.0)]
# Desvios por ciclo (índice do ciclo -> (atividade, segundos)) inseridos depois da montagem.
DISTURBANCES = {2: ("search", 7.0), 4: ("wait", 9.0), 5: ("rework", 6.0), 7: ("wait", 3.0)}


def demo_events(cycles: int = 8, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    classes = DEFAULT_CATALOG.value_mapping()
    frame = 0
    rows: list[dict] = []

    def add(kind: str, start: int, end: int) -> None:
        rows.append({"event_id": f"e{len(rows) + 1:04d}", "event_type": kind, "start_frame": start, "end_frame": end,
                     "value_class": "NA" if kind.startswith("cycle_") else classes[kind],
                     "category": "marker" if kind.startswith("cycle_") else "activity"})

    for c in range(cycles):
        add("cycle_start", frame, frame)
        steps = list(STANDARD_SEQUENCE)
        if c in DISTURBANCES:
            steps.insert(3, DISTURBANCES[c])
        for kind, seconds in steps:
            n = max(5, round(seconds * FPS * rng.uniform(0.85, 1.15)))
            add(kind, frame, frame + n)
            frame += n
        add("cycle_end", frame, frame)
        frame += round(FPS * rng.uniform(0.3, 1.0))  # pequena pausa entre ciclos, fora do ciclo
    return rows


def demo_csv(rows: list[dict], video_id: str, station_id: str) -> str:
    lines = [HEADER]
    for r in rows:
        s, e = r["start_frame"] / FPS, r["end_frame"] / FPS
        lines.append(f"{r['event_id']},{video_id},,{station_id},OP-DEMO,PRODUTO-DEMO,{s:.3f},{e:.3f},{e - s:.3f},"
                     f"{r['event_type']},,{r['category']},{r['value_class']},1,manual,true,,{r['start_frame']},{r['end_frame']}")
    return "\n".join(lines) + "\n"


def demo_video(rows: list[dict], out_path: str | Path, size: tuple[int, int] = (640, 360)) -> Path | None:
    """Gera um .webm em que cada frame mostra a atividade rotulada. None se o OpenCV não gravar webm."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    colors = {a.code: a.color for a in DEFAULT_CATALOG.activities}
    labels = {a.code: a.label for a in DEFAULT_CATALOG.activities}
    total = max(r["end_frame"] for r in rows) + FPS
    timeline: list[tuple[str | None, int]] = [(None, 0)] * total
    cycle = 0
    for r in rows:
        if r["event_type"] == "cycle_start":
            cycle += 1
        elif not r["event_type"].startswith("cycle_"):
            for i in range(r["start_frame"], r["end_frame"]):
                timeline[i] = (r["event_type"], cycle)
    w, h = size
    out = Path(out_path)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"VP80"), FPS, (w, h))
    if not writer.isOpened():
        return None
    try:
        for i, (kind, cyc) in enumerate(timeline):
            img = np.full((h, w, 3), 30, np.uint8)
            if kind:
                hexc = colors.get(kind, "#64748b").lstrip("#")
                bgr = (int(hexc[4:6], 16), int(hexc[2:4], 16), int(hexc[0:2], 16))
                cv2.rectangle(img, (0, 0), (w, 70), bgr, -1)
                text = labels.get(kind, kind).encode("ascii", "ignore").decode() or kind
                cv2.putText(img, text, (20, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2, cv2.LINE_AA)
                # "mão" do operador: um círculo que se move dentro da bancada
                x = int(w / 2 + (w / 3) * np.sin(i / 7.0))
                y = int(h * 0.62 + 40 * np.cos(i / 5.0))
                cv2.rectangle(img, (60, int(h * 0.45)), (w - 60, h - 40), (80, 80, 80), 2)
                cv2.circle(img, (x, y), 22, bgr, -1)
                cv2.putText(img, f"Ciclo {cyc}", (20, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1, cv2.LINE_AA)
            else:
                cv2.putText(img, "Entre ciclos", (20, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (160, 160, 160), 2, cv2.LINE_AA)
            cv2.putText(img, f"frame {i}  {i / FPS:6.1f}s", (w - 230, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (220, 220, 220), 1, cv2.LINE_AA)
            writer.write(img)
    finally:
        writer.release()
    return out if out.exists() and out.stat().st_size > 0 else None
