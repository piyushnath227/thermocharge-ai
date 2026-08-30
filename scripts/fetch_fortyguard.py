from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.fortyguard import FortyGuardClient, FortyGuardError, save_json
from app.services.geospatial import feature_temperature, match_point_to_heatmap


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


async def fetch_one(client: FortyGuardClient, pilot: dict, chargers: list[dict], date: str, time: str) -> dict:
    """Fetch one heatmap + one env_params-per-site snapshot for a single date/time.
    This is the exact working request/response logic from the original script,
    just extracted so it can be called once per replay time point."""
    heatmap_payload = {
        'polygon_aoi': pilot['polygon_aoi'],
        'date_time': {
            'start_date': date,
            'start_time': time,
            'filter_type': pilot['fortyguard']['filter_type'],
        },
        'granularity': pilot['fortyguard']['granularity_m'],
        'analytic_type': pilot['fortyguard'].get('analytic_type', 'tcm'),
    }

    print(f'  [{time}] heatmap request...')
    heatmap_response = await client.heatmap(heatmap_payload)
    raw_heatmap_path = settings.data_dir / 'live' / f'fortyguard_heatmap_raw_{time.replace(":", "")}.json'
    save_json(raw_heatmap_path, heatmap_response)
    heatmap = heatmap_response['data']['result']['map_data']
    print(f'  [{time}] heatmap OK: {len(heatmap.get("features", []))} tiles')

    sites: dict[str, dict] = {}
    for charger in chargers:
        sites.setdefault(charger['site_id'], charger)

    env_by_site = {}
    warnings: list[str] = []
    for site_id, charger in sites.items():
        feature = match_point_to_heatmap(charger['latitude'], charger['longitude'], heatmap)
        temp = feature_temperature(feature) if feature else None
        if temp is None:
            msg = f'{site_id}: could not match to a heatmap tile; env_params skipped.'
            print(f'  [{time}] WARNING: {msg}')
            warnings.append(msg)
            continue
        payload = {
            'latitude': charger['latitude'],
            'longitude': charger['longitude'],
            'temperature': temp,
            'date_time': {'start_date': date, 'start_time': time, 'filter_type': 1},
            'analysis': ['relative_humidity_percent', 'solar_irradiance', 'heat_index_celsius'],
        }
        print(f'  [{time}] env_params for {site_id} ({temp:.1f}°C)...')
        try:
            env_response = await client.env_params(payload)
        except FortyGuardError as exc:
            msg = f'{site_id}: env_params did not complete ({exc}); this site has no environmental data for {time}.'
            print(f'  [{time}] WARNING: {msg}')
            warnings.append(msg)
            continue
        save_json(settings.data_dir / 'live' / f'env_{site_id}_raw_{time.replace(":", "")}.json', env_response)
        location = env_response['data']['result']['locations'][0]
        params = location.get('parameters', {})
        env_by_site[site_id] = {
            'temperature_c': location.get('temperature', temp),
            'relative_humidity_percent': (params.get('relative_humidity_percent') or [None])[0],
            'heat_index_celsius': (params.get('heat_index_celsius') or [None])[0],
            'solar_irradiance': (location.get('solar_irradiance') or {}).get('clear_sky', {}),
        }

    return {
        'source': 'fortyguard',
        'analysis_time': f'{date}T{time}:00-07:00',
        'time_local': time,
        'heatmap_activity_id': heatmap_response['data']['activity_id'],
        'heatmap': heatmap,
        'heatmap_stats': heatmap_response['data']['result'].get('stats_data'),
        'env_by_site': env_by_site,
        'warning': '; '.join(warnings) if warnings else None,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description='Fetch real FortyGuard data for the Phoenix pilot.')
    parser.add_argument('--date', help='YYYY-MM-DD override. Defaults to pilot analysis date.')
    parser.add_argument('--time', help='Single HH:MM. Overrides replay mode; fetches just this one point.')
    parser.add_argument('--times', help='Comma-separated HH:MM list. Defaults to pilot replay_times_local.')
    parser.add_argument('--dry-run', action='store_true', help='Print the planned API call count and exit — spends zero credits.')
    parser.add_argument(
        '--force', action='store_true',
        help='Re-fetch every time point even if a cached frame already exists in data/live/ (costs credits again).',
    )
    args = parser.parse_args()

    pilot = load(settings.data_dir / 'pilot.json')
    chargers = load(settings.data_dir / 'chargers.json')
    date = args.date or pilot['analysis_date']

    if args.time:
        times = [args.time]
    elif args.times:
        times = [t.strip() for t in args.times.split(',')]
    else:
        times = pilot.get('replay_times_local', [pilot['analysis_time_local']])

    num_sites = len({c['site_id'] for c in chargers})
    total_calls = len(times) * (1 + num_sites)
    print(f'Plan: {len(times)} time point(s) x (1 heatmap + {num_sites} env_params) = {total_calls} total FortyGuard calls.')
    print(f'Times: {times}')
    if args.dry_run:
        print('Dry run only — no requests sent.')
        return

    live_dir = settings.data_dir / 'live'
    frames_by_time: dict[str, dict] = {}
    pending: list[str] = []
    for time in times:
        cache_path = live_dir / f'frame_{time.replace(":", "")}.json'
        if cache_path.exists() and not args.force:
            frames_by_time[time] = json.loads(cache_path.read_text(encoding='utf-8'))
        else:
            pending.append(time)

    if frames_by_time:
        print(
            f'Reusing {len(frames_by_time)} already-fetched time point(s) from data/live/ '
            f'(pass --force to re-fetch and re-spend credits): {list(frames_by_time)}'
        )

    if pending:
        api_key = os.getenv('FORTYGUARD_API_KEY')
        if not api_key:
            raise SystemExit('FORTYGUARD_API_KEY is missing. Put it in .env or set it in your terminal.')

        client = FortyGuardClient(api_key)
        for time in pending:
            print(f'\n--- Fetching {date} {time} ---')
            try:
                frame = await fetch_one(client, pilot, chargers, date, time)
            except FortyGuardError as exc:
                print(f'  [{time}] SKIPPED — heatmap could not be completed: {exc}')
                print(f'  [{time}] Nothing cached for this time; re-run the script later to retry just this one.')
                continue
            save_json(live_dir / f'frame_{time.replace(":", "")}.json', frame)
            frames_by_time[time] = frame

    frames = [frames_by_time[time] for time in times if time in frames_by_time]
    missing_times = [time for time in times if time not in frames_by_time]
    if missing_times:
        print(f'\nWARNING: no data for {missing_times} — re-run the script to retry just these.')
    if not frames:
        raise SystemExit('No time points were successfully fetched. Nothing to save.')

    # Always keep snapshot.json pointing at the pilot's designated headline
    # time (the documented real peak), so the existing single-snapshot
    # dashboard keeps working exactly as before, with zero code changes.
    headline_time = pilot['analysis_time_local']
    headline_frame = next((f for f in frames if f['time_local'] == headline_time), frames[-1])
    save_json(settings.data_dir / 'live' / 'snapshot.json', headline_frame)

    if len(frames) > 1:
        save_json(settings.data_dir / 'live' / 'replay_snapshot.json', {'date': date, 'frames': frames})
        print(f'\nSaved {len(frames)}-frame replay to data/live/replay_snapshot.json')

    print('\nSUCCESS ✅')
    print('Restart the app. Single-snapshot dashboard uses the headline time automatically.')
    print('If a replay file was saved, /api/replay will serve it once the corresponding route is added.')


if __name__ == '__main__':
    asyncio.run(main())