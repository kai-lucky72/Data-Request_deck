from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass  # Leave the base class empty so child models can define their own table metadata and behaviors.