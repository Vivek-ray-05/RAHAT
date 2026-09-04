from sqlmodel import SQLModel, Session, create_engine

from app.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)


def init_db() -> None:
    """Create tables from SQLModel metadata. Used for local dev/tests only —
    real deployments should rely on Alembic migrations instead."""
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
