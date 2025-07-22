from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import math
import aiohttp
from geopy.distance import geodesic
import logging
from pydantic import BaseModel
import numpy as np
import asyncio
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import warnings
import uvicorn
import re
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Earthquake Prediction API",
    description="Real-time earthquake data and analysis API for geological monitoring",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class EarthquakeData(BaseModel):
    magnitude: float
    place: str
    time: str
    latitude: float
    longitude: float
    depth: float
    distance_km: float = 0.0
    url: str
    alert: Optional[str] = None
    tsunami: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert EarthquakeData to dictionary"""
        return {
            "magnitude": self.magnitude,
            "place": self.place,
            "time": self.time,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "depth": self.depth,
            "distance_km": self.distance_km,
            "url": self.url,
            "alert": self.alert,
            "tsunami": self.tsunami
        }

class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: int = 500
    days: int = 30
    min_magnitude: float = 2.5

class StressAnalysisResult(BaseModel):
    stress_level: str
    stress_score: float
    earthquake_count: int
    recent_activity: List[EarthquakeData]
    recommendations: List[str]

# USGS Earthquake API endpoints
USGS_BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_REALTIME_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary"

# Comprehensive earthquake data sources
GLOBAL_SOURCES = {
    "USGS_GEOJSON": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "USGS_WEEK": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson",
    "EMSC_GLOBAL": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc",
    "IRIS_RECENT": "http://service.iris.edu/fdsnws/event/1/query?format=geojson&limit=100&orderby=time",
    "GEOFON_GFZ": "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=100",
}

# Indian earthquake data sources - Enhanced with multiple free APIs
INDIAN_SOURCES = {
    # Primary Indian sources
    "IMD_RSS": "https://mausam.imd.gov.in/backend/assets/earthquake/earthquake.xml",
    "NCS_CATALOG": "https://www.seismo.gov.in/earthquakes/recent",
    "GSI_SEISMO": "https://www.gsi.gov.in/webcenter/portal/ENGLISH/pagelets/seismology",
    
    # EMSC for Indian subcontinent (highly reliable)
    "EMSC_INDIA": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=6&max_lat=38&min_lon=68&max_lon=98",
    "EMSC_INDIA_HIGH": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=8&max_lat=37&min_lon=68&max_lon=97&min_mag=3.0",
    
    # IRIS for South Asia
    "IRIS_INDIA": "http://service.iris.edu/fdsnws/event/1/query?format=geojson&minlat=6&maxlat=38&minlon=68&maxlon=98&limit=100&orderby=time",
    
    # GeoNet for regional coverage
    "GEONET_SOUTH_ASIA": "https://api.geonet.org.nz/quake?MMI=3",
    
    # GEOFON for Indian Ocean region
    "GEOFON_INDIAN_OCEAN": "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=100&latmin=6&latmax=38&lonmin=68&lonmax=98",
    
    # Alternative RSS feeds
    "EARTHQUAKE_TRACK_INDIA": "https://earthquaketrack.com/recent/in/rss.xml",
    "VOLCANODISCOVERY_INDIA": "https://www.volcanodiscovery.com/earthquakes/india/recent.xml"
}

# Japanese earthquake data sources - Enhanced with multiple free APIs
JAPANESE_SOURCES = {
    # Primary Japanese sources
    "JMA_API": "https://www.jma.go.jp/bosai/forecast/data/earthquake",
    "JMA_RSS": "https://www.jma.go.jp/bosai/rss/jma.rss",
    "NIED_HINET": "https://www.hinet.bosai.go.jp/",
    "JMA_EQVOL": "https://www.data.jma.go.jp/svd/eqev/data/daily_map/",
    
    # EMSC for Japanese archipelago (highly reliable)
    "EMSC_JAPAN": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=24&max_lat=46&min_lon=122&max_lon=146",
    "EMSC_JAPAN_HIGH": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=24&max_lat=46&min_lon=122&max_lon=146&min_mag=2.5",
    
    # IRIS for Japan region
    "IRIS_JAPAN": "http://service.iris.edu/fdsnws/event/1/query?format=geojson&minlat=24&maxlat=46&minlon=122&maxlon=146&limit=100&orderby=time",
    
    # GEOFON for Japan
    "GEOFON_JAPAN": "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=100&latmin=24&latmax=46&lonmin=122&lonmax=146",
    
    # Pacific region sources covering Japan
    "PACIFIC_TSUNAMI_CENTER": "https://ptwc.weather.gov/feeds/ptwc_rss_pacific.xml",
    
    # Alternative sources
    "EARTHQUAKE_TRACK_JAPAN": "https://earthquaketrack.com/recent/jp/rss.xml",
    "VOLCANODISCOVERY_JAPAN": "https://www.volcanodiscovery.com/earthquakes/japan/recent.xml"
}

# Additional regional sources
REGIONAL_SOURCES = {
    # European sources
    "INGV_ITALY": "http://webservices.ingv.it/fdsnws/event/1/query?format=geojson&limit=100&orderby=time",
    "EMSC_EUROPE": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=35&max_lat=75&min_lon=-15&max_lon=45",
    
    # Pacific sources
    "GEONET_NZ": "https://api.geonet.org.nz/quake?MMI=3",
    "EMSC_PACIFIC": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-50&max_lat=70&min_lon=120&max_lon=-60",
    
    # Americas
    "EMSC_AMERICAS": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-60&max_lat=80&min_lon=-180&max_lon=-30",
    
    # Global coverage
    "SIGNIFICANT_EARTHQUAKES": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson"
}

class EarthquakeService:
    """Service for fetching and processing earthquake data from USGS API"""
    
    @staticmethod
    async def get_earthquakes_by_location(
        latitude: float, 
        longitude: float, 
        radius_km: int = 500,
        days: int = 30,
        min_magnitude: float = 2.5
    ) -> List[EarthquakeData]:
        """
        Fetch earthquakes near a specific location from USGS API
        """
        try:
            # Calculate date range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # USGS API parameters
            params = {
                'format': 'geojson',
                'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'latitude': latitude,
                'longitude': longitude,
                'maxradiuskm': radius_km,
                'minmagnitude': min_magnitude,
                'orderby': 'time-asc'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(USGS_BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = []
                        
                        for feature in data.get('features', []):
                            props = feature['properties']
                            coords = feature['geometry']['coordinates']
                            
                            # Calculate distance from search location
                            eq_location = (coords[1], coords[0])  # lat, lon
                            search_location = (latitude, longitude)
                            distance = geodesic(search_location, eq_location).kilometers
                            
                            earthquake = EarthquakeData(
                                magnitude=props.get('mag', 0),
                                place=props.get('place', 'Unknown'),
                                time=datetime.fromtimestamp(props.get('time', 0) / 1000).isoformat(),
                                latitude=coords[1],
                                longitude=coords[0],
                                depth=coords[2] if len(coords) > 2 else 0,
                                distance_km=round(distance, 2),
                                url=props.get('url', ''),
                                alert=props.get('alert'),
                                tsunami=bool(props.get('tsunami', 0))
                            )
                            earthquakes.append(earthquake)
                        
                        # Sort by time (most recent first)
                        earthquakes.sort(key=lambda x: x.time, reverse=True)
                        
                        logger.info(f"Found {len(earthquakes)} earthquakes near {latitude}, {longitude}")
                        return earthquakes
                    
                    else:
                        logger.error(f"USGS API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching earthquake data: {str(e)}")
            return []

class IndianEarthquakeService:
    """Enhanced service for fetching earthquake data from multiple Indian and regional sources"""
    
    @staticmethod
    async def get_indian_earthquakes(
        latitude: float,
        longitude: float,
        radius_km: int = 500,
        days: int = 30,
        min_magnitude: float = 1.5  # Lower threshold for Indian region
    ) -> List[EarthquakeData]:
        """
        Fetch earthquakes from multiple Indian sources with comprehensive coverage
        Enhanced specifically for Indian continent with lower magnitude threshold
        """
        all_earthquakes = []
        
        # Use a wider search area for Indian continent
        extended_radius = max(radius_km, 800)  # Minimum 800km for Indian subcontinent
        
        # Fetch from multiple sources in parallel with Indian-specific parameters
        tasks = [
            IndianEarthquakeService._fetch_emsc_india_comprehensive(days, min_magnitude),
            IndianEarthquakeService._fetch_iris_india_data(days, min_magnitude),
            IndianEarthquakeService._fetch_geofon_india_data(days, min_magnitude),
            IndianEarthquakeService._fetch_usgs_india_comprehensive(latitude, longitude, extended_radius, days, min_magnitude),
            IndianEarthquakeService._fetch_global_for_india(days, min_magnitude),
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                    logger.info(f"Indian source {i+1}: Retrieved {len(result)} earthquakes")
                elif isinstance(result, Exception):
                    logger.warning(f"Indian data source {i+1} failed: {str(result)}")
            
            # Filter by location and radius (more permissive for Indian continent)
            filtered_earthquakes = []
            for eq in all_earthquakes:
                eq_location = (eq.latitude, eq.longitude)
                search_location = (latitude, longitude)
                distance = geodesic(search_location, eq_location).kilometers
                
                # More inclusive filtering for Indian subcontinent
                if distance <= extended_radius:
                    eq.distance_km = round(distance, 2)
                    filtered_earthquakes.append(eq)
            
            # Remove duplicates based on time and location proximity
            filtered_earthquakes = IndianEarthquakeService._remove_duplicates(filtered_earthquakes)
            
            # Sort by time (most recent first)
            filtered_earthquakes.sort(key=lambda x: x.time, reverse=True)
            
            logger.info(f"Found {len(filtered_earthquakes)} unique Indian region earthquakes from {len([r for r in results if isinstance(r, list)])} sources")
            return filtered_earthquakes
            
        except Exception as e:
            logger.error(f"Error in Indian earthquake data aggregation: {str(e)}")
            # Return empty list but with better logging
            return []
    
    @staticmethod
    async def _fetch_emsc_india_comprehensive(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC India region - Primary source"""
        earthquakes = []
        try:
            # Multiple EMSC endpoints for comprehensive Indian coverage
            urls = [
                f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=6&max_lat=38&min_lon=68&max_lon=98&min_mag={min_magnitude}",
                f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=8&max_lat=37&min_lon=68&max_lon=97&min_mag={max(1.0, min_magnitude-0.5)}"
            ]
            
            async with aiohttp.ClientSession() as session:
                for url in urls:
                    try:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                            if response.status == 200:
                                content = await response.text()
                                url_earthquakes = IndianEarthquakeService._parse_emsc_rss(content, "EMSC-India")
                                earthquakes.extend(url_earthquakes)
                                logger.info(f"EMSC India: Fetched {len(url_earthquakes)} earthquakes from {url}")
                            else:
                                logger.warning(f"EMSC India API returned status: {response.status}")
                    except Exception as e:
                        logger.warning(f"Error fetching from EMSC URL {url}: {str(e)}")
        except Exception as e:
            logger.warning(f"Error fetching EMSC India comprehensive data: {str(e)}")
        
        return earthquakes
        """Comprehensive EMSC data for Indian region with multiple feeds"""
        earthquakes = []
        
        # Multiple EMSC feeds for better coverage
        urls = [
            f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=6&max_lat=38&min_lon=68&max_lon=98&min_mag={min_magnitude}",
            f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=8&max_lat=37&min_lon=68&max_lon=97&min_mag={max(min_magnitude-0.5, 1.0)}",
            "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=20&max_lat=30&min_lon=70&max_lon=88",  # Central India
        ]
        
        for i, url in enumerate(urls):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed_earthquakes = IndianEarthquakeService._parse_emsc_rss(content, "India")
                            earthquakes.extend(feed_earthquakes)
                            logger.info(f"EMSC India Feed {i+1}: Fetched {len(feed_earthquakes)} earthquakes")
                        else:
                            logger.warning(f"EMSC India Feed {i+1} returned status: {response.status}")
            except Exception as e:
                logger.warning(f"Error fetching EMSC India feed {i+1}: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_usgs_india_comprehensive(latitude: float, longitude: float, radius_km: int, days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Comprehensive USGS data for Indian region with optimized parameters"""
        earthquakes = []
        
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # Multiple USGS queries for comprehensive coverage
            queries = [
                {
                    'format': 'geojson',
                    'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'minlatitude': 6,
                    'maxlatitude': 38,
                    'minlongitude': 68,
                    'maxlongitude': 98,
                    'minmagnitude': min_magnitude,
                    'orderby': 'time-desc',
                    'limit': 1000
                },
                # Focused query for Indian subcontinent core
                {
                    'format': 'geojson',
                    'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'minlatitude': 8,
                    'maxlatitude': 37,
                    'minlongitude': 68,
                    'maxlongitude': 97,
                    'minmagnitude': max(min_magnitude - 0.5, 1.0),
                    'orderby': 'time-desc',
                    'limit': 500
                }
            ]
            
            for i, params in enumerate(queries):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(USGS_BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                            if response.status == 200:
                                data = await response.json()
                                query_earthquakes = IndianEarthquakeService._parse_geojson_data(data, f"India-USGS-{i+1}")
                                earthquakes.extend(query_earthquakes)
                                logger.info(f"USGS India Query {i+1}: Fetched {len(query_earthquakes)} earthquakes")
                            else:
                                logger.warning(f"USGS India Query {i+1} returned status: {response.status}")
                except Exception as e:
                    logger.warning(f"Error in USGS India query {i+1}: {str(e)}")
        
        except Exception as e:
            logger.warning(f"Error fetching comprehensive USGS India data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_global_for_india(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch global earthquake data specifically filtered for Indian region"""
        earthquakes = []
        
        # Global feeds that might contain Indian earthquakes
        global_urls = [
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/1.0_day.geojson",
        ]
        
        for url in global_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=25)) as response:
                        if response.status == 200:
                            data = await response.json()
                            global_earthquakes = IndianEarthquakeService._parse_geojson_data(data, "Global-for-India")
                            
                            # Filter for Indian region
                            indian_filtered = []
                            for eq in global_earthquakes:
                                if (6 <= eq.latitude <= 38 and 68 <= eq.longitude <= 98 and 
                                    eq.magnitude >= min_magnitude):
                                    indian_filtered.append(eq)
                            
                            earthquakes.extend(indian_filtered)
                            logger.info(f"Global feed for India ({url.split('/')[-1]}): Found {len(indian_filtered)} Indian earthquakes")
                        else:
                            logger.warning(f"Global feed for India returned status: {response.status}")
            except Exception as e:
                logger.warning(f"Error fetching global data for India: {str(e)}")
        
        return earthquakes
        """Fetch from EMSC India region - Primary source"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=6&max_lat=38&min_lon=68&max_lon=98&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = IndianEarthquakeService._parse_emsc_rss(content, "India")
                        logger.info(f"EMSC India: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"EMSC India API returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching EMSC India data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_iris_india_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from IRIS for India region"""
        earthquakes = []
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            url = f"http://service.iris.edu/fdsnws/event/1/query?format=geojson&minlat=6&maxlat=38&minlon=68&maxlon=98&limit=100&orderby=time&starttime={start_time.strftime('%Y-%m-%dT%H:%M:%S')}&endtime={end_time.strftime('%Y-%m-%dT%H:%M:%S')}&minmag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = IndianEarthquakeService._parse_geojson_data(data, "India-IRIS")
                        logger.info(f"IRIS India: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"IRIS India API returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching IRIS India data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_geofon_india_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from GEOFON for India region"""
        earthquakes = []
        try:
            url = "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=100&latmin=6&latmax=38&lonmin=68&lonmax=98"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = IndianEarthquakeService._parse_geojson_data(data, "India-GEOFON")
                        # Filter by magnitude
                        earthquakes = [eq for eq in earthquakes if eq.magnitude >= min_magnitude]
                        logger.info(f"GEOFON India: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"GEOFON India API returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching GEOFON India data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_usgs_india_data(latitude: float, longitude: float, radius_km: int, days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch USGS data specifically for India region"""
        earthquakes = []
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # USGS API parameters for India region
            params = {
                'format': 'geojson',
                'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'minlatitude': 6,
                'maxlatitude': 38,
                'minlongitude': 68,
                'maxlongitude': 98,
                'minmagnitude': min_magnitude,
                'orderby': 'time-asc',
                'limit': 1000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(USGS_BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=25)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = IndianEarthquakeService._parse_geojson_data(data, "India-USGS")
                        logger.info(f"USGS India: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"USGS India API returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching USGS India data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_earthquake_track_india(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EarthquakeTrack RSS for India"""
        earthquakes = []
        try:
            url = "https://earthquaketrack.com/recent/in/rss.xml"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = IndianEarthquakeService._parse_earthquake_track_rss(content, "India")
                        # Filter by magnitude
                        earthquakes = [eq for eq in earthquakes if eq.magnitude >= min_magnitude]
                        logger.info(f"EarthquakeTrack India: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"EarthquakeTrack India returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching EarthquakeTrack India data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    def _parse_emsc_rss(content: str, region: str) -> List[EarthquakeData]:
        """Parse EMSC RSS XML content"""
        earthquakes = []
        try:
            root = ET.fromstring(content)
            
            for item in root.findall('.//item'):
                title = item.find('title')
                description = item.find('description')
                pub_date = item.find('pubDate')
                link = item.find('link')
                
                if title is not None and description is not None:
                    title_text = title.text or ""
                    desc_text = description.text or ""
                    
                    if "M " in title_text:
                        try:
                            # Extract magnitude
                            mag_part = title_text.split("M ")[1].split(" ")[0]
                            magnitude = float(mag_part)
                            
                            # Extract location info
                            location = title_text.split(" - ")[1] if " - " in title_text else f"Unknown Location, {region}"
                            
                            # Extract coordinates from description
                            lat, lon, depth = None, None, 10.0
                            if "Lat:" in desc_text and "Lon:" in desc_text:
                                try:
                                    lat_part = desc_text.split("Lat:")[1].split(",")[0].strip()
                                    lon_part = desc_text.split("Lon:")[1].split(",")[0].strip()
                                    lat = float(lat_part)
                                    lon = float(lon_part)
                                    
                                    if "Depth:" in desc_text:
                                        depth_part = desc_text.split("Depth:")[1].split("km")[0].strip()
                                        depth = float(depth_part)
                                except Exception:
                                    continue
                            
                            if lat is not None and lon is not None:
                                # Parse time
                                eq_time = datetime.utcnow().isoformat()
                                if pub_date is not None and pub_date.text:
                                    try:
                                        parsed_time = parsedate_to_datetime(pub_date.text)
                                        eq_time = parsed_time.isoformat()
                                    except Exception:
                                        pass
                                
                                earthquake = EarthquakeData(
                                    magnitude=magnitude,
                                    place=location,
                                    time=eq_time,
                                    latitude=lat,
                                    longitude=lon,
                                    depth=depth,
                                    distance_km=0.0,
                                    url=link.text if link is not None and link.text else "",
                                    alert=None,
                                    tsunami=False
                                )
                                earthquakes.append(earthquake)
                        except Exception as e:
                            logger.debug(f"Error parsing EMSC item: {e}")
                            continue
        except ET.ParseError as e:
            logger.warning(f"Error parsing EMSC XML: {e}")
        
        return earthquakes
    
    @staticmethod
    def _parse_geojson_data(data: dict, source: str) -> List[EarthquakeData]:
        """Parse GeoJSON earthquake data"""
        earthquakes = []
        try:
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                coords = feature.get('geometry', {}).get('coordinates', [])
                
                if len(coords) >= 2:
                    magnitude = props.get('mag', 0) or props.get('magnitude', 0)
                    place = props.get('place', '') or props.get('title', '') or f"Unknown Location ({source})"
                    
                    # Handle time - could be timestamp or ISO string
                    time_val = props.get('time', 0) or props.get('datetime', '')
                    if isinstance(time_val, (int, float)) and time_val > 0:
                        eq_time = datetime.fromtimestamp(time_val / 1000).isoformat()
                    elif isinstance(time_val, str) and time_val:
                        try:
                            eq_time = datetime.fromisoformat(time_val.replace('Z', '')).isoformat()
                        except Exception:
                            eq_time = datetime.utcnow().isoformat()
                    else:
                        eq_time = datetime.utcnow().isoformat()
                    
                    depth = coords[2] if len(coords) > 2 else props.get('depth', 10.0)
                    
                    earthquake = EarthquakeData(
                        magnitude=magnitude,
                        place=place,
                        time=eq_time,
                        latitude=coords[1],
                        longitude=coords[0],
                        depth=depth,
                        distance_km=0.0,
                        url=props.get('url', '') or props.get('uri', ''),
                        alert=props.get('alert'),
                        tsunami=bool(props.get('tsunami', 0))
                    )
                    earthquakes.append(earthquake)
        except Exception as e:
            logger.warning(f"Error parsing GeoJSON data from {source}: {e}")
        
        return earthquakes
    
    @staticmethod
    def _parse_earthquake_track_rss(content: str, region: str) -> List[EarthquakeData]:
        """Parse EarthquakeTrack RSS content"""
        earthquakes = []
        try:
            root = ET.fromstring(content)
            
            for item in root.findall('.//item'):
                title = item.find('title')
                description = item.find('description')
                pub_date = item.find('pubDate')
                link = item.find('link')
                
                if title is not None:
                    title_text = title.text or ""
                    
                    # EarthquakeTrack format: "Magnitude 4.2 Earthquake near Location"
                    if "Magnitude" in title_text and "Earthquake" in title_text:
                        try:
                            # Extract magnitude
                            mag_part = title_text.split("Magnitude")[1].split("Earthquake")[0].strip()
                            magnitude = float(mag_part)
                            
                            # Extract location
                            location = title_text.split("near")[1].strip() if "near" in title_text else f"{region} Region"
                            
                            # Try to extract coordinates from description if available
                            lat, lon = None, None
                            if description is not None and description.text:
                                desc_text = description.text
                                # Look for coordinate patterns
                                coord_match = re.search(r'(\d+\.?\d*)[°\s]*[NS][,\s]*(\d+\.?\d*)[°\s]*[EW]', desc_text)
                                if coord_match:
                                    lat = float(coord_match.group(1))
                                    lon = float(coord_match.group(2))
                                    # Adjust signs based on hemisphere
                                    if 'S' in desc_text:
                                        lat = -lat
                                    if 'W' in desc_text:
                                        lon = -lon
                            
                            # Use default coordinates for region if not found
                            if lat is None or lon is None:
                                if region == "India":
                                    lat, lon = 20.0, 77.0  # Center of India
                                elif region == "Japan":
                                    lat, lon = 36.0, 138.0  # Center of Japan
                                else:
                                    continue  # Skip if no coordinates
                            
                            # Parse time
                            eq_time = datetime.utcnow().isoformat()
                            if pub_date is not None and pub_date.text:
                                try:
                                    parsed_time = parsedate_to_datetime(pub_date.text)
                                    eq_time = parsed_time.isoformat()
                                except Exception:
                                    pass
                            
                            earthquake = EarthquakeData(
                                magnitude=magnitude,
                                place=location,
                                time=eq_time,
                                latitude=lat,
                                longitude=lon,
                                depth=10.0,  # Default depth
                                distance_km=0.0,
                                url=link.text if link is not None and link.text else "",
                                alert=None,
                                tsunami=False
                            )
                            earthquakes.append(earthquake)
                        except Exception as e:
                            logger.debug(f"Error parsing EarthquakeTrack item: {e}")
                            continue
        except ET.ParseError as e:
            logger.warning(f"Error parsing EarthquakeTrack XML: {e}")
        
        return earthquakes
    
    @staticmethod
    def _remove_duplicates(earthquakes: List[EarthquakeData]) -> List[EarthquakeData]:
        """Remove duplicate earthquakes based on time and location proximity"""
        if not earthquakes:
            return []
        
        unique_earthquakes = []
        
        for eq in earthquakes:
            is_duplicate = False
            for existing in unique_earthquakes:
                # Check time difference (within 30 minutes)
                try:
                    time1 = datetime.fromisoformat(eq.time.replace('Z', ''))
                    time2 = datetime.fromisoformat(existing.time.replace('Z', ''))
                    time_diff = abs((time1 - time2).total_seconds())
                except Exception:
                    time_diff = float('inf')
                
                # Check distance (within 10km)
                try:
                    distance = geodesic((eq.latitude, eq.longitude), (existing.latitude, existing.longitude)).kilometers
                except Exception:
                    distance = float('inf')
                
                # Check magnitude similarity (within 0.5)
                mag_diff = abs(eq.magnitude - existing.magnitude)
                
                if time_diff < 1800 and distance < 10 and mag_diff < 0.5:  # 30 min, 10km, 0.5 magnitude
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_earthquakes.append(eq)
        
        return unique_earthquakes

class JapaneseEarthquakeService:
    """Enhanced service for fetching earthquake data from multiple Japanese and regional sources"""
    
    @staticmethod
    async def get_japanese_earthquakes(
        latitude: float,
        longitude: float,
        radius_km: int = 500,
        days: int = 30,
        min_magnitude: float = 2.0
    ) -> List[EarthquakeData]:
        """
        Fetch earthquakes from multiple Japanese sources with comprehensive coverage
        """
        all_earthquakes = []
        
        # Fetch from multiple sources in parallel
        tasks = [
            JapaneseEarthquakeService._fetch_emsc_japan_data(days, min_magnitude),
            JapaneseEarthquakeService._fetch_iris_japan_data(days, min_magnitude),
            JapaneseEarthquakeService._fetch_geofon_japan_data(days, min_magnitude),
            JapaneseEarthquakeService._fetch_usgs_japan_data(latitude, longitude, radius_km, days, min_magnitude),
            JapaneseEarthquakeService._fetch_earthquake_track_japan(days, min_magnitude),
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"One of the Japanese data sources failed: {str(result)}")
            
            # Filter by location and radius
            filtered_earthquakes = []
            for eq in all_earthquakes:
                eq_location = (eq.latitude, eq.longitude)
                search_location = (latitude, longitude)
                distance = geodesic(search_location, eq_location).kilometers
                
                if distance <= radius_km:
                    eq.distance_km = round(distance, 2)
                    filtered_earthquakes.append(eq)
            
            # Remove duplicates
            filtered_earthquakes = JapaneseEarthquakeService._remove_duplicates(filtered_earthquakes)
            
            # Sort by time (most recent first)
            filtered_earthquakes.sort(key=lambda x: x.time, reverse=True)
            
            logger.info(f"Found {len(filtered_earthquakes)} unique Japanese region earthquakes from {len([r for r in results if isinstance(r, list)])} sources")
            return filtered_earthquakes
            
        except Exception as e:
            logger.error(f"Error in Japanese earthquake data aggregation: {str(e)}")
            return []
    
    @staticmethod
    async def _fetch_emsc_japan_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Japan region - Primary source"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=24&max_lat=46&min_lon=122&max_lon=146&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = JapaneseEarthquakeService._parse_emsc_rss(content, "Japan")
                        logger.info(f"EMSC Japan: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"EMSC Japan API returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Japan data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_iris_japan_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from IRIS for Japan region"""
        earthquakes = []
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            url = f"http://service.iris.edu/fdsnws/event/1/query?format=geojson&minlat=24&maxlat=46&minlon=122&maxlon=146&limit=100&orderby=time&starttime={start_time.strftime('%Y-%m-%dT%H:%M:%S')}&endtime={end_time.strftime('%Y-%m-%dT%H:%M:%S')}&minmag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = JapaneseEarthquakeService._parse_geojson_data(data, "Japan-IRIS")
                        logger.info(f"IRIS Japan: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"IRIS Japan API returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching IRIS Japan data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_geofon_japan_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from GEOFON for Japan region"""
        earthquakes = []
        try:
            url = "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=100&latmin=24&latmax=46&lonmin=122&lonmax=146"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = JapaneseEarthquakeService._parse_geojson_data(data, "Japan-GEOFON")
                        # Filter by magnitude
                        earthquakes = [eq for eq in earthquakes if eq.magnitude >= min_magnitude]
                        logger.info(f"GEOFON Japan: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"GEOFON Japan API returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching GEOFON Japan data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_usgs_japan_data(latitude: float, longitude: float, radius_km: int, days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch USGS data specifically for Japan region"""
        earthquakes = []
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # USGS API parameters for Japan region
            params = {
                'format': 'geojson',
                'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'minlatitude': 24,
                'maxlatitude': 46,
                'minlongitude': 122,
                'maxlongitude': 146,
                'minmagnitude': min_magnitude,
                'orderby': 'time-asc',
                'limit': 1000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(USGS_BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=25)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = JapaneseEarthquakeService._parse_geojson_data(data, "Japan-USGS")
                        logger.info(f"USGS Japan: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"USGS Japan API returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching USGS Japan data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_earthquake_track_japan(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EarthquakeTrack RSS for Japan"""
        earthquakes = []
        try:
            url = "https://earthquaketrack.com/recent/jp/rss.xml"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = JapaneseEarthquakeService._parse_earthquake_track_rss(content, "Japan")
                        # Filter by magnitude
                        earthquakes = [eq for eq in earthquakes if eq.magnitude >= min_magnitude]
                        logger.info(f"EarthquakeTrack Japan: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"EarthquakeTrack Japan returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching EarthquakeTrack Japan data: {str(e)}")
        
        return earthquakes
    
    # Reuse the same parsing methods from IndianEarthquakeService
    @staticmethod
    def _parse_emsc_rss(content: str, region: str) -> List[EarthquakeData]:
        return IndianEarthquakeService._parse_emsc_rss(content, region)
    
    @staticmethod
    def _parse_geojson_data(data: dict, source: str) -> List[EarthquakeData]:
        return IndianEarthquakeService._parse_geojson_data(data, source)
    
    @staticmethod
    def _parse_earthquake_track_rss(content: str, region: str) -> List[EarthquakeData]:
        return IndianEarthquakeService._parse_earthquake_track_rss(content, region)
    
    @staticmethod
    def _remove_duplicates(earthquakes: List[EarthquakeData]) -> List[EarthquakeData]:
        return IndianEarthquakeService._remove_duplicates(earthquakes)

class GlobalEarthquakeService:
    """Service for fetching earthquake data from multiple global sources"""
    
    @staticmethod
    async def get_global_earthquakes(
        latitude: float,
        longitude: float,
        radius_km: int = 1000,
        days: int = 7,
        min_magnitude: float = 4.0
    ) -> List[EarthquakeData]:
        """
        Fetch earthquakes from multiple global sources
        """
        all_earthquakes = []
        
        # Fetch from multiple global sources in parallel
        tasks = [
            GlobalEarthquakeService._fetch_usgs_global_feed(),
            GlobalEarthquakeService._fetch_emsc_global_data(min_magnitude),
            GlobalEarthquakeService._fetch_iris_global_data(days, min_magnitude),
            GlobalEarthquakeService._fetch_geofon_global_data(min_magnitude),
            GlobalEarthquakeService._fetch_significant_earthquakes(),
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"One of the global data sources failed: {str(result)}")
            
            # Filter by location and radius
            filtered_earthquakes = []
            for eq in all_earthquakes:
                eq_location = (eq.latitude, eq.longitude)
                search_location = (latitude, longitude)
                distance = geodesic(search_location, eq_location).kilometers
                
                if distance <= radius_km:
                    eq.distance_km = round(distance, 2)
                    filtered_earthquakes.append(eq)
            
            # Remove duplicates
            filtered_earthquakes = IndianEarthquakeService._remove_duplicates(filtered_earthquakes)
            
            # Sort by time (most recent first)
            filtered_earthquakes.sort(key=lambda x: x.time, reverse=True)
            
            logger.info(f"Found {len(filtered_earthquakes)} unique global earthquakes from {len([r for r in results if isinstance(r, list)])} sources")
            return filtered_earthquakes
            
        except Exception as e:
            logger.error(f"Error in global earthquake data aggregation: {str(e)}")
            return []
    
    @staticmethod
    async def _fetch_usgs_global_feed() -> List[EarthquakeData]:
        """Fetch from USGS global feeds"""
        earthquakes = []
        urls = [
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson",
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
        ]
        
        for url in urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                        if response.status == 200:
                            data = await response.json()
                            feed_earthquakes = IndianEarthquakeService._parse_geojson_data(data, "USGS-Global")
                            earthquakes.extend(feed_earthquakes)
                            logger.info(f"USGS Global ({url.split('/')[-1]}): Fetched {len(feed_earthquakes)} earthquakes")
                        else:
                            logger.warning(f"USGS Global feed {url} returned status: {response.status}")
            except Exception as e:
                logger.warning(f"Error fetching USGS global feed {url}: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_emsc_global_data(min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC global feed"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = IndianEarthquakeService._parse_emsc_rss(content, "Global")
                        logger.info(f"EMSC Global: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"EMSC Global API returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching EMSC global data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_iris_global_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from IRIS global network"""
        earthquakes = []
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            url = f"http://service.iris.edu/fdsnws/event/1/query?format=geojson&limit=500&orderby=time&starttime={start_time.strftime('%Y-%m-%dT%H:%M:%S')}&endtime={end_time.strftime('%Y-%m-%dT%H:%M:%S')}&minmag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=25)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = IndianEarthquakeService._parse_geojson_data(data, "IRIS-Global")
                        logger.info(f"IRIS Global: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"IRIS Global API returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching IRIS global data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_geofon_global_data(min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from GEOFON global network"""
        earthquakes = []
        try:
            url = "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=200"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = IndianEarthquakeService._parse_geojson_data(data, "GEOFON-Global")
                        # Filter by magnitude
                        earthquakes = [eq for eq in earthquakes if eq.magnitude >= min_magnitude]
                        logger.info(f"GEOFON Global: Fetched {len(earthquakes)} earthquakes")
                    else:
                        logger.warning(f"GEOFON Global API returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching GEOFON global data: {str(e)}")
        
        return earthquakes
    
    @staticmethod
    async def _fetch_significant_earthquakes() -> List[EarthquakeData]:
        """Fetch significant earthquakes from USGS"""
        earthquakes = []
        try:
            urls = [
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson",
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson"
            ]
            
            for url in urls:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                        if response.status == 200:
                            data = await response.json()
                            sig_earthquakes = IndianEarthquakeService._parse_geojson_data(data, "USGS-Significant")
                            earthquakes.extend(sig_earthquakes)
                            logger.info(f"USGS Significant ({url.split('/')[-1]}): Fetched {len(sig_earthquakes)} earthquakes")
                        else:
                            logger.warning(f"USGS Significant feed returned status: {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching significant earthquakes: {str(e)}")
        
        return earthquakes

class EarthquakeMLPredictor:
    """Advanced ML-based earthquake prediction and analysis system"""
    
    def __init__(self):
        self.magnitude_predictor = None
        self.anomaly_detector = None
        self.stress_analyzer = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def prepare_features(self, earthquakes: List[EarthquakeData], location_lat: float, location_lon: float) -> np.ndarray:
        """
        Extract comprehensive features from earthquake data for ML models
        """
        if not earthquakes:
            return np.array([]).reshape(0, -1)
        
        features = []
        
        for i, eq in enumerate(earthquakes):
            # Basic earthquake features
            distance = eq.distance_km
            time_since = (datetime.utcnow() - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() / 3600  # hours
            
            # Spatial features
            lat_diff = eq.latitude - location_lat
            lon_diff = eq.longitude - location_lon
            bearing = math.atan2(lon_diff, lat_diff) * 180 / math.pi
            
            # Temporal features
            hour_of_day = datetime.fromisoformat(eq.time.replace('Z', '')).hour
            day_of_week = datetime.fromisoformat(eq.time.replace('Z', '')).weekday()
            
            # Statistical features from nearby earthquakes
            recent_eqs = [e for e in earthquakes[:i+10] if e.distance_km <= distance * 2]
            avg_magnitude = np.mean([e.magnitude for e in recent_eqs]) if recent_eqs else eq.magnitude
            magnitude_trend = eq.magnitude - avg_magnitude
            
            # Energy calculations
            energy_released = 10 ** (1.5 * eq.magnitude + 4.8)
            cumulative_energy = sum(10 ** (1.5 * e.magnitude + 4.8) for e in recent_eqs)
            
            # Depth-based features
            depth_normalized = eq.depth / 700  # Normalize to typical max depth
            shallow_indicator = 1 if eq.depth < 35 else 0
            
            # Frequency features
            events_last_24h = len([e for e in recent_eqs if 
                                 (datetime.utcnow() - datetime.fromisoformat(e.time.replace('Z', ''))).total_seconds() < 86400])
            events_last_week = len([e for e in recent_eqs if 
                                  (datetime.utcnow() - datetime.fromisoformat(e.time.replace('Z', ''))).total_seconds() < 604800])
            
            # Regional risk indicators
            regional_risk = self._get_regional_risk_score(eq.latitude, eq.longitude)
            
            feature_vector = [
                eq.magnitude,
                distance,
                time_since,
                eq.depth,
                lat_diff,
                lon_diff,
                bearing,
                hour_of_day,
                day_of_week,
                magnitude_trend,
                energy_released,
                cumulative_energy,
                depth_normalized,
                shallow_indicator,
                events_last_24h,
                events_last_week,
                regional_risk,
                avg_magnitude
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    def _get_regional_risk_score(self, lat: float, lon: float) -> float:
        """
        Calculate regional seismic risk based on location
        """
        # Known high-risk regions
        high_risk_zones = [
            # Ring of Fire regions
            {"lat": 35.7, "lon": 139.7, "risk": 0.9, "name": "Tokyo"},  # Japan
            {"lat": 37.7, "lon": -122.4, "risk": 0.85, "name": "San Francisco"},  # California
            {"lat": 36.1, "lon": 140.1, "risk": 0.9, "name": "Fukushima"},  # Japan
            {"lat": 28.6, "lon": 77.2, "risk": 0.7, "name": "Delhi"},  # India
            {"lat": 41.0, "lon": 29.0, "risk": 0.8, "name": "Istanbul"},  # Turkey
            {"lat": -6.2, "lon": 106.8, "risk": 0.75, "name": "Jakarta"},  # Indonesia
            {"lat": 19.4, "lon": -99.1, "risk": 0.8, "name": "Mexico City"},  # Mexico
            {"lat": -33.4, "lon": -70.6, "risk": 0.85, "name": "Santiago"},  # Chile
        ]
        
        max_risk = 0.1  # Base risk
        for zone in high_risk_zones:
            distance = geodesic((lat, lon), (zone["lat"], zone["lon"])).kilometers
            if distance < 500:  # Within 500km of high-risk zone
                proximity_factor = max(0, 1 - distance / 500)
                risk_contribution = zone["risk"] * proximity_factor
                max_risk = max(max_risk, risk_contribution)
        
        return max_risk
    
    def train_models(self, historical_earthquakes: List[EarthquakeData], location_lat: float, location_lon: float):
        """
        Train ML models using historical earthquake data
        """
        if len(historical_earthquakes) < 10:
            logger.warning("Insufficient data for ML training, using baseline models")
            return
        
        try:
            # Prepare features
            features = self.prepare_features(historical_earthquakes, location_lat, location_lon)
            if features.shape[0] == 0:
                return
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Prepare targets for magnitude prediction
            magnitudes = np.array([eq.magnitude for eq in historical_earthquakes])
            
            # Train magnitude predictor
            self.magnitude_predictor = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            if len(features_scaled) > 5:
                X_train, X_test, y_train, y_test = train_test_split(
                    features_scaled, magnitudes, test_size=0.2, random_state=42
                )
                self.magnitude_predictor.fit(X_train, y_train)
                
                # Evaluate model
                predictions = self.magnitude_predictor.predict(X_test)
                mse = mean_squared_error(y_test, predictions)
                logger.info(f"Magnitude predictor MSE: {mse:.3f}")
            else:
                self.magnitude_predictor.fit(features_scaled, magnitudes)
            
            # Train anomaly detector
            self.anomaly_detector = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            self.anomaly_detector.fit(features_scaled)
            
            self.is_trained = True
            logger.info("ML models trained successfully")
            
        except Exception as e:
            logger.error(f"Error training ML models: {str(e)}")
    
    def predict_earthquake_probability(self, earthquakes: List[EarthquakeData], location_lat: float, location_lon: float) -> Dict[str, Any]:
        """
        Predict earthquake probability using ML models
        """
        if not earthquakes:
            return {
                "probability_24h": 0.05,
                "probability_7d": 0.15,
                "probability_30d": 0.35,
                "predicted_magnitude_range": [2.0, 4.0],
                "confidence": 0.3,
                "model_status": "no_data"
            }
        
        try:
            # Extract features
            features = self.prepare_features(earthquakes, location_lat, location_lon)
            if features.shape[0] == 0:
                return self._baseline_prediction()
            
            # Scale features
            features_scaled = self.scaler.transform(features) if self.is_trained else features
            
            # Calculate base probability from recent activity
            recent_24h = [eq for eq in earthquakes if 
                         (datetime.utcnow() - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 86400]
            recent_7d = [eq for eq in earthquakes if 
                        (datetime.utcnow() - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 604800]
            recent_30d = earthquakes
            
            # Base probability calculation
            base_prob_24h = min(0.8, len(recent_24h) * 0.15 + 0.05)
            base_prob_7d = min(0.9, len(recent_7d) * 0.08 + 0.15)
            base_prob_30d = min(0.95, len(recent_30d) * 0.03 + 0.35)
            
            # ML enhancement if models are trained
            if self.is_trained and self.magnitude_predictor is not None and self.anomaly_detector is not None:
                # Predict expected magnitude
                latest_features = features_scaled[-1:] if len(features_scaled) > 0 else features[-1:]
                predicted_mag = self.magnitude_predictor.predict(latest_features)[0]
                
                # Anomaly detection
                is_anomaly = self.anomaly_detector.predict(latest_features)[0] == -1
                
                # Adjust probabilities based on ML predictions
                magnitude_factor = min(2.0, predicted_mag / 4.0)
                anomaly_factor = 1.5 if is_anomaly else 1.0
                
                ml_prob_24h = base_prob_24h * magnitude_factor * anomaly_factor
                ml_prob_7d = base_prob_7d * magnitude_factor * anomaly_factor * 0.8
                ml_prob_30d = base_prob_30d * magnitude_factor * anomaly_factor * 0.6
                
                confidence = 0.8
                predicted_range = [max(1.0, predicted_mag - 1.0), predicted_mag + 1.0]
            else:
                ml_prob_24h = base_prob_24h
                ml_prob_7d = base_prob_7d
                ml_prob_30d = base_prob_30d
                confidence = 0.5
                is_anomaly = False
                avg_magnitude = np.mean([eq.magnitude for eq in earthquakes])
                predicted_range = [max(1.0, avg_magnitude - 0.5), avg_magnitude + 0.5]
            
            return {
                "probability_24h": min(0.95, ml_prob_24h),
                "probability_7d": min(0.98, ml_prob_7d),
                "probability_30d": min(0.99, ml_prob_30d),
                "predicted_magnitude_range": predicted_range,
                "confidence": confidence,
                "model_status": "trained" if self.is_trained else "baseline",
                "anomaly_detected": is_anomaly if self.is_trained else False,
                "recent_activity_factor": len(recent_7d) / 7.0  # Activity per day
            }
            
        except Exception as e:
            logger.error(f"Error in ML prediction: {str(e)}")
            return self._baseline_prediction()
    
    def _baseline_prediction(self) -> Dict[str, Any]:
        """Fallback prediction when ML models fail"""
        return {
            "probability_24h": 0.1,
            "probability_7d": 0.25,
            "probability_30d": 0.5,
            "predicted_magnitude_range": [2.0, 4.5],
            "confidence": 0.4,
            "model_status": "baseline",
            "anomaly_detected": False,
            "recent_activity_factor": 0.1
        }
    
    def analyze_stress_patterns(self, earthquakes: List[EarthquakeData], location_lat: float, location_lon: float) -> Dict[str, Any]:
        """
        Advanced stress pattern analysis using ML techniques
        """
        if not earthquakes:
            return {"stress_pattern": "insufficient_data", "stress_indicators": {}}
        
        try:
            # Time series analysis
            earthquake_times = [datetime.fromisoformat(eq.time.replace('Z', '')) for eq in earthquakes]
            magnitudes = [eq.magnitude for eq in earthquakes]
            depths = [eq.depth for eq in earthquakes]
            
            # Calculate stress accumulation indicators
            stress_indicators = {}
            
            # Magnitude progression analysis
            if len(magnitudes) >= 3:
                magnitude_trend = np.polyfit(range(len(magnitudes)), magnitudes, 1)[0]
                stress_indicators["magnitude_trend"] = float(magnitude_trend)
                stress_indicators["magnitude_acceleration"] = float(np.std(np.diff(magnitudes)))
            
            # Depth pattern analysis
            if len(depths) >= 3:
                depth_trend = np.polyfit(range(len(depths)), depths, 1)[0]
                stress_indicators["depth_trend"] = float(depth_trend)
                stress_indicators["depth_variance"] = float(np.var(depths))
            
            # Temporal clustering analysis
            time_intervals = []
            for i in range(1, len(earthquake_times)):
                interval = (earthquake_times[i-1] - earthquake_times[i]).total_seconds() / 3600  # hours
                time_intervals.append(interval)
            
            if time_intervals:
                stress_indicators["average_interval_hours"] = float(np.mean(time_intervals))
                stress_indicators["interval_variance"] = float(np.var(time_intervals))
                stress_indicators["clustering_coefficient"] = float(1.0 / (1.0 + np.mean(time_intervals) / 24))
            
            # Energy release pattern
            energies = [10 ** (1.5 * eq.magnitude + 4.8) for eq in earthquakes]
            cumulative_energy = np.cumsum(energies)
            
            if len(cumulative_energy) >= 5:
                # Fit exponential trend to cumulative energy
                x = np.arange(len(cumulative_energy))
                log_energy = np.log((cumulative_energy+1))
                energy_trend = np.polyfit(x, log_energy, 1)[0]
                stress_indicators["energy_accumulation_rate"] = float(energy_trend)
            
            # Spatial pattern analysis
            lats = [eq.latitude for eq in earthquakes]
            lons = [eq.longitude for eq in earthquakes]
            
            if len(lats) >= 3:
                lat_centroid = np.mean(lats)
                lon_centroid = np.mean(lons)
                spatial_spread = np.sqrt(np.var(lats) + np.var(lons))
                
                stress_indicators["spatial_centroid"] = [float(lat_centroid), float(lon_centroid)]
                stress_indicators["spatial_spread"] = float(spatial_spread)
                
                # Calculate migration direction
                if len(earthquakes) >= 5:
                    recent_centroid = [np.mean(lats[:len(lats)//2]), np.mean(lons[:len(lons)//2])]
                    older_centroid = [np.mean(lats[len(lats)//2:]), np.mean(lons[len(lons)//2:])]
                    migration_vector = [
                        recent_centroid[0] - older_centroid[0],
                        recent_centroid[1] - older_centroid[1]
                    ]
                    stress_indicators["migration_vector"] = migration_vector
            
            # Overall stress pattern classification
            stress_pattern = self._classify_stress_pattern(stress_indicators)
            
            return {
                "stress_pattern": stress_pattern,
                "stress_indicators": stress_indicators,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "earthquake_count": len(earthquakes)
            }
            
        except Exception as e:
            logger.error(f"Error in stress pattern analysis: {str(e)}")
            return {
                "stress_pattern": "analysis_error",
                "stress_indicators": {},
                "error": str(e)
            }
    
    def _classify_stress_pattern(self, indicators: Dict[str, Any]) -> str:
        """
        Classify the stress accumulation pattern based on indicators
        """
        # Define classification rules
        magnitude_trend = indicators.get("magnitude_trend", 0)
        clustering_coeff = indicators.get("clustering_coefficient", 0)
        energy_rate = indicators.get("energy_accumulation_rate", 0)
        spatial_spread = indicators.get("spatial_spread", 0)
        
        if magnitude_trend > 0.1 and clustering_coeff > 0.3:
            return "escalating_sequence"
        elif clustering_coeff > 0.5 and spatial_spread < 0.1:
            return "tight_clustering"
        elif energy_rate > 2.0:
            return "rapid_energy_release"
        elif magnitude_trend < -0.1:
            return "decreasing_activity"
        elif spatial_spread > 0.3:
            return "distributed_activity"
        else:
            return "normal_background"

class CombinedEarthquakeService:
    """
    Advanced earthquake service combining multiple data sources with ML predictions
    Enhanced with comprehensive global, Indian, and Japanese earthquake sources
    """
    
    def __init__(self):
        self.usgs_service = EarthquakeService()
        self.indian_service = IndianEarthquakeService()
        self.japanese_service = JapaneseEarthquakeService()
        self.global_service = GlobalEarthquakeService()
        self.ml_predictor = EarthquakeMLPredictor()
        
    async def get_comprehensive_analysis(self, latitude: float, longitude: float, radius_km: float = 500) -> Dict[str, Any]:
        """
        Get comprehensive earthquake analysis with ML predictions from multiple sources
        """
        try:
            # Determine region and fetch appropriate data
            region = self._determine_region(latitude, longitude)
            
            # Fetch data from multiple sources in parallel
            tasks = []
            
            # Always fetch USGS data
            tasks.append(self.usgs_service.get_earthquakes_by_location(latitude, longitude, int(radius_km)))
            
            # Add regional sources
            if region == "india":
                tasks.append(self.indian_service.get_indian_earthquakes(latitude, longitude, int(radius_km)))
            elif region == "japan":
                tasks.append(self.japanese_service.get_japanese_earthquakes(latitude, longitude, int(radius_km)))
            
            # Add global sources for comprehensive coverage
            tasks.append(self.global_service.get_global_earthquakes(latitude, longitude, int(radius_km * 2)))  # Wider radius for global
            
            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine all earthquake data
            all_earthquakes = []
            data_sources = ["USGS"]
            
            for i, result in enumerate(results):
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                    if i == 1:  # Regional source
                        if region == "india":
                            data_sources.append("Indian_Geological_Multi")
                        elif region == "japan":
                            data_sources.append("Japanese_Seismic_Multi")
                    elif i == 2 or (i == 1 and region == "global"):  # Global source
                        data_sources.append("Global_Multi_Source")
                elif isinstance(result, Exception):
                    logger.warning(f"Data source {i} failed: {str(result)}")
            
            # Remove duplicates and sort
            all_earthquakes = self._combine_earthquake_data_enhanced(all_earthquakes)
            
            # Train ML models on comprehensive historical data
            if len(all_earthquakes) >= 10:
                await self._train_ml_models(all_earthquakes, latitude, longitude)
            
            # Generate ML predictions
            predictions = self.ml_predictor.predict_earthquake_probability(all_earthquakes, latitude, longitude)
            
            # Perform stress analysis
            stress_analysis = self.ml_predictor.analyze_stress_patterns(all_earthquakes, latitude, longitude)
            
            # Calculate risk assessment
            risk_assessment = self._calculate_comprehensive_risk(all_earthquakes, predictions, stress_analysis, latitude, longitude)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(predictions, stress_analysis, risk_assessment)
            
            return {
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "region": region,
                    "analysis_radius_km": radius_km
                },
                "earthquake_data": {
                    "total_earthquakes": len(all_earthquakes),
                    "recent_earthquakes": [eq.to_dict() for eq in all_earthquakes[:15]],  # More earthquakes
                    "data_sources": data_sources,
                    "source_coverage": {
                        "usgs_global": True,
                        "regional_specialized": region in ["india", "japan"],
                        "multi_source_feeds": True,
                        "real_time_feeds": True
                    }
                },
                "ml_predictions": predictions,
                "stress_analysis": stress_analysis,
                "risk_assessment": risk_assessment,
                "recommendations": recommendations,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "model_info": {
                    "ml_trained": self.ml_predictor.is_trained,
                    "feature_count": 18,
                    "model_types": ["RandomForest", "IsolationForest"],
                    "data_sources_count": len(data_sources)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {str(e)}")
            return {
                "error": str(e),
                "location": {"latitude": latitude, "longitude": longitude},
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
    
    def _combine_earthquake_data_enhanced(self, all_earthquakes: List[EarthquakeData]) -> List[EarthquakeData]:
        """
        Enhanced method to combine and deduplicate earthquake data from multiple sources
        """
        if not all_earthquakes:
            return []
        
        # Remove duplicates using the enhanced method
        unique_earthquakes = IndianEarthquakeService._remove_duplicates(all_earthquakes)
        
        # Sort by time (most recent first)
        unique_earthquakes.sort(key=lambda x: x.time, reverse=True)
        
        logger.info(f"Combined {len(all_earthquakes)} earthquakes into {len(unique_earthquakes)} unique events")
        return unique_earthquakes
    
    def _determine_region(self, latitude: float, longitude: float) -> str:
        """Determine geographical region for specialized data sources with enhanced Indian detection"""
        # Enhanced India region detection (including Pakistan, Bangladesh, Sri Lanka, Nepal, Bhutan)
        if 6 <= latitude <= 38 and 68 <= longitude <= 98:
            return "india"
        # Japan region (including extended EEZ)
        elif 24 <= latitude <= 46 and 123 <= longitude <= 146:
            return "japan"
        # China region
        elif 18 <= latitude <= 54 and 73 <= longitude <= 135:
            return "china"
        # Indonesia/Southeast Asia
        elif -11 <= latitude <= 21 and 95 <= longitude <= 141:
            return "indonesia"
        # Turkey/Middle East
        elif 35 <= latitude <= 42 and 26 <= longitude <= 45:
            return "turkey"
        # California/West Coast
        elif 32 <= latitude <= 42 and -125 <= longitude <= -114:
            return "california"
        # Chile
        elif -56 <= latitude <= -17 and -76 <= longitude <= -66:
            return "chile"
        else:
            return "global"
    
    def _combine_earthquake_data(self, usgs_data: List[EarthquakeData], additional_data: List[EarthquakeData]) -> List[EarthquakeData]:
        """
        Combine and deduplicate earthquake data from multiple sources
        """
        combined = list(usgs_data)
        
        # Add additional data while avoiding duplicates
        for additional_eq in additional_data:
            is_duplicate = False
            for existing_eq in combined:
                # Check for potential duplicates (same location and time within tolerance)
                time_diff = abs((
                    datetime.fromisoformat(additional_eq.time.replace('Z', '')) - 
                    datetime.fromisoformat(existing_eq.time.replace('Z', ''))
                ).total_seconds())
                
                distance_diff = geodesic(
                    (additional_eq.latitude, additional_eq.longitude),
                    (existing_eq.latitude, existing_eq.longitude)
                ).kilometers
                
                if time_diff < 1800 and distance_diff < 10:  # 30 minutes and 10km tolerance
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                combined.append(additional_eq)
        
        # Sort by time (most recent first)
        combined.sort(key=lambda x: x.time, reverse=True)
        
        return combined
    
    async def _train_ml_models(self, earthquakes: List[EarthquakeData], latitude: float, longitude: float):
        """Train ML models on historical data"""
        try:
            # Use older earthquakes for training (exclude very recent ones)
            training_data = earthquakes[5:] if len(earthquakes) > 10 else earthquakes
            
            # Train in background to avoid blocking
            self.ml_predictor.train_models(training_data, latitude, longitude)
            
        except Exception as e:
            logger.error(f"Error training ML models: {str(e)}")
    
    def _calculate_comprehensive_risk(self, earthquakes: List[EarthquakeData], predictions: Dict[str, Any], 
                                    stress_analysis: Dict[str, Any], latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Calculate comprehensive risk assessment
        """
        try:
            # Base risk from recent activity
            recent_24h = [eq for eq in earthquakes if 
                         (datetime.utcnow() - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 86400]
            recent_7d = [eq for eq in earthquakes if 
                        (datetime.utcnow() - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 604800]
            
            # Activity-based risk
            activity_risk = min(0.9, len(recent_24h) * 0.2 + len(recent_7d) * 0.05)
            
            # ML prediction risk
            ml_risk = predictions.get("probability_7d", 0.3)
            
            # Stress pattern risk
            stress_pattern = stress_analysis.get("stress_pattern", "normal_background")
            stress_risk_map = {
                "escalating_sequence": 0.8,
                "tight_clustering": 0.7,
                "rapid_energy_release": 0.9,
                "distributed_activity": 0.4,
                "decreasing_activity": 0.2,
                "normal_background": 0.3
            }
            stress_risk = stress_risk_map.get(stress_pattern, 0.3)
            
            # Regional risk
            regional_risk = self.ml_predictor._get_regional_risk_score(latitude, longitude)
            
            # Combined risk calculation
            overall_risk = (
                activity_risk * 0.3 +
                ml_risk * 0.4 +
                stress_risk * 0.2 +
                regional_risk * 0.1
            )
            
            # Risk categorization
            if overall_risk >= 0.8:
                risk_level = "very_high"
                risk_color = "#FF0000"
            elif overall_risk >= 0.6:
                risk_level = "high"
                risk_color = "#FF6600"
            elif overall_risk >= 0.4:
                risk_level = "moderate"
                risk_color = "#FFA500"
            elif overall_risk >= 0.2:
                risk_level = "low"
                risk_color = "#FFFF00"
            else:
                risk_level = "very_low"
                risk_color = "#00FF00"
            
            return {
                "overall_risk_score": round(overall_risk, 3),
                "risk_level": risk_level,
                "risk_color": risk_color,
                "risk_components": {
                    "recent_activity": round(activity_risk, 3),
                    "ml_prediction": round(ml_risk, 3),
                    "stress_pattern": round(stress_risk, 3),
                    "regional_baseline": round(regional_risk, 3)
                },
                "confidence_level": predictions.get("confidence", 0.5),
                "time_horizon_days": 7
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk: {str(e)}")
            return {
                "overall_risk_score": 0.3,
                "risk_level": "unknown",
                "risk_color": "#808080",
                "error": str(e)
            }
    
    def _generate_recommendations(self, predictions: Dict[str, Any], stress_analysis: Dict[str, Any], 
                                risk_assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate actionable recommendations based on analysis
        """
        recommendations = []
        
        risk_level = risk_assessment.get("risk_level", "unknown")
        stress_pattern = stress_analysis.get("stress_pattern", "normal_background")
        
        # High risk recommendations
        if risk_level in ["very_high", "high"]:
            recommendations.extend([
                {
                    "priority": "critical",
                    "type": "emergency_preparedness",
                    "title": "Enhanced Emergency Preparedness",
                    "description": "Review and update emergency kits, evacuation plans, and communication protocols.",
                    "icon": "AlertTriangle"
                },
                {
                    "priority": "high",
                    "type": "monitoring",
                    "title": "Increased Monitoring",
                    "description": "Monitor seismic activity closely. Consider temporary relocation if possible.",
                    "icon": "Eye"
                }
            ])
        
        # Stress pattern specific recommendations
        if stress_pattern == "escalating_sequence":
            recommendations.append({
                "priority": "high",
                "type": "alert",
                "title": "Escalating Sequence Detected",
                "description": "Seismic activity shows escalating pattern. Avoid non-essential travel to affected areas.",
                "icon": "TrendingUp"
            })
        
        elif stress_pattern == "tight_clustering":
            recommendations.append({
                "priority": "medium",
                "type": "localized_risk",
                "title": "Localized Seismic Cluster",
                "description": "Earthquake activity concentrated in small area. Monitor local geological conditions.",
                "icon": "MapPin"
            })
        
        # ML model recommendations
        if predictions.get("anomaly_detected", False):
            recommendations.append({
                "priority": "high",
                "type": "anomaly",
                "title": "Seismic Anomaly Detected",
                "description": "ML models detected unusual seismic patterns. Increased vigilance recommended.",
                "icon": "AlertCircle"
            })
        
        # General safety recommendations
        recommendations.extend([
            {
                "priority": "medium",
                "type": "preparation",
                "title": "Structural Assessment",
                "description": "Ensure buildings meet seismic safety standards. Secure heavy objects.",
                "icon": "Shield"
            },
            {
                "priority": "low",
                "type": "education",
                "title": "Emergency Training",
                "description": "Practice drop, cover, and hold on drills. Learn earthquake safety procedures.",
                "icon": "BookOpen"
            }
        ])
        
        return recommendations

# Global combined service instance
combined_service = CombinedEarthquakeService()

# API Endpoints
@app.get("/")
async def read_root():
    return {
        "message": "Advanced Earthquake Prediction and Analysis API",
        "version": "2.0.0",
        "features": [
            "Multi-source earthquake data",
            "Machine Learning predictions",
            "Stress pattern analysis",
            "Risk assessment",
            "Regional specialization"
        ],
        "endpoints": {
            "earthquake_analysis": "/earthquake-analysis",
            "recent_earthquakes": "/earthquakes/recent",
            "ml_predictions": "/predictions/ml",
            "stress_analysis": "/analysis/stress",
            "risk_assessment": "/assessment/risk"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

@app.get("/earthquake-analysis")
async def comprehensive_earthquake_analysis(
    latitude: float,
    longitude: float,
    radius_km: float = 500
):
    """
    Comprehensive earthquake analysis with ML predictions
    """
    return await combined_service.get_comprehensive_analysis(latitude, longitude, radius_km)

@app.get("/earthquakes/recent")
async def get_recent_earthquakes(
    latitude: float,
    longitude: float,
    radius_km: float = 500,
    source: str = "auto"
):
    """
    Get recent earthquakes from specified or automatic source selection
    Enhanced for Indian subcontinent with comprehensive coverage
    """
    try:
        if source == "usgs":
            service = combined_service.usgs_service
            earthquakes = await service.get_earthquakes_by_location(latitude, longitude, int(radius_km))
            return [eq.to_dict() for eq in earthquakes]
        elif source == "indian":
            service = combined_service.indian_service
            earthquakes = await service.get_indian_earthquakes(latitude, longitude, int(radius_km))
            return [eq.to_dict() for eq in earthquakes]
        elif source == "japanese":
            service = combined_service.japanese_service
            earthquakes = await service.get_japanese_earthquakes(latitude, longitude, int(radius_km))
            return [eq.to_dict() for eq in earthquakes]
        else:
            # Auto-select based on location with enhanced Indian handling
            region = combined_service._determine_region(latitude, longitude)
            usgs_data = await combined_service.usgs_service.get_earthquakes_by_location(latitude, longitude, int(radius_km))
            
            additional_data = []
            if region == "india":
                # For India, use enhanced radius and lower magnitude threshold
                enhanced_radius = max(int(radius_km), 800)
                additional_data = await combined_service.indian_service.get_indian_earthquakes(
                    latitude, longitude, enhanced_radius
                )
                logger.info(f"Indian region detected: Using enhanced radius {enhanced_radius}km and comprehensive sources")
            elif region == "japan":
                additional_data = await combined_service.japanese_service.get_japanese_earthquakes(latitude, longitude, int(radius_km))
            else:
                # For other regions, also get global data
                additional_data = await combined_service.global_service.get_global_earthquakes(latitude, longitude, int(radius_km * 1.5))
            
            combined_data = combined_service._combine_earthquake_data(usgs_data, additional_data)
            result = [eq.to_dict() for eq in combined_data]
            
            logger.info(f"Recent earthquakes query for {region}: Found {len(result)} earthquakes")
            return result
            
    except Exception as e:
        logger.error(f"Error in recent earthquakes endpoint: {str(e)}")
        return {"error": str(e), "earthquakes": []}

@app.get("/predictions/ml")
async def get_ml_predictions(
    latitude: float,
    longitude: float,
    radius_km: float = 500
):
    """
    Get ML-based earthquake predictions
    """
    # Get recent earthquake data
    usgs_data = await combined_service.usgs_service.get_earthquakes_by_location(latitude, longitude, int(radius_km))
    
    # Train models if enough data
    if len(usgs_data) >= 10:
        await combined_service._train_ml_models(usgs_data, latitude, longitude)
    
    # Generate predictions
    predictions = combined_service.ml_predictor.predict_earthquake_probability(usgs_data, latitude, longitude)
    
    return {
        "location": {"latitude": latitude, "longitude": longitude},
        "predictions": predictions,
        "data_points_used": len(usgs_data),
        "analysis_timestamp": datetime.utcnow().isoformat()
    }

@app.get("/analysis/stress")
async def get_stress_analysis(
    latitude: float,
    longitude: float,
    radius_km: float = 500
):
    """
    Get detailed stress pattern analysis
    """
    # Get recent earthquake data
    usgs_data = await combined_service.usgs_service.get_earthquakes_by_location(latitude, longitude, int(radius_km))
    
    # Perform stress analysis
    stress_analysis = combined_service.ml_predictor.analyze_stress_patterns(usgs_data, latitude, longitude)
    
    return {
        "location": {"latitude": latitude, "longitude": longitude},
        "stress_analysis": stress_analysis,
        "earthquake_count": len(usgs_data),
        "analysis_timestamp": datetime.utcnow().isoformat()
    }

def convert_stress_pattern_to_level(stress_pattern: str, stress_indicators: Dict[str, Any]) -> tuple[str, float]:
    """
    Convert stress pattern to stress level and numerical score
    """
    # Pattern to level mapping
    pattern_mapping = {
        "escalating_sequence": ("High", 85.0),
        "tight_clustering": ("High", 80.0),
        "rapid_energy_release": ("Critical", 95.0),
        "decreasing_activity": ("Low", 25.0),
        "distributed_activity": ("Medium", 50.0),
        "normal_background": ("Low", 15.0),
        "insufficient_data": ("Unknown", 0.0),
        "analysis_error": ("Unknown", 0.0)
    }
    
    base_level, base_score = pattern_mapping.get(stress_pattern, ("Unknown", 0.0))
    
    # Adjust score based on indicators
    score_adjustment = 0.0
    
    if stress_indicators:
        # Magnitude trend adjustment
        magnitude_trend = stress_indicators.get("magnitude_trend", 0)
        if magnitude_trend > 0.1:
            score_adjustment += 10.0
        elif magnitude_trend < -0.1:
            score_adjustment -= 10.0
        
        # Clustering coefficient adjustment
        clustering_coeff = stress_indicators.get("clustering_coefficient", 0)
        if clustering_coeff > 0.5:
            score_adjustment += 15.0
        
        # Energy accumulation rate adjustment
        energy_rate = stress_indicators.get("energy_accumulation_rate", 0)
        if energy_rate > 2.0:
            score_adjustment += 20.0
        
        # Spatial spread adjustment
        spatial_spread = stress_indicators.get("spatial_spread", 0)
        if spatial_spread < 0.1:  # Very localized
            score_adjustment += 5.0
        elif spatial_spread > 0.3:  # Very distributed
            score_adjustment -= 5.0
    
    # Calculate final score and level
    final_score = max(0.0, min(100.0, base_score + score_adjustment))
    
    # Determine final level based on adjusted score
    if final_score >= 80:
        final_level = "Critical"
    elif final_score >= 60:
        final_level = "High"
    elif final_score >= 40:
        final_level = "Medium"
    elif final_score >= 20:
        final_level = "Low"
    else:
        final_level = "Unknown" if final_score == 0.0 else "Low"
    
    return final_level, final_score

@app.post("/analysis/stress")
async def post_stress_analysis(request: LocationRequest):
    """
    Get detailed stress pattern analysis (POST version)
    """
    # Get recent earthquake data
    usgs_data = await combined_service.usgs_service.get_earthquakes_by_location(
        request.latitude, 
        request.longitude, 
        request.radius_km
    )
    
    # Perform stress analysis
    stress_analysis = combined_service.ml_predictor.analyze_stress_patterns(usgs_data, request.latitude, request.longitude)
    
    # Convert stress pattern to stress level and calculate score
    stress_pattern = stress_analysis.get("stress_pattern", "normal_background")
    stress_level, stress_score = convert_stress_pattern_to_level(stress_pattern, stress_analysis.get("stress_indicators", {}))
    
    return {
        "location": {"latitude": request.latitude, "longitude": request.longitude},
        "stress_analysis": stress_analysis,
        "stress_level": stress_level,
        "stress_score": stress_score,
        "earthquake_count": len(usgs_data),
        "analysis_timestamp": datetime.utcnow().isoformat()
    }

@app.get("/assessment/risk")
async def get_risk_assessment(
    latitude: float,
    longitude: float,
    radius_km: float = 500
):
    """
    Get comprehensive risk assessment
    """
    # Get earthquake data
    usgs_data = await combined_service.usgs_service.get_earthquakes_by_location(latitude, longitude, int(radius_km))
    
    # Generate predictions and stress analysis
    predictions = combined_service.ml_predictor.predict_earthquake_probability(usgs_data, latitude, longitude)
    stress_analysis = combined_service.ml_predictor.analyze_stress_patterns(usgs_data, latitude, longitude)
    
    # Calculate risk assessment
    risk_assessment = combined_service._calculate_comprehensive_risk(usgs_data, predictions, stress_analysis, latitude, longitude)
    
    # Generate recommendations
    recommendations = combined_service._generate_recommendations(predictions, stress_analysis, risk_assessment)
    
    return {
        "location": {"latitude": latitude, "longitude": longitude},
        "risk_assessment": risk_assessment,
        "recommendations": recommendations,
        "analysis_timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
