from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy import text
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@db:5432/osm_cache"
)

engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    """
    Initialize database, ensure PostGIS extension exists, and create tables.
    """
    with engine.connect() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))
        conn.commit()
    SQLModel.metadata.create_all(engine)

def get_session():
    """
    Dependency for FastAPI routes.
    """
    with Session(engine) as session:
        yield session
