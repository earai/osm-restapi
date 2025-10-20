import os
from fastapi import FastAPI, Query, Body, Depends, HTTPException
import requests
import sys
from sqlmodel import Session
from app.db import init_db, get_session
from app.utils import feature_to_wkt
from app import crud


app = FastAPI(title="OSM FastAPI with PostGIS Cache")
OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")

@app.on_event("startup")
def on_startup():
    init_db()

def bbox_to_polygon_wkt(bbox: str) -> str:
    """Convert bbox string 'lat_min,lon_min,lat_max,lon_max' to polygon WKT."""
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
    # Check cache coverage
    if crud.cached_covers_aoi(session, aoi_wkt, key, value):
        return crud.get_cached_features_intersecting(session, aoi_wkt, key, value)

    # Not fully covered – fetch from Overpass and insert
    query = f"""
    [out:json];
    node[\"{key}\"=\"{value}\"]({bbox});
    way[\"{key}\"=\"{value}\"]({bbox});
    relation[\"{key}\"=\"{value}\"]({bbox});
    out body;
    >;
    out skel qt;
    """
    try:
        response = requests.post(OVERPASS_URL, data=query, timeout=120)
        response.raise_for_status()
        raw = response.json()
        print(raw, file=sys.stdout, flush=True)
        # Convert Overpass raw to GeoJSON features (simple conversion)
        features = []
        for elem in raw.get("elements", []):
            geom = None
            if elem.get("type") == "node":
                geom = {"type": "Point", "coordinates": [elem.get("lon"), elem.get("lat")]}
            elif elem.get("type") == "way" and "geometry" in elem:
                coords = [[pt["lon"], pt["lat"]] for pt in elem["geometry"]]
                geom = {"type": "LineString", "coordinates": coords}
            elif elem.get("type") == "relation":
                # relations are complex; if they have members with geometry in Overpass output
                if "members" in elem:
                    # try to assemble polygons from members where possible (best-effort)
                    polys = []
                    for m in elem["members"]:
                        if m.get("geometry"):
                            pts = [[p["lon"], p["lat"]] for p in m["geometry"]]
                            polys.append(pts)
                    if polys:
                        geom = {"type": "MultiPolygon", "coordinates": [[p] for p in polys]}
            if not geom:
                continue

            features.append({"type": "Feature", "properties": elem.get("tags", {}), "geometry": geom})


# Insert into cache
        crud.insert_features(session, features, key, value)


        return {"type": "FeatureCollection", "features": features}


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/osm/polygon")
def get_osm_polygon(
    key: str = Query("amenity"),
    value: str = Query("cafe"),
    polygon: dict = Body(..., description="GeoJSON Polygon object"),
    session: Session = Depends(get_session),
    ):
    if polygon.get("type") != "Polygon":
        raise HTTPException(status_code=400, detail="Invalid GeoJSON: must be type Polygon")


    # Convert to WKT for spatial queries
    from shapely.geometry import shape
    aoi_wkt = shape(polygon["coordinates"]) if False else None
    # shapely expects the full GeoJSON geometry; use mapping


