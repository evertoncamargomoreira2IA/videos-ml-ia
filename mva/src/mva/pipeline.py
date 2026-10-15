"""Análise completa reutilizada pela CLI e pela interface web."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .anomalies import detect_anomalies
from .cycles import segment_cycles
from .metrics import classify_cycle_time, cycle_time_statistics
from .models import Event, TaktInput
from .report import render_report
from .yamazumi import yamazumi, yamazumi_average


class Thresholds(BaseModel):
    search_seconds: float = Field(default=5.0, ge=0)
    waiting_seconds: float = Field(default=5.0, ge=0)
    mad_z: float = Field(default=3.5, gt=0)
    near_fraction: float = Field(default=0.05, ge=0)
    severe_ratio: float = Field(default=1.20, gt=1)


def _vs_standard(ct: float, standard: float | None) -> dict | None:
    if not standard:
        return None
    return {"standard_cycle_time": standard, "deviation_seconds": ct - standard, "ratio": ct / standard}


def _summary(mean_ct: float | None, takt: TaktInput) -> dict:
    """Comparações do CT médio com o takt e com o CT padrão."""
    if mean_ct is None:
        return {}
    out = {"mean_ct_vs_takt_seconds": mean_ct - takt.takt_time_seconds, "takt_utilization": mean_ct / takt.takt_time_seconds}
    if takt.standard_cycle_time_seconds:
        std = takt.standard_cycle_time_seconds
        out.update({"mean_ct_vs_standard_seconds": mean_ct - std, "mean_ct_vs_standard_ratio": mean_ct / std,
                    "standard_vs_takt_seconds": std - takt.takt_time_seconds})
    return out


def run_analysis(events: list[Event], takt: TaktInput, thresholds: Thresholds | None = None) -> tuple[dict, str]:
    """Devolve (metrics, relatório Markdown) a partir de eventos já validados."""
    thresholds = thresholds or Thresholds()
    cycles, events = segment_cycles(events)
    stats = cycle_time_statistics(cycles)
    anomalies = detect_anomalies(cycles, events, takt.takt_time_seconds, search_threshold=thresholds.search_seconds,
                                 waiting_threshold=thresholds.waiting_seconds, mad_threshold=thresholds.mad_z,
                                 standard_ct=takt.standard_cycle_time_seconds, standard_tolerance=thresholds.near_fraction)
    ymz = yamazumi(cycles, events)
    metrics = {
        "takt": takt.model_dump(),
        "thresholds": thresholds.model_dump(),
        "statistics": stats.model_dump(),
        "cycles": [{**c.model_dump(),
                    "comparison": classify_cycle_time(c.duration, takt.takt_time_seconds, thresholds.near_fraction, thresholds.severe_ratio)
                    if c.complete and c.duration is not None else None,
                    "vs_standard": _vs_standard(c.duration, takt.standard_cycle_time_seconds) if c.complete and c.duration is not None else None}
                   for c in cycles],
        "summary": _summary(stats.mean, takt),
        "events": [e.model_dump() for e in events],
        "yamazumi": ymz,
        "yamazumi_average": yamazumi_average(ymz),
        "anomalies": [a.model_dump() for a in anomalies],
    }
    return metrics, render_report(cycles, events, stats, takt, anomalies)
