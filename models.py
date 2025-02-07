from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from datetime import datetime

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    source = Column(String(100), nullable=False)
    region = Column(String(100), default='Global')  # Added region field
    summary = Column(Text)
    category = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    threat_type = Column(String(100))  # New field for threat classification

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "region": self.region,
            "summary": self.summary,
            "category": self.category,
            "threat_type": self.threat_type,
            "created_at": self.created_at.isoformat()
        }

class SecurityRecommendation(Base):
    __tablename__ = "security_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    threat_type = Column(String(100), nullable=False)
    recommendation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "threat_type": self.threat_type,
            "recommendation": self.recommendation,
            "created_at": self.created_at.isoformat()
        }

# Create all tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()