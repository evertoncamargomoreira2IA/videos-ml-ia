from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

EVENT_TYPES = (
    "cycle_start", "cycle_end", "pick_part", "place_part", "assemble", "fasten",
    "torque", "connect", "disconnect", "inspect", "measure", "test", "search",
    "walk", "reach", "wait", "talk", "rework", "debug", "remove_part",
    "replace_part", "error", "unknown",
)


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    video_id: str
    cycle_id: str | None = None
    station_id: str
    operator_id: str | None = None
    product_id: str | None = None
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)
    duration: float = Field(ge=0)
    event_type: str
    object: str | None = None
    category: str
    value_class: str
    confidence: float = Field(ge=0, le=1)
    source: Literal["vision_model", "manual", "rule"]
    human_verified: bool
    model_version: str | None = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"event_type inválido: {self.event_type}")
        if self.end_time < self.start_time:
            raise ValueError("end_time deve ser maior ou igual a start_time")
        if abs((self.end_time - self.start_time) - self.duration) > 0.01:
            raise ValueError("duration deve corresponder a end_time - start_time (tolerância 0.01s)")
        return self


class Cycle(BaseModel):
    cycle_id: str
    start_time: float
    end_time: float | None = None
    duration: float | None = None
    event_ids: list[str] = Field(default_factory=list)
    complete: bool

    @model_validator(mode="after")
    def duration_matches(self):
        if self.end_time is not None:
            if self.end_time < self.start_time:
                raise ValueError("end_time do ciclo anterior ao início")
            actual = self.end_time - self.start_time
            if self.duration is None:
                self.duration = actual
            elif abs(actual - self.duration) > 0.01:
                raise ValueError("duration do ciclo inconsistente")
        return self


class TaktInput(BaseModel):
    available_time_seconds: float = Field(gt=0)
    customer_demand_units: float = Field(gt=0)

    @property
    def takt_time_seconds(self) -> float:
        return self.available_time_seconds / self.customer_demand_units


class CycleMetrics(BaseModel):
    n: int
    mean: float | None
    median: float | None
    min: float | None
    max: float | None
    std: float | None
    p90: float | None
    p95: float | None
    cv: float | None


class AnomalyFlag(BaseModel):
    anomaly_type: str
    severity: str = "info"
    description: str
    evidence_class: Literal["measured", "detected", "inferred", "hypothesis", "recommendation"]
    cycle_ids: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    value: float | None = None
    threshold: float | None = None
