from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False)
    country = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())