from typing import Any, List
from pydantic import BaseModel, Field

class Geometry(BaseModel):
    type: str = Field(..., description="Geometry type, e.g. Point, Polygon")
    coordinates: Any

class GeoJSONFeature(BaseModel):
    type: str = Field(default="Feature")
    id: str
    geometry: Geometry
    properties: dict = {}

class GeoJSONFeatureCollection(BaseModel):
    type: str = Field(default="FeatureCollection")
    features: List[GeoJSONFeature]

class OSMRequest(BaseModel):
    bbox: List[float] | None = None
    polygon: List[List[float]] | None = None
