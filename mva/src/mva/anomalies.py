import numpy as np
from .models import AnomalyFlag, Cycle, Event

DEFAULT_ROLES = {"search": "search", "wait": "wait", "rework": "rework", "debug": "rework"}


def detect_anomalies(cycles: list[Cycle], events: list[Event], takt_time: float | None = None, search_threshold: float = 5.0, waiting_threshold: float = 5.0, mad_threshold: float = 3.5, standard_ct: float | None = None, standard_tolerance: float = 0.05, roles: dict[str, str] | None = None) -> list[AnomalyFlag]:
    """roles liga cada código de atividade a uma regra: wait, search ou rework."""
    flags: list[AnomalyFlag] = []
    roles = DEFAULT_ROLES if roles is None else roles
    for c in cycles:
        ev = [e for e in events if e.cycle_id == c.cycle_id]
        ids = [e.event_id for e in ev]
        if not c.complete:
            flags.append(AnomalyFlag(anomaly_type="incomplete_cycle", description="Ciclo sem evento de encerramento", evidence_class="detected", cycle_ids=[c.cycle_id], event_ids=ids))
        if c.complete and takt_time and c.duration is not None and c.duration > takt_time:
            flags.append(AnomalyFlag(anomaly_type="above_takt", severity="warning", description="Cycle Time acima do takt", evidence_class="measured", cycle_ids=[c.cycle_id], event_ids=ids, value=c.duration, threshold=takt_time))
        if c.complete and standard_ct and c.duration is not None and c.duration > standard_ct * (1 + standard_tolerance):
            flags.append(AnomalyFlag(anomaly_type="above_standard_ct", severity="warning", description="Cycle Time acima do CT padrão", evidence_class="measured", cycle_ids=[c.cycle_id], event_ids=ids, value=c.duration, threshold=standard_ct))
        search = [e for e in ev if roles.get(e.event_type) == "search"]
        search_time = sum(e.duration for e in search)
        if search_time > search_threshold:
            flags.append(AnomalyFlag(anomaly_type="excessive_search", severity="warning", description="Tempo de busca acima do limiar", evidence_class="measured", cycle_ids=[c.cycle_id], event_ids=[e.event_id for e in search], value=search_time, threshold=search_threshold))
        waiting = [e for e in ev if roles.get(e.event_type) == "wait"]
        waiting_time = sum(e.duration for e in waiting)
        if waiting_time > waiting_threshold:
            flags.append(AnomalyFlag(anomaly_type="excessive_waiting", severity="warning", description="Tempo de espera acima do limiar", evidence_class="measured", cycle_ids=[c.cycle_id], event_ids=[e.event_id for e in waiting], value=waiting_time, threshold=waiting_threshold))
        rework_events = [e for e in ev if roles.get(e.event_type) == "rework"]
        if rework_events:
            flags.append(AnomalyFlag(anomaly_type="rework_debug", severity="warning", description="Evento de retrabalho ou debug observado", evidence_class="detected", cycle_ids=[c.cycle_id], event_ids=[e.event_id for e in rework_events]))
    valid = [c for c in cycles if c.complete and c.duration is not None]
    vals = np.array([c.duration for c in valid], dtype=float)
    if len(vals):
        median = float(np.median(vals))
        mad = float(np.median(np.abs(vals - median)))
        # Iglewicz-Hoaglin: when over half the cycles share the median, MAD is 0;
        # fall back to the mean absolute deviation so slow cycles still surface.
        mean_ad = float(np.mean(np.abs(vals - median)))
        scale = mad / 0.6745 if mad > 0 else 1.253314 * mean_ad
        if scale > 0:
            for c in valid:
                z = (c.duration - median) / scale
                if abs(z) > mad_threshold:
                    flags.append(AnomalyFlag(anomaly_type="mad_outlier", severity="warning", description="Cycle Time é outlier pelo MAD robusto", evidence_class="measured", cycle_ids=[c.cycle_id], event_ids=[e.event_id for e in events if e.cycle_id == c.cycle_id], value=float(z), threshold=mad_threshold))
    return flags
