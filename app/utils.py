from shapely.geometry import shape, mapping
from shapely import wkt
import json

def feature_to_wkt(feature: dict) -> str:
    """Convert a GeoJSON feature to WKT string for insertion into PostGIS."""
    geom = feature.get("geometry")
    if not geom:
        return None
    shapely_geom = shape(geom)
    return shapely_geom.wkt
