from mva.models import Event, TaktInput
from mva.cycles import segment_cycles
from mva.metrics import cycle_time_statistics
from mva.yamazumi import yamazumi
from mva.anomalies import detect_anomalies

def event(eid,start,end,kind="assemble",cycle=None):
    return Event(event_id=eid,video_id="v",cycle_id=cycle,station_id="s",start_time=start,end_time=end,duration=end-start,event_type=kind,category="x",value_class="VA",confidence=.9,source="manual",human_verified=False)

def test_event_validates_duration_and_order():
    event("a",1,2)
    try: Event(event_id="b",video_id="v",station_id="s",start_time=2,end_time=1,duration=1,event_type="assemble",category="x",value_class="VA",confidence=.9,source="manual",human_verified=False)
    except ValueError: pass
    else: assert False, "timestamps reversed should fail"

def test_cycle_segmentation_and_statistics():
    source=[event("s1",0,0,"cycle_start"),event("a",0,10),event("e1",10,10,"cycle_end"),event("s2",10,10,"cycle_start"),event("b",10,30),event("e2",30,30,"cycle_end")]
    cycles,assigned=segment_cycles(source); stats=cycle_time_statistics(cycles)
    assert [c.duration for c in cycles]==[10,20]
    assert stats.n==2 and stats.mean==15 and stats.median==15
    assert TaktInput(available_time_seconds=25200,customer_demand_units=600).takt_time_seconds==42

def test_yamazumi_reconciles_and_anomalies():
    source=[event("s",0,0,"cycle_start"),event("a",0,5),event("b",5,10,"search"),event("e",10,10,"cycle_end")]
    cycles,ev=segment_cycles(source); row=yamazumi(cycles,ev)[cycles[0].cycle_id]
    assert row["gap_seconds"]==0 and row["overlap_seconds"]==0
    flags=detect_anomalies(cycles,ev,takt_time=8,search_threshold=3)
    assert {"above_takt","excessive_search"} <= {f.anomaly_type for f in flags}
