from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# SQLAlchemy engine, built from the constructed PostgreSQL URL
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """
    Base class for all ORM models (SQLAlchemy 2.x style).
    All models in app/models/ should inherit from this class so that
    Alembic can detect them via Base.metadata.
    """

    pass
