import argparse, json
from pathlib import Path
from .anomalies import detect_anomalies
from .cycles import segment_cycles
from .io import load_events
from .metrics import cycle_time_statistics, classify_cycle_time
from .models import TaktInput
from .report import render_report
from .yamazumi import yamazumi, yamazumi_average

def analyze(events_path: str, available_time: float, demand: float, out_path: str) -> None:
    events=load_events(events_path); cycles,events=segment_cycles(events)
    takt=TaktInput(available_time_seconds=available_time,customer_demand_units=demand)
    stats=cycle_time_statistics(cycles); anomalies=detect_anomalies(cycles,events,takt.takt_time_seconds)
    report=render_report(cycles,events,stats,takt,anomalies); out=Path(out_path); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(report,encoding="utf-8")
    y=yamazumi(cycles,events)
    metrics={"takt":{"available_time_seconds":available_time,"customer_demand_units":demand,"takt_time_seconds":takt.takt_time_seconds},"statistics":stats.model_dump(),"cycles":[{**c.model_dump(),"comparison":classify_cycle_time(c.duration,takt.takt_time_seconds) if c.complete and c.duration is not None else None} for c in cycles],"yamazumi":y,"yamazumi_average":yamazumi_average(y),"anomalies":[a.model_dump() for a in anomalies]}
    out.with_name("metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")

def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog="mva",description="Análise determinística de eventos de manufatura")
    sub=parser.add_subparsers(dest="command",required=True); p=sub.add_parser("analyze")
    p.add_argument("--events",required=True); p.add_argument("--available-time",required=True,type=float); p.add_argument("--demand",required=True,type=float); p.add_argument("--out",required=True)
    args=parser.parse_args(argv)
    try: analyze(args.events,args.available_time,args.demand,args.out)
    except Exception as exc: parser.error(str(exc))
    return 0

if __name__=="__main__": raise SystemExit(main())
