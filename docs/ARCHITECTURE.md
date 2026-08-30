# ThermoCharge AI architecture

## Core principle

FortyGuard observes the thermal environment. ThermoCharge translates that environment into an auditable capacity estimate and an operational plan.

```text
Public charger inventory
        |
        v
Charger asset registry -------------------------+
        |                                       |
        v                                       |
FortyGuard Heatmap API                          |
        |                                       |
        v                                       |
GeoJSON thermal tiles                           |
        |                                       |
        +--> point-in-polygon charger matching  |
                        |                       |
                        v                       |
               local ambient temperature        |
                        |                       |
FortyGuard env_params -- humidity/solar context |
                        |                       |
                        v                       |
               Thermal Capacity Engine <--------+
                        |
                        v
         rated kW / usable kW / kW at risk
                        |
                        v
              Auditable Agent Planner
             /          |           \
       scan risk   find headroom   plan action
             \          |           /
                        v
                  Operations dashboard
```

## Why the math is outside the LLM

The LLM is not allowed to invent capacity factors. Numeric capacity is calculated by a deterministic reference model. The agent receives those structured results and can only choose from constrained operational action types.

## Data modes

- `simulated_demo`: synthetic Phoenix heat field for UI development. Clearly labelled in the UI.
- `fortyguard_live_or_historical`: created by `scripts/fetch_fortyguard.py`; uses real FortyGuard heatmap and environmental-parameter outputs.
- `auto` (default): prefer the real snapshot when present; otherwise use demo mode.

## FortyGuard credit protection

The fetch script uses one heatmap request for the whole pilot polygon and one environmental-parameter request per unique site. The public web page reads cached JSON and does not call FortyGuard on every page load.

## Production extension

A production deployment would replace the public reference derating proxy with charger-model-specific curves and ingest OCPP/CPMS telemetry, delivered-power history, alarms, cabinet temperatures, cooling status, utilization forecasts, and operator-defined control policies.
