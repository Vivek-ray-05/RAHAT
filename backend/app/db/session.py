from sqlmodel import SQLModel, Session, create_engine

from app.config import settings

# SQLAlchemy's default pool (5 + 10 overflow = 15 connections) was
# found too small under real concurrent load -- a 100-request burst
# to one backend process exhausted it and started timing out requests
# (found via an actual load test, not by inspection). 20 + 20 gives
# headroom per process; with two replicas sharing one Postgres that's
# up to 80 connections, comfortably under Postgres's default
# max_connections=100.
engine = create_engine(settings.DATABASE_URL, echo=False, pool_size=20, max_overflow=20)


def init_db() -> None:
    """Create tables from SQLModel metadata. Used for local dev/tests only —
    real deployments should rely on Alembic migrations instead."""
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
