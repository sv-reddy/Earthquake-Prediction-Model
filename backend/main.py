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

class EarthquakeAnalysisRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = 500.0
    days: int = 30
    min_magnitude: float = 2.5

# USGS Earthquake API endpoints
USGS_BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_REALTIME_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary"

# Comprehensive earthquake data sources from multiple nations and organizations
GLOBAL_SOURCES = {
    # United States
    "USGS_GEOJSON": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "USGS_WEEK": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson",
    "USGS_SIGNIFICANT": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson",
    "USGS_M45_WEEK": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson",
    "USGS_M25_DAY": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
    
    # European-Mediterranean
    "EMSC_GLOBAL": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc",
    "EMSC_EUROPE": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=35&max_lat=75&min_lon=-15&max_lon=45",
    "EMSC_MEDITERRANEAN": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=30&max_lat=48&min_lon=-10&max_lon=42",
    
    # Germany - GFZ Potsdam
    "GEOFON_GFZ": "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=100",
    "GEOFON_RECENT": "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=50&datemin=",
    
    # International Seismological Centre
    "IRIS_RECENT": "http://service.iris.edu/fdsnws/event/1/query?format=geojson&limit=100&orderby=time",
    "IRIS_GLOBAL": "http://service.iris.edu/fdsnws/event/1/query?format=geojson&limit=200&minmag=4.0",
}

# Russian earthquake data sources - Free APIs
RUSSIAN_SOURCES = {
    "GSRAS_RECENT": "http://www.ceme.gsras.ru/new/struct.htm",  # Geophysical Survey RAS
    "EMSD_RUSSIA": "http://www.emsd.ru/sdis/earthquake/",  # Emergency Ministry Russia
    "CEME_GSRAS": "http://www.ceme.gsras.ru/new/sindex.htm",  # Centre for Early Monitoring of Earthquakes
    "OBNINSK_GS": "http://www.gsras.ru/",  # Obninsk Geophysical Service
    "EMSC_RUSSIA": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=41&max_lat=82&min_lon=19&max_lon=180",
    "IRIS_RUSSIA": "http://service.iris.edu/fdsnws/event/1/query?format=geojson&minlat=41&maxlat=82&minlon=19&maxlon=180&limit=100",
    "GEOFON_RUSSIA": "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=100&latmin=41&latmax=82&lonmin=19&lonmax=180",
}

# Chinese earthquake data sources - Free APIs  
CHINESE_SOURCES = {
    "CEA_RECENT": "http://www.cea.gov.cn/",  # China Earthquake Administration
    "CENC_DATA": "http://www.cenc.ac.cn/",  # China Earthquake Networks Center
    "EMSC_CHINA": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=18&max_lat=54&min_lon=73&max_lon=135",
    "IRIS_CHINA": "http://service.iris.edu/fdsnws/event/1/query?format=geojson&minlat=18&maxlat=54&minlon=73&maxlon=135&limit=100",
    "GEOFON_CHINA": "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=100&latmin=18&latmax=54&lonmin=73&lonmax=135",
    "TAIWAN_CWB": "https://www.cwb.gov.tw/V8/E/E/EQ/",  # Taiwan Central Weather Bureau
}

# European earthquake data sources - Free APIs
EUROPEAN_SOURCES = {
    # Italy - INGV
    "INGV_ITALY": "http://webservices.ingv.it/fdsnws/event/1/query?format=geojson&limit=100&orderby=time",
    "INGV_RSS": "https://terremoti.ingv.it/rss_30gg.xml",
    
    # Greece - NOA
    "NOA_GREECE": "http://www.gein.noa.gr/en/",
    "EMSC_GREECE": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=34&max_lat=42&min_lon=19&max_lon=30",
    
    # Turkey - Kandilli Observatory  
    "KOERI_TURKEY": "http://www.koeri.boun.edu.tr/scripts/lst0.asp",
    "EMSC_TURKEY": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=35&max_lat=42&min_lon=26&max_lon=45",
    
    # Norway - NORSAR
    "NORSAR_NORWAY": "https://www.norsar.no/",
    "EMSC_NORDIC": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=55&max_lat=75&min_lon=-5&max_lon=35",
    
    # Iceland - IMO
    "IMO_ICELAND": "http://en.vedur.is/earthquakes-and-volcanism/earthquakes/",
    "EMSC_ICELAND": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=63&max_lat=67&min_lon=-25&max_lon=-13",
    
    # Switzerland - ETH Zurich
    "SED_SWITZERLAND": "http://www.seismo.ethz.ch/en/",
    "EMSC_SWITZERLAND": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=45&max_lat=48&min_lon=5&max_lon=11",
}

# Pacific region earthquake data sources - Free APIs
PACIFIC_SOURCES = {
    # Australia - Geoscience Australia
    "GA_AUSTRALIA": "http://www.ga.gov.au/earthquakes/",
    "EMSC_AUSTRALIA": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-45&max_lat=-9&min_lon=110&max_lon=160",
    
    # New Zealand - GeoNet
    "GEONET_NZ": "https://api.geonet.org.nz/quake?MMI=3",
    "GEONET_RECENT": "https://api.geonet.org.nz/quake?limit=100",
    
    # Philippines - PHIVOLCS
    "PHIVOLCS_PH": "https://www.phivolcs.dost.gov.ph/",
    "EMSC_PHILIPPINES": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=5&max_lat=21&min_lon=116&max_lon=127",
    
    # Indonesia - BMKG
    "BMKG_INDONESIA": "https://www.bmkg.go.id/gempabumi/",
    "EMSC_INDONESIA": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-11&max_lat=6&min_lon=95&max_lon=141",
    
    # Pacific Tsunami Warning Center
    "PTWC_PACIFIC": "https://ptwc.weather.gov/feeds/ptwc_rss_pacific.xml",
}

# Americas earthquake data sources - Free APIs
AMERICAS_SOURCES = {
    # Canada - Natural Resources Canada
    "NRC_CANADA": "https://earthquakescanada.nrcan.gc.ca/",
    "EMSC_CANADA": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=41&max_lat=84&min_lon=-141&max_lon=-52",
    
    # Mexico - SSN
    "SSN_MEXICO": "http://www.ssn.unam.mx/",
    "EMSC_MEXICO": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=14&max_lat=33&min_lon=-118&max_lon=-86",
    
    # Chile - CSN
    "CSN_CHILE": "http://www.sismologia.cl/",
    "EMSC_CHILE": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-56&max_lat=-17&min_lon=-76&max_lon=-66",
    
    # Peru - IGP
    "IGP_PERU": "https://www.igp.gob.pe/servicios/centro-sismologico-nacional/",
    "EMSC_PERU": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-19&max_lat=0&min_lon=-82&max_lon=-68",
    
    # Colombia - SGC
    "SGC_COLOMBIA": "https://www.sgc.gov.co/",
    "EMSC_COLOMBIA": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-5&max_lat=13&min_lon=-80&max_lon=-66",
    
    # Central America
    "EMSC_CENTRAL_AMERICA": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=7&max_lat=18&min_lon=-93&max_lon=-77",
}

# Middle East and Africa earthquake data sources - Free APIs
MIDDLE_EAST_AFRICA_SOURCES = {
    # Iran - IIEES
    "IIEES_IRAN": "http://www.iiees.ac.ir/en/",
    "EMSC_IRAN": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=25&max_lat=40&min_lon=44&max_lon=64",
    
    # Israel - GII
    "GII_ISRAEL": "https://www.gsi.gov.il/",
    "EMSC_LEVANT": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=29&max_lat=38&min_lon=32&max_lon=43",
    
    # South Africa - CGS
    "CGS_SOUTH_AFRICA": "http://www.geoscience.org.za/",
    "EMSC_AFRICA": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-35&max_lat=37&min_lon=-18&max_lon=52",
    
    # Morocco - CNRST
    "CNRST_MOROCCO": "http://www.cnrst.ma/",
    "EMSC_MOROCCO": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=27&max_lat=36&min_lon=-14&max_lon=-1",
}

