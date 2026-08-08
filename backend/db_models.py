"""
ORM models.

CaseRecord stores each case as a single JSON blob (`data`), mirroring the
exact dict shape every agent already works with in memory. This keeps the
persistence layer a thin save/restore of `main.CASES` rather than a full
relational redesign — swap for real columns later if querying by field
becomes necessary.
"""
from sqlalchemy import Column, String, Float, JSON
from .database import Base


class CaseRecord(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, index=True)
    created_at = Column(Float, index=True)
    data = Column(JSON, nullable=False)
