from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

class OSMCache(SQLModel, table=True):
    """Cache table for OSM features. Mixed geometry types stored in a single column."""
    id: Optional[int] = Field(default=None, primary_key=True)
    query_key: Optional[str] = Field(default=None, index=True)
    query_value: Optional[str] = Field(default=None, index=True)

    geom: Optional[str] = Field(
        default=None,
        sa_column=Column(Geometry(geometry_type='GEOMETRY', srid=4326))
    )

    properties: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB)
    )

    source: Optional[str] = Field(default="overpass")

    created_at: Optional[str] = Field(
        default=None,
        sa_column=Column(text("TIMESTAMP WITH TIME ZONE DEFAULT now()"))
    )
