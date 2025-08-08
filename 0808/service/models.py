# service/models.py
from sqlalchemy import Column, Integer, String, DateTime, func
from config.db import Base

class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    txt = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    path = Column(String(500))
    created_at = Column(DateTime, server_default=func.current_timestamp())
