from collections import defaultdict
from .models import Cycle, Event

DEFAULT_BUCKETS = {"assemble":"VA", "fasten":"VA", "torque":"VA", "connect":"VA", "place_part":"VA", "pick_part":"Necessary NVA", "inspect":"Inspection", "measure":"Inspection", "test":"Inspection", "wait":"Waiting", "search":"Search", "walk":"Motion", "reach":"Motion", "rework":"Rework", "debug":"Rework", "remove_part":"Rework", "replace_part":"Rework", "talk":"Other", "error":"Other", "unknown":"Other"}


def yamazumi(cycles: list[Cycle], events: list[Event], mapping: dict[str, str] | None = None) -> dict:
    mapping = mapping or DEFAULT_BUCKETS
    out = {}
    for cycle in cycles:
        selected = [e for e in events if e.cycle_id == cycle.cycle_id and e.event_type not in {"cycle_start", "cycle_end"}]
        buckets = defaultdict(float)
        for e in selected:
            buckets[mapping.get(e.event_type, "Other")] += e.duration
        total = sum(buckets.values())
        covered = sorted((e.start_time, e.end_time, e.event_id) for e in selected)
        union = 0.0
        overlap = 0.0
        if covered:
            left, right, _ = covered[0]
            for start, end, _ in covered[1:]:
                if start < right:
                    overlap += max(0.0, min(right, end) - start)
                    right = max(right, end)
                else:
                    union += right - left
                    left, right = start, end
            union += right - left
        ct = cycle.duration
        out[cycle.cycle_id] = {"buckets": dict(sorted(buckets.items())), "event_duration_sum": total, "cycle_time": ct, "gap_seconds": max(0.0, (ct or 0) - union), "overlap_seconds": overlap, "reconciliation_delta_seconds": (total - (ct or 0)) if ct is not None else None}
    return out


def yamazumi_average(data: dict) -> dict[str, float]:
    # Only complete cycles: a partial cycle would drag every bucket average down.
    rows = [row for row in data.values() if row["cycle_time"] is not None]
    keys = sorted({k for row in rows for k in row["buckets"]})
    n = len(rows)
    return {k: sum(row["buckets"].get(k, 0.0) for row in rows) / n for k in keys} if n else {}
