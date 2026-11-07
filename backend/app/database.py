"""
Database engine, session factory, and base model.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# Prefer native C-optimized psycopg2 driver when available for maximum speed and lowest latency.
# Fall back to pure-python pg8000 only if psycopg2 is missing (e.g. serverless environments).
try:
    import psycopg2
    driver = "psycopg2"
except ImportError:
    driver = "pg8000"

connect_args = {}
engine_kwargs = {
    "echo": settings.DEBUG,
}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    if driver == "psycopg2":
        connect_args["connect_timeout"] = 5
    else:
        connect_args["timeout"] = 10
    engine_kwargs.update({
        "pool_size": 15,
        "max_overflow": 10,
        "pool_pre_ping": False,  # Disabled to eliminate 2.5s handshake delay over cloud connection
        "pool_recycle": 1800,
        "pool_use_lifo": True,   # Reuses the most recently used connection (hot connection)
    })

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", f"postgresql+{driver}://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", f"postgresql+{driver}://", 1)

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
