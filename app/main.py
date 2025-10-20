import os
import sys
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


# -------------------------------------------------------
# 🧮 Helper function: BBOX to WKT polygon
# -------------------------------------------------------
def bbox_to_polygon_wkt(bbox: str) -> str:
    parts = [float(p.strip()) for p in bbox.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must have 4 comma-separated numbers: lat_min,lon_min,lat_max,lon_max")
    lat_min, lon_min, lat_max, lon_max = parts
    coords = [
        (lon_min, lat_min),
        (lon_max, lat_min),
        (lon_max, lat_max),
        (lon_min, lat_max),
        (lon_min, lat_min),
    ]
    pts = ", ".join([f"{c[0]} {c[1]}" for c in coords])
    return f"POLYGON(({pts}))"


# -------------------------------------------------------
# 🌐 Helper: Convert Overpass elements to GeoJSON
# -------------------------------------------------------
def elements_to_features(elements: list) -> list:
    features = []
    for elem in elements:
        geom = None
        if elem.get("type") == "node":
            if elem.get("lon") is None or elem.get("lat") is None:
                continue
            geom = {"type": "Point", "coordinates": [elem.get("lon"), elem.get("lat")]}
        elif elem.get("type") == "way" and "geometry" in elem:
            coords = [[pt["lon"], pt["lat"]] for pt in elem["geometry"] if pt.get("lon") is not None]
            if len(coords) >= 2:
                geom = {"type": "LineString", "coordinates": coords}
        elif elem.get("type") == "relation" and "members" in elem:
            polys = []
            for m in elem["members"]:
                if m.get("geometry"):
                    pts = [[p["lon"], p["lat"]] for p in m["geometry"] if p.get("lon") is not None]
                    if len(pts) >= 3:
                        polys.append(pts)
            if polys:
                geom = {"type": "MultiPolygon", "coordinates": [[p] for p in polys]}
        if not geom:
            continue
        features.append({
            "type": "Feature",
            "id": str(elem.get("id")),
            "properties": elem.get("tags", {}),
            "geometry": geom
        })
    return features


# -------------------------------------------------------
# 🧭 BBOX Endpoint
# -------------------------------------------------------
@app.get("/osm")
def get_osm(
    key: str = Query("amenity"),
    value: str = Query("cafe"),
    bbox: str = Query("40.730610,-73.935242,40.750610,-73.915242"),
    session: Session = Depends(get_session),
):
    try:
        aoi_wkt = bbox_to_polygon_wkt(bbox)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Try cache first
    try:
        if crud.is_area_covered(session, aoi_wkt, key, value):
            return crud.get_cached_features_intersecting(session, aoi_wkt, key, value)
    except Exception as e:
        print(f"Cache check error: {e}", file=sys.stderr, flush=True)

    # Overpass query
    query = f"""
    [out:json];
    node["{key}"="{value}"]({bbox});
    way["{key}"="{value}"]({bbox});
    relation["{key}"="{value}"]({bbox});
    out body;
    >;
    out skel qt;
    """
    print(f"Query: {query}", flush=True)
    headers = {
        "User-Agent": "osm-fastapi/1.0 (https://example.com)",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(OVERPASS_URL,
                             data={"data": query},
                             headers=headers,
                             timeout=120)
    print(f"Status code: {response.status_code}", flush=True)
    print(f"Response headers: {response.headers}", flush=True)
    print(f"Response text (first 300 chars): {response.text[:300]}", flush=True)
    response.raise_for_status()
    raw = response.json()
    print(f"Raw response: {raw}", flush=True)
    print(f"Fetched from Overpass: {len(raw.get('elements', []))} elements", flush=True)

    features = elements_to_features(raw.get("elements", []))
    try:
        crud.insert_features(session, features, key, value)
    except Exception as e:
        print(f"Failed to insert features into cache: {e}", file=sys.stderr, flush=True)

    return {"type": "FeatureCollection", "features": features}


# -------------------------------------------------------
# 🟡 Polygon Endpoint
# -------------------------------------------------------
@app.post("/osm/polygon")
def get_osm_polygon(
    key: str = Query("amenity"),
    value: str = Query("cafe"),
    polygon: dict = Body(..., description="GeoJSON Polygon object"),
    session: Session = Depends(get_session),
):
    # Validate
    if not isinstance(polygon, dict) or polygon.get("type") != "Polygon":
        raise HTTPException(status_code=400, detail="Invalid GeoJSON: must be Polygon")

    try:
        aoi_shape = shape(polygon)
        aoi_wkt = aoi_shape.wkt
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid polygon geometry: {e}")

    # Try cache
    try:
        if crud.is_area_covered(session, aoi_wkt, key, value):
            return crud.get_cached_features_intersecting(session, aoi_wkt, key, value)
    except Exception as e:
        print(f"Cache check error: {e}", file=sys.stderr, flush=True)

    # Overpass polygon string
    coords = polygon.get("coordinates", [[]])[0]
    poly_string = " ".join([f"{c[1]} {c[0]}" for c in coords])
    query = f"""
    [out:json];
    node["{key}"="{value}"](poly:"{poly_string}");
    way["{key}"="{value}"](poly:"{poly_string}");
    relation["{key}"="{value}"](poly:"{poly_string}");
    out body;
    >;
    out skel qt;
    """

    response = requests.post(OVERPASS_URL, data=query, timeout=180)
    response.raise_for_status()
    raw = response.json()
    print(f"Fetched polygon from Overpass: {len(raw.get('elements', []))} elements", flush=True)

    features = elements_to_features(raw.get("elements", []))
    try:
        crud.insert_features(session, features, key, value)
    except Exception as e:
        print(f"Failed to insert polygon features into cache: {e}", file=sys.stderr, flush=True)

    return {"type": "FeatureCollection", "features": features}
