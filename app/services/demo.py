from __future__ import annotations

import math
from typing import Any


def build_demo_heatmap(pilot: dict[str, Any], nx: int = 12, ny: int = 5) -> dict[str, Any]:
    """Generate an explicitly simulated thermal field for UI development only."""
    coords = pilot['polygon_aoi']['features'][0]['geometry']['coordinates'][0]
    lons = [p[0] for p in coords]
    lats = [p[1] for p in coords]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    dx = (max_lon - min_lon) / nx
    dy = (max_lat - min_lat) / ny
    features = []
    temps = []
    tile_id = 0

    for y in range(ny):
        for x in range(nx):
            x0, x1 = min_lon + x * dx, min_lon + (x + 1) * dx
            y0, y1 = min_lat + y * dy, min_lat + (y + 1) * dy
            # Smooth west-east heat gradient plus a small central hot spot.
            east_factor = x / max(1, nx - 1)
            hot_spot = math.exp(-(((x - 7.5) / 2.5) ** 2 + ((y - 2.0) / 1.5) ** 2))
            temp = 44.4 + 1.5 * east_factor + 1.1 * hot_spot
            temp = round(temp, 3)
            temps.append(temp)
            features.append({
                'type': 'Feature',
                'id': str(tile_id),
                'properties': {
                    'tile_id': tile_id,
                    'average_temperature': temp,
                    'min_temperature': temp,
                    'max_temperature': temp,
                    'source': 'simulated_demo',
                },
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]],
                },
            })
            tile_id += 1

    mean = sum(temps) / len(temps)
    return {
        'type': 'FeatureCollection',
        'features': features,
        'thermocharge_metadata': {
            'source': 'simulated_demo',
            'warning': 'Synthetic heatmap for UI development. Replace with real FortyGuard output before submission.',
            'temperature_stats': {
                'minimum': min(temps),
                'maximum': max(temps),
                'mean': mean,
            },
        },
    }
