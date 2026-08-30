# ThermoCharge AI

**Thermal Capacity Intelligence for EV Charging Networks**

ThermoCharge AI is a FortyGuard Global AI Hackathon 2026 project that converts hyperlocal thermal intelligence into heat-adjusted EV charging capacity estimates and auditable operational recommendations.

> FortyGuard tells us where heat is happening. ThermoCharge tells an EV charging operator what that heat could mean for usable capacity and what to do next.

## What the project does

1. Loads real public EV fast-charging assets in a South Phoenix pilot corridor.
2. Fetches a real FortyGuard heatmap for the pilot polygon.
3. Maps each charger site into its matching FortyGuard GeoJSON temperature tile.
4. Fetches selected FortyGuard environmental context once per unique site.
5. Converts local ambient temperature into a transparent, configurable reference capacity estimate.
6. Runs an auditable agent planner that scans risk, ranks assets, finds modeled lower-risk headroom, and produces constrained recommendations.
7. Presents the result in a no-login operations dashboard.

## Pilot assets

The repo includes eight real named EVgo charger assets across two South Phoenix fast-charging sites:

- **Southgate Center** — PHILLIPA 100 kW, AIDY 100 kW, MARQUIS 350 kW, QUAN 350 kW.
- **Laveen Village Center** — MARE 100 kW, KIMIKO 100 kW, FELDER 350 kW, ERMA 350 kW.

See `data/source_notes.md` for source URLs, evidence, and limitations.

## Data honesty

The UI and API distinguish four categories:

- **Real public charger data** — public location/nameplate information.
- **FortyGuard data** — real only after `scripts/fetch_fortyguard.py` creates `data/live/snapshot.json`.
- **Model estimates** — usable kW, kW at risk, risk bands, throughput/session impact.
- **Demonstrated actions** — recommendations only. ThermoCharge does not claim to control real chargers.

The included fallback heatmap is explicitly **simulated development data** so the project can be built and reviewed before API credentials are configured.

## Architecture

```text
Public EV charger data
        |
        v
Charger registry
        |
        +-------------------------+
        |                         |
        v                         v
FortyGuard heatmap           FortyGuard env_params
        |                         |
        v                         |
GeoJSON tiles                    |
        |                         |
        v                         |
charger -> tile matching <-------+
        |
        v
local thermal exposure
        |
        v
Thermal Capacity Engine
        |
        v
rated kW -> usable kW -> kW at risk
        |
        v
Auditable Agent Planner
        |
        v
FastAPI + web dashboard
```

More detail: `docs/ARCHITECTURE.md`.

---

# Quick start on Windows PowerShell

## 1. Unzip and enter the project

```powershell
cd E:\ThermoCharge
```

## 2. Create a virtual environment

If you want to reuse your existing `E:\.venv`, skip this step. Otherwise:

```powershell
python -m venv .venv
```

## 3. Install dependencies

With a project-local venv:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Or with your existing venv:

```powershell
E:\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 4. Generate/check development data

```powershell
.\.venv\Scripts\python.exe scripts\generate_demo_data.py
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

## 5. Run the dashboard

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

The page will clearly show **SIMULATED DEV MODE** until a real FortyGuard snapshot exists.

---

# Connect FortyGuard

Do **not** hardcode or commit the key.

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Edit `.env` locally:

```text
FORTYGUARD_API_KEY=your_current_key_here
```

`.env` is already ignored by Git.

Then fetch the real Phoenix historical snapshot:

```powershell
.\.venv\Scripts\python.exe scripts\fetch_fortyguard.py
```

The script intentionally uses:

- **1 heatmap request** for the full pilot corridor.
- **1 env_params request per unique charging site** (2 sites in this repo).
- cached JSON afterward, so page refreshes do not consume FortyGuard credits.

Successful output creates:

```text
data/live/fortyguard_heatmap_raw.json
data/live/env_southgate_raw.json
data/live/env_laveen_raw.json
data/live/snapshot.json
```

Restart the app. `THERMOCHARGE_DATA_MODE=auto` automatically prefers `data/live/snapshot.json` and the badge changes to **FORTYGUARD DATA**.

## Change the historical replay time

```powershell
.\.venv\Scripts\python.exe scripts\fetch_fortyguard.py --date 2024-07-08 --time 15:00
```

The default is July 5, 2024 at 15:00 Phoenix local time, selected because the U.S. National Weather Service reports a 118°F Phoenix high that day.

---

# Optional LLM explanation layer

The operational planner works without an LLM. It is intentionally deterministic and auditable.

If you add an OpenAI API key locally:

```text
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6
```

ThermoCharge uses the Responses API only to summarize the already-calculated state and already-approved action list. The LLM cannot change capacity numbers or create unapproved control actions.

If no key is configured or the LLM request fails, the application automatically falls back to the deterministic explanation.

---

# Thermal model

The current hackathon model is a transparent **reference sensitivity proxy**, not an EVgo hardware claim.

A public EvoCharge DC fast charger specification states that maximum charging current decreases by 2% for each 1°C above 25°C. The current model uses that as a replaceable sensitivity curve:

```text
factor = 1.0                          T <= 25°C
factor = 1 - 0.02 * (T - 25)         T > 25°C
factor floor = 0.50
usable_kW = rated_kW * factor
```

ABB's Terra 360 documentation independently notes temperature derating beginning at 40°C, supporting the broader premise that ambient-temperature derating is a genuine DCFC equipment consideration.

