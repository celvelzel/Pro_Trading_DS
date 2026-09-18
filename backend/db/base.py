"""SQLAlchemy declarative base shared by API and worker processes."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all persisted platform models."""

