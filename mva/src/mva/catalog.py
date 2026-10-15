"""Catálogo de atividades: o que o operador pode estar fazendo em cada frame.

O catálogo é editável na interface (Atividades). Cada atividade tem uma classe de valor
Lean (VA, NVA necessário, desperdício) que alimenta o Yamazumi, e um papel opcional
que liga a atividade às regras de anomalia (espera, busca, retrabalho).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

VALUE_CLASSES = {"VA": "Agrega valor (VA)", "NNVA": "NVA necessário", "NVA": "Desperdício (NVA)"}
ROLES = {"": "—", "wait": "Espera", "search": "Busca", "rework": "Retrabalho"}
# Teclas que a tela de rotulagem usa para outras funções.
RESERVED_KEYS = {"s", "e", "i", "o"}
MARKER_TYPES = {"cycle_start", "cycle_end"}


class Activity(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9_]{2,30}$")
    label: str = Field(min_length=1, max_length=60)
    value_class: Literal["VA", "NNVA", "NVA"]
    color: str = Field(default="#64748b", pattern=r"^#[0-9a-fA-F]{6}$")
    key: str = Field(default="", pattern=r"^[a-z0-9]?$")
    role: Literal["", "wait", "search", "rework"] = ""
    description: str = ""


class Catalog(BaseModel):
    activities: list[Activity] = Field(min_length=1)

    @model_validator(mode="after")
    def unique(self):
        codes = [a.code for a in self.activities]
        dup = {c for c in codes if codes.count(c) > 1}
        if dup:
            raise ValueError(f"Código repetido: {', '.join(sorted(dup))}")
        if MARKER_TYPES & set(codes):
            raise ValueError("cycle_start e cycle_end são marcadores de ciclo, não atividades")
        keys = [a.key for a in self.activities if a.key]
        dup = {k for k in keys if keys.count(k) > 1}
        if dup:
            raise ValueError(f"Tecla repetida: {', '.join(sorted(dup))}")
        if RESERVED_KEYS & set(keys):
            raise ValueError("As teclas S, E, I e O são reservadas da rotulagem")
        return self

    def value_mapping(self) -> dict[str, str]:
        return {a.code: a.value_class for a in self.activities}

    def roles(self) -> dict[str, str]:
        return {a.code: a.role for a in self.activities if a.role}


def _a(code, label, value_class, color, key, role="", description=""):
    return Activity(code=code, label=label, value_class=value_class, color=color, key=key, role=role, description=description)


DEFAULT_CATALOG = Catalog(activities=[
    _a("assemble", "Montar", "VA", "#16a34a", "1", description="Monta componentes no produto"),
    _a("fit", "Encaixar", "VA", "#22c55e", "2", description="Encaixa peça, conector ou tampa"),
    _a("fasten", "Parafusar", "VA", "#15803d", "3", description="Parafusa ou aplica torque"),
    _a("connect", "Conectar cabo", "VA", "#4ade80", "4"),
    _a("pick_part", "Pegar / colocar item", "NNVA", "#eab308", "5", description="Pega item do kit/caixa ou coloca o produto na esteira"),
    _a("move_material", "Movimentação de material", "NNVA", "#ca8a04", "6", description="Abastece, troca caixa, movimenta bandeja"),
    _a("inspect", "Inspecionar", "NNVA", "#a16207", "7", description="Inspeção visual ou checagem obrigatória"),
    _a("test", "Testar", "NNVA", "#facc15", "8"),
    _a("wait", "Esperar", "NVA", "#f97316", "9", role="wait", description="Operador parado aguardando máquina, material ou outra pessoa"),
    _a("search", "Procurar", "NVA", "#ef4444", "0", role="search", description="Procura peça ou ferramenta"),
    _a("walk", "Deslocamento", "NVA", "#fb7185", "w", description="Anda ou se desloca sem carregar o produto"),
    _a("rework", "Retrabalho", "NVA", "#b91c1c", "r", role="rework", description="Desfaz e refaz uma operação"),
])


def load_catalog(path: str | Path) -> Catalog:
    path = Path(path)
    if not path.exists():
        return DEFAULT_CATALOG.model_copy(deep=True)
    return Catalog.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_catalog(path: str | Path, catalog: Catalog) -> None:
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(catalog.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
