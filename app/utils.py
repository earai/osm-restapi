import sys
import os
import osm2geojson
import requests
from shapely.geometry import shape
from fastapi import HTTPException
from app import crud

OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")

def overpass_to_geojson(osm_json):
    return osm2geojson.json2geojson(osm_json)

def fetch_osm_by_polygon(polygon: dict, key: str, value: str, query_template: str, session):
    # ✅ Validate polygon input
    if not isinstance(polygon, dict) or polygon.get("type") != "Polygon":
        raise HTTPException(status_code=400, detail="Invalid GeoJSON: must be Polygon")

    try:
        aoi_shape = shape(polygon)
        aoi_wkt = aoi_shape.wkt
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid polygon geometry: {e}")

    # ✅ Check cache
    try:
        if crud.is_area_covered(session, aoi_wkt, key, value):
            return crud.get_cached_features_intersecting(session, aoi_wkt, key, value)
    except Exception as e:
        print(f"Cache check error: {e}", file=sys.stderr, flush=True)

    # ✅ Build Overpass query dynamically
    # Convert polygon coordinates into Overpass poly string
    coords = polygon.get("coordinates", [[]])[0]
    poly_str = " ".join([f"{lat} {lon}" for lon, lat in coords])
    query = query_template.format(poly=poly_str)

    # ✅ Send Overpass request
    try:
        response = requests.post(OVERPASS_URL, data=query, timeout=(20, 180))
        response.raise_for_status()
        raw = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overpass request failed: {e}")

    print(f"Fetched {key} features from Overpass: {len(raw.get('elements', []))} elements", flush=True)

    # ✅ Convert and cache
    geojson_features = overpass_to_geojson(raw)
    try:
        crud.insert_features(session, geojson_features["features"], key, value)
    except Exception as e:
        print(f"Failed to insert {key} features into cache: {e}", file=sys.stderr, flush=True)

    return geojson_features
