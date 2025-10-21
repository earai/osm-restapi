import os
import sys
import osm2geojson
from typing import Any

import requests
from fastapi import FastAPI, Query, Body, Depends, HTTPException
from sqlmodel import Session
from shapely.geometry import shape

from app.db import init_db, get_session
from app import crud

app = FastAPI(title="OSM FastAPI with PostGIS Cache")

# Overpass API endpoint
OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")


# -------------------------------------------------------
# 🧭 Initialize Database on Startup
# -------------------------------------------------------
@app.on_event("startup")
def on_startup():
    print("🚀 Initializing database and creating tables…", flush=True)
    try:
        init_db()
        print("✅ Database initialization complete.", flush=True)
    except Exception as e:
        print(f"❌ Database initialization failed: {e}", file=sys.stderr, flush=True)

def overpass_to_geojson(osm_json):
    return osm2geojson.json2geojson(osm_json)
# -------------------------------------------------------

# -------------------------------------------------------
# 🟡 Polygon Road Endpoint
# -------------------------------------------------------
@app.post("/osm/roads/polygon")
def get_osm_roads_polygon(
    polygon: dict = Body(..., description="GeoJSON Polygon object"),
    session: Session = Depends(get_session),
):
    """
    Fetch OSM road features (highway=*) within a GeoJSON polygon,
    cache them in PostGIS, and return as GeoJSON.
    """

    key = "highway"   # fixed for roads
    value = None      # fetch all road types, not just one kind (e.g. 'residential')

    # ✅ Validate polygon input
    if not isinstance(polygon, dict) or polygon.get("type") != "Polygon":
        raise HTTPException(status_code=400, detail="Invalid GeoJSON: must be Polygon")

    try:
        aoi_shape = shape(polygon)
        aoi_wkt = aoi_shape.wkt
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid polygon geometry: {e}")

    # ✅ Check cache coverage
    try:
        if crud.is_area_covered(session, aoi_wkt, key, value):
            return crud.get_cached_features_intersecting(session, aoi_wkt, key, value)
    except Exception as e:
        print(f"Cache check error: {e}", file=sys.stderr, flush=True)

    # ✅ Build Overpass polygon string
    #coords = polygon.get("coordinates", [[]])[0]
    #poly_string = " ".join([f"{c[1]} {c[0]}" for c in coords])

    # ✅ Build Overpass query for highways
    query = f"""
        [out:json];
        (
            way["highway"](poly:"40.7585 -73.9885 40.7585 -73.9855 40.7605 -73.9855 40.7605 -73.9885 40.7585 -73.9885");
        );
        (._;>;);
        out geom;
        """
    try:
        response = requests.post(OVERPASS_URL, data=query, timeout=180)
        response.raise_for_status()
        raw = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overpass request failed: {e}")

    print(f"Fetched roads from Overpass: {len(raw.get('elements', []))} elements", flush=True)

    # ✅ Convert to GeoJSON features
    geojson_features = overpass_to_geojson(raw)

    # ✅ Insert into cache
    try:
        crud.insert_features(session, geojson_features['features'], key, value)
    except Exception as e:
        print(f"Failed to insert road features into cache: {e}", file=sys.stderr, flush=True)
    return geojson_features
    #return {"type": "FeatureCollection", "features": features}