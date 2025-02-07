import pandas as pd
from openai import OpenAI
import os
import json
from models import SecurityRecommendation, get_db
from collections import Counter

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def classify_article(article: dict) -> dict:
    """Classify a single article using OpenAI."""
    try:
        prompt = f"""
        Title: {article['title']}
        Content: {article['summary'][:1000]}

        Classify this cybersecurity news article into these categories and identify the main threat type.
        Return the response as a JSON object with format:
        {{
            "category": "category_name",
            "threat_type": "main_threat_type"
        }}

        Categories:
        - Malware & Threats
        - Data Breach
        - Vulnerability
        - Privacy
        - Security Research
        - Industry News

        Threat Types:
        - Phishing
        - Ransomware
        - Data Breach
        - Social Engineering
        - Zero-day Vulnerability
        - Supply Chain Attack
        - DDoS
        - Insider Threat
        - Other
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        article['category'] = result.get('category', 'Uncategorized')
        article['threat_type'] = result.get('threat_type', 'Other')
        return article
    except Exception as e:
        print(f"Error classifying article: {str(e)}")
        article['category'] = 'Uncategorized'
        article['threat_type'] = 'Other'
        return article

def generate_recommendations(threat_type: str) -> str:
    """Generate security recommendations for a specific threat type."""
    try:
        prompt = f"""
        Generate practical cybersecurity recommendations to protect against {threat_type} attacks.
        Focus on actionable steps that both individuals and organizations can take.
        Keep it concise but comprehensive (3-5 bullet points).
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating recommendations: {str(e)}")
        return f"Standard protection measures against {threat_type}:\n- Use strong passwords\n- Enable two-factor authentication\n- Keep systems updated\n- Use antivirus software"

def update_recommendations(articles_df: pd.DataFrame) -> None:
    """Update security recommendations based on trending threats."""
    if articles_df.empty:
        return

    try:
        # Get top threats
        threat_counts = Counter(articles_df['threat_type'].dropna())
        top_threats = [threat for threat, _ in threat_counts.most_common(3)]

        if not top_threats:
            return

        db = next(get_db())
        try:
            # Clear old recommendations
            db.query(SecurityRecommendation).delete()

            # Add new recommendations
            for threat in top_threats:
                recommendation = generate_recommendations(threat)
                new_rec = SecurityRecommendation(
                    threat_type=threat,
                    recommendation=recommendation
                )
                db.add(new_rec)

            db.commit()
        except Exception as db_error:
            print(f"Database error in update_recommendations: {str(db_error)}")
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        print(f"Error updating recommendations: {str(e)}")

def classify_news(articles: list) -> pd.DataFrame:
    """Classify all news articles and return as DataFrame."""
    if not articles:
        return pd.DataFrame()

    classified_articles = []
    for article in articles:
        classified_article = classify_article(article)
        classified_articles.append(classified_article)

    df = pd.DataFrame(classified_articles)
    update_recommendations(df)
    return df