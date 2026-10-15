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


def run_analysis(events: list[Event], takt: TaktInput, thresholds: Thresholds | None = None) -> tuple[dict, str]:
    """Devolve (metrics, relatório Markdown) a partir de eventos já validados."""
    thresholds = thresholds or Thresholds()
    cycles, events = segment_cycles(events)
    stats = cycle_time_statistics(cycles)
    anomalies = detect_anomalies(cycles, events, takt.takt_time_seconds, search_threshold=thresholds.search_seconds,
                                 waiting_threshold=thresholds.waiting_seconds, mad_threshold=thresholds.mad_z)
    ymz = yamazumi(cycles, events)
    metrics = {
        "takt": {"available_time_seconds": takt.available_time_seconds, "customer_demand_units": takt.customer_demand_units,
                 "takt_time_seconds": takt.takt_time_seconds},
        "thresholds": thresholds.model_dump(),
        "statistics": stats.model_dump(),
        "cycles": [{**c.model_dump(),
                    "comparison": classify_cycle_time(c.duration, takt.takt_time_seconds, thresholds.near_fraction, thresholds.severe_ratio)
                    if c.complete and c.duration is not None else None} for c in cycles],
        "events": [e.model_dump() for e in events],
        "yamazumi": ymz,
        "yamazumi_average": yamazumi_average(ymz),
        "anomalies": [a.model_dump() for a in anomalies],
    }
    return metrics, render_report(cycles, events, stats, takt, anomalies)
