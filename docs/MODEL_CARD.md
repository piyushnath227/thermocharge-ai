# Thermal Capacity Model Card

## Purpose

Convert FortyGuard ambient temperature at each charger location into a transparent **scenario estimate** of usable DC fast-charging capacity.

## Current reference model

The hackathon reference profile uses a public EvoCharge DC fast charger specification stating that maximum charging current decreases by 2% per 1°C above 25°C. The model therefore uses:

```text
capacity_factor = 1.0                              when T <= 25°C
capacity_factor = 1 - 0.02 * (T - 25)             when T > 25°C
capacity_factor is floored at 0.50 for this demo
usable_kW = rated_kW * capacity_factor
```

This curve is implemented in `app/services/thermal.py`.

## Critical limitation

The Phoenix pilot uses real public EVgo charger locations and public charger power ratings, but ThermoCharge does **not** claim that those EVgo cabinets use the EvoCharge curve. The curve is a public-reference sensitivity proxy to demonstrate the product's conversion layer.

## Why this is still useful in a hackathon

The product architecture is designed so that the reference curve is replaceable. A CPO or OEM can supply the actual derating curve for each charger model without changing the FortyGuard ingestion, geospatial mapping, dashboard, or agent workflow.

## Risk bands

- LOW: <10% modeled loss
- MODERATE: 10–20%
- HIGH: 20–35%
- CRITICAL: >=35%

These are product prioritization bands, not safety classifications.

## Environmental parameters

Humidity and solar irradiance are displayed as supporting context. They are intentionally **not** used to alter the current capacity factor because the project does not yet have a defensible OEM-specific multivariate thermal curve. This avoids false precision.

## Required next validation for a real company

1. Obtain charger make/model and OEM derating documentation.
2. Integrate OCPP/CPMS telemetry and delivered-power history.
3. Compare predicted vs observed power under matched vehicle SOC and demand conditions.
4. Fit model per charger family/site configuration.
5. Track uncertainty and confidence intervals.
6. Validate recommendations with operator engineers before enabling any automated control.