**Important:** the specific Phoenix EVgo hardware may use different cooling systems and derating curves. Production ThermoCharge must replace the proxy with charger-model/OEM/operator-specific curves and validate against telemetry.

See `docs/MODEL_CARD.md`.

---

# Agent behavior

The agent executes an auditable internal workflow:

```text
scan_network
    -> rank_thermal_risk
    -> find_lower_risk_capacity
    -> create_operational_plan
```

Possible recommendations include:

- Rebalance flexible charging demand toward modeled lower-risk headroom.
- Inspect cooling path on high/critical assets.
- Re-run thermal analysis before the next peak period.

No physical command is sent to an EV charger.

## Ask ThermoCharge (goal-driven Q&A)

Beyond the fixed pipeline above, `POST /api/ask` lets an operator (or a judge, live) ask a
plain-language question and get an answer grounded entirely in the already-computed,
already-audited dashboard state:

```text
POST /api/ask
{"question": "Should we rebalance demand?"}

-> {
  "question": "Should we rebalance demand?",
  "answer": "Yes — Rebalance up to 120 kW of flexible demand. ...",
  "grounded_on": ["actions.rebalance_flexible_demand"],
  "mode": "deterministic"
}
```

The answer never invents a number: it is produced by pattern-matching the question against
the same structured state used everywhere else in the dashboard
(`app/services/agent.py: answer_question_deterministic`). If `OPENAI_API_KEY` is configured,
the deterministic answer is optionally rephrased/elaborated by an LLM that is given the
grounded answer plus the structured state and is explicitly instructed not to invent facts —
if that call fails or no key is present, the deterministic answer is served directly so the
live demo never depends on external API availability.

The map also visualizes the agent's own top rebalance recommendation, if any, as an
animated flow line between the source and destination sites, so the audience sees the
decision, not only a text description of it.

---

# Business-impact assumptions

To make technical risk understandable, the dashboard estimates:

```text
throughput_at_risk_kWh = capacity_at_risk_kW * risk_window_hours
sessions_affected = throughput_at_risk_kWh / average_session_kWh
revenue_at_risk = throughput_at_risk_kWh * scenario_price_per_kWh
```

Current scenario assumptions are stored in `data/pilot.json` and are clearly marked as modeled assumptions, not operator financial data.

---

# API endpoints

```text
GET  /health
GET  /api/dashboard
GET  /api/replay
POST /api/ask
GET  /
```

The dashboard API returns the complete current snapshot: charger assets, thermal matches, capacity estimates, summary metrics, agent actions, agent trace, model disclaimer, and provenance labels. `/api/replay` returns one precomputed dashboard frame per fetched historical time point. `/api/ask` accepts `{"question": "..."}` and returns a grounded natural-language answer over the current dashboard state — see "Ask ThermoCharge" above.

---

# Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover:

- thermal reference curve
- usable-capacity calculation
- point-in-polygon heatmap matching
- full dashboard assembly

---

# Deployment

## Render

A `render.yaml` and `Dockerfile` are included.

1. Push this repo to GitHub.
2. Create a new Render Blueprint/Web Service from the repository.
3. Add `FORTYGUARD_API_KEY` only if you intend server-side fetches. For the safest hackathon demo, pre-fetch `snapshot.json` locally and deploy it intentionally, or use a private data service/storage strategy.
4. Add `OPENAI_API_KEY` only if using the optional explanation layer.
5. Keep `ALLOW_LIVE_REFRESH=false`.
6. Verify `/health` and open the site in an incognito window.

### Important note about `data/live`

`data/live/*.json` is gitignored by default to prevent accidentally committing raw hackathon API outputs (per-timepoint `*_raw_*.json` and `frame_*.json` intermediates). The two processed files the running app actually reads — `data/live/snapshot.json` (used by `/api/dashboard`) and `data/live/replay_snapshot.json` (used by `/api/replay`) — are explicitly un-ignored and **are committed to this repo**. Both were scanned for API keys, tokens, and secrets before committing (none found — FortyGuard responses don't echo back the request key).

**This means a fresh `git clone` + deploy shows real FortyGuard data immediately, with no manual "remember to commit the snapshot" step.** If you regenerate these files with `scripts/fetch_fortyguard.py`, re-run the same secret scan before committing the refreshed versions:

```powershell
Select-String -Path data/live/snapshot.json,data/live/replay_snapshot.json -Pattern '"(api_?key|authorization|token|secret|bearer)"\s*:\s*"[^"]{4,}"'
```

No output = safe to commit.

---

# Hackathon files

- Architecture: `docs/ARCHITECTURE.md`
- Model transparency: `docs/MODEL_CARD.md`
- <=3 minute demo script: `docs/DEMO_SCRIPT.md`
- Submission wording: `docs/SUBMISSION_NOTES.md`
- Evidence/source notes: `data/source_notes.md`
- Prior successful FortyGuard API sample from development: `data/samples/fortyguard_heatmap_result_nyc.json`

---

# Next production upgrades

1. Replace the reference derating proxy with OEM-specific curves.
2. Add OCPP/CPMS integration.
3. Add charger telemetry and observed delivered-power validation.
4. Use FortyGuard persistence/exceedance as duration features.
5. Add load/session forecasting.
6. Add operator policy constraints for autonomous action approval.
7. Add confidence intervals and model monitoring.

## Hackathon definition of success

A judge should understand this within 30 seconds:

> FortyGuard tells ThermoCharge where heat is happening. ThermoCharge maps that heat to real charging assets, converts it into a transparent estimate of usable charging capacity, and an agent recommends what the operator should do next.
