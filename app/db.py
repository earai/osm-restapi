import os
from typing import Generator
from sqlmodel import SQLModel, create_engine
from sqlmodel import Session
from sqlalchemy import text


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/osm")

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

def init_db() -> None:
    """Initialize DB: enable PostGIS extension and create tables."""
    from app.models import OSMCache
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session."""
    with Session(engine) as session:
        yield session