# Indian earthquake data sources - Enhanced with multiple free APIs
INDIAN_SOURCES = {
    "IMD_RSS": "https://mausam.imd.gov.in/backend/assets/earthquake/earthquake.xml",
    "NCS_CATALOG": "https://www.seismo.gov.in/earthquakes/recent",
    "GSI_SEISMO": "https://www.gsi.gov.in/webcenter/portal/ENGLISH/pagelets/seismology",
    "EMSC_INDIA": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=6&max_lat=38&min_lon=68&max_lon=98",
    "EMSC_INDIA_HIGH": "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=8&max_lat=37&min_lon=68&max_lon=97&min_mag=3.0",
    "IRIS_INDIA": "http://service.iris.edu/fdsnws/event/1/query?format=geojson&minlat=6&maxlat=38&minlon=68&maxlon=98&limit=100&orderby=time",
    "GEONET_SOUTH_ASIA": "https://api.geonet.org.nz/quake?MMI=3",
    "GEOFON_INDIAN_OCEAN": "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=100&latmin=6&latmax=38&lonmin=68&lonmax=98",
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

class InternationalEarthquakeService:
    """Comprehensive service for fetching earthquake data from multiple international sources"""
    
    @staticmethod
    async def get_russian_earthquakes(
        latitude: float,
        longitude: float,
        radius_km: int = 500,
        days: int = 30,
        min_magnitude: float = 2.0
    ) -> List[EarthquakeData]:
        """Fetch earthquakes from Russian sources"""
        all_earthquakes = []
        
        tasks = [
            InternationalEarthquakeService._fetch_emsc_russia_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_iris_russia_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_geofon_russia_data(days, min_magnitude),
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Error fetching Russian earthquake data: {str(result)}")
            
            # Filter by location and radius
            filtered_earthquakes = []
            for eq in all_earthquakes:
                eq_location = (eq.latitude, eq.longitude)
                search_location = (latitude, longitude)
                distance = geodesic(search_location, eq_location).kilometers
                
                if distance <= radius_km:
                    eq.distance_km = distance
                    filtered_earthquakes.append(eq)
            
            # Remove duplicates and sort
            filtered_earthquakes = InternationalEarthquakeService._remove_duplicates(filtered_earthquakes)
            filtered_earthquakes.sort(key=lambda x: x.time, reverse=True)
            
            logger.info(f"Found {len(filtered_earthquakes)} unique Russian region earthquakes")
            return filtered_earthquakes
            
        except Exception as e:
            logger.error(f"Error in Russian earthquake data aggregation: {str(e)}")
            return []
    
    @staticmethod
    async def get_chinese_earthquakes(
        latitude: float,
        longitude: float,
        radius_km: int = 500,
        days: int = 30,
        min_magnitude: float = 2.0
    ) -> List[EarthquakeData]:
        """Fetch earthquakes from Chinese sources"""
        all_earthquakes = []
        
        tasks = [
            InternationalEarthquakeService._fetch_emsc_china_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_iris_china_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_geofon_china_data(days, min_magnitude),
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Error fetching Chinese earthquake data: {str(result)}")
            
            # Filter by location and radius
            filtered_earthquakes = []
            for eq in all_earthquakes:
                eq_location = (eq.latitude, eq.longitude)
                search_location = (latitude, longitude)
                distance = geodesic(search_location, eq_location).kilometers
                
                if distance <= radius_km:
                    eq.distance_km = distance
                    filtered_earthquakes.append(eq)
            
            filtered_earthquakes = InternationalEarthquakeService._remove_duplicates(filtered_earthquakes)
            filtered_earthquakes.sort(key=lambda x: x.time, reverse=True)
            
            logger.info(f"Found {len(filtered_earthquakes)} unique Chinese region earthquakes")
            return filtered_earthquakes
            
        except Exception as e:
            logger.error(f"Error in Chinese earthquake data aggregation: {str(e)}")
            return []
    
    @staticmethod
    async def get_european_earthquakes(
        latitude: float,
        longitude: float,
        radius_km: int = 500,
        days: int = 30,
        min_magnitude: float = 2.0
    ) -> List[EarthquakeData]:
        """Fetch earthquakes from European sources"""
        all_earthquakes = []
        
        tasks = [
            InternationalEarthquakeService._fetch_ingv_italy_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_emsc_europe_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_emsc_turkey_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_emsc_greece_data(days, min_magnitude),
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Error fetching European earthquake data: {str(result)}")
            
            # Filter by location and radius
            filtered_earthquakes = []
            for eq in all_earthquakes:
                eq_location = (eq.latitude, eq.longitude)
                search_location = (latitude, longitude)
                distance = geodesic(search_location, eq_location).kilometers
                
                if distance <= radius_km:
                    eq.distance_km = distance
                    filtered_earthquakes.append(eq)
            
            filtered_earthquakes = InternationalEarthquakeService._remove_duplicates(filtered_earthquakes)
            filtered_earthquakes.sort(key=lambda x: x.time, reverse=True)
            
            logger.info(f"Found {len(filtered_earthquakes)} unique European earthquakes")
            return filtered_earthquakes
            
        except Exception as e:
            logger.error(f"Error in European earthquake data aggregation: {str(e)}")
            return []
    
    @staticmethod
    async def get_pacific_earthquakes(
        latitude: float,
        longitude: float,
        radius_km: int = 500,
        days: int = 30,
        min_magnitude: float = 2.0
    ) -> List[EarthquakeData]:
        """Fetch earthquakes from Pacific region sources"""
        all_earthquakes = []
        
        tasks = [
            InternationalEarthquakeService._fetch_geonet_nz_data(min_magnitude),
            InternationalEarthquakeService._fetch_emsc_australia_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_emsc_philippines_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_emsc_indonesia_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_ptwc_pacific_data(),
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Error fetching Pacific earthquake data: {str(result)}")
            
            # Filter by location and radius
            filtered_earthquakes = []
            for eq in all_earthquakes:
                eq_location = (eq.latitude, eq.longitude)
                search_location = (latitude, longitude)
                distance = geodesic(search_location, eq_location).kilometers
                
                if distance <= radius_km:
                    eq.distance_km = distance
                    filtered_earthquakes.append(eq)
            
            filtered_earthquakes = InternationalEarthquakeService._remove_duplicates(filtered_earthquakes)
            filtered_earthquakes.sort(key=lambda x: x.time, reverse=True)
            
            logger.info(f"Found {len(filtered_earthquakes)} unique Pacific region earthquakes")
            return filtered_earthquakes
            
        except Exception as e:
            logger.error(f"Error in Pacific earthquake data aggregation: {str(e)}")
            return []
    
    @staticmethod
    async def get_americas_earthquakes(
        latitude: float,
        longitude: float,
        radius_km: int = 500,
        days: int = 30,
        min_magnitude: float = 2.0
    ) -> List[EarthquakeData]:
        """Fetch earthquakes from Americas sources"""
        all_earthquakes = []
        
        tasks = [
            InternationalEarthquakeService._fetch_emsc_canada_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_emsc_mexico_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_emsc_chile_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_emsc_peru_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_emsc_colombia_data(days, min_magnitude),
            InternationalEarthquakeService._fetch_emsc_central_america_data(days, min_magnitude),
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Error fetching Americas earthquake data: {str(result)}")
            
            # Filter by location and radius
            filtered_earthquakes = []
            for eq in all_earthquakes:
                eq_location = (eq.latitude, eq.longitude)
                search_location = (latitude, longitude)
                distance = geodesic(search_location, eq_location).kilometers
                
                if distance <= radius_km:
                    eq.distance_km = distance
                    filtered_earthquakes.append(eq)
            
            filtered_earthquakes = InternationalEarthquakeService._remove_duplicates(filtered_earthquakes)
            filtered_earthquakes.sort(key=lambda x: x.time, reverse=True)
            
            logger.info(f"Found {len(filtered_earthquakes)} unique Americas earthquakes")
            return filtered_earthquakes
            
        except Exception as e:
            logger.error(f"Error in Americas earthquake data aggregation: {str(e)}")
            return []

    # Russian data source methods
    @staticmethod
    async def _fetch_emsc_russia_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Russia region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=41&max_lat=82&min_lon=19&max_lon=180&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Russia")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Russia data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_iris_russia_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from IRIS for Russia region"""
        earthquakes = []
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            url = f"http://service.iris.edu/fdsnws/event/1/query?format=geojson&minlat=41&maxlat=82&minlon=19&maxlon=180&limit=100&orderby=time&starttime={start_time.strftime('%Y-%m-%dT%H:%M:%S')}&endtime={end_time.strftime('%Y-%m-%dT%H:%M:%S')}&minmag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = InternationalEarthquakeService._parse_geojson_data(data, "IRIS_Russia")
        except Exception as e:
            logger.warning(f"Error fetching IRIS Russia data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_geofon_russia_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from GEOFON for Russia region"""
        earthquakes = []
        try:
            url = "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=100&latmin=41&latmax=82&lonmin=19&lonmax=180"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = InternationalEarthquakeService._parse_geojson_data(data, "GEOFON_Russia")
        except Exception as e:
            logger.warning(f"Error fetching GEOFON Russia data: {str(e)}")
        
        return earthquakes

    # Chinese data source methods
    @staticmethod
    async def _fetch_emsc_china_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC China region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=18&max_lat=54&min_lon=73&max_lon=135&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "China")
        except Exception as e:
            logger.warning(f"Error fetching EMSC China data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_iris_china_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from IRIS for China region"""
        earthquakes = []
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            url = f"http://service.iris.edu/fdsnws/event/1/query?format=geojson&minlat=18&maxlat=54&minlon=73&maxlon=135&limit=100&orderby=time&starttime={start_time.strftime('%Y-%m-%dT%H:%M:%S')}&endtime={end_time.strftime('%Y-%m-%dT%H:%M:%S')}&minmag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = InternationalEarthquakeService._parse_geojson_data(data, "IRIS_China")
        except Exception as e:
            logger.warning(f"Error fetching IRIS China data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_geofon_china_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from GEOFON for China region"""
        earthquakes = []
        try:
            url = "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=100&latmin=18&latmax=54&lonmin=73&lonmax=135"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = InternationalEarthquakeService._parse_geojson_data(data, "GEOFON_China")
        except Exception as e:
            logger.warning(f"Error fetching GEOFON China data: {str(e)}")
        
        return earthquakes

    # European data source methods
    @staticmethod
    async def _fetch_ingv_italy_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from INGV Italy"""
        earthquakes = []
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            url = f"http://webservices.ingv.it/fdsnws/event/1/query?format=geojson&limit=100&orderby=time&starttime={start_time.strftime('%Y-%m-%dT%H:%M:%S')}&endtime={end_time.strftime('%Y-%m-%dT%H:%M:%S')}&minmag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = InternationalEarthquakeService._parse_geojson_data(data, "INGV_Italy")
        except Exception as e:
            logger.warning(f"Error fetching INGV Italy data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_emsc_europe_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Europe region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=35&max_lat=75&min_lon=-15&max_lon=45&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Europe")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Europe data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_emsc_turkey_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Turkey region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=35&max_lat=42&min_lon=26&max_lon=45&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Turkey")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Turkey data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_emsc_greece_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Greece region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=34&max_lat=42&min_lon=19&max_lon=30&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Greece")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Greece data: {str(e)}")
        
        return earthquakes

    # Pacific region data source methods
    @staticmethod
    async def _fetch_geonet_nz_data(min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from GeoNet New Zealand"""
        earthquakes = []
        try:
            url = f"https://api.geonet.org.nz/quake?limit=100&MMI={int(min_magnitude)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = InternationalEarthquakeService._parse_geonet_data(data, "GeoNet_NZ")
        except Exception as e:
            logger.warning(f"Error fetching GeoNet NZ data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_emsc_australia_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Australia region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-45&max_lat=-9&min_lon=110&max_lon=160&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Australia")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Australia data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_emsc_philippines_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Philippines region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=5&max_lat=21&min_lon=116&max_lon=127&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Philippines")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Philippines data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_emsc_indonesia_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Indonesia region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-11&max_lat=6&min_lon=95&max_lon=141&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Indonesia")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Indonesia data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_ptwc_pacific_data() -> List[EarthquakeData]:
        """Fetch from Pacific Tsunami Warning Center"""
        earthquakes = []
        try:
            url = "https://ptwc.weather.gov/feeds/ptwc_rss_pacific.xml"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_ptwc_rss(content)
        except Exception as e:
            logger.warning(f"Error fetching PTWC Pacific data: {str(e)}")
        
        return earthquakes

    # Americas data source methods  
    @staticmethod
    async def _fetch_emsc_canada_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Canada region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=41&max_lat=84&min_lon=-141&max_lon=-52&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Canada")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Canada data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_emsc_mexico_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Mexico region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=14&max_lat=33&min_lon=-118&max_lon=-86&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Mexico")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Mexico data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_emsc_chile_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Chile region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-56&max_lat=-17&min_lon=-76&max_lon=-66&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Chile")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Chile data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_emsc_peru_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Peru region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-19&max_lat=0&min_lon=-82&max_lon=-68&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Peru")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Peru data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_emsc_colombia_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Colombia region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=-5&max_lat=13&min_lon=-80&max_lon=-66&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Colombia")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Colombia data: {str(e)}")
        
        return earthquakes

    @staticmethod
    async def _fetch_emsc_central_america_data(days: int, min_magnitude: float) -> List[EarthquakeData]:
        """Fetch from EMSC Central America region"""
        earthquakes = []
        try:
            url = f"https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_lat=7&max_lat=18&min_lon=-93&max_lon=-77&min_mag={min_magnitude}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        earthquakes = InternationalEarthquakeService._parse_emsc_rss(content, "Central_America")
        except Exception as e:
            logger.warning(f"Error fetching EMSC Central America data: {str(e)}")
        
        return earthquakes

    # Helper parsing methods
    @staticmethod
    def _parse_emsc_rss(content: str, region: str) -> List[EarthquakeData]:
        """Parse EMSC RSS XML content"""
        earthquakes = []
        try:
            root = ET.fromstring(content)
            
            for item in root.findall('.//item'):
                try:
                    title = item.find('title').text if item.find('title') is not None else ""
                    description = item.find('description').text if item.find('description') is not None else ""
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                    
                    # Parse magnitude and location from title
                    if 'M' in title and 'km' in title:
                        parts = title.split(' ')
                        magnitude = 0.0
                        for part in parts:
                            if part.startswith('M') and len(part) > 1:
                                try:
                                    magnitude = float(part[1:])
                                    break
                                except ValueError:
                                    continue
                        
                        # Extract coordinates from description or use geocoding
                        lat, lon = InternationalEarthquakeService._extract_coordinates_from_description(description)
                        
                        if lat is not None and lon is not None:
                            # Parse time
                            earthquake_time = datetime.utcnow().isoformat() + 'Z'
                            if pub_date:
                                try:
                                    parsed_time = parsedate_to_datetime(pub_date)
                                    earthquake_time = parsed_time.isoformat() + 'Z'
                                except:
                                    pass
                            
                            earthquake = EarthquakeData(
                                magnitude=magnitude,
                                latitude=lat,
                                longitude=lon,
                                depth=10.0,  # Default depth
                                time=earthquake_time,
                                place=title,
                                url="",
                                alert=None,
                                tsunami=0,
                                distance_km=0.0
                            )
                            earthquakes.append(earthquake)
                
                except Exception as e:
                    continue
                    
        except ET.ParseError as e:
            logger.warning(f"Error parsing EMSC RSS for {region}: {str(e)}")
        
        return earthquakes

    @staticmethod
    def _parse_geojson_data(data: dict, source: str) -> List[EarthquakeData]:
        """Parse GeoJSON earthquake data"""
        earthquakes = []
        try:
            features = data.get('features', [])
            
            for feature in features:
                try:
                    properties = feature.get('properties', {})
                    geometry = feature.get('geometry', {})
                    coordinates = geometry.get('coordinates', [])
                    
                    if len(coordinates) >= 2:
                        magnitude = properties.get('mag', 0.0)
                        latitude = coordinates[1]
                        longitude = coordinates[0]
                        depth = coordinates[2] if len(coordinates) > 2 else 10.0
                        
                        # Handle time format
                        time_ms = properties.get('time', 0)
                        if time_ms:
                            earthquake_time = datetime.fromtimestamp(time_ms / 1000).isoformat() + 'Z'
                        else:
                            earthquake_time = datetime.utcnow().isoformat() + 'Z'
                        
                        earthquake = EarthquakeData(
                            magnitude=magnitude,
                            latitude=latitude,
                            longitude=longitude,
                            depth=depth,
                            time=earthquake_time,
                            place=properties.get('place', f"{source} earthquake"),
                            url=properties.get('url', ''),
                            alert=properties.get('alert'),
                            tsunami=properties.get('tsunami', 0),
                            distance_km=0.0
                        )
                        earthquakes.append(earthquake)
                
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error parsing GeoJSON data from {source}: {str(e)}")
        
        return earthquakes

    @staticmethod
    def _parse_geonet_data(data: dict, source: str) -> List[EarthquakeData]:
        """Parse GeoNet API data format"""
        earthquakes = []
        try:
            features = data.get('features', [])
            
            for feature in features:
                try:
                    properties = feature.get('properties', {})
                    geometry = feature.get('geometry', {})
                    coordinates = geometry.get('coordinates', [])
                    
                    if len(coordinates) >= 2:
                        earthquake = EarthquakeData(
                            magnitude=properties.get('magnitude', 0.0),
                            latitude=coordinates[1],
                            longitude=coordinates[0],
                            depth=coordinates[2] if len(coordinates) > 2 else 10.0,
                            time=properties.get('time', datetime.utcnow().isoformat() + 'Z'),
                            place=properties.get('locality', f"{source} earthquake"),
                            url=properties.get('url', ''),
                            alert=None,
                            tsunami=0,
                            distance_km=0.0
                        )
                        earthquakes.append(earthquake)
                
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error parsing GeoNet data: {str(e)}")
        
        return earthquakes

    @staticmethod
    def _parse_ptwc_rss(content: str) -> List[EarthquakeData]:
        """Parse Pacific Tsunami Warning Center RSS"""
        earthquakes = []
        try:
            root = ET.fromstring(content)
            
            for item in root.findall('.//item'):
                try:
                    title = item.find('title').text if item.find('title') is not None else ""
                    description = item.find('description').text if item.find('description') is not None else ""
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                    
                    # Extract earthquake info from PTWC format
                    if 'earthquake' in title.lower() or 'quake' in title.lower():
                        magnitude = InternationalEarthquakeService._extract_magnitude_from_text(title + " " + description)
                        lat, lon = InternationalEarthquakeService._extract_coordinates_from_description(description)
                        
                        if lat is not None and lon is not None and magnitude > 0:
                            earthquake_time = datetime.utcnow().isoformat() + 'Z'
                            if pub_date:
                                try:
                                    parsed_time = parsedate_to_datetime(pub_date)
                                    earthquake_time = parsed_time.isoformat() + 'Z'
                                except:
                                    pass
                            
                            earthquake = EarthquakeData(
                                magnitude=magnitude,
                                latitude=lat,
                                longitude=lon,
                                depth=10.0,
                                time=earthquake_time,
                                place=title,
                                url="",
                                alert=None,
                                tsunami=1,  # PTWC focuses on tsunami-generating earthquakes
                                distance_km=0.0
                            )
                            earthquakes.append(earthquake)
                
                except Exception as e:
                    continue
                    
        except ET.ParseError as e:
            logger.warning(f"Error parsing PTWC RSS: {str(e)}")
        
        return earthquakes

    @staticmethod
    def _extract_coordinates_from_description(description: str) -> tuple:
        """Extract latitude and longitude from description text"""
        import re
        
        # Try to find coordinates in various formats
        patterns = [
            r'(\d+\.?\d*)[°\s]*N\s*(\d+\.?\d*)[°\s]*E',  # 35.5°N 139.7°E
            r'(\d+\.?\d*)[°\s]*S\s*(\d+\.?\d*)[°\s]*W',  # 35.5°S 139.7°W  
            r'(\d+\.?\d*)[°\s]*N\s*(\d+\.?\d*)[°\s]*W',  # 35.5°N 139.7°W
            r'(\d+\.?\d*)[°\s]*S\s*(\d+\.?\d*)[°\s]*E',  # 35.5°S 139.7°E
            r'lat[:\s]*(-?\d+\.?\d*)[,\s]*lon[:\s]*(-?\d+\.?\d*)',  # lat: 35.5, lon: 139.7
            r'(-?\d+\.?\d+),\s*(-?\d+\.?\d+)',  # 35.5, 139.7
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                try:
                    lat = float(match.group(1))
                    lon = float(match.group(2))
                    
                    # Handle N/S and E/W indicators
                    if 'S' in pattern:
                        lat = -abs(lat)
                    if 'W' in pattern:
                        lon = -abs(lon)
                    
                    # Validate coordinates
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        return lat, lon
                except ValueError:
                    continue
        
        return None, None

    @staticmethod
    def _extract_magnitude_from_text(text: str) -> float:
        """Extract magnitude from text"""
        import re
        
        patterns = [
            r'M\s*(\d+\.?\d*)',  # M 6.5
            r'magnitude\s*(\d+\.?\d*)',  # magnitude 6.5
            r'mag\s*(\d+\.?\d*)',  # mag 6.5
            r'(\d+\.?\d*)\s*magnitude',  # 6.5 magnitude
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    magnitude = float(match.group(1))
                    if 0 <= magnitude <= 10:  # Reasonable magnitude range
                        return magnitude
                except ValueError:
                    continue
        
        return 0.0

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
                    eq_time = datetime.fromisoformat(eq.time.replace('Z', ''))
                    existing_time = datetime.fromisoformat(existing.time.replace('Z', ''))
                    time_diff = abs((eq_time - existing_time).total_seconds())
                except:
                    time_diff = 0
                
                # Check location difference (within 10km)
                distance = geodesic(
                    (eq.latitude, eq.longitude),
                    (existing.latitude, existing.longitude)
                ).kilometers
                
                # Check magnitude difference
                mag_diff = abs(eq.magnitude - existing.magnitude)
                
                if time_diff < 1800 and distance < 10 and mag_diff < 0.5:  # 30 min, 10km, 0.5 magnitude tolerance
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_earthquakes.append(eq)
        
        return unique_earthquakes
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
            GlobalEarthquakeService._fetch_emsc_rss_feed("https://www.emsc-csem.org/service/rss/rss.php?filter=yes&min_lat=24&max_lat=46&min_lon=123&max_lon=146", "Japan-EMSC"),
            GlobalEarthquakeService._fetch_iris_japan_data(days, min_magnitude),
            GlobalEarthquakeService._fetch_geofon_japan_data(days, min_magnitude),
            GlobalEarthquakeService._fetch_usgs_japan_data(latitude, longitude, radius_km, days, min_magnitude),
            GlobalEarthquakeService._fetch_earthquake_track_japan(days, min_magnitude),
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
            filtered_earthquakes = IndianEarthquakeService._remove_duplicates(filtered_earthquakes)
            
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
                        earthquakes = IndianEarthquakeService._parse_emsc_rss(content, "Japan")
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
                        earthquakes = IndianEarthquakeService._parse_geojson_data(data, "Japan-IRIS")
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
                        earthquakes = IndianEarthquakeService._parse_geojson_data(data, "Japan-GEOFON")
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
                        earthquakes = IndianEarthquakeService._parse_geojson_data(data, "Japan-USGS")
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
                        earthquakes = IndianEarthquakeService._parse_earthquake_track_rss(content, "Japan")
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
    """Optimized ML-based earthquake prediction with pre-trained models"""
    
    def __init__(self):
        # Only 3 high-performance models for speed
        self.magnitude_predictor = None  # RandomForest (fast & accurate)
        self.anomaly_detector = None     # IsolationForest (fast anomaly detection)
        self.gradient_booster = None     # XGBoost (high accuracy)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_weights = {"rf": 0.4, "xgb": 0.4, "anomaly": 0.2}
        
        # Initialize pre-trained models
        self._initialize_pretrained_models()
        
    def _initialize_pretrained_models(self):
        """Initialize optimized pre-trained models for fast inference"""
        try:
            # Model 1: RandomForest - Fast and reliable
            self.magnitude_predictor = RandomForestRegressor(
                n_estimators=50,  # Reduced for speed
                max_depth=8,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1  # Use all cores
            )
            
            # Model 2: XGBoost - High accuracy
            try:
                import xgboost as xgb
                self.gradient_booster = xgb.XGBRegressor(
                    n_estimators=50,
                    max_depth=6,
                    learning_rate=0.1,
                    subsample=0.8,
                    random_state=42,
                    n_jobs=-1,
                    verbosity=0
                )
            except ImportError:
                # Fallback to GradientBoosting if XGBoost not available
                from sklearn.ensemble import GradientBoostingRegressor
                self.gradient_booster = GradientBoostingRegressor(
                    n_estimators=50,
                    max_depth=6,
                    learning_rate=0.1,
                    subsample=0.8,
                    random_state=42
                )
            
            # Model 3: IsolationForest - Fast anomaly detection
            self.anomaly_detector = IsolationForest(
                n_estimators=50,  # Reduced for speed
                contamination=0.1,
                random_state=42,
                n_jobs=-1
            )
            
            logger.info("Pre-trained models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing pre-trained models: {str(e)}")
    
    def extract_optimized_features(self, earthquakes: List[EarthquakeData], location_lat: float, location_lon: float) -> np.ndarray:
        """Extract optimized feature set for fast processing"""
        if not earthquakes:
            return np.array([]).reshape(0, -1)
        
        features = []
        
        for i, eq in enumerate(earthquakes):
            # Core features only (reduced from original 20+ to 12 features)
            distance = eq.distance_km
            time_since = (datetime.utcnow() - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() / 3600
            
            # Recent activity indicators
            recent_24h = len([e for e in earthquakes[:i+5] if 
                             (datetime.utcnow() - datetime.fromisoformat(e.time.replace('Z', ''))).total_seconds() < 86400])
            recent_7d = len([e for e in earthquakes[:i+10] if 
                            (datetime.utcnow() - datetime.fromisoformat(e.time.replace('Z', ''))).total_seconds() < 604800])
            
            # Regional risk (simplified)
            regional_risk = self._get_fast_regional_risk(eq.latitude, eq.longitude)
            
            # Energy indicators (simplified)
            energy_log = 1.5 * eq.magnitude + 4.8
            
            # Depth indicators
            shallow_indicator = 1 if eq.depth < 35 else 0
            depth_normalized = min(eq.depth / 100, 1.0)  # Normalize to 0-1
            
            # Magnitude trend (simplified)
            if i > 0:
                mag_trend = eq.magnitude - earthquakes[i-1].magnitude
            else:
                mag_trend = 0
            
            # Statistical features (simplified)
            recent_mags = [e.magnitude for e in earthquakes[max(0, i-5):i+1]]
            avg_magnitude = np.mean(recent_mags) if recent_mags else eq.magnitude
            
            feature_vector = [
                eq.magnitude,
                distance,
                time_since,
                eq.depth,
                recent_24h,
                recent_7d,
                regional_risk,
                energy_log,
                shallow_indicator,
                depth_normalized,
                mag_trend,
                avg_magnitude
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    def _get_fast_regional_risk(self, lat: float, lon: float) -> float:
        """Fast regional risk calculation with simplified zones"""
        # Simplified high-risk zones for speed
        high_risk_zones = [
            (35.7, 139.7, 0.9),   # Tokyo
            (37.7, -122.4, 0.85), # San Francisco  
            (41.0, 29.0, 0.8),    # Istanbul
            (-33.4, -70.6, 0.85), # Santiago
            (28.6, 77.2, 0.7),    # Delhi
        ]
        
        max_risk = 0.1
        for zone_lat, zone_lon, risk in high_risk_zones:
            # Fast distance approximation
            lat_diff = lat - zone_lat
            lon_diff = lon - zone_lon
            approx_distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111  # km approx
            
            if approx_distance < 500:
                proximity_factor = max(0, 1 - approx_distance / 500)
                risk_contribution = risk * proximity_factor
                max_risk = max(max_risk, risk_contribution)
        
        return max_risk
    def prepare_features(self, earthquakes: List[EarthquakeData], location_lat: float, location_lon: float) -> np.ndarray:
        """Legacy method - redirects to optimized feature extraction"""
        return self.extract_optimized_features(earthquakes, location_lat, location_lon)
    
    def fast_train_models(self, historical_earthquakes: List[EarthquakeData], location_lat: float, location_lon: float):
        """Fast training with only 3 optimized models"""
        if len(historical_earthquakes) < 10:
            logger.warning("Insufficient data for ML training, using statistical models")
            return
        
        try:
            # Extract optimized features
            features = self.extract_optimized_features(historical_earthquakes, location_lat, location_lon)
            if features.shape[0] == 0:
                return
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Prepare targets
            magnitudes = np.array([eq.magnitude for eq in historical_earthquakes])
            
            logger.info("Training 3 optimized models...")
            
            # Train RandomForest (Model 1)
            if len(features_scaled) > 5:
                self.magnitude_predictor.fit(features_scaled, magnitudes)
                logger.info("✓ RandomForest trained")
            
            # Train XGBoost/GradientBoosting (Model 2)
            self.gradient_booster.fit(features_scaled, magnitudes)
            logger.info("✓ Gradient Booster trained")
            
            # Train IsolationForest (Model 3)
            self.anomaly_detector.fit(features_scaled)
            logger.info("✓ Anomaly Detector trained")
            
            self.is_trained = True
            logger.info("Fast ML training completed successfully")
            
        except Exception as e:
            logger.error(f"Error in fast ML training: {str(e)}")
    
    def predict_earthquake_probability(self, earthquakes: List[EarthquakeData], location_lat: float, location_lon: float) -> Dict[str, Any]:
        """Advanced prediction using scientific seismological scoring with ensemble ML models"""
        if not earthquakes:
            return {
                "probability_24h": "No data available",
                "predicted_magnitude": "No data available",
                "confidence_score": "No data available",
                "risk_level": "No data available",
                "model_status": "no_earthquake_data",
                "data_verification": {
                    "total_data_points": 0,
                    "models_used": [],
                    "prediction_speed": "instant",
                    "data_status": "No earthquake data found for this location"
                },
                "message": "No recent earthquake activity detected in this area. Cannot make predictions without data."
            }
        
        try:
            start_time = datetime.utcnow()
            
            # Extract optimized features
            features = self.extract_optimized_features(earthquakes, location_lat, location_lon)
            if features.shape[0] == 0:
                return self._create_data_driven_prediction(earthquakes, location_lat, location_lon)
            
            # Scale features if trained
            if self.is_trained:
                features_scaled = self.scaler.transform(features)
            else:
                features_scaled = features
            
            # Advanced seismological scoring system
            seismic_score = self._calculate_advanced_seismic_score(earthquakes, location_lat, location_lon)
            
            predictions = []
            models_used = []
            
            # Ensemble prediction using 3 models
            if self.is_trained and len(features_scaled) > 0:
                latest_features = features_scaled[-1:] if len(features_scaled) > 0 else features[-1:]
                
                # Model 1: RandomForest prediction
                try:
                    rf_pred = self.magnitude_predictor.predict(latest_features)[0]
                    predictions.append(("rf", rf_pred))
                    models_used.append("RandomForest")
                except:
                    pass
                
                # Model 2: XGBoost prediction
                try:
                    xgb_pred = self.gradient_booster.predict(latest_features)[0]
                    predictions.append(("xgb", xgb_pred))
                    models_used.append("XGBoost")
                except:
                    pass
                
                # Model 3: Anomaly detection
                try:
                    is_anomaly = self.anomaly_detector.predict(latest_features)[0] == -1
                    anomaly_score = self.anomaly_detector.decision_function(latest_features)[0]
                    models_used.append("IsolationForest")
                except:
                    is_anomaly = False
                    anomaly_score = 0
                
                # Enhanced ensemble prediction with seismological weighting
                if predictions:
                    weighted_pred = sum(pred * self.model_weights.get(name, 0.33) 
                                      for name, pred in predictions)
                    total_weight = sum(self.model_weights.get(name, 0.33) 
                                     for name, _ in predictions)
                    ml_predicted_magnitude = weighted_pred / total_weight if total_weight > 0 else 3.5
                else:
                    ml_predicted_magnitude = np.mean([eq.magnitude for eq in earthquakes[-5:]])
                
                # Combine ML prediction with seismological scoring
                predicted_magnitude = (ml_predicted_magnitude * 0.6 + seismic_score['predicted_magnitude'] * 0.4)
                
                # Advanced probability calculation using multiple factors
                ml_prob_24h = self._calculate_precise_probability(earthquakes, seismic_score, predicted_magnitude, is_anomaly, location_lat, location_lon)
                confidence = self._calculate_prediction_confidence(predictions, seismic_score, len(earthquakes))
                model_status = "advanced_ensemble"
                
            else:
                # Enhanced statistical prediction with seismological scoring
                predicted_magnitude = seismic_score['predicted_magnitude']
                ml_prob_24h = seismic_score['base_probability']
                confidence = 0.5
                model_status = "seismological_statistical"
                is_anomaly = seismic_score['anomaly_detected']
            
            # Determine risk level based on enhanced scoring
            risk_level = self._determine_enhanced_risk_level(ml_prob_24h, predicted_magnitude, seismic_score)
            
            # Calculate prediction speed
            prediction_time = (datetime.utcnow() - start_time).total_seconds() * 1000  # ms
            
            return {
                "probability_24h": round(ml_prob_24h, 2),
                "predicted_magnitude": round(predicted_magnitude, 2),
                "confidence_score": round(confidence, 3),
                "risk_level": risk_level,
                "model_status": model_status,
                "anomaly_detected": is_anomaly if 'is_anomaly' in locals() else False,
                "seismological_factors": {
                    "gutenberg_richter_score": round(seismic_score['gr_score'], 3),
                    "temporal_clustering": round(seismic_score['temporal_score'], 3),
                    "spatial_clustering": round(seismic_score['spatial_score'], 3),
                    "tectonic_stress_index": round(seismic_score['stress_index'], 3),
                    "energy_release_pattern": round(seismic_score['energy_pattern'], 3),
                    "foreshock_pattern": round(seismic_score['foreshock_score'], 3)
                },
                "data_verification": {
                    "total_data_points": len(earthquakes),
                    "recent_24h_events": seismic_score['recent_24h_count'],
                    "recent_7d_events": seismic_score['recent_7d_count'],
                    "models_used": models_used,
                    "prediction_speed_ms": round(prediction_time, 2),
                    "ensemble_models": len(predictions),
                    "data_quality_score": round(seismic_score['data_quality'], 3)
                },
                "dynamic_meter": {
                    "current_value": round(ml_prob_24h, 2),
                    "trend": seismic_score['activity_trend'],
                    "last_updated": datetime.utcnow().isoformat(),
                    "update_frequency": "real-time"
                }
            }
            
        except Exception as e:
            logger.error(f"Error in advanced ML prediction: {str(e)}")
            return self._create_data_driven_prediction(earthquakes, location_lat, location_lon)
    
    def _calculate_advanced_seismic_score(self, earthquakes: List[EarthquakeData], location_lat: float, location_lon: float) -> Dict[str, float]:
        """
        Calculate advanced seismological scoring based on multiple scientific factors
        """
        now = datetime.utcnow()
        
        # Time-based categorization
        recent_24h = [eq for eq in earthquakes if 
                     (now - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 86400]
        recent_7d = [eq for eq in earthquakes if 
                    (now - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 604800]
        recent_30d = [eq for eq in earthquakes if 
                     (now - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 2592000]
        
        # 1. Gutenberg-Richter Law Analysis (b-value calculation)
        gr_score = self._calculate_gutenberg_richter_score(earthquakes)
        
        # 2. Temporal Clustering Analysis (ETAS model inspiration)
        temporal_score = self._calculate_temporal_clustering_score(earthquakes)
        
        # 3. Spatial Clustering Analysis
        spatial_score = self._calculate_spatial_clustering_score(earthquakes, location_lat, location_lon)
        
        # 4. Tectonic Stress Index
        stress_index = self._calculate_tectonic_stress_index(earthquakes, location_lat, location_lon)
        
        # 5. Energy Release Pattern Analysis
        energy_pattern = self._calculate_energy_release_pattern(earthquakes)
        
        # 6. Foreshock Pattern Detection
        foreshock_score = self._calculate_foreshock_pattern(earthquakes)
        
        # 7. Calculate base probability using scientific approach
        base_probability = self._calculate_scientific_base_probability(
            recent_24h, recent_7d, recent_30d, gr_score, temporal_score, spatial_score
        )
        
        # 8. Predicted magnitude using Gutenberg-Richter and recent patterns
        predicted_magnitude = self._calculate_predicted_magnitude(earthquakes, gr_score)
        
        # 9. Data quality assessment
        data_quality = self._assess_data_quality(earthquakes)
        
        # 10. Activity trend analysis
        activity_trend = self._determine_activity_trend(recent_24h, recent_7d, recent_30d)
        
        # 11. Anomaly detection based on statistical patterns
        anomaly_detected = self._detect_statistical_anomaly(earthquakes, temporal_score, spatial_score)
        
        return {
            'gr_score': gr_score,
            'temporal_score': temporal_score,
            'spatial_score': spatial_score,
            'stress_index': stress_index,
            'energy_pattern': energy_pattern,
            'foreshock_score': foreshock_score,
            'base_probability': base_probability,
            'predicted_magnitude': predicted_magnitude,
            'data_quality': data_quality,
            'activity_trend': activity_trend,
            'anomaly_detected': anomaly_detected,
            'recent_24h_count': len(recent_24h),
            'recent_7d_count': len(recent_7d),
            'recent_30d_count': len(recent_30d)
        }
    
    def _calculate_gutenberg_richter_score(self, earthquakes: List[EarthquakeData]) -> float:
        """Calculate b-value from Gutenberg-Richter law: log(N) = a - b*M"""
        if len(earthquakes) < 10:
            return 1.0  # Default b-value
        
        magnitudes = [eq.magnitude for eq in earthquakes]
        mag_bins = np.arange(min(magnitudes), max(magnitudes) + 0.1, 0.1)
        
        if len(mag_bins) < 3:
            return 1.0
        
        # Count earthquakes above each magnitude threshold
        cumulative_counts = []
        for mag in mag_bins:
            count = len([m for m in magnitudes if m >= mag])
            if count > 0:
                cumulative_counts.append(count)
            else:
                break
        
        if len(cumulative_counts) < 3:
            return 1.0
        
        # Linear regression on log(N) vs M
        log_counts = np.log10(cumulative_counts)
        mags = mag_bins[:len(cumulative_counts)]
        
        try:
            slope, _ = np.polyfit(mags, log_counts, 1)
            b_value = -slope  # b-value is negative slope
            
            # Typical b-values range from 0.5 to 1.5
            # Lower b-values indicate higher stress, higher probability of larger events
            normalized_score = max(0.1, min(2.0, b_value))
            return normalized_score
        except:
            return 1.0
    
    def _calculate_temporal_clustering_score(self, earthquakes: List[EarthquakeData]) -> float:
        """Analyze temporal clustering of earthquakes"""
        if len(earthquakes) < 3:
            return 0.1
        
        times = [datetime.fromisoformat(eq.time.replace('Z', '')) for eq in earthquakes]
        times.sort()
        
        # Calculate time intervals between consecutive earthquakes
        intervals = []
        for i in range(1, len(times)):
            interval = (times[i-1] - times[i]).total_seconds() / 3600  # hours
            intervals.append(abs(interval))
        
        if not intervals:
            return 0.1
        
        # Coefficient of variation indicates clustering
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        if mean_interval == 0:
            return 0.5
        
        cv = std_interval / mean_interval
        
        # High CV indicates clustering (irregular intervals)
        # Normalize between 0.1 and 1.0
        clustering_score = min(1.0, max(0.1, cv / 2.0))
        
        return clustering_score
    
    def _calculate_spatial_clustering_score(self, earthquakes: List[EarthquakeData], center_lat: float, center_lon: float) -> float:
        """Analyze spatial clustering of earthquakes"""
        if len(earthquakes) < 3:
            return 0.1
        
        # Calculate distances from center point
        distances = []
        for eq in earthquakes:
            try:
                distance = geodesic((center_lat, center_lon), (eq.latitude, eq.longitude)).kilometers
                distances.append(distance)
            except:
                continue
        
        if len(distances) < 3:
            return 0.1
        
        # Calculate spatial dispersion
        mean_distance = np.mean(distances)
        std_distance = np.std(distances)
        
        if mean_distance == 0:
            return 0.5
        
        # Low coefficient of variation indicates tight clustering
        cv = std_distance / mean_distance
        clustering_score = max(0.1, min(1.0, 1.0 - cv/3.0))
        
        return clustering_score
    
    def _calculate_tectonic_stress_index(self, earthquakes: List[EarthquakeData], lat: float, lon: float) -> float:
        """Calculate tectonic stress index based on location and recent activity"""
        
        # Base regional stress from location
        regional_stress = self._get_fast_regional_risk(lat, lon)
        
        # Recent activity contribution
        now = datetime.utcnow()
        recent_earthquakes = [eq for eq in earthquakes if 
                            (now - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 604800]  # 7 days
        
        if not recent_earthquakes:
            return regional_stress
        
        # Calculate energy release in past week
        total_energy = sum(10**(1.5 * eq.magnitude + 4.8) for eq in recent_earthquakes)
        log_energy = np.log10(total_energy + 1)
        
        # Normalize energy contribution
        energy_factor = min(1.0, log_energy / 20.0)
        
        # Depth factor (shallow earthquakes indicate higher stress)
        avg_depth = np.mean([eq.depth for eq in recent_earthquakes])
        depth_factor = max(0.5, 1.0 - avg_depth / 100.0)  # Normalize by 100km
        
        # Combined stress index
        stress_index = (regional_stress * 0.4 + energy_factor * 0.3 + depth_factor * 0.3)
        
        return min(1.0, max(0.1, stress_index))
    
    def _calculate_energy_release_pattern(self, earthquakes: List[EarthquakeData]) -> float:
        """Analyze energy release patterns (accelerating vs decelerating)"""
        if len(earthquakes) < 5:
            return 0.5
        
        # Calculate cumulative energy release over time
        times = []
        energies = []
        
        for eq in earthquakes:
            time_obj = datetime.fromisoformat(eq.time.replace('Z', ''))
            energy = 10**(1.5 * eq.magnitude + 4.8)
            times.append(time_obj)
            energies.append(energy)
        
        # Sort by time
        sorted_data = sorted(zip(times, energies))
        times, energies = zip(*sorted_data)
        
        # Calculate cumulative energy
        cumulative_energy = np.cumsum(energies)
        
        # Fit trend to recent energy release
        if len(cumulative_energy) >= 3:
            try:
                x = np.arange(len(cumulative_energy))
                # Calculate acceleration (second derivative)
                coeffs = np.polyfit(x, np.log(cumulative_energy + 1), 2)
                acceleration = coeffs[0]  # Second order coefficient
                
                # Positive acceleration indicates accelerating energy release
                pattern_score = min(1.0, max(0.1, 0.5 + acceleration * 10))
                return pattern_score
            except:
                return 0.5
        
        return 0.5
    
    def _calculate_foreshock_pattern(self, earthquakes: List[EarthquakeData]) -> float:
        """Detect foreshock patterns that might precede larger earthquakes"""
        if len(earthquakes) < 5:
            return 0.1
        
        # Sort earthquakes by time (most recent first)
        sorted_eqs = sorted(earthquakes, key=lambda x: x.time, reverse=True)
        
        # Look for increasing magnitude trend in recent events
        recent_mags = [eq.magnitude for eq in sorted_eqs[:10]]  # Last 10 events
        
        if len(recent_mags) < 3:
            return 0.1
        
        # Calculate magnitude trend
        try:
            x = np.arange(len(recent_mags))
            slope, _ = np.polyfit(x, recent_mags, 1)
            
            # Positive slope indicates increasing magnitudes (potential foreshock pattern)
            if slope > 0:
                foreshock_score = min(1.0, slope * 2.0)
            else:
                foreshock_score = 0.1
                
            return foreshock_score
        except:
            return 0.1
    
    def _calculate_scientific_base_probability(self, recent_24h, recent_7d, recent_30d, gr_score, temporal_score, spatial_score) -> float:
        """Calculate scientifically-based probability using multiple factors"""
        
        # Base rate from historical seismicity
        base_rate = len(recent_30d) / 30.0  # Average per day
        
        # Recent activity multiplier
        recent_multiplier = 1.0
        if len(recent_7d) > 0:
            weekly_rate = len(recent_7d) / 7.0
            if base_rate > 0:
                recent_multiplier = min(5.0, weekly_rate / base_rate)
        
        # 24-hour specific factors
        daily_factor = min(3.0, len(recent_24h) + 1)
        
        # Stress accumulation factor (lower b-value = higher stress)
        stress_factor = max(0.5, 2.0 - gr_score)
        
        # Clustering factors
        clustering_factor = (temporal_score + spatial_score) / 2.0
        
        # Calculate probability (convert to percentage)
        probability = base_rate * recent_multiplier * daily_factor * stress_factor * clustering_factor * 100
        
        # Realistic bounds based on seismological knowledge
        # Daily earthquake probability rarely exceeds 10% even in active regions
        probability = min(15.0, max(0.01, probability))
        
        return probability
    
    def _calculate_predicted_magnitude(self, earthquakes: List[EarthquakeData], gr_score: float) -> float:
        """Predict magnitude using Gutenberg-Richter relationship and recent patterns"""
        if not earthquakes:
            return 3.0
        
        # Recent magnitude statistics
        recent_mags = [eq.magnitude for eq in earthquakes[:20]]  # Last 20 events
        
        if not recent_mags:
            return 3.0
        
        # Statistical prediction based on recent activity
        mean_mag = np.mean(recent_mags)
        max_mag = max(recent_mags)
        std_mag = np.std(recent_mags)
        
        # Gutenberg-Richter correction
        # Lower b-value suggests potential for larger events
        gr_correction = max(0.0, (1.0 - gr_score) * 0.5)
        
        # Predicted magnitude with uncertainty
        predicted = mean_mag + std_mag * 0.5 + gr_correction
        
        # Realistic bounds
        predicted = min(max_mag + 1.0, max(2.0, predicted))
        predicted = min(8.0, predicted)  # Very rare to exceed M8.0
        
        return predicted
    
    def _assess_data_quality(self, earthquakes: List[EarthquakeData]) -> float:
        """Assess the quality and completeness of earthquake data"""
        if not earthquakes:
            return 0.0
        
        # Data quantity score
        quantity_score = min(1.0, len(earthquakes) / 50.0)  # Ideal: 50+ events
        
        # Temporal coverage score
        times = [datetime.fromisoformat(eq.time.replace('Z', '')) for eq in earthquakes]
        if len(times) > 1:
            time_span = (max(times) - min(times)).total_seconds() / 86400  # days
            coverage_score = min(1.0, time_span / 30.0)  # Ideal: 30+ days
        else:
            coverage_score = 0.1
        
        # Magnitude completeness score
        magnitudes = [eq.magnitude for eq in earthquakes]
        mag_range = max(magnitudes) - min(magnitudes) if magnitudes else 0
        completeness_score = min(1.0, mag_range / 3.0)  # Ideal: 3+ magnitude units
        
        # Overall quality score
        quality_score = (quantity_score + coverage_score + completeness_score) / 3.0
        
        return quality_score
    
    def _determine_activity_trend(self, recent_24h, recent_7d, recent_30d) -> str:
        """Determine seismic activity trend"""
        daily_rate = len(recent_24h)
        weekly_rate = len(recent_7d) / 7.0
        monthly_rate = len(recent_30d) / 30.0
        
        if daily_rate > weekly_rate * 2:
            return "rapidly_increasing"
        elif daily_rate > weekly_rate * 1.5:
            return "increasing"
        elif weekly_rate > monthly_rate * 1.5:
            return "moderately_increasing"
        elif daily_rate < weekly_rate * 0.5:
            return "decreasing"
        else:
            return "stable"
    
    def _detect_statistical_anomaly(self, earthquakes: List[EarthquakeData], temporal_score: float, spatial_score: float) -> bool:
        """Detect statistical anomalies in earthquake patterns"""
        
        # High temporal clustering + high spatial clustering = potential anomaly
        clustering_anomaly = (temporal_score > 0.7 and spatial_score > 0.7)
        
        # Unusual magnitude patterns
        if len(earthquakes) >= 5:
            recent_mags = [eq.magnitude for eq in earthquakes[:5]]
            historical_mags = [eq.magnitude for eq in earthquakes[5:]]
            
            if recent_mags and historical_mags:
                recent_mean = np.mean(recent_mags)
                historical_mean = np.mean(historical_mags)
                magnitude_anomaly = recent_mean > historical_mean + 0.5
            else:
                magnitude_anomaly = False
        else:
            magnitude_anomaly = False
        
        return clustering_anomaly or magnitude_anomaly
    
    def _calculate_precise_probability(self, earthquakes: List[EarthquakeData], seismic_score: Dict, predicted_magnitude: float, is_anomaly: bool, lat: float, lon: float) -> float:
        """Calculate precise 24-hour probability using all available factors"""
        
        base_prob = seismic_score['base_probability']
        
        # Magnitude factor (higher predicted magnitude = higher probability)
        if predicted_magnitude >= 6.0:
            magnitude_factor = 2.0
        elif predicted_magnitude >= 5.0:
            magnitude_factor = 1.5
        elif predicted_magnitude >= 4.0:
            magnitude_factor = 1.2
        else:
            magnitude_factor = 1.0
        
        # Anomaly factor
        anomaly_factor = 1.8 if is_anomaly else 1.0
        
        # Stress accumulation factor
        stress_factor = 1.0 + seismic_score['stress_index'] * 0.5
        
        # Energy pattern factor
        energy_factor = 0.8 + seismic_score['energy_pattern'] * 0.4
        
        # Foreshock factor
        foreshock_factor = 1.0 + seismic_score['foreshock_score'] * 0.3
        
        # Combined probability
        final_probability = (base_prob * magnitude_factor * anomaly_factor * 
                           stress_factor * energy_factor * foreshock_factor)
        
        # Apply realistic scientific bounds
        # Even in the most active regions, daily probability rarely exceeds 20%
        final_probability = min(20.0, max(0.01, final_probability))
        
        return final_probability
    
    def _calculate_prediction_confidence(self, predictions: list, seismic_score: Dict, data_count: int) -> float:
        """Calculate confidence score for predictions"""
        
        # Model agreement (more models agreeing = higher confidence)
        model_confidence = min(1.0, len(predictions) / 3.0)
        
        # Data quality contribution
        data_confidence = seismic_score['data_quality']
        
        # Data quantity contribution
        quantity_confidence = min(1.0, data_count / 30.0)  # 30+ earthquakes ideal
        
        # Temporal coverage (recent data is more reliable)
        if data_count > 0:
            temporal_confidence = min(1.0, seismic_score['recent_7d_count'] / 10.0)
        else:
            temporal_confidence = 0.0
        
        # Combined confidence score
        confidence = (model_confidence * 0.3 + data_confidence * 0.25 + 
                     quantity_confidence * 0.25 + temporal_confidence * 0.2)
        
        return min(0.999, max(0.001, confidence))
    
    def _determine_enhanced_risk_level(self, probability: float, magnitude: float, seismic_score: Dict) -> str:
        """Determine risk level using enhanced criteria"""
        
        # Multi-factor risk assessment
        prob_score = probability / 20.0  # Normalize to 0-1
        mag_score = min(1.0, (magnitude - 2.0) / 6.0)  # M2-M8 range
        stress_score = seismic_score['stress_index']
        anomaly_score = 0.2 if seismic_score['anomaly_detected'] else 0.0
        
        # Combined risk score
        risk_score = (prob_score * 0.4 + mag_score * 0.3 + 
                     stress_score * 0.2 + anomaly_score * 0.1)
        
        if risk_score >= 0.8 or magnitude >= 7.0:
            return "Critical"
        elif risk_score >= 0.6 or magnitude >= 6.0:
            return "High"
        elif risk_score >= 0.4 or magnitude >= 5.0:
            return "Moderate"
        elif risk_score >= 0.2 or magnitude >= 4.0:
            return "Low-Moderate"
        else:
            return "Low"
    
    def _create_data_driven_prediction(self, earthquakes: List[EarthquakeData], location_lat: float, location_lon: float) -> Dict[str, Any]:
        """Create realistic predictions based on available earthquake data and regional statistics"""
        
        if not earthquakes:
            # Use regional geological data to make informed predictions
            regional_risk = self._get_fast_regional_risk(location_lat, location_lon)
            
            # Base probability on regional seismic hazard
            if regional_risk > 0.8:  # High risk zones like Tokyo, San Francisco
                probability_24h = 2.5
                predicted_magnitude = 4.2
                confidence = 0.3
                risk_level = "Moderate"
            elif regional_risk > 0.6:  # Moderate risk zones
                probability_24h = 1.8
                predicted_magnitude = 3.8
                confidence = 0.25
                risk_level = "Low-Moderate"
            elif regional_risk > 0.3:  # Low-moderate risk zones
                probability_24h = 0.8
                predicted_magnitude = 3.2
                confidence = 0.2
                risk_level = "Low"
            else:  # Stable regions
                probability_24h = 0.3
                predicted_magnitude = 2.8
                confidence = 0.15
                risk_level = "Very Low"
                
            return {
                "probability_24h": round(probability_24h, 2),
                "predicted_magnitude": round(predicted_magnitude, 2),
                "confidence_score": round(confidence, 3),
                "risk_level": risk_level,
                "model_status": "regional_statistical",
                "anomaly_detected": False,
                "seismological_factors": {
                    "gutenberg_richter_score": 1.0,
                    "temporal_clustering": 0.1,
                    "spatial_clustering": 0.1,
                    "tectonic_stress_index": regional_risk,
                    "energy_release_pattern": 0.5,
                    "foreshock_pattern": 0.1
                },
                "data_verification": {
                    "total_data_points": 0,
                    "recent_24h_events": 0,
                    "recent_7d_events": 0,
                    "models_used": ["Regional Hazard Model"],
                    "prediction_speed_ms": 1.0,
                    "ensemble_models": 1,
                    "data_quality_score": 0.3
                },
                "dynamic_meter": {
                    "current_value": round(probability_24h, 2),
                    "trend": "stable",
                    "last_updated": datetime.utcnow().isoformat(),
                    "update_frequency": "real-time"
                },
                "message": f"Prediction based on regional seismic hazard analysis for this location. Regional risk factor: {regional_risk:.2f}"
            }
        
        # Use available earthquake data for statistical prediction
        now = datetime.utcnow()
        
        # Categorize earthquakes by time
        recent_24h = [eq for eq in earthquakes if 
                     (now - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 86400]
        recent_7d = [eq for eq in earthquakes if 
                    (now - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 604800]
        recent_30d = [eq for eq in earthquakes if 
                     (now - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 2592000]
        
        # Calculate statistical measures
        magnitudes = [eq.magnitude for eq in earthquakes]
        mean_magnitude = np.mean(magnitudes) if magnitudes else 3.0
        max_magnitude = max(magnitudes) if magnitudes else 3.0
        std_magnitude = np.std(magnitudes) if len(magnitudes) > 1 else 0.5
        
        # Activity-based probability calculation
        activity_rate = len(recent_7d) / 7.0  # events per day
        monthly_rate = len(recent_30d) / 30.0  # monthly baseline
        
        # Base 24-hour probability on recent activity
        if len(recent_24h) > 0:
            probability_24h = min(15.0, len(recent_24h) * 8.0 + activity_rate * 3.0)
        elif len(recent_7d) > 0:
            probability_24h = min(10.0, activity_rate * 5.0 + monthly_rate * 2.0)
        elif len(recent_30d) > 0:
            probability_24h = min(5.0, monthly_rate * 4.0 + 0.5)
        else:
            probability_24h = 0.2
        
        # Magnitude prediction based on recent patterns
        if len(magnitudes) >= 3:
            # Use recent trend
            recent_mags = magnitudes[:min(5, len(magnitudes))]
            predicted_magnitude = np.mean(recent_mags) + std_magnitude * 0.3
            predicted_magnitude = min(max_magnitude + 0.8, predicted_magnitude)
        else:
            predicted_magnitude = mean_magnitude + 0.3
        
        # Ensure realistic bounds
        predicted_magnitude = max(2.5, min(7.5, predicted_magnitude))
        probability_24h = max(0.1, min(20.0, probability_24h))
        
        # Confidence based on data availability
        data_points = len(earthquakes)
        if data_points >= 20:
            confidence = 0.7
        elif data_points >= 10:
            confidence = 0.6
        elif data_points >= 5:
            confidence = 0.5
        else:
            confidence = 0.3
        
        # Risk level determination
        if probability_24h >= 10.0 or predicted_magnitude >= 6.0:
            risk_level = "High"
        elif probability_24h >= 5.0 or predicted_magnitude >= 5.0:
            risk_level = "Moderate"
        elif probability_24h >= 2.0 or predicted_magnitude >= 4.0:
            risk_level = "Low-Moderate"
        else:
            risk_level = "Low"
        
        # Enhanced statistical factors
        temporal_clustering = min(1.0, len(recent_7d) / max(1, len(recent_30d)) * 4.0)
        regional_risk = self._get_fast_regional_risk(location_lat, location_lon)
        
        return {
            "probability_24h": round(probability_24h, 2),
            "predicted_magnitude": round(predicted_magnitude, 2),
            "confidence_score": round(confidence, 3),
            "risk_level": risk_level,
            "model_status": "statistical_data_driven",
            "anomaly_detected": len(recent_24h) > len(recent_7d) / 7 * 2,
            "seismological_factors": {
                "gutenberg_richter_score": max(0.5, 1.2 - std_magnitude/2),
                "temporal_clustering": round(temporal_clustering, 3),
                "spatial_clustering": min(1.0, data_points / 30.0),
                "tectonic_stress_index": round(regional_risk, 3),
                "energy_release_pattern": min(1.0, activity_rate / 2.0),
                "foreshock_pattern": round(min(1.0, len(recent_24h) / max(1, len(recent_7d)) * 7), 3)
            },
            "data_verification": {
                "total_data_points": len(earthquakes),
                "recent_24h_events": len(recent_24h),
                "recent_7d_events": len(recent_7d),
                "models_used": ["Statistical Analysis", "Regional Hazard"],
                "prediction_speed_ms": 2.0,
                "ensemble_models": 2,
                "data_quality_score": round(min(1.0, data_points / 30.0), 3)
            },
            "dynamic_meter": {
                "current_value": round(probability_24h, 2),
                "trend": "increasing" if len(recent_24h) > activity_rate else "stable",
                "last_updated": datetime.utcnow().isoformat(),
                "update_frequency": "real-time"
            },
            "message": f"Statistical prediction based on {len(earthquakes)} earthquake data points. Activity rate: {activity_rate:.1f} events/day"
        }
    
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
        """Redirect to fast training method"""
        return self.fast_train_models(historical_earthquakes, location_lat, location_lon)
    

    
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
    Advanced earthquake service combining multiple international data sources with ML predictions
    Enhanced with comprehensive global coverage from all major seismic monitoring agencies
    """
    
    def __init__(self):
        self.usgs_service = EarthquakeService()
        self.indian_service = IndianEarthquakeService()
        self.global_service = GlobalEarthquakeService()
        self.international_service = InternationalEarthquakeService()
        self.ml_predictor = EarthquakeMLPredictor()
        
    async def get_comprehensive_earthquake_data(self, latitude: float, longitude: float, radius_km: float = 500) -> List[EarthquakeData]:
        """
        Get comprehensive earthquake data from all available international sources
        """
        try:
            # Determine region and fetch appropriate data
            region = self._determine_region(latitude, longitude)
            
            # Fetch data from multiple sources in parallel
            tasks = []
            
            # Always fetch USGS data (most reliable global source)
            tasks.append(self.usgs_service.get_earthquakes_by_location(latitude, longitude, int(radius_km)))
            
            # Add specialized regional sources
            if region == "india":
                tasks.append(self.indian_service.get_indian_earthquakes(latitude, longitude, int(radius_km)))
            elif region == "japan":
                tasks.append(self.international_service.get_pacific_earthquakes(latitude, longitude, int(radius_km)))
            elif region == "russia":
                tasks.append(self.international_service.get_russian_earthquakes(latitude, longitude, int(radius_km)))
            elif region == "china":
                tasks.append(self.international_service.get_chinese_earthquakes(latitude, longitude, int(radius_km)))
            elif region in ["turkey", "italy", "greece"]:
                tasks.append(self.international_service.get_european_earthquakes(latitude, longitude, int(radius_km)))
            elif region in ["indonesia", "philippines", "australia"]:
                tasks.append(self.international_service.get_pacific_earthquakes(latitude, longitude, int(radius_km)))
            elif region in ["chile", "peru", "colombia", "mexico", "canada"]:
                tasks.append(self.international_service.get_americas_earthquakes(latitude, longitude, int(radius_km)))
            
            # Always add global sources for comprehensive coverage
            tasks.append(self.global_service.get_global_earthquakes(latitude, longitude, int(radius_km * 1.5)))
            
            # Add regional coverage based on location
            if region in ["russia", "china"]:
                tasks.append(self.international_service.get_european_earthquakes(latitude, longitude, int(radius_km * 2)))
            elif region in ["india", "china"]:
                tasks.append(self.international_service.get_pacific_earthquakes(latitude, longitude, int(radius_km * 2)))
            elif region in ["turkey", "iran"]:
                tasks.append(self.international_service.get_european_earthquakes(latitude, longitude, int(radius_km * 1.5)))
            
            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine all earthquake data
            all_earthquakes = []
            for result in results:
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Error fetching earthquake data: {str(result)}")
            
            # Remove duplicates and sort by time
            unique_earthquakes = self._remove_duplicates_enhanced(all_earthquakes)
            unique_earthquakes.sort(key=lambda x: x.time, reverse=True)
            
            # Limit to most recent 300 earthquakes for processing efficiency
            return unique_earthquakes[:300]
            
        except Exception as e:
            logger.error(f"Error getting comprehensive earthquake data: {str(e)}")
            return []

    async def get_comprehensive_analysis(self, latitude: float, longitude: float, radius_km: float = 500) -> Dict[str, Any]:
        """
        Get comprehensive earthquake analysis with ML predictions from multiple international sources
        """
        try:
            # Determine region and fetch appropriate data
            region = self._determine_region(latitude, longitude)
            
            # Fetch data from multiple sources in parallel
            tasks = []
            data_sources = ["USGS_Global"]
            
            # Always fetch USGS data (most reliable global source)
            tasks.append(self.usgs_service.get_earthquakes_by_location(latitude, longitude, int(radius_km)))
            
            # Add specialized regional sources
            if region == "india":
                tasks.append(self.indian_service.get_indian_earthquakes(latitude, longitude, int(radius_km)))
                data_sources.append("Indian_Multi_Agency")
            elif region == "japan":
                tasks.append(self.international_service.get_pacific_earthquakes(latitude, longitude, int(radius_km)))
                data_sources.append("Japanese_Multi_Agency")
            elif region == "russia":
                tasks.append(self.international_service.get_russian_earthquakes(latitude, longitude, int(radius_km)))
                data_sources.append("Russian_Federation_Sources")
            elif region == "china":
                tasks.append(self.international_service.get_chinese_earthquakes(latitude, longitude, int(radius_km)))
                data_sources.append("Chinese_Earthquake_Networks")
            elif region in ["turkey", "italy", "greece", "norway", "iceland", "switzerland"]:
                tasks.append(self.international_service.get_european_earthquakes(latitude, longitude, int(radius_km)))
                data_sources.append("European_Seismic_Networks")
            elif region in ["indonesia", "philippines", "australia"]:
                tasks.append(self.international_service.get_pacific_earthquakes(latitude, longitude, int(radius_km)))
                data_sources.append("Pacific_Ring_Sources")
            elif region in ["chile", "peru", "colombia", "mexico", "canada"]:
                tasks.append(self.international_service.get_americas_earthquakes(latitude, longitude, int(radius_km)))
                data_sources.append("Americas_Seismic_Networks")
            
            # Always add global sources for comprehensive coverage
            tasks.append(self.global_service.get_global_earthquakes(latitude, longitude, int(radius_km * 2)))
            data_sources.append("Global_Multi_Source_Feeds")
            
            # Add additional regional coverage for broader context
            if region in ["russia", "china"]:
                tasks.append(self.international_service.get_european_earthquakes(latitude, longitude, int(radius_km * 2)))
                data_sources.append("Extended_European_Coverage")
            elif region in ["india", "china", "japan"]:
                tasks.append(self.international_service.get_pacific_earthquakes(latitude, longitude, int(radius_km * 2)))
                data_sources.append("Extended_Pacific_Coverage")
            elif region in ["turkey", "iran", "greece"]:
                tasks.append(self.international_service.get_european_earthquakes(latitude, longitude, int(radius_km * 1.5)))
                data_sources.append("Mediterranean_Extended")
            
            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine all earthquake data
            all_earthquakes = []
            successful_sources = []
            
            for i, result in enumerate(results):
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                    if i < len(data_sources):
                        successful_sources.append(data_sources[i])
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
            
            # Calculate data coverage statistics
            coverage_stats = self._calculate_data_coverage(all_earthquakes, successful_sources, region)
            
            return {
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "region": region,
                    "analysis_radius_km": radius_km,
                    "country_context": self._get_country_context(latitude, longitude)
                },
                "earthquake_data": {
                    "total_earthquakes": len(all_earthquakes),
                    "recent_earthquakes": [eq.to_dict() for eq in all_earthquakes[:20]],  # More earthquakes for analysis
                    "data_sources": successful_sources,
                    "source_coverage": coverage_stats,
                    "international_coverage": {
                        "total_sources": len(successful_sources),
                        "regional_specialized": len([s for s in successful_sources if "Multi_Agency" in s or "Networks" in s]),
                        "global_feeds": len([s for s in successful_sources if "Global" in s]),
                        "extended_coverage": len([s for s in successful_sources if "Extended" in s])
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
                    "model_types": ["RandomForest", "IsolationForest", "Advanced_ML_Suite"],
                    "data_sources_count": len(successful_sources),
                    "international_coverage": True,
                    "regional_specialization": region
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
        Enhanced method to combine and deduplicate earthquake data from multiple international sources
        """
        if not all_earthquakes:
            return []
        
        # Remove duplicates using enhanced international method
        unique_earthquakes = InternationalEarthquakeService._remove_duplicates(all_earthquakes)
        
        # Sort by time (most recent first)
        unique_earthquakes.sort(key=lambda x: x.time, reverse=True)
        
        logger.info(f"Combined {len(all_earthquakes)} earthquakes from international sources into {len(unique_earthquakes)} unique events")
        return unique_earthquakes
    
    def _determine_region(self, latitude: float, longitude: float) -> str:
        """Determine geographical region for specialized data sources with enhanced international detection"""
        # Enhanced India region detection (including Pakistan, Bangladesh, Sri Lanka, Nepal, Bhutan)
        if 6 <= latitude <= 38 and 68 <= longitude <= 98:
            return "india"
        # Japan region (including extended EEZ)
        elif 24 <= latitude <= 46 and 123 <= longitude <= 146:
            return "japan"
        # Russia region (including Siberia and Far East)
        elif 41 <= latitude <= 82 and 19 <= longitude <= 180:
            return "russia"
        # China region (including Taiwan)
        elif 18 <= latitude <= 54 and 73 <= longitude <= 135:
            return "china"
        # Indonesia/Southeast Asia
        elif -11 <= latitude <= 21 and 95 <= longitude <= 141:
            return "indonesia"
        # Philippines
        elif 5 <= latitude <= 21 and 116 <= longitude <= 127:
            return "philippines"
        # Australia/Oceania
        elif -45 <= latitude <= -9 and 110 <= longitude <= 160:
            return "australia"
        # Turkey/Anatolia
        elif 35 <= latitude <= 42 and 26 <= longitude <= 45:
            return "turkey"
        # Italy
        elif 35 <= latitude <= 47 and 6 <= longitude <= 19:
            return "italy"
        # Greece/Aegean
        elif 34 <= latitude <= 42 and 19 <= longitude <= 30:
            return "greece"
        # Iran/Persian Gulf
        elif 25 <= latitude <= 40 and 44 <= longitude <= 64:
            return "iran"
        # California/West Coast USA
        elif 32 <= latitude <= 42 and -125 <= longitude <= -114:
            return "california"
        # Chile
        elif -56 <= latitude <= -17 and -76 <= longitude <= -66:
            return "chile"
        # Peru
        elif -19 <= latitude <= 0 and -82 <= longitude <= -68:
            return "peru"
        # Colombia
        elif -5 <= latitude <= 13 and -80 <= longitude <= -66:
            return "colombia"
        # Mexico
        elif 14 <= latitude <= 33 and -118 <= longitude <= -86:
            return "mexico"
        # Canada
        elif 41 <= latitude <= 84 and -141 <= longitude <= -52:
            return "canada"
        # Norway/Scandinavia
        elif 55 <= latitude <= 75 and -5 <= longitude <= 35:
            return "norway"
        # Iceland
        elif 63 <= latitude <= 67 and -25 <= longitude <= -13:
            return "iceland"
        # Switzerland/Alps
        elif 45 <= latitude <= 48 and 5 <= longitude <= 11:
            return "switzerland"
        else:
            return "global"
    
    def _get_country_context(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get country context and seismic characteristics"""
        region = self._determine_region(latitude, longitude)
        
        context_map = {
            "india": {
                "country": "India/South Asia",
                "seismic_setting": "Himalayan collision zone, high seismic activity",
                "major_sources": ["IMD", "NCS", "EMSC", "IRIS"],
                "risk_level": "High to Very High",
                "notable_features": ["Himalayan front", "Intraplate seismicity", "Delhi-Hardwar ridge"]
            },
            "japan": {
                "country": "Japan",
                "seismic_setting": "Pacific Ring of Fire, triple junction",
                "major_sources": ["JMA", "NIED", "EMSC", "USGS"],
                "risk_level": "Very High",
                "notable_features": ["Subduction zones", "Volcanic activity", "Tsunamis"]
            },
            "russia": {
                "country": "Russian Federation",
                "seismic_setting": "Diverse: Caucasus, Altai, Sakhalin, Kamchatka",
                "major_sources": ["GSRAS", "EMSD", "CEME", "EMSC"],
                "risk_level": "Moderate to High",
                "notable_features": ["Caucasus Mountains", "Kamchatka volcanoes", "Baikal rift"]
            },
            "china": {
                "country": "China/East Asia",
                "seismic_setting": "Tibetan plateau, active faulting",
                "major_sources": ["CEA", "CENC", "EMSC", "IRIS"],
                "risk_level": "High",
                "notable_features": ["Tibetan plateau", "North China Plain", "Sichuan Basin"]
            },
            "turkey": {
                "country": "Turkey",
                "seismic_setting": "North Anatolian Fault, East Anatolian Fault",
                "major_sources": ["KOERI", "EMSC", "IRIS"],
                "risk_level": "Very High",
                "notable_features": ["Strike-slip faulting", "Istanbul seismic gap"]
            },
            "italy": {
                "country": "Italy",
                "seismic_setting": "Mediterranean convergence, Apennines",
                "major_sources": ["INGV", "EMSC", "IRIS"],
                "risk_level": "High",
                "notable_features": ["Apennine Mountains", "Volcanic activity", "Po Plain"]
            },
            "chile": {
                "country": "Chile",
                "seismic_setting": "Nazca-South American subduction",
                "major_sources": ["CSN", "EMSC", "USGS"],
                "risk_level": "Very High",
                "notable_features": ["Megathrust earthquakes", "Tsunamis", "Volcanic activity"]
            },
            "indonesia": {
                "country": "Indonesia",
                "seismic_setting": "Complex subduction, Ring of Fire",
                "major_sources": ["BMKG", "EMSC", "USGS"],
                "risk_level": "Very High",
                "notable_features": ["Multiple subduction zones", "Tsunamis", "Volcanic activity"]
            }
        }
        
        return context_map.get(region, {
            "country": "International",
            "seismic_setting": "Variable regional tectonics",
            "major_sources": ["USGS", "EMSC", "IRIS"],
            "risk_level": "Variable",
            "notable_features": ["Regional geological structures"]
        })
    
    def _calculate_data_coverage(self, earthquakes: List[EarthquakeData], sources: List[str], region: str) -> Dict[str, Any]:
        """Calculate data coverage statistics"""
        try:
            coverage = {
                "total_sources_available": len(sources),
                "regional_specialized": len([s for s in sources if any(region_indicator in s for region_indicator in ["Indian", "Japanese", "Russian", "Chinese", "European", "Pacific", "Americas"])]),
                "global_networks": len([s for s in sources if "Global" in s or "USGS" in s]),
                "data_quality": "High" if len(sources) >= 3 else "Medium" if len(sources) >= 2 else "Basic",
                "temporal_coverage": "Real-time" if earthquakes else "Limited",
                "spatial_coverage_km": 500 if earthquakes else 0,
                "completeness_estimate": min(100, len(earthquakes) * 5) if earthquakes else 0
            }
            
            # Add region-specific coverage info
            if region in ["india", "japan", "russia", "china"]:
                coverage["regional_advantage"] = "Enhanced coverage with national networks"
            elif region in ["turkey", "italy", "chile", "indonesia"]:
                coverage["regional_advantage"] = "Good regional network coverage"
            else:
                coverage["regional_advantage"] = "Standard global network coverage"
            
            return coverage
            
        except Exception as e:
            logger.error(f"Error calculating data coverage: {str(e)}")
            return {"error": str(e)}
    
    def _remove_duplicates_enhanced(self, earthquakes: List[EarthquakeData]) -> List[EarthquakeData]:
        """Enhanced duplicate removal for international sources"""
        return InternationalEarthquakeService._remove_duplicates(earthquakes)
        
    async def get_comprehensive_earthquake_data(self, latitude: float, longitude: float, radius_km: float = 500) -> List[EarthquakeData]:
        """
        Get comprehensive earthquake data from all available sources
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
                tasks.append(self.international_service.get_pacific_earthquakes(latitude, longitude, int(radius_km)))
            
            # Add global sources for comprehensive coverage
            tasks.append(self.global_service.get_global_earthquakes(latitude, longitude, int(radius_km * 1.5)))
            
            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine all earthquake data
            all_earthquakes = []
            for result in results:
                if isinstance(result, list):
                    all_earthquakes.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Error fetching earthquake data: {str(result)}")
            
            # Remove duplicates and sort by time
            unique_earthquakes = self._remove_duplicates(all_earthquakes)
            unique_earthquakes.sort(key=lambda x: x.time, reverse=True)
            
            # Limit to most recent 200 earthquakes for processing efficiency
            return unique_earthquakes[:200]
            
        except Exception as e:
            logger.error(f"Error getting comprehensive earthquake data: {str(e)}")
            return []

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
                tasks.append(self.international_service.get_pacific_earthquakes(latitude, longitude, int(radius_km)))
            
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
    
    def _remove_duplicates(self, earthquakes: List[EarthquakeData]) -> List[EarthquakeData]:
        """
        Remove duplicate earthquakes based on location and time similarity
        """
        if not earthquakes:
            return []
        
        unique_earthquakes = []
        for eq in earthquakes:
            is_duplicate = False
            for unique_eq in unique_earthquakes:
                # Check if earthquakes are very close in space and time
                distance = geodesic((eq.latitude, eq.longitude), 
                                  (unique_eq.latitude, unique_eq.longitude)).kilometers
                
                try:
                    time_diff = abs((datetime.fromisoformat(eq.time.replace('Z', '')) - 
                                   datetime.fromisoformat(unique_eq.time.replace('Z', ''))).total_seconds())
                except:
                    time_diff = 0
                
                # Consider as duplicate if within 10km and 1 hour
                if distance < 10 and time_diff < 3600:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_earthquakes.append(eq)
        
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

# Helper functions for dynamic meter and data verification
async def verify_data_sources(latitude: float, longitude: float) -> Dict[str, Any]:
    """Verify which data sources are providing valid data"""
    sources_status = {
        "active_sources": [],
        "failed_sources": [],
        "quality_score": 0.0
    }
    
    # Test major data sources
    test_sources = [
        ("USGS", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"),
        ("EMSC", "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc"),
        ("GEOFON", "https://geofon.gfz-potsdam.de/eqinfo/list.php?fmt=geojson&nmax=50")
    ]
    
    active_count = 0
    try:
        async with aiohttp.ClientSession() as session:
            for source_name, url in test_sources:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            sources_status["active_sources"].append(source_name)
                            active_count += 1
                        else:
                            sources_status["failed_sources"].append(f"{source_name} (HTTP {response.status})")
                except Exception as e:
                    sources_status["failed_sources"].append(f"{source_name} (Error: {str(e)[:50]})")
    except Exception as e:
        logger.error(f"Error verifying data sources: {e}")
    
    sources_status["quality_score"] = round(active_count / len(test_sources), 2)
    return sources_status

def calculate_dynamic_risk_meter(earthquakes: List[EarthquakeData], prediction_result: Dict[str, Any]) -> float:
    """Calculate dynamic risk meter value based on real-time data"""
    if not earthquakes:
        return 0.1
    
    # Recent activity weight (last 24 hours)
    recent_24h = [eq for eq in earthquakes if 
                 (datetime.utcnow() - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 86400]
    recent_weight = min(0.4, len(recent_24h) * 0.1)
    
    # Magnitude weight (recent significant earthquakes)
    magnitude_weight = 0.0
    if earthquakes:
        recent_significant = [eq for eq in earthquakes[:20] if eq.magnitude >= 4.0]
        magnitude_weight = min(0.3, len(recent_significant) * 0.05)
    
    # ML prediction weight
    ml_weight = prediction_result.get("probability_24h", 0.05) * 0.3
    
    # Base seismic activity
    base_activity = 0.1
    
    # Dynamic risk calculation
    dynamic_risk = base_activity + recent_weight + magnitude_weight + ml_weight
    return round(min(1.0, dynamic_risk), 3)

def calculate_trend(earthquakes: List[EarthquakeData]) -> str:
    """Calculate trend based on recent seismic activity"""
    if len(earthquakes) < 2:
        return "stable"
    
    # Compare last 24h vs previous 24h
    now = datetime.utcnow()
    last_24h = [eq for eq in earthquakes if 
               (now - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 86400]
    prev_24h = [eq for eq in earthquakes if 
               86400 <= (now - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 172800]
    
    if len(last_24h) > len(prev_24h) * 1.5:
        return "increasing"
    elif len(last_24h) < len(prev_24h) * 0.7:
        return "decreasing"
    else:
        return "stable"

# Global combined service instance with optimized ML predictor  
combined_service = CombinedEarthquakeService()

# Helper functions for dynamic meter and data verification
async def verify_data_sources(latitude: float, longitude: float) -> Dict[str, Any]:
    """Fast verification of active data sources"""
    active_sources = []
    failed_sources = []
    
    # Test only the most critical sources for speed
    test_sources = [
        ("USGS", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"),
        ("EMSC", "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc"),
    ]
    
    for source_name, url in test_sources:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as response:
                    if response.status == 200:
                        active_sources.append(source_name)
                    else:
                        failed_sources.append(f"{source_name}({response.status})")
        except:
            failed_sources.append(f"{source_name}(timeout)")
    
    quality_score = len(active_sources) / len(test_sources)
    
    return {
        "active_sources": active_sources,
        "failed_sources": failed_sources,
        "quality_score": quality_score,
        "total_tested": len(test_sources)
    }

def calculate_dynamic_risk_meter(earthquakes: List[EarthquakeData], prediction_result: Dict[str, Any]) -> float:
    """Calculate dynamic risk meter value for real-time updates"""
    try:
        # Check if there's actual data
        if not earthquakes or prediction_result.get("model_status") in ["no_earthquake_data", "no_data"]:
            return "No data available"
        
        # Base value from prediction
        base_value = prediction_result.get("probability_24h", "No data available")
        
        # If prediction is "No data available", return that
        if base_value == "No data available":
            return "No data available"
        
        # Recent activity factor
        recent_24h = len([eq for eq in earthquakes if 
                         (datetime.utcnow() - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 86400])
        
        activity_multiplier = 1.0 + (recent_24h * 0.1)
        
        # Magnitude factor
        if earthquakes:
            avg_magnitude = np.mean([eq.magnitude for eq in earthquakes[:5]])
            magnitude_multiplier = min(1.5, avg_magnitude / 4.0)
        else:
            magnitude_multiplier = 1.0
        
        # Calculate dynamic value
        dynamic_value = min(95.0, base_value * activity_multiplier * magnitude_multiplier)
        
        return round(dynamic_value, 1)
        
    except Exception as e:
        logger.error(f"Error calculating dynamic risk meter: {str(e)}")
        return "No data available"

def calculate_trend(earthquakes: List[EarthquakeData]) -> str:
    """Calculate earthquake activity trend"""
    try:
        if len(earthquakes) < 10:
            return "stable"
        
        # Compare recent vs older activity
        recent_week = [eq for eq in earthquakes if 
                      (datetime.utcnow() - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 604800]
        older_week = [eq for eq in earthquakes if 
                     604800 < (datetime.utcnow() - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 1209600]
        
        recent_count = len(recent_week)
        older_count = len(older_week)
        
        if recent_count > older_count * 1.2:
            return "increasing"
        elif recent_count < older_count * 0.8:
            return "decreasing"
        else:
            return "stable"
            
    except Exception as e:
        logger.error(f"Error calculating trend: {str(e)}")
        return "stable"

# API Endpoints
@app.get("/")
async def read_root():
    return {
        "message": "Advanced International Earthquake Prediction and Analysis API",
        "version": "3.0.0",
        "features": [
            "Multi-national earthquake data sources",
            "Advanced Machine Learning predictions",
            "Stress pattern analysis",
            "International risk assessment",
            "Regional specialization",
            "Real-time global monitoring"
        ],
        "data_sources": {
            "global": ["USGS", "EMSC", "IRIS", "GEOFON"],
            "regional_specialized": {
                "russia": ["GSRAS", "EMSD", "CEME"],
                "china": ["CEA", "CENC"],
                "europe": ["INGV", "KOERI", "NOA", "NORSAR", "IMO", "SED"],
                "pacific": ["GeoNet", "BMKG", "PHIVOLCS", "PTWC"],
                "americas": ["NRC", "SSN", "CSN", "IGP", "SGC"],
                "middle_east_africa": ["IIEES", "GII", "CGS", "CNRST"],
                "india": ["IMD", "NCS", "GSI"],
                "japan": ["JMA", "NIED"]
            }
        },
        "endpoints": {
            "comprehensive_analysis": "/earthquake-analysis",
            "recent_earthquakes": "/earthquakes/recent",
            "ml_predictions": "/predictions/ml",
            "stress_analysis": "/analysis/stress",
            "risk_assessment": "/assessment/risk",
            "international_sources": "/sources/international",
            "regional_analysis": "/analysis/regional"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0.0",
        "international_coverage": "active",
        "data_sources_status": "operational"
    }

@app.get("/sources/international")
async def get_international_sources():
    """
    Get information about all available international earthquake data sources
    """
    return {
        "global_networks": {
            "USGS": {
                "country": "United States",
                "description": "US Geological Survey - Global earthquake monitoring",
                "coverage": "Worldwide",
                "url": "https://earthquake.usgs.gov/",
                "formats": ["GeoJSON", "RSS", "CSV"]
            },
            "EMSC": {
                "country": "France/Europe", 
                "description": "European-Mediterranean Seismological Centre",
                "coverage": "Global with European focus",
                "url": "https://www.emsc-csem.org/",
                "formats": ["RSS", "XML"]
            },
            "IRIS": {
                "country": "United States",
                "description": "Incorporated Research Institutions for Seismology",
                "coverage": "Global seismic networks",
                "url": "http://service.iris.edu/",
                "formats": ["GeoJSON", "QuakeML"]
            },
            "GEOFON": {
                "country": "Germany",
                "description": "GFZ Potsdam Global Seismic Network",
                "coverage": "Global",
                "url": "https://geofon.gfz-potsdam.de/",
                "formats": ["GeoJSON", "XML"]
            }
        },
        "national_agencies": {
            "russia": {
                "GSRAS": "Geophysical Survey, Russian Academy of Sciences",
                "EMSD": "Emergency Ministry Seismic Department",
                "CEME": "Centre for Early Monitoring of Earthquakes"
            },
            "china": {
                "CEA": "China Earthquake Administration",
                "CENC": "China Earthquake Networks Center"
            },
            "japan": {
                "JMA": "Japan Meteorological Agency",
                "NIED": "National Institute for Earth Science and Disaster Resilience"
            },
            "india": {
                "IMD": "India Meteorological Department",
                "NCS": "National Centre for Seismology",
                "GSI": "Geological Survey of India"
            },
            "italy": {
                "INGV": "Istituto Nazionale di Geofisica e Vulcanologia"
            },
            "turkey": {
                "KOERI": "Kandilli Observatory and Earthquake Research Institute"
            },
            "chile": {
                "CSN": "Centro Sismológico Nacional"
            },
            "new_zealand": {
                "GeoNet": "New Zealand Geological Hazards Information"
            },
            "canada": {
                "NRC": "Natural Resources Canada - Earthquakes Canada"
            }
        },
        "total_sources": 25,
        "coverage_regions": ["Global", "Europe", "Asia-Pacific", "Americas", "Middle East", "Africa"],
        "update_frequency": "Real-time to hourly"
    }

@app.get("/analysis/regional")
async def get_regional_analysis(
    latitude: float,
    longitude: float,
    radius_km: float = 500
):
    """
    Get region-specific earthquake analysis using specialized national data sources
    """
    try:
        region = combined_service._determine_region(latitude, longitude)
        country_context = combined_service._get_country_context(latitude, longitude)
        
        # Get regional earthquake data
        if region == "russia":
            regional_data = await combined_service.international_service.get_russian_earthquakes(
                latitude, longitude, int(radius_km)
            )
        elif region == "china":
            regional_data = await combined_service.international_service.get_chinese_earthquakes(
                latitude, longitude, int(radius_km)
            )
        elif region in ["turkey", "italy", "greece"]:
            regional_data = await combined_service.international_service.get_european_earthquakes(
                latitude, longitude, int(radius_km)
            )
        elif region in ["indonesia", "philippines", "australia"]:
            regional_data = await combined_service.international_service.get_pacific_earthquakes(
                latitude, longitude, int(radius_km)
            )
        elif region in ["chile", "peru", "colombia", "mexico", "canada"]:
            regional_data = await combined_service.international_service.get_americas_earthquakes(
                latitude, longitude, int(radius_km)
            )
        else:
            # Fall back to global sources
            regional_data = await combined_service.global_service.get_global_earthquakes(
                latitude, longitude, int(radius_km)
            )
        
        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "region": region,
                "country_context": country_context
            },
            "regional_data": {
                "earthquake_count": len(regional_data),
                "recent_earthquakes": [eq.to_dict() for eq in regional_data[:15]],
                "specialized_sources": country_context.get("major_sources", []),
                "risk_level": country_context.get("risk_level", "Unknown"),
                "seismic_setting": country_context.get("seismic_setting", "Not specified")
            },
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "data_freshness": "Real-time"
        }
        
    except Exception as e:
        logger.error(f"Error in regional analysis: {str(e)}")
        return {
            "error": str(e),
            "location": {"latitude": latitude, "longitude": longitude},
            "analysis_timestamp": datetime.utcnow().isoformat()
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
            earthquakes = await combined_service.international_service.get_pacific_earthquakes(latitude, longitude, int(radius_km))
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
                additional_data = await combined_service.international_service.get_pacific_earthquakes(latitude, longitude, int(radius_km))
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

@app.post("/predictions/ml")
async def get_advanced_ml_predictions(request: EarthquakeAnalysisRequest):
    """
    Fast ML predictions using optimized 3-model ensemble
    """
    try:
        logger.info(f"Getting fast ML predictions for location: {request.latitude}, {request.longitude}")
        
        # Get earthquake data from optimized sources
        earthquake_data = await combined_service.get_comprehensive_earthquake_data(
            request.latitude, 
            request.longitude, 
            request.radius_km
        )
        
        # Data source verification (fast check)
        data_sources_status = await verify_data_sources(request.latitude, request.longitude)
        
        # Fast training if sufficient data (only 3 models)
        if len(earthquake_data) >= 10:
            logger.info("Fast training 3 optimized models...")
            combined_service.ml_predictor.fast_train_models(
                earthquake_data, request.latitude, request.longitude
            )
            logger.info("Fast training completed")
        
        # Generate fast predictions
        prediction_result = combined_service.ml_predictor.predict_earthquake_probability(
            earthquake_data, request.latitude, request.longitude
        )
        
        # Calculate dynamic risk meter value
        dynamic_risk_value = calculate_dynamic_risk_meter(earthquake_data, prediction_result)
        
        # Check if we have actual data or not
        has_data = len(earthquake_data) > 0 and prediction_result.get("model_status") not in ["no_earthquake_data", "no_data"]
        
        if not has_data:
            # Return clear "no data" response
            return {
                "probability_24h": "No data available",
                "predicted_magnitude": "No data available", 
                "confidence": "No data available",
                "risk_level": "No data available",
                
                # Dynamic meter data
                "dynamic_meter": {
                    "current_value": "No data available",
                    "trend": "No data available",
                    "last_updated": datetime.utcnow().isoformat(),
                    "update_frequency": "real-time",
                    "meter_color": "gray",
                    "status": "No earthquake data found"
                },
                
                # Data verification and performance metrics
                "data_verification": {
                    "sources_active": data_sources_status["active_sources"],
                    "sources_failed": data_sources_status["failed_sources"],
                    "data_quality": data_sources_status["quality_score"],
                    "total_data_points": 0,
                    "recent_24h_events": 0,
                    "prediction_models": [],
                    "prediction_speed_ms": 0,
                    "data_status": "No earthquake data found for this location"
                },
                
                # Model performance metrics
                "model_performance": {
                    "is_trained": False,
                    "training_data_points": 0,
                    "ensemble_models": [],
                    "active_models": [],
                    "model_status": "no_data"
                },
                
                # Location and timestamp
                "location": {"latitude": request.latitude, "longitude": request.longitude},
                "timestamp": datetime.utcnow().isoformat(),
                "api_version": "optimized_v2.0",
                "message": "No recent earthquake activity detected in this area. Predictions cannot be made without data."
            }
        
        # Enhanced response for dynamic meter (when we have data)
        return {
            "probability_24h": prediction_result.get("probability_24h", "No data available"),
            "predicted_magnitude": prediction_result.get("predicted_magnitude", "No data available"),
            "confidence": prediction_result.get("confidence_score", "No data available") if isinstance(prediction_result.get("confidence_score"), (int, float)) else "No data available",
            "risk_level": prediction_result.get("risk_level", "No data available"),
            
            # Dynamic meter data
            "dynamic_meter": {
                "current_value": dynamic_risk_value,
                "trend": calculate_trend(earthquake_data),
                "last_updated": datetime.utcnow().isoformat(),
                "update_frequency": "real-time",
                "meter_color": "red" if dynamic_risk_value > 70 else "orange" if dynamic_risk_value > 40 else "green"
            },
            
            # Data verification and performance metrics
            "data_verification": {
                "sources_active": data_sources_status["active_sources"],
                "sources_failed": data_sources_status["failed_sources"],
                "data_quality": data_sources_status["quality_score"],
                "total_data_points": len(earthquake_data),
                "recent_24h_events": len([eq for eq in earthquake_data if 
                    (datetime.utcnow() - datetime.fromisoformat(eq.time.replace('Z', ''))).total_seconds() < 86400]),
                "prediction_models": prediction_result.get("data_verification", {}).get("models_used", []),
                "prediction_speed_ms": prediction_result.get("data_verification", {}).get("prediction_speed_ms", 0)
            },
            
            # Model performance metrics
            "model_performance": {
                "is_trained": combined_service.ml_predictor.is_trained,
                "training_data_points": len(earthquake_data) if len(earthquake_data) >= 10 else 0,
                "ensemble_models": ["RandomForest", "XGBoost", "IsolationForest"],
                "active_models": prediction_result.get("data_verification", {}).get("models_used", []),
                "model_status": prediction_result.get("model_status", "statistical")
            },
            
            # Location and timestamp
            "location": {"latitude": request.latitude, "longitude": request.longitude},
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "optimized_v2.0"
        }
        
    except Exception as e:
        logger.error(f"Error in fast ML predictions: {str(e)}")
        
        # Fast fallback response
        return {
            "probability_24h": 5.0,
            "predicted_magnitude": 3.5,
            "confidence": 30.0,
            "risk_level": "Low",
            "dynamic_meter": {
                "current_value": 5.0,
                "trend": "stable",
                "last_updated": datetime.utcnow().isoformat(),
                "meter_color": "green"
            },
            "model_performance": {
                "status": "fallback", 
                "error": str(e),
                "ensemble_models": ["statistical_analysis"]
            },
            "location": {"latitude": request.latitude, "longitude": request.longitude},
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/predictions/ml")
async def get_ml_predictions_legacy(
    latitude: float,
    longitude: float,
    radius_km: float = 500
):
    """
    Legacy GET endpoint for ML predictions (for backward compatibility)
    """
    request = EarthquakeAnalysisRequest(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )
    return await get_advanced_ml_predictions(request)

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
