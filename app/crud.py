from typing import List, Optional
from sqlmodel import Session
from sqlalchemy import text
import json

def is_area_covered(session: Session, aoi_wkt: str, key: Optional[str], value: Optional[str]) -> bool:
    """Return True if the union of cached geometries for this key/value covers the AOI."""
    print("I am in crud is_area_covered")
    print(f"Checking area coverage for AOI: {aoi_wkt}, key: {key}, value: {value}")
    params = {"aoi": aoi_wkt}
    where_clause = ""
    if key is not None:
        where_clause += " AND query_key = :k"
        params["k"] = key
    if value is not None:
        where_clause += " AND query_value = :v"
        params["v"] = value

    sql = f"""
    SELECT CASE WHEN ST_Covers(ST_Union(geom), ST_GeomFromText(:aoi,4326)) IS NULL THEN false
                ELSE ST_Covers(ST_Union(geom), ST_GeomFromText(:aoi,4326)) END as covers
    FROM osm_cache
    WHERE 1=1 {where_clause}
    """

    result = session.execute(text(sql), params).first()
    if not result:
        return False
    return bool(result[0])


def get_cached_features_intersecting(session: Session, aoi_wkt: str, key: Optional[str], value: Optional[str]) -> dict:
    """Return a GeoJSON FeatureCollection of cached features that intersect the AOI."""
    params = {"aoi": aoi_wkt}
    where_clause = ""
    if key is not None:
        where_clause += " AND query_key = :k"
        params["k"] = key
    if value is not None:
        where_clause += " AND query_value = :v"
        params["v"] = value

    sql = f"""
    SELECT id, ST_AsGeoJSON(geom) as geom_json, properties
    FROM osm_cache
    WHERE ST_Intersects(geom, ST_GeomFromText(:aoi,4326)) {where_clause}
    """

    rows = session.execute(text(sql), params).all()
    features = []
    for r in rows:
        geom_json = json.loads(r[1]) if r[1] else None
        props = r[2] or {}
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": geom_json
        })
    return {"type": "FeatureCollection", "features": features}


def insert_features(session: Session, features: List[dict], key: Optional[str], value: Optional[str]) -> None:
    """Insert GeoJSON features into osm_cache. Uses ST_GeomFromGeoJSON for geometry."""

    insert_sql = text(
        "INSERT INTO osm_cache (query_key, query_value, geom, properties) "
        "VALUES (:k, :v, ST_SetSRID(ST_GeomFromGeoJSON(:geojson),4326), :props)"
    )
    for feat in features:
        geom = feat.get("geometry")
        props = feat.get("properties") or {}
        if not geom:
            continue
        geojson_text = json.dumps(geom)
        params = {"k": key, "v": value, "geojson": geojson_text, "props": json.dumps(props)}

        session.execute(insert_sql, params)
    session.commit()
