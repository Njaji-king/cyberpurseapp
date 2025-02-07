import folium
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderRateLimited
import numpy as np
from datetime import datetime, timedelta
import time
from functools import lru_cache

# Cache coordinates for 24 hours
@lru_cache(maxsize=128)
def get_coordinates(region: str) -> tuple:
    """Get coordinates for a given region with caching."""
    # Default coordinates for common regions
    default_coords = {
        'Kenya': (-1.2921, 36.8219),  # Nairobi
        'Global': (0, 0),             # Default center point
        'USA': (37.0902, -95.7129),
        'UK': (51.5074, -0.1278),
        'EU': (50.8503, 4.3517),      # Brussels
        'Africa': (0.0236, 37.9062),
        'Asia': (34.0479, 100.6197),
        'Europe': (54.5260, 15.2551),
        'North America': (54.5260, -105.2551),
        'South America': (-8.7832, -55.4915),
        'Australia': (-25.2744, 133.7751),
    }

    # Return default coordinates if available
    if region in default_coords:
        return default_coords[region]

    try:
        geolocator = Nominatim(user_agent="cybersecurity_news_app")
        # Add delay between requests to respect rate limits
        time.sleep(1)
        location = geolocator.geocode(region)
        if location:
            return (location.latitude, location.longitude)
    except GeocoderRateLimited:
        print(f"Rate limit exceeded for region: {region}")
        time.sleep(2)  # Wait longer on rate limit
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Geocoding error for region {region}: {str(e)}")
    except Exception as e:
        print(f"Unexpected error for region {region}: {str(e)}")

    # Return global coordinates as fallback
    return default_coords.get('Global', (0, 0))

def calculate_threat_severity(threat_type: str, category: str = None) -> int:
    """Calculate severity score for threat types with category context."""
    # Base severity scores for threat types
    severity_mapping = {
        'Ransomware': 5,
        'Zero-day Vulnerability': 5,
        'Data Breach': 4,
        'Supply Chain Attack': 4,
        'Phishing': 3,
        'Social Engineering': 3,
        'DDoS': 2,
        'Insider Threat': 3,
        'APT': 5,
        'Malware': 4,
        'Other': 1
    }

    # Category modifiers
    category_modifiers = {
        'Critical Infrastructure': 1,  # Increase severity by 1
        'Government': 1,
        'Healthcare': 1,
        'Financial': 1,
    }

    # Get base severity
    base_severity = severity_mapping.get(threat_type, 1)

    # Apply category modifier if applicable
    if category:
        modifier = category_modifiers.get(category, 0)
        return min(5, base_severity + modifier)

    return base_severity

def create_threat_map(news_data: pd.DataFrame) -> folium.Map:
    """Create an interactive threat map from news data."""
    # Initialize the map centered on Kenya
    m = folium.Map(location=(-1.2921, 36.8219), zoom_start=3)

    if news_data.empty:
        return m

    # Process each threat
    processed_regions = set()  # Track processed regions to avoid duplicates
    region_threats = {}  # Collect threats by region for aggregation

    # First pass: collect and aggregate threats by region
    for _, article in news_data.iterrows():
        region = article['region']

        if region not in region_threats:
            region_threats[region] = {
                'threats': [],
                'max_severity': 0,
                'count': 0
            }

        severity = calculate_threat_severity(article['threat_type'], article.get('category'))
        region_threats[region]['threats'].append({
            'title': article['title'],
            'threat_type': article['threat_type'],
            'severity': severity,
            'source': article['source'],
            'url': article['url']
        })
        region_threats[region]['max_severity'] = max(
            region_threats[region]['max_severity'],
            severity
        )
        region_threats[region]['count'] += 1

    # Second pass: create markers for each region
    for region, data in region_threats.items():
        coords = get_coordinates(region)
        max_severity = data['max_severity']

        # Color based on maximum severity in the region
        color = {
            1: 'lightgray',
            2: 'blue',
            3: 'orange',
            4: 'red',
            5: 'darkred'
        }.get(max_severity, 'lightgray')

        # Create detailed popup content
        threat_list = ''.join([
            f"""<li>
                <b>{threat['threat_type']}</b> (Severity: {threat['severity']}/5)<br>
                {threat['title'][:50]}...<br>
                <small>Source: {threat['source']}</small><br>
                <a href='{threat['url']}' target='_blank'>Read More</a>
            </li>"""
            for threat in sorted(
                data['threats'],
                key=lambda x: x['severity'],
                reverse=True
            )
        ])

        popup_html = f"""
        <div style='width: 300px'>
            <h4>🌍 {region}</h4>
            <p><b>Active Threats:</b> {data['count']}</p>
            <p><b>Maximum Severity:</b> {max_severity}/5</p>
            <hr>
            <h5>Recent Threats:</h5>
            <ul style='padding-left: 20px'>
                {threat_list}
            </ul>
        </div>
        """

        # Add marker to map
        folium.CircleMarker(
            location=coords,
            radius=10 + (max_severity * 2),  # Size based on severity
            popup=folium.Popup(popup_html, max_width=350),
            color=color,
            fill=True,
            fillOpacity=0.7
        ).add_to(m)

        # Add a visible label for the region
        folium.map.Marker(
            coords,
            icon=folium.DivIcon(
                html=f"""
                <div style='text-align: center; color: {color};'>
                    <strong>{region}</strong>
                </div>
                """
            )
        ).add_to(m)

    # Add legend
    legend_html = """
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; background-color: white;
                padding: 10px; border: 2px solid grey; border-radius: 5px">
        <h4>Threat Severity</h4>
        <p><i class="fa fa-circle" style="color:darkred"></i> Critical (5)</p>
        <p><i class="fa fa-circle" style="color:red"></i> High (4)</p>
        <p><i class="fa fa-circle" style="color:orange"></i> Medium (3)</p>
        <p><i class="fa fa-circle" style="color:blue"></i> Low (2)</p>
        <p><i class="fa fa-circle" style="color:lightgray"></i> Info (1)</p>
        <small>Marker size indicates threat count</small>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m