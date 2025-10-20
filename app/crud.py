from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import OSMCache
from app.utils import feature_to_wkt


def is_area_covered(session: Session, polygon_wkt: str) -> bool:
    """
    Checks if cached features already fully cover the requested polygon area.
    """
    # Union all cached geometries and check coverage
    union_geom = session.query(func.ST_Union(OSMCache.geometry)).scalar()
    if not union_geom:
        return False
    return session.query(func.ST_Covers(union_geom, func.ST_GeomFromText(polygon_wkt, 4326))).scalar()


def get_cached_features(session: Session, polygon_wkt: str):
    """
    Get cached features intersecting a polygon.
    """
    return session.query(OSMCache).filter(
        func.ST_Intersects(OSMCache.geometry, func.ST_GeomFromText(polygon_wkt, 4326))
    ).all()


def insert_features(session: Session, features: list):
    """
    Insert GeoJSON features into cache.
    """
    for feature in features:
        try:
            geometry_wkt = feature_to_wkt(feature)
            properties = feature.get("properties", {})
            osm_id = str(feature.get("id"))
            osm_type = feature.get("type", "unknown")

            cache_item = OSMCache(
                osm_id=osm_id,
                osm_type=osm_type,
                geometry=func.ST_GeomFromText(geometry_wkt, 4326),
                properties=properties
            )
            session.add(cache_item)
        except Exception as e:
            print(f"Skipping feature due to error: {e}")
    session.commit()
