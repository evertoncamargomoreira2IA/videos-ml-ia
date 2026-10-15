# MVA — núcleo determinístico

Requer Python 3.10 ou superior.

```bash
pip install -e .
python -m pytest -q
python -m mva analyze --events examples/sample_events.csv --takt 42 --standard-ct 40 --out relatorio.md
```

A CLI grava o relatório Markdown indicado e `metrics.json` na mesma pasta.

Para instalar suporte a vídeo: `pip install -e ".[video]"` (ou `pip install -e ".[dev]"` para desenvolvimento). Os comandos de ingestão usam OpenCV:

```bash
python -m mva probe video.mp4
python -m mva ingest video.mp4 --out saida --every 1.0 --max-frames 20 --width 640
```

`probe` exibe metadados e o identificador estável do vídeo. `ingest` salva quadros em `saida/frames/`, uma grade `contact_sheet.jpg` e `manifest.json`.

## Interface local de validação

```bash
pip install -e ".[web,video]"
python -m mva serve --open            # http://127.0.0.1:8765/, dados em ~/mva_dados
```

No Windows, use o `iniciar.bat` na raiz do repositório. A tela de rotulagem também funciona sozinha: abra `src/mva/webapp/static/labeler.html` com duplo clique.
