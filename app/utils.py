from shapely.geometry import shape

def feature_to_wkt(feature: dict) -> str:
    """
    Convert a GeoJSON feature to WKT using shapely.
    """
    geom = feature.get("geometry")
    if not geom:
        raise ValueError("Feature missing geometry")
    shapely_geom = shape(geom)
    return shapely_geom.wkt