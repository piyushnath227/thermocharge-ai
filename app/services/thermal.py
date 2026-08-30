from __future__ import annotations

from dataclasses import dataclass

from app.models import Charger, ThermalResult


@dataclass(frozen=True)
class ReferenceDeratingProfile:
    """Transparent reference profile for hackathon analysis.

    The 2%/°C current reduction above 25°C is based on a public EvoCharge DC fast
    charger specification. It is intentionally treated as a reference sensitivity
    curve, NOT as a claim about the EVgo hardware used in the Phoenix pilot.
    """

    name: str = 'Public-reference DCFC sensitivity (EvoCharge-derived proxy)'
    onset_c: float = 25.0
    loss_per_c: float = 0.02
    minimum_factor: float = 0.50
    maximum_supported_c: float = 50.0

    def capacity_factor(self, ambient_c: float) -> float:
        if ambient_c <= self.onset_c:
            return 1.0
        raw = 1.0 - (ambient_c - self.onset_c) * self.loss_per_c
        return max(self.minimum_factor, min(1.0, raw))


DEFAULT_PROFILE = ReferenceDeratingProfile()
DISCLAIMER = (
    'Model estimate only. The thermal response curve is a public-reference proxy and is not '
    'an EVgo/OEM-specific performance claim. Production deployment requires operator- or '
    'manufacturer-specific derating curves and telemetry validation.'
)


def risk_level(loss_percent: float) -> str:
    if loss_percent < 10:
        return 'LOW'
    if loss_percent < 20:
        return 'MODERATE'
    if loss_percent < 35:
        return 'HIGH'
    return 'CRITICAL'


def evaluate_charger(charger: Charger, ambient_c: float, profile: ReferenceDeratingProfile = DEFAULT_PROFILE) -> ThermalResult:
    factor = profile.capacity_factor(ambient_c)
    usable = charger.rated_kw * factor
    at_risk = charger.rated_kw - usable
    loss_pct = (1 - factor) * 100
    return ThermalResult(
        charger_id=charger.id,
        ambient_temperature_c=round(ambient_c, 3),
        capacity_factor=round(factor, 4),
        usable_kw=round(usable, 2),
        capacity_at_risk_kw=round(at_risk, 2),
        capacity_loss_percent=round(loss_pct, 1),
        risk_level=risk_level(loss_pct),
        model_name=profile.name,
        model_disclaimer=DISCLAIMER,
    )
