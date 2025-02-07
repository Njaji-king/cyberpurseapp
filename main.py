import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from scraper import scrape_all_sources
from classifier import classify_news
from utils import load_news_from_db, save_to_db, get_security_recommendations, get_trending_threats
from threat_map import create_threat_map
import streamlit_folium as st_folium
import time

# Page configuration
st.set_page_config(
    page_title="Cybersecurity News Aggregator",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .threat-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    .news-title {
        color: #1f1f1f;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .news-meta {
        color: #666;
        font-size: 0.9rem;
    }
    .recommendation-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

def initialize_session_state():
    if 'last_update' not in st.session_state:
        st.session_state.last_update = None
    if 'news_data' not in st.session_state:
        st.session_state.news_data = None

def display_header():
    """Display the application header with stats."""
    st.title("🔒 Cybersecurity News Aggregator")
    st.markdown("Real-time cybersecurity news and threat intelligence from global sources")

    if st.session_state.news_data is not None and not st.session_state.news_data.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Active Sources", len(st.session_state.news_data['source'].unique()))
        with col2:
            st.metric("Tracked Threats", len(st.session_state.news_data['threat_type'].unique()))
        with col3:
            if st.session_state.last_update:
                time_diff = datetime.now() - st.session_state.last_update
                minutes_ago = int(time_diff.total_seconds() / 60)
                st.metric("Last Update", f"{minutes_ago} minutes ago")

def display_recommendations():
    """Display security recommendations section."""
    st.markdown("## 🛡️ Security Recommendations")

    if st.session_state.news_data is not None and not st.session_state.news_data.empty:
        col1, col2 = st.columns([1, 2])

        with col1:
            # Show trending threats
            st.markdown("### 📊 Trending Threats")
            trending_threats = get_trending_threats(st.session_state.news_data)
            for threat in trending_threats:
                with st.container():
                    st.markdown(f"""
                    <div class='threat-card'>
                        <h4>{threat['threat']}</h4>
                        <p class='news-meta'>{threat['count']} mentions</p>
                    </div>
                    """, unsafe_allow_html=True)

        with col2:
            # Show recommendations
            st.markdown("### 🔐 Protection Measures")
            recommendations = get_security_recommendations()
            for rec in recommendations:
                with st.expander(f"Protect against {rec['threat_type']}"):
                    st.markdown(f"""
                    <div class='recommendation-card'>
                        {rec['recommendation']}
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("Security recommendations will appear here once news data is loaded.")

def update_news():
    with st.spinner('Fetching latest cybersecurity news...'):
        # Try to load news from database first
        news_df = load_news_from_db()

        if not news_df.empty and st.session_state.last_update is not None:
            if datetime.now() - st.session_state.last_update < timedelta(minutes=30):
                return news_df

        # Scrape fresh news
        news_items = scrape_all_sources()
        if news_items:
            # Classify news using AI
            classified_news = classify_news(news_items)
            # Save to database
            save_to_db(classified_news.to_dict('records'))
            st.session_state.last_update = datetime.now()
            return classified_news
        return pd.DataFrame()

def display_news_article(article):
    """Display a single news article with better styling."""
    st.markdown(f"""
    <div class='threat-card'>
        <a href="{article['url']}" target="_blank" class="news-title">
            {article['title']}
        </a>
        <p class='news-meta'>
            📰 {article['source']} | 🏷️ {article['category']} | ⚠️ {article['threat_type']}
        </p>
        <p>{article['summary'][:300]}...</p>
    </div>
    """, unsafe_allow_html=True)

def display_news_section(filtered_data, title):
    st.markdown(f"### {title} ({len(filtered_data)} articles)")
    for _, article in filtered_data.iterrows():
        display_news_article(article)

def display_threat_map(news_data: pd.DataFrame):
    """Display the interactive threat map section."""
    st.markdown("## 🗺️ Global Threat Map")
    st.markdown("This map shows the geographical distribution of cybersecurity threats with severity indicators.")

    if not news_data.empty:
        # Create and display the map
        threat_map = create_threat_map(news_data)
        st_folium.st_folium(threat_map, width=1200, height=600)

        # Add legend explanation
        st.markdown("""
        ### Map Legend
        - **Marker Size**: Larger markers indicate higher severity threats
        - **Colors**:
          - 🔴 Dark Red: Critical threats (Level 5)
          - 🔴 Red: High-severity threats (Level 4)
          - 🟠 Orange: Medium-severity threats (Level 3)
          - 🔵 Blue: Low-severity threats (Level 2)
          - ⚪ Gray: Informational alerts (Level 1)
        """)
    else:
        st.info("No threat data available for visualization. Please refresh the news feed.")

def main():
    initialize_session_state()

    # Sidebar filters and controls
    st.sidebar.title("Controls & Filters")
    if st.sidebar.button("🔄 Refresh News"):
        st.session_state.news_data = update_news()

    # Main content
    display_header()
    st.markdown("---")

    if st.session_state.news_data is None:
        st.session_state.news_data = update_news()

    # Display recommendations section
    display_recommendations()
    st.markdown("---")

    # Display threat map
    display_threat_map(st.session_state.news_data)
    st.markdown("---")

    # News sections with filters
    if not st.session_state.news_data.empty:
        # Filter controls
        col1, col2, col3 = st.sidebar.columns([1, 1, 1])

        # Region filter
        regions = ['All'] + sorted(st.session_state.news_data['region'].unique().tolist())
        selected_region = st.sidebar.selectbox("🌍 Region", regions)

        # Category filter
        categories = ['All'] + sorted(st.session_state.news_data['category'].unique().tolist())
        selected_category = st.sidebar.selectbox("📁 Category", categories)

        # Search box
        search_query = st.sidebar.text_input("🔍 Search News", "")

        # Apply filters
        filtered_data = st.session_state.news_data.copy()
        if selected_region != 'All':
            filtered_data = filtered_data[filtered_data['region'] == selected_region]
        if selected_category != 'All':
            filtered_data = filtered_data[filtered_data['category'] == selected_category]
        if search_query:
            filtered_data = filtered_data[
                filtered_data['title'].str.contains(search_query, case=False) |
                filtered_data['summary'].str.contains(search_query, case=False)
            ]

        # Display news sections
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("## 🇰🇪 Kenyan Cybersecurity Updates")
            kenyan_news = filtered_data[filtered_data['region'] == 'Kenya']
            if not kenyan_news.empty:
                display_news_section(kenyan_news, "Latest Kenyan Security News")
            else:
                st.info("No Kenyan cybersecurity news available at the moment.")

        with col2:
            st.markdown("## 🌍 Global Cybersecurity News")
            global_news = filtered_data[filtered_data['region'] != 'Kenya']
            if not global_news.empty:
                display_news_section(global_news, "Latest Global Security News")
            else:
                st.info("No global cybersecurity news available at the moment.")

    else:
        st.error("Unable to fetch news. Please try refreshing.")

    # Footer
    st.markdown("---")
    st.markdown("Powered by AI - Aggregating news from top cybersecurity sources")

if __name__ == "__main__":
    main()