import json
from pathlib import Path
import pandas as pd
from pydantic import ValidationError
from .models import Event

def load_events(path: str | Path) -> list[Event]:
    path=Path(path); suffix=path.suffix.lower()
    if suffix==".csv":
        try: rows=pd.read_csv(path,dtype=str,keep_default_na=False,encoding="utf-8-sig").to_dict(orient="records")
        except Exception as exc: raise ValueError(f"Erro lendo CSV: {exc}") from exc
    elif suffix==".json":
        with path.open(encoding="utf-8") as f: rows=json.load(f)
        if not isinstance(rows,list): raise ValueError("JSON deve conter uma lista de eventos")
    else: raise ValueError("Formato não suportado; use CSV ou JSON")
    result=[]
    for line,row in enumerate(rows,start=2 if suffix==".csv" else 1):
        try:
            row={k:(None if v=="" else v) for k,v in row.items()}
            result.append(Event.model_validate(row))
        except (ValidationError,TypeError,ValueError) as exc: raise ValueError(f"Evento inválido na linha {line}: {exc}") from exc
    return result
