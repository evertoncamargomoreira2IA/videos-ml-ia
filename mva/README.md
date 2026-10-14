# MVA — núcleo determinístico

Requer Python 3.10 ou superior.

```bash
pip install -e .
python -m pytest -q
python -m mva.cli analyze --events examples/sample_events.csv --available-time 25200 --demand 600 --out relatorio.md
```

A CLI grava o relatório Markdown indicado e `metrics.json` na mesma pasta.

Para suporte a vídeo: `pip install -e ".[video]"` (ou `pip install -e ".[dev]"` para desenvolvimento).

```bash
python -m mva probe video.mp4
python -m mva ingest video.mp4 --out saida --every 1.0 --max-frames 20 --width 640
```

`probe` exibe metadados e um identificador estável do vídeo. `ingest` salva quadros em `saida/frames/`, uma grade `contact_sheet.jpg` e `manifest.json`.
