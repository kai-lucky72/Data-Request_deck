from .base import Base

__all__ = ["Base", "engine", "SessionLocal", "get_db"]


def __getattr__(name: str):
    if name in {"engine", "SessionLocal", "get_db"}:
        from .session import SessionLocal, engine, get_db

        return {
            "engine": engine,
            "SessionLocal": SessionLocal,
            "get_db": get_db,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
