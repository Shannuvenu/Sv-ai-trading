from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (UniqueConstraint("finnhub_id", name="uq_news_finnhub_id"),)

    id = Column(Integer, primary_key=True, index=True)
    finnhub_id = Column(BigInteger, nullable=True, index=True)
    category = Column(String(20), nullable=False, index=True)  # "company" | "market"
    symbol = Column(String(20), nullable=True, index=True)
    headline = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String(120), nullable=True)
    url = Column(String(1000), nullable=True)
    image_url = Column(String(1000), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())