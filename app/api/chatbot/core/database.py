"""Shim module re-exporting the infrastructure database implementation."""
from .infrastructure import database as _db  # type: ignore

# expose the same names as the original module expects
SessionLocal = getattr(_db, "SessionLocal", None)
Base = getattr(_db, "Base", None)
def get_db():
    return getattr(_db, "get_db")()

__all__ = ["SessionLocal", "Base", "get_db"]

