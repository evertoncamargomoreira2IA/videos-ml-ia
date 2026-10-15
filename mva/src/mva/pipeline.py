"""Análise completa reutilizada pela CLI e pela interface web."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .anomalies import detect_anomalies
from .catalog import VALUE_CLASSES, Catalog
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


def _value_mapping(catalog: Catalog, events: list[Event]) -> dict[str, str]:
    """Código -> VA/NNVA/NVA; códigos fora do catálogo usam o value_class gravado no evento."""
    mapping = catalog.value_mapping()
    for e in events:
        if e.event_type not in mapping:
            mapping[e.event_type] = e.value_class if e.value_class in VALUE_CLASSES else "Outros"
    return mapping


def _activity_summary(cycles, events: list[Event], catalog: Catalog | None) -> list[dict]:
    """Tempo por atividade: total e média por ciclo completo."""
    complete = {c.cycle_id for c in cycles if c.complete}
    labels = {a.code: a for a in catalog.activities} if catalog else {}
    out: dict[str, dict] = {}
    for e in events:
        if e.event_type in {"cycle_start", "cycle_end"}:
            continue
        row = out.setdefault(e.event_type, {"code": e.event_type, "label": labels[e.event_type].label if e.event_type in labels else e.event_type,
                                            "value_class": labels[e.event_type].value_class if e.event_type in labels else e.value_class,
                                            "count": 0, "total_seconds": 0.0, "in_complete_cycles_seconds": 0.0})
        row["count"] += 1
        row["total_seconds"] += e.duration
        if e.cycle_id in complete:
            row["in_complete_cycles_seconds"] += e.duration
    n = len(complete)
    for row in out.values():
        row["mean_per_cycle_seconds"] = row.pop("in_complete_cycles_seconds") / n if n else None
    return sorted(out.values(), key=lambda r: -r["total_seconds"])


def run_analysis(events: list[Event], takt: TaktInput, thresholds: Thresholds | None = None,
                 catalog: Catalog | None = None) -> tuple[dict, str]:
    """Devolve (metrics, relatório Markdown) a partir de eventos já validados.

    Com catálogo, o Yamazumi agrupa por classe de valor (VA/NNVA/NVA) e as regras de
    espera/busca/retrabalho seguem o papel de cada atividade.
    """
    thresholds = thresholds or Thresholds()
    cycles, events = segment_cycles(events)
    mapping = _value_mapping(catalog, events) if catalog else None
    stats = cycle_time_statistics(cycles)
    anomalies = detect_anomalies(cycles, events, takt.takt_time_seconds, search_threshold=thresholds.search_seconds,
                                 waiting_threshold=thresholds.waiting_seconds, mad_threshold=thresholds.mad_z,
                                 standard_ct=takt.standard_cycle_time_seconds, standard_tolerance=thresholds.near_fraction,
                                 roles=catalog.roles() if catalog else None)
    ymz = yamazumi(cycles, events, mapping)
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
        "activities": _activity_summary(cycles, events, catalog),
        "catalog": catalog.model_dump() if catalog else None,
    }
    return metrics, render_report(cycles, events, stats, takt, anomalies, mapping)
