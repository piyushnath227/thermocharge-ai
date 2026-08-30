from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.models import Charger
from app.services.agent import ThermoChargeAgent, deterministic_explanation, llm_explanation
from app.services.demo import build_demo_heatmap
from app.services.geospatial import feature_temperature, match_point_to_heatmap
from app.services.thermal import evaluate_charger


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def load_chargers() -> list[Charger]:
    return [Charger(**item) for item in load_json(settings.data_dir / 'chargers.json')]


def load_pilot() -> dict[str, Any]:
    return load_json(settings.data_dir / 'pilot.json')


def choose_snapshot() -> tuple[str, dict[str, Any]]:
    live = settings.data_dir / 'live' / 'snapshot.json'
    if settings.data_mode in {'auto', 'live'} and live.exists():
        return 'fortyguard_live_or_historical', load_json(live)
    if settings.data_mode == 'live' and not live.exists():
        raise FileNotFoundError('THERMOCHARGE_DATA_MODE=live but data/live/snapshot.json does not exist')

    demo_path = settings.data_dir / 'demo_heatmap.json'
    if not demo_path.exists():
        pilot = load_pilot()
        demo_path.write_text(json.dumps(build_demo_heatmap(pilot), indent=2), encoding='utf-8')
    return 'simulated_demo', {
        'source': 'simulated_demo',
        'heatmap': load_json(demo_path),
        'env_by_site': {
            'southgate': {'relative_humidity_percent': 14.0, 'solar_irradiance': {'ghi': 930.0}},
            'laveen': {'relative_humidity_percent': 15.0, 'solar_irradiance': {'ghi': 910.0}},
        },
        'analysis_time': '2024-07-05T15:00:00-07:00',
        'warning': 'Simulated UI dataset. Run scripts/fetch_fortyguard.py before hackathon submission.',
    }


def build_dashboard() -> dict[str, Any]:
    chargers = load_chargers()
    pilot = load_pilot()
    mode, snapshot = choose_snapshot()
    return build_dashboard_from_snapshot(chargers, pilot, mode, snapshot)


def build_replay() -> dict[str, Any]:
    """Precompute one full dashboard state per fetched time point, so the
    frontend slider only ever indexes into already-computed frames — no
    recomputation, and no live FortyGuard dependency, during a judge's demo."""
    replay_path = settings.data_dir / 'live' / 'replay_snapshot.json'
    if not replay_path.exists():
        raise FileNotFoundError(
            'No replay data yet. Run: python scripts/fetch_fortyguard.py '
            '(fetches all pilot.json replay_times_local in one run).'
        )
    chargers = load_chargers()
    pilot = load_pilot()
    replay = load_json(replay_path)
    frames = [
        build_dashboard_from_snapshot(chargers, pilot, 'fortyguard_live_or_historical', frame)
        for frame in replay['frames']
    ]
    return {
        'date': replay['date'],
        'times_local': [f['analysis_time'] for f in frames],
        'frames': frames,
    }


def build_dashboard_from_snapshot(
    chargers: list[Charger], pilot: dict[str, Any], mode: str, snapshot: dict[str, Any]
) -> dict[str, Any]:
    heatmap = snapshot['heatmap']

    thermal_results = []
    charger_rows = []
    for charger in chargers:
        feature = match_point_to_heatmap(charger.latitude, charger.longitude, heatmap)
        temp = feature_temperature(feature) if feature else None
        if temp is None:
            raise RuntimeError(f'No temperature could be matched for charger {charger.id}')
        result = evaluate_charger(charger, temp)
        thermal_results.append(result)
        env = snapshot.get('env_by_site', {}).get(charger.site_id, {})
        charger_rows.append({
            **charger.model_dump(),
            'tile_id': feature.get('properties', {}).get('tile_id') if feature else None,
            'temperature_c': result.ambient_temperature_c,
            'usable_kw': result.usable_kw,
            'capacity_at_risk_kw': result.capacity_at_risk_kw,
            'capacity_loss_percent': result.capacity_loss_percent,
            'risk_level': result.risk_level,
            'relative_humidity_percent': env.get('relative_humidity_percent'),
            'solar_ghi': (env.get('solar_irradiance') or {}).get('ghi'),
        })

    installed_kw = sum(c.rated_kw for c in chargers)
    usable_kw = sum(t.usable_kw for t in thermal_results)
    at_risk_kw = installed_kw - usable_kw
    risk_window_hours = float(pilot['commercial_assumptions']['risk_window_hours'])
    avg_session_kwh = float(pilot['commercial_assumptions']['average_session_kwh'])
    energy_price = float(pilot['commercial_assumptions']['energy_price_usd_per_kwh'])
    throughput_at_risk = at_risk_kw * risk_window_hours
    sessions_affected = throughput_at_risk / avg_session_kwh if avg_session_kwh else 0
    revenue_at_risk = throughput_at_risk * energy_price

    actions, trace = ThermoChargeAgent().run(chargers, thermal_results)
    state = {
        'summary': {
            'installed_kw': installed_kw,
            'usable_kw': usable_kw,
            'capacity_at_risk_kw': at_risk_kw,
        },
        'actions': [a.model_dump() for a in actions],
    }
    explanation = deterministic_explanation(actions)
    explanation_mode = 'deterministic'
    if settings.openai_api_key:
        try:
            explanation = llm_explanation(settings.openai_api_key, settings.openai_model, state)
            explanation_mode = f'openai:{settings.openai_model}'
        except Exception as exc:  # public demo should not fail because an optional LLM call failed
            explanation += f' (Optional LLM explanation unavailable: {type(exc).__name__})'

    return {
        'project': 'ThermoCharge AI',
        'pilot': pilot,
        'data_mode': mode,
        'data_warning': snapshot.get('warning'),
        'analysis_time': snapshot.get('analysis_time'),
        'heatmap': heatmap,
        'chargers': charger_rows,
        'summary': {
            'installed_kw': round(installed_kw, 1),
            'usable_kw': round(usable_kw, 1),
            'capacity_at_risk_kw': round(at_risk_kw, 1),
            'capacity_loss_percent': round((at_risk_kw / installed_kw) * 100, 1) if installed_kw else 0,
            'high_or_critical_assets': sum(1 for t in thermal_results if t.risk_level in {'HIGH', 'CRITICAL'}),
            'throughput_at_risk_kwh': round(throughput_at_risk, 1),
            'sessions_affected_estimate': round(sessions_affected, 1),
            'revenue_at_risk_usd_estimate': round(revenue_at_risk, 2),
        },
        'actions': [a.model_dump() for a in actions],
        'agent_trace': [t.model_dump() for t in trace],
        'agent_explanation': explanation,
        'agent_explanation_mode': explanation_mode,
        'model': {
            'label': thermal_results[0].model_name if thermal_results else None,
            'disclaimer': thermal_results[0].model_disclaimer if thermal_results else None,
        },
        'provenance': {
            'charger_locations': 'Public EVgo station pages / DCFC Tracker; see data/source_notes.md',
            'temperature': 'FortyGuard when live snapshot exists; otherwise explicit simulated demo field',
            'capacity': 'Model estimate using public-reference sensitivity curve',
            'agent_actions': 'Demonstrated recommendations only; no physical charger control',
        },
    }
