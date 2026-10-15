from .models import Cycle, Event


def segment_cycles(events: list[Event], start_type: str = "cycle_start", end_type: str = "cycle_end") -> tuple[list[Cycle], list[Event]]:
    # At equal timestamps, close the running cycle before opening the next one.
    rank = {end_type: 0, start_type: 1}
    ordered = sorted(events, key=lambda e: (e.start_time, rank.get(e.event_type, 2), e.end_time, e.event_id))
    cycles: list[Cycle] = []
    active: dict | None = None
    counter = 0
    assignments: dict[str, str] = {}
    for event in ordered:
        if event.event_type == start_type:
            if active is not None:
                cycles.append(Cycle(cycle_id=active["id"], start_time=active["start"], event_ids=active["ids"], complete=False))
            counter += 1
            active = {"id": event.cycle_id or f"cycle_{counter:03d}", "start": event.start_time, "ids": [event.event_id]}
            assignments[event.event_id] = active["id"]
        elif active is not None:
            active["ids"].append(event.event_id)
            assignments[event.event_id] = active["id"]
            if event.event_type == end_type:
                cycles.append(Cycle(cycle_id=active["id"], start_time=active["start"], end_time=event.end_time, event_ids=active["ids"], complete=True))
                active = None
    if active is not None:
        cycles.append(Cycle(cycle_id=active["id"], start_time=active["start"], event_ids=active["ids"], complete=False))
    assigned = [e.model_copy(update={"cycle_id": assignments.get(e.event_id, e.cycle_id)}) for e in events]
    return cycles, assigned
