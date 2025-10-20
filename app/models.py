from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from datetime import datetime

class OSMCache(SQLModel, table=True):
    __tablename__ = "osm_cache"

    id: Optional[int] = Field(default=None, primary_key=True)
    osm_id: str = Field(index=True)
    osm_type: str = Field(index=True)  # node, way, relation
    geometry: Optional[str] = Field(
        sa_column=Column(Geometry(geometry_type="GEOMETRY", srid=4326))
    )
    properties: Optional[dict] = Field(
        sa_column=Column(JSONB)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
