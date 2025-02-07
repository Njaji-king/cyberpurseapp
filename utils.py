import pandas as pd
from datetime import datetime, timedelta
from models import get_db, NewsArticle, SecurityRecommendation
from sqlalchemy import desc
from collections import Counter

def save_to_db(news_items: list) -> None:
    """Save news items to database."""
    db = next(get_db())
    try:
        for item in news_items:
            # Check if article already exists
            existing = db.query(NewsArticle).filter_by(url=item['url']).first()
            if not existing:
                article = NewsArticle(
                    title=item['title'],
                    url=item['url'],
                    source=item['source'],
                    summary=item['summary'],
                    category=item.get('category', 'Uncategorized'),
                    region=item.get('region', 'Global'),
                    threat_type=item.get('threat_type', 'Other')
                )
                db.add(article)
        db.commit()
    except Exception as e:
        print(f"Error saving to database: {str(e)}")
        db.rollback()
    finally:
        db.close()

def load_news_from_db() -> pd.DataFrame:
    """Load news from database."""
    db = next(get_db())
    try:
        # Get articles from last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        articles = db.query(NewsArticle)\
            .filter(NewsArticle.created_at >= cutoff)\
            .order_by(desc(NewsArticle.created_at))\
            .all()

        if not articles:
            return pd.DataFrame()

        news_data = [article.to_dict() for article in articles]
        return pd.DataFrame(news_data)
    except Exception as e:
        print(f"Error loading from database: {str(e)}")
        return pd.DataFrame()
    finally:
        db.close()

def get_security_recommendations() -> list:
    """Get current security recommendations."""
    db = next(get_db())
    try:
        recommendations = db.query(SecurityRecommendation)\
            .order_by(desc(SecurityRecommendation.created_at))\
            .limit(3)\
            .all()
        return [rec.to_dict() for rec in recommendations]
    except Exception as e:
        print(f"Error loading recommendations: {str(e)}")
        return []
    finally:
        db.close()

def get_trending_threats(df: pd.DataFrame) -> list:
    """Get trending threats from recent news."""
    if df.empty:
        return []

    threat_counts = Counter(df['threat_type'].dropna())
    return [{"threat": threat, "count": count} 
            for threat, count in threat_counts.most_common(3)]