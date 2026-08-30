from __future__ import annotations

from typing import Any

from shapely.geometry import Point, shape


def feature_temperature(feature: dict[str, Any]) -> float | None:
    props = feature.get('properties', {})
    for key in ('average_temperature', 'temperature', 'value'):
        value = props.get(key)
        if value is not None:
            return float(value)
    return None


def match_point_to_heatmap(latitude: float, longitude: float, geojson: dict[str, Any]) -> dict[str, Any] | None:
    """Return the GeoJSON feature containing the point, falling back to nearest centroid."""
    point = Point(longitude, latitude)
    features = geojson.get('features', [])

    for feature in features:
        geom = shape(feature['geometry'])
        if geom.contains(point) or geom.touches(point):
            return feature

    nearest: tuple[float, dict[str, Any]] | None = None
    for feature in features:
        geom = shape(feature['geometry'])
        distance = geom.centroid.distance(point)
        if nearest is None or distance < nearest[0]:
            nearest = (distance, feature)
    return nearest[1] if nearest else None


def bounds_from_polygon(feature_collection: dict[str, Any]) -> list[list[float]]:
    coords = feature_collection['features'][0]['geometry']['coordinates'][0]
    lons = [p[0] for p in coords]
    lats = [p[1] for p in coords]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]
