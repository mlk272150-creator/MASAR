import os
from pathlib import Path
from typing import Generator

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

if load_dotenv is not None:
    load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/masar_db",
)

Base = declarative_base()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "backend" / "masar.db"
database_url = (
    os.getenv("MASAR_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
)
if database_url.startswith("postgres://"):
    database_url = f"postgresql://{database_url.removeprefix('postgres://')}"
database_url_parts = make_url(database_url)
if database_url_parts.drivername == "postgresql":
    database_url_parts = database_url_parts.set(drivername="postgresql+psycopg2")

if database_url_parts.get_backend_name() == "sqlite":
    sqlite_path = database_url_parts.database
    if sqlite_path and sqlite_path != ":memory:":
        resolved_sqlite_path = Path(sqlite_path)
        if not resolved_sqlite_path.is_absolute():
            resolved_sqlite_path = (PROJECT_ROOT / resolved_sqlite_path).resolve()
        resolved_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        database_url_parts = database_url_parts.set(database=str(resolved_sqlite_path))

DATABASE_URL = database_url_parts.render_as_string(hide_password=False)
engine_options = {"pool_pre_ping": True, "future": True}
if database_url_parts.get_backend_name() == "sqlite":
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    **engine_options,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
