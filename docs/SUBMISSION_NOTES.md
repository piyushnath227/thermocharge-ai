# Hackathon submission notes

## Project title
ThermoCharge AI

## Primary track
Track 06 — Agentic AI

## Secondary tags
- Track 03 — Industrial & Enterprise
- Track 02 — Future Buildings & Energy

## One-line pitch
ThermoCharge AI uses FortyGuard's hyperlocal temperature intelligence to estimate heat-adjusted capacity across EV fast-charging networks and generate proactive operational recommendations before thermal constraints impact service.

## Pilot geography
South Phoenix, Arizona, USA. Historical replay target: July 5, 2024 at approximately 3 PM local time. The U.S. National Weather Service reports a Phoenix high of 118°F on that date.

## What is real
- Public EVgo charging locations and charger names/power ratings.
- FortyGuard data after `scripts/fetch_fortyguard.py` is run with the hackathon API key.
- GeoJSON point-to-tile mapping and all deterministic calculations.

## What is modeled
- Thermal capacity factor and usable kW.
- kWh throughput at risk, sessions affected, and revenue-at-risk scenario calculations.
- Modeled utilization fractions used to demonstrate network headroom.

## What is demonstrated, not executed
- Rebalancing flexible charging demand.
- CPO/CPMS control action.
- Maintenance workflow dispatch.

## Judge verification
Keep the FortyGuard key out of GitHub. Supply it only through the official submission field requested by the organizer.
