import trafilatura
import requests
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
import time
from bs4 import BeautifulSoup

# Expanded cybersecurity news sources
SOURCES = {
    # Original sources
    'Krebs on Security': {'url': 'https://krebsonsecurity.com', 'region': 'North America'},
    'The Hacker News': {'url': 'https://thehackernews.com', 'region': 'Global'},
    'Bleeping Computer': {'url': 'https://www.bleepingcomputer.com', 'region': 'North America'},
    'Security Week': {'url': 'https://www.securityweek.com', 'region': 'North America'},
    'Dark Reading': {'url': 'https://www.darkreading.com', 'region': 'North America'},
    'Threatpost': {'url': 'https://threatpost.com', 'region': 'North America'},
    'CSO Online': {'url': 'https://www.csoonline.com', 'region': 'North America'},
    'Naked Security': {'url': 'https://nakedsecurity.sophos.com', 'region': 'Europe'},

    # Kenyan sources
    'Kenya Cybersecurity Report': {'url': 'https://www.serianu.com/blog', 'region': 'Kenya'},
    'Kenya Tech News': {'url': 'https://techweez.com/category/security', 'region': 'Kenya'},
    'Business Daily Security': {'url': 'https://www.businessdailyafrica.com/bd/corporate/technology', 'region': 'Kenya'},
    'The Standard Tech': {'url': 'https://www.standardmedia.co.ke/tech', 'region': 'Kenya'},

    # Additional global sources
    'ZDNet Security': {'url': 'https://www.zdnet.com/security', 'region': 'Global'},
    'Infosecurity Magazine': {'url': 'https://www.infosecurity-magazine.com', 'region': 'Europe'},
    'SC Magazine': {'url': 'https://www.scmagazine.com', 'region': 'North America'},
    'The Register Security': {'url': 'https://www.theregister.com/security', 'region': 'Europe'},
    'Cyber Scoop': {'url': 'https://www.cyberscoop.com', 'region': 'North America'},
    'The Record': {'url': 'https://therecord.media', 'region': 'Global'},
    'IT Security Guru': {'url': 'https://www.itsecurityguru.org', 'region': 'Europe'},
    'Security Affairs': {'url': 'https://securityaffairs.com', 'region': 'Europe'},

    # Regional sources
    'The Stack Asia': {'url': 'https://thestack.technology/category/security', 'region': 'Asia'},
    'Security Brief Asia': {'url': 'https://securitybrief.asia', 'region': 'Asia'},
    'IT News Africa': {'url': 'https://www.itnewsafrica.com/category/security', 'region': 'Africa'}
}

def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    return " ".join(text.split())

def scrape_article(url: str) -> str:
    """Scrape article content using trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded)
        return clean_text(text)
    except Exception as e:
        print(f"Error scraping article {url}: {str(e)}")
        return ""

def extract_url(element) -> str:
    """Safely extract URL from an element."""
    if isinstance(element, str):
        return element
    elif hasattr(element, 'get'):
        return element.get('href', '')
    return ''

def scrape_source(source_name: str, source_info: dict) -> List[Dict]:
    """Generic scraper for a news source."""
    articles = []
    try:
        response = requests.get(source_info['url'], timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Common article selectors
        selectors = [
            'article', 
            '.post',
            '.article',
            '.news-item',
            '.story',
            '.entry'
        ]

        # Try different selectors until we find articles
        for selector in selectors:
            articles_elements = soup.select(selector)
            if articles_elements:
                for article in articles_elements[:5]:
                    # Try different title selectors
                    title_element = (
                        article.select_one('h1 a') or 
                        article.select_one('h2 a') or
                        article.select_one('h3 a') or
                        article.select_one('.title a') or
                        article.select_one('.headline a')
                    )

                    if title_element:
                        url = extract_url(title_element)
                        if url and isinstance(url, str):
                            if not url.startswith('http'):
                                url = source_info['url'] + url

                            articles.append({
                                'title': title_element.text.strip(),
                                'url': url,
                                'source': source_name,
                                'region': source_info['region'],
                                'summary': scrape_article(url)
                            })

                if articles:  # If we found articles, break the loop
                    break

    except Exception as e:
        print(f"Error scraping {source_name}: {str(e)}")

    return articles

def scrape_all_sources() -> List[Dict]:
    """Scrape all sources in parallel."""
    all_articles = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_source = {
            executor.submit(scrape_source, name, info): name 
            for name, info in SOURCES.items()
        }

        for future in future_to_source:
            try:
                articles = future.result()
                if articles:
                    all_articles.extend(articles)
            except Exception as e:
                print(f"Error in scraper {future_to_source[future]}: {str(e)}")

    return all_articles