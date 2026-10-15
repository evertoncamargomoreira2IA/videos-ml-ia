import argparse
import json
from pathlib import Path
from .io import load_events
from .models import TaktInput
from .pipeline import run_analysis


def analyze(events_path: str, available_time: float | None, demand: float | None, out_path: str,
            takt_time: float | None = None, standard_ct: float | None = None) -> None:
    takt = TaktInput(takt_time_seconds=takt_time, available_time_seconds=available_time, customer_demand_units=demand,
                     standard_cycle_time_seconds=standard_ct)
    metrics, report = run_analysis(load_events(events_path), takt)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    out.with_name("metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="mva", description="Análise determinística de eventos de manufatura")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("analyze")
    p.add_argument("--events", required=True)
    p.add_argument("--takt", type=float, help="Takt time em segundos (ou use --available-time e --demand)")
    p.add_argument("--standard-ct", type=float, help="Cycle Time padrão do posto em segundos")
    p.add_argument("--available-time", type=float)
    p.add_argument("--demand", type=float)
    p.add_argument("--out", required=True)
    probe = sub.add_parser("probe", help="Exibe metadados de um vídeo")
    probe.add_argument("video")
    ingest = sub.add_parser("ingest", help="Extrai quadros e cria materiais de revisão")
    ingest.add_argument("video")
    ingest.add_argument("--out", required=True)
    ingest.add_argument("--every", type=float, default=1.0)
    ingest.add_argument("--max-frames", type=int)
    ingest.add_argument("--width", type=int)
    serve = sub.add_parser("serve", help="Abre a interface web local de validação")
    serve.add_argument("--data", default=str(Path.home() / "mva_dados"), help="Pasta onde as análises ficam salvas")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--open", action="store_true", help="Abre o navegador automaticamente")
    args = parser.parse_args(argv)
    if args.command == "serve":
        from .webapp.server import serve as run_server
        run_server(args.data, args.host, args.port, args.open)
        return 0
    try:
        if args.command == "analyze":
            analyze(args.events, args.available_time, args.demand, args.out, args.takt, args.standard_ct)
        elif args.command == "probe":
            # OpenCV only loads for video commands, so analyze works without it.
            from .video import probe_video, video_id_for
            info = probe_video(args.video)
            print(json.dumps({**info.model_dump(), "video_id": video_id_for(args.video)}, ensure_ascii=False, indent=2))
        else:
            from .video import contact_sheet, extract_frames, probe_video, write_manifest
            out = Path(args.out)
            info = probe_video(args.video)
            frames = extract_frames(args.video, out / "frames", args.every, args.max_frames, args.width)
            contact_sheet(frames, out / "contact_sheet.jpg")
            write_manifest(info, frames, out)
            print(f"Ingestão concluída: {len(frames)} quadros em {out}")
    except Exception as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
