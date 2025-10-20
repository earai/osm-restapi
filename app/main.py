from fastapi import Body
from typing import Dict, Any
from fastapi import FastAPI, Query
import requests
import sys

app = FastAPI()
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def overpass_to_geojson(data):
    features = []
    for element in data.get("elements", []):
        if element["type"] == "node":
            geometry = {
                "type": "Point",
                "coordinates": [element["lon"], element["lat"]]
            }
        elif element["type"] == "way" and "geometry" in element:
            geometry = {
                "type": "LineString",
                "coordinates": [[pt["lon"], pt["lat"]] for pt in element["geometry"]]
            }
        else:
            continue

        features.append({
            "type": "Feature",
            "properties": element.get("tags", {}),
            "geometry": geometry
        })

    return {"type": "FeatureCollection", "features": features}


@app.get("/osm")
def get_osm(
    key: str = Query("amenity"),
    value: str = Query("cafe"),
    bbox: str = Query("40.730610,-73.935242,40.750610,-73.915242")
):
    query = f"""
    [out:json];
    node[\"{key}\"=\"{value}\"]({bbox});
    out;
    """
    try:
        response = requests.post(OVERPASS_URL, data=query, timeout=30)
        raw_data = response.json()
        print(raw_data, file=sys.stdout, flush=True)
        return overpass_to_geojson(raw_data)
    except Exception as e:
        return {"error": str(e)}


@app.post("/osm/polygon")
def get_osm_polygon(
    key: str = Query("amenity"),
    value: str = Query("cafe"),
    polygon: Dict[str, Any] = Body(..., description="GeoJSON Polygon object")
):
    try:
        if polygon.get("type") != "Polygon":
            return {"error": "Invalid GeoJSON: must be type Polygon"}
        coords = polygon.get("coordinates", [[]])[0]
        poly_string = " ".join([f"{c[1]} {c[0]}" for c in coords])
        query = f"""
        [out:json];
        node[\"{key}\"=\"{value}\"](poly:"{poly_string}");
        out;
        """
        response = requests.post(OVERPASS_URL, data=query, timeout=60)
        raw_data = response.json()
        print(raw_data, file=sys.stdout, flush=True)
        return overpass_to_geojson(raw_data)
    except Exception as e:
        return {"error": str(e)}

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr, flush=True)
        return {"error": str(e)}
