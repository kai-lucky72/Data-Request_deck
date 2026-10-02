from collections.abc import Generator  # Import the Generator type for type hinting the database session generator function.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,Session

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True, # enable pre-ping to check connection are alive before use
    echo=settings.DEBUG #enable SQLAlchemy's SQL query logging for debugging
)
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

def get_db()->Generator[Session, None, None]:
    """Generator function to provide a database session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()