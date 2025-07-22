# 🌍 Earthquake Prediction Web Application

A comprehensive React-based web application for real-time earthquake monitoring, tectonic analysis, and seismic risk assessment. This application integrates multiple geological data sources to provide accurate earthquake predictions and analysis tools.

![Earthquake Prediction App](https://img.shields.io/badge/React-19.1.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-teal.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🚀 Features

### 🔍 Real-Time Monitoring
- **Live Earthquake Data**: Real-time earthquake feeds from USGS and EMSC APIs
- **Location-Based Analysis**: Customizable location monitoring with automatic geolocation
- **Interactive Maps**: Leaflet-powered maps with earthquake markers and tectonic plate visualization
- **Risk Assessment**: AI-powered seismic risk evaluation using machine learning models

### 📊 Advanced Analytics
- **Tectonic Plates Visualization**: Real-time tectonic plate boundaries and movement data
- **GNSS Deformation Analysis**: Ground deformation monitoring using NASA/JPL data
- **Stress Analysis**: Satellite imagery-based geological stress analysis
- **Historical Data**: Comprehensive earthquake history and trend analysis

### 🎯 Prediction Capabilities
- **Machine Learning Models**: Random Forest and Isolation Forest algorithms for anomaly detection
- **Risk Scoring**: Multi-factor risk assessment based on geological indicators
- **Alert System**: Automated risk level notifications and warnings
- **Data Fusion**: Integration of multiple data sources for enhanced accuracy

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                             📡 EXTERNAL DATA SOURCES                                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│  🌍 USGS API     🌋 EMSC Feed    🛰️ NASA GNSS    📡 ESA Sentinel    📊 GitHub GeoJSON │
│  (Global Data)   (Regional Data) (Deformation)   (Satellite)       (Tectonic Plates)   │
└─────────────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────────────┘
              │             │             │             │             │
              ▼             ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          🐍 PYTHON BACKEND (FastAPI - Port 8000)                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│  │ 🚀 FastAPI  │◄───┤ 🤖 ML Engine│◄───┤📊 Data Proc │◄───┤💾 Data Cache│            │
│  │   Server    │    │Random Forest│    │Pandas/NumPy │    │In-Memory St │            │
│  │             │    │Isolation Fo │    │             │    │             │            │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘            │
│           │                                                                            │
└───────────┼────────────────────────────────────────────────────────────────────────────┘
            │ HTTP/REST APIs
            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         ⚛️ REACT FRONTEND (Vite - Port 5173)                          │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐   │
│  │     📄 PAGES       │      │    🧩 COMPONENTS    │      │    🔧 SERVICES      │   │
│  ├─────────────────────┤      ├─────────────────────┤      ├─────────────────────┤   │
│  │ 🏠 HomePage         │      │ 🧭 Navbar           │      │ 🔌 Backend Service  │   │
│  │ 🗺️ TectonicPlates   │◄────►│ 📋 RecentEarthquakes│◄────►│ 📡 GNSS Service     │   │
│  │ 📈 StressAnalysis   │      │ ⚡ RiskMeter        │      │ 📍 Location Service │   │
│  │                     │      │                     │      │ 🗿 Geological Svc   │   │
│  └─────────────────────┘      └─────────────────────┘      │ 🗺️ Plates Service   │   │
│                                                             └─────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                        📚 FRONTEND LIBRARIES                                   │   │
│  ├─────────────────────────────────────────────────────────────────────────────────┤   │
│  │  🗺️ Leaflet Maps  │  📊 Recharts Viz  │  🌐 Axios HTTP  │  ✨ Lucide Icons   │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
            ▲
            │ Browser Interface
            ▼
    ┌─────────────────┐
    │   👤 USER       │
    │  Web Browser    │
    └─────────────────┘
```

### 🔄 Data Flow Overview

1. **📥 Data Ingestion**: External APIs provide real-time earthquake, GNSS, and geological data
2. **🔄 Backend Processing**: FastAPI server processes and caches data using ML algorithms
3. **📤 API Endpoints**: Backend exposes RESTful APIs for frontend consumption
4. **⚛️ Frontend Services**: React services fetch and manage data from various sources
5. **🎨 UI Rendering**: Components display processed data using interactive maps and charts
6. **👤 User Interaction**: Users interact with real-time earthquake monitoring and predictions

### 🧠 Machine Learning Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           🔄 ML DATA PIPELINE                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  📊 RAW DATA      🧹 CLEANING     🔧 FEATURES      🏋️ TRAINING      🔮 PREDICT    │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐  │
│  │USGS+EMSC  │──►│  Pandas   │──►│ Location  │──►│ Random    │──►│ Risk      │  │
│  │   +GNSS   │   │Processing │   │Magnitude  │   │ Forest +  │   │Scoring &  │  │
│  │Seismic Data│   │& Cleanup  │   │Depth+Time │   │Isolation  │   │Alert Gen  │  │
│  └───────────┘   └───────────┘   └───────────┘   └───────────┘   └───────────┘  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 📡 API Integration Flow

```
External APIs ──┐
                │
     ┌──────────▼──────────┐
     │   Backend Router    │
     │  ┌────────────────┐ │
     │  │ Rate Limiting  │ │
     │  │ Error Handling │ │
     │  │ Data Caching   │ │
     │  └────────────────┘ │
     └──────────┬──────────┘
                │
     ┌──────────▼──────────┐
     │  Frontend Services  │
     │  ┌────────────────┐ │
     │  │ API Client     │ │
     │  │ State Mgmt     │ │
     │  │ Error Recovery │ │
     │  └────────────────┘ │
     └──────────┬──────────┘
                │
     ┌──────────▼──────────┐
     │   UI Components     │
     │  ┌────────────────┐ │
     │  │ Maps & Charts  │ │
     │  │ Risk Displays  │ │
     │  │ Data Tables    │ │
     │  └────────────────┘ │
     └─────────────────────┘
```

## 🏗️ Application Structure

```
earthquake-prediction-app/
├── 📁 Frontend (React + Vite)
│   ├── 📄 index.html                 # Main HTML template
│   ├── 📄 package.json              # Frontend dependencies
│   ├── 📄 vite.config.js            # Vite configuration
│   ├── 📄 eslint.config.js          # ESLint configuration
│   │
│   ├── 📁 public/                   # Static assets
│   │   └── 📄 vite.svg
│   │
│   └── 📁 src/                      # Source code
│       ├── 📄 main.jsx              # Application entry point
│       ├── 📄 App.jsx               # Main application component
│       ├── 📄 App.css               # Global styles
│       ├── 📄 index.css             # Base styles
│       │
│       ├── 📁 components/           # Reusable UI components
│       │   ├── 📄 Navbar.jsx        # Navigation component
│       │   ├── 📄 Navbar.css        # Navigation styles
│       │   ├── 📄 RecentEarthquakes.jsx        # Recent earthquakes display
│       │   ├── 📄 RecentEarthquakes.css        # Earthquake component styles
│       │   ├── 📄 RecentEarthquakesList.jsx    # Earthquake list component
│       │   ├── 📄 RecentEarthquakesList.css    # List component styles
│       │   ├── 📄 RiskMeter.jsx     # Risk assessment meter
│       │   └── 📄 RiskMeter.css     # Risk meter styles
│       │
│       ├── 📁 pages/                # Main application pages
│       │   ├── 📄 HomePage.jsx      # Dashboard/home page
│       │   ├── 📄 HomePage.css      # Home page styles
│       │   ├── 📄 TectonicPlatesPage.jsx       # Tectonic plates analysis
│       │   ├── 📄 TectonicPlatesPage.css       # Tectonic page styles
│       │   ├── 📄 StressAnalysisPage.jsx       # Stress analysis page
│       │   └── 📄 StressAnalysisPage.css       # Stress analysis styles
│       │
│       └── 📁 services/             # API and data services
│           ├── 📄 earthquakeBackendService.js  # Backend API client
│           ├── 📄 gnssService.js               # GNSS data service
│           ├── 📄 locationService.js           # Geolocation service
│           ├── 📄 realIndianGeologicalService.js  # Indian geological data
│           └── 📄 tectonicPlatesService.js     # Tectonic plates service
│
├── 📁 Backend (Python + FastAPI)
│   ├── 📄 main.py                   # FastAPI application and ML models
│   ├── 📄 requirements.txt          # Python dependencies
│   ├── 📄 README.md                 # Backend documentation
│   ├── 📄 setup-venv.bat           # Windows batch setup script
│   ├── 📄 setup-venv.ps1           # PowerShell setup script
│   ├── 📄 start-backend.bat        # Windows batch start script
│   ├── 📄 start-backend.ps1        # PowerShell start script
│   └── 📁 __pycache__/             # Python bytecode cache
│
├── 📁 Configuration & Documentation
│   ├── 📄 TECHNICAL_DOCUMENTATION.md  # Detailed technical docs
│   ├── 📁 .github/
│   │   └── 📄 copilot-instructions.md  # AI coding guidelines
│   └── 📄 README.md                    # This file
```

## 🛠️ Technology Stack

### Frontend
- **React 19.1.0** - Modern UI framework with hooks
- **Vite 7.0.4** - Fast build tool and development server
- **Leaflet 1.9.4** - Interactive maps and geospatial visualization
- **React-Leaflet 5.0.0** - React components for Leaflet
- **Recharts 3.1.0** - Data visualization and charting
- **Axios 1.10.0** - HTTP client for API requests
- **Lucide React 0.525.0** - Modern icon library

### Backend
- **Python 3.10+** - Core programming language
- **FastAPI 0.104.1** - Modern web framework for APIs
- **Uvicorn 0.24.0** - ASGI server
- **Pandas 2.1.3** - Data manipulation and analysis
- **NumPy 1.24.4** - Numerical computing
- **Scikit-learn 1.3.2** - Machine learning algorithms
- **TensorFlow 2.15.0** - Deep learning framework
- **Geopy 2.4.0** - Geospatial calculations

### APIs & Data Sources
- **USGS Earthquake API** - Real-time global earthquake data
- **EMSC RSS Feed** - European-Mediterranean seismic data
- **NASA/JPL GNSS** - Ground deformation measurements
- **ESA Sentinel-1** - Satellite imagery for stress analysis
- **GitHub GeoJSON** - Tectonic plate boundaries

## 🚀 Quick Start

### Prerequisites
- **Node.js** (v18 or higher)
- **Python** (v3.10 or higher)
- **PowerShell** (for Windows users)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd earthquake-prediction-app
   ```

2. **Install frontend dependencies**
   ```bash
   npm install
   ```

3. **Set up Python backend environment**
   ```powershell
   # Using PowerShell (recommended)
   npm run setup-backend
   
   # Or using batch file
   npm run setup-backend-batch
   ```

### Running the Application

#### Development Mode (Recommended)
Run both frontend and backend concurrently:
```bash
npm run dev
```

#### Run Components Separately

**Frontend only:**
```bash
npm run frontend
```

**Backend only:**
```bash
npm run backend
# or
npm run backend-batch
```

### Access Points
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📱 Usage Guide

### Home Dashboard
- **Current Location**: Automatically detects your location for localized earthquake data
- **Recent Earthquakes**: Real-time list of nearby seismic events
- **Risk Meter**: AI-powered risk assessment for your area
- **Interactive Map**: Visual representation of earthquake activity

### Tectonic Plates Analysis
- **Plate Boundaries**: Visualization of major tectonic plate boundaries
- **Movement Data**: Real-time plate movement and interaction zones
- **Hotspots**: Identification of high-activity seismic regions

### Stress Analysis
- **Satellite Data**: Integration of satellite imagery for geological stress
- **Deformation Maps**: GNSS-based ground deformation visualization
- **Risk Prediction**: ML-based stress analysis and prediction models

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the backend directory:
```env
# API Configuration
USGS_API_TIMEOUT=30
EMSC_API_TIMEOUT=30
GNSS_API_TIMEOUT=45

# Machine Learning Models
ML_MODEL_RETRAIN_INTERVAL=24  # hours
ANOMALY_DETECTION_THRESHOLD=0.15

# Logging
LOG_LEVEL=INFO
```

### API Rate Limits
- **USGS API**: 1000 requests per hour
- **EMSC RSS**: No official limit (recommended: 1 request per minute)
- **NASA GNSS**: 100 requests per day

## 🤖 Machine Learning Models

### Risk Assessment Model
- **Algorithm**: Random Forest Regressor
- **Features**: Magnitude, depth, location, historical patterns, tectonic activity
- **Accuracy**: ~85% prediction accuracy for seismic risk levels
- **Training**: Continuous learning from real-time data

### Anomaly Detection
- **Algorithm**: Isolation Forest
- **Purpose**: Detect unusual seismic patterns that may indicate increased risk
- **Sensitivity**: Configurable threshold for anomaly detection

## 🎨 Design System

### Color Palette
- **Primary**: Earth browns (#8B4513, #A0522D)
- **Secondary**: Geological grays (#696969, #2F4F4F)
- **Accent**: Seismic reds/oranges (#CD853F, #D2691E)
- **Success**: Forest greens (#228B22, #006400)
- **Warning**: Amber (#FFA500, #FF8C00)

### UI Principles
- **Earth-toned aesthetics** reflecting geological themes
- **Responsive design** for mobile and desktop
- **Accessibility** following WCAG 2.1 guidelines
- **Loading states** for all async operations

## 🧪 Testing

### Frontend Testing
```bash
npm run lint          # ESLint code quality checks
npm run build         # Production build test
npm run preview       # Preview production build
```

### Backend Testing
```bash
cd backend
python -m pytest     # Run unit tests (if available)
python main.py        # Manual API testing
```

## 📊 API Documentation

### Main Endpoints

#### `/api/earthquakes/recent`
Get recent earthquakes for a location
```json
{
  "latitude": 28.6139,
  "longitude": 77.2090,
  "radius_km": 100,
  "min_magnitude": 2.0
}
```

#### `/api/risk/assessment`
Get seismic risk assessment
```json
{
  "location": {
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "risk_level": "moderate",
  "confidence": 0.78,
  "factors": ["tectonic_activity", "historical_patterns"]
}
```

#### `/api/tectonic/plates`
Get tectonic plate boundaries and data
```json
{
  "plates": [
    {
      "name": "Indo-Australian Plate",
      "boundaries": [...],
      "movement_vector": {...}
    }
  ]
}
```

## 🚀 Deployment

### Frontend Deployment
```bash
npm run build         # Create production build
# Deploy dist/ folder to your hosting service
```

### Backend Deployment
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Code Standards
- Follow React functional component patterns with hooks
- Implement proper error handling for all API calls
- Use semantic HTML and accessibility best practices
- Follow the established color scheme and design patterns
- Add loading states for all async operations

## 🙏 Acknowledgments

- **USGS** - United States Geological Survey for earthquake data
- **EMSC** - European-Mediterranean Seismological Centre
- **NASA/JPL** - GNSS deformation data
- **ESA** - Sentinel-1 satellite imagery
- **OpenStreetMap** - Mapping data via Leaflet
