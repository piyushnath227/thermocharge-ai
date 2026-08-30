from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Charger(BaseModel):
    id: str
    site_id: str
    site_name: str
    charger_name: str
    network: str
    address: str
    latitude: float
    longitude: float
    rated_kw: float
    connector: str
    data_source: str
    source_url: str
    modeled_demand_fraction: float = Field(ge=0.0, le=1.0)


class ThermalResult(BaseModel):
    charger_id: str
    ambient_temperature_c: float
    capacity_factor: float
    usable_kw: float
    capacity_at_risk_kw: float
    capacity_loss_percent: float
    risk_level: Literal['LOW', 'MODERATE', 'HIGH', 'CRITICAL']
    model_name: str
    model_disclaimer: str


class AgentAction(BaseModel):
    priority: int
    action_type: str
    charger_id: str | None = None
    site_id: str | None = None
    title: str
    rationale: str
    redirect_kw: float = 0.0
    destination_site_id: str | None = None
    status: Literal['recommended', 'ready_for_integration', 'informational'] = 'recommended'


class AgentTraceStep(BaseModel):
    tool: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
