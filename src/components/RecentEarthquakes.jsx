import React, { useState, useEffect } from 'react';
import { MapPin, Clock, Activity, AlertTriangle, Waves, ExternalLink, RotateCcw } from 'lucide-react';
import EarthquakeBackendService from '../services/earthquakeBackendService';
import './RecentEarthquakes.css';

const RecentEarthquakes = ({ location, onEarthquakeSelect }) => {
  const [earthquakes, setEarthquakes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchParams, setSearchParams] = useState({
    radiusKm: 500,
    days: 7,
    minMagnitude: 2.5
  });
  const [lastUpdated, setLastUpdated] = useState(null);
  const [backendHealth, setBackendHealth] = useState(false);
  const [dataSource, setDataSource] = useState('comprehensive'); // 'comprehensive', 'usgs', 'indian'
  const [dataSources, setDataSources] = useState([]);

  useEffect(() => {
    checkBackendHealth();
  }, []);

  useEffect(() => {
    if (location && backendHealth) {
      // Auto-select data source based on location
      const isIndianRegion = location.latitude >= 6.0 && location.latitude <= 37.0 && 
                            location.longitude >= 68.0 && location.longitude <= 97.0;
      
      if (isIndianRegion && dataSource === 'comprehensive') {
        // For Indian locations, comprehensive data gives better regional coverage
        setDataSource('comprehensive');
      }
      
      loadRecentEarthquakes();
    }
  }, [location, searchParams, backendHealth, dataSource]);

  const checkBackendHealth = async () => {
    const isHealthy = await EarthquakeBackendService.checkHealth();
    setBackendHealth(isHealthy);
    if (!isHealthy) {
      setError('Backend API is not available. Please start the Python backend server.');
    }
  };

  const loadRecentEarthquakes = async () => {
    if (!location) return;

    setLoading(true);
    setError(null);

    try {
      let result;
      
      // Choose data source based on location and user preference
      if (dataSource === 'indian') {
        result = await EarthquakeBackendService.getIndianEarthquakes(
          location.latitude,
          location.longitude,
          searchParams
        );
      } else if (dataSource === 'comprehensive') {
        // Use comprehensive data (USGS + Indian) for better coverage
        result = await EarthquakeBackendService.getComprehensiveEarthquakes(
          location.latitude,
          location.longitude,
          searchParams
        );
      } else {
        // Default to the original method for USGS data
        result = await EarthquakeBackendService.getRecentEarthquakes(
          location.latitude,
          location.longitude,
          searchParams
        );
      }

      if (result.success) {
        const formattedEarthquakes = result.data.map(eq => 
          EarthquakeBackendService.formatEarthquakeData(eq)
        );
        setEarthquakes(formattedEarthquakes);
        setLastUpdated(result.lastUpdated);
        setDataSources(result.dataSources || ['USGS']);
      } else {
        setError(result.error || 'Failed to load earthquake data');
      }
    } catch (err) {
      setError('Error loading earthquake data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    loadRecentEarthquakes();
  };

  const handleParameterChange = (param, value) => {
    setSearchParams(prev => ({
      ...prev,
      [param]: value
    }));
  };

  const handleEarthquakeClick = (earthquake) => {
    if (onEarthquakeSelect) {
      onEarthquakeSelect(earthquake);
    }
  };

  if (!backendHealth) {
    return (
      <div className="recent-earthquakes-container">
        <div className="backend-status-warning">
          <AlertTriangle className="warning-icon" />
          <div>
            <h3>Backend API Required</h3>
            <p>Please start the Python backend server to load real-time earthquake data.</p>
            <div className="backend-instructions">
              <p><strong>To start the backend:</strong></p>
              <ol>
                <li>Open PowerShell in the project directory</li>
                <li>Run: <code>cd backend</code></li>
                <li>Run: <code>pip install -r requirements.txt</code></li>
                <li>Run: <code>python main.py</code></li>
              </ol>
            </div>
            <button onClick={checkBackendHealth} className="retry-button">
              Check Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="recent-earthquakes-container">
      <div className="earthquakes-header">
        <div className="header-title">
          <Activity className="section-icon" />
          <h2>Recent Earthquakes</h2>
          <span className="earthquake-count">({earthquakes.length})</span>
        </div>
        <button 
          onClick={handleRefresh} 
          className="refresh-button"
          disabled={loading}
        >
          <RotateCcw className={`refresh-icon ${loading ? 'spinning' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Search Parameters */}
      <div className="search-parameters">
        <div className="param-group">
          <label>Data Source:</label>
          <select 
            value={dataSource} 
            onChange={(e) => setDataSource(e.target.value)}
          >
            <option value="comprehensive">🌍 Comprehensive (USGS + Indian)</option>
            <option value="usgs">🇺🇸 USGS Global</option>
            <option value="indian">🇮🇳 Indian Sources (IMD/NCS/GSI)</option>
          </select>
        </div>
        <div className="param-group">
          <label>Radius (km):</label>
          <select 
            value={searchParams.radiusKm} 
            onChange={(e) => handleParameterChange('radiusKm', parseInt(e.target.value))}
          >
            <option value={100}>100 km</option>
            <option value={200}>200 km</option>
            <option value={500}>500 km</option>
            <option value={1000}>1000 km</option>
          </select>
        </div>
        <div className="param-group">
          <label>Time Period:</label>
          <select 
            value={searchParams.days} 
            onChange={(e) => handleParameterChange('days', parseInt(e.target.value))}
          >
            <option value={1}>Last 24 hours</option>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
        <div className="param-group">
          <label>Min Magnitude:</label>
          <select 
            value={searchParams.minMagnitude} 
            onChange={(e) => handleParameterChange('minMagnitude', parseFloat(e.target.value))}
          >
            <option value={1.0}>1.0+</option>
            <option value={2.0}>2.0+</option>
            <option value={2.5}>2.5+</option>
            <option value={3.0}>3.0+</option>
            <option value={4.0}>4.0+</option>
            <option value={5.0}>5.0+</option>
          </select>
        </div>
      </div>

      {/* Data Sources Info */}
      {dataSources.length > 0 && (
        <div className="active-data-sources">
          <h4>📡 Active Data Sources:</h4>
          <div className="sources-list">
            {dataSources.map((source, index) => (
              <span key={index} className="source-badge">{source}</span>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading recent earthquakes...</p>
        </div>
      )}

      {error && (
        <div className="error-container">
          <AlertTriangle className="error-icon" />
          <p>{error}</p>
          <button onClick={handleRefresh} className="retry-button">
            Try Again
          </button>
        </div>
      )}

      {!loading && !error && earthquakes.length === 0 && (
        <div className="no-earthquakes">
          <Activity className="no-data-icon" />
          <h3>No Recent Earthquakes</h3>
          <p>No earthquakes found in the specified area and time period.</p>
          <p className="suggestion">Try increasing the search radius or time period.</p>
        </div>
      )}

      {/* Earthquakes List */}
      {!loading && earthquakes.length > 0 && (
        <div className="earthquakes-list">
          {earthquakes.map((earthquake, index) => (
            <div 
              key={earthquake.id || index} 
              className="earthquake-card"
              onClick={() => handleEarthquakeClick(earthquake)}
            >
              <div className="earthquake-header">
                <div className="magnitude-badge" style={{ backgroundColor: earthquake.severity.color }}>
                  <span className="magnitude-icon">{earthquake.severity.icon}</span>
                  <span className="magnitude-value">M {earthquake.magnitude != null ? earthquake.magnitude.toFixed(1) : 'N/A'}</span>
                </div>
                <div className="earthquake-location">
                  <h4>{earthquake.place}</h4>
                  <div className="location-details">
                    <MapPin className="detail-icon" />
                    <span>{earthquake.distanceKm != null ? earthquake.distanceKm.toFixed(0) : '0'} km away</span>
                  </div>
                </div>
              </div>

              <div className="earthquake-details">
                <div className="detail-row">
                  <Clock className="detail-icon" />
                  <span>{earthquake.time}</span>
                  <span className="time-ago">({earthquake.timeAgo})</span>
                </div>
                
                <div className="detail-row">
                  <Activity className="detail-icon" />
                  <span>Depth: {earthquake.depth != null ? earthquake.depth.toFixed(1) : '0'} km</span>
                  <span className="severity-badge">{earthquake.severity.level}</span>
                </div>

                {earthquake.tsunami && (
                  <div className="detail-row tsunami-warning">
                    <Waves className="detail-icon" />
                    <span>Tsunami Warning</span>
                  </div>
                )}

                {earthquake.alert && (
                  <div className="detail-row alert-level">
                    <AlertTriangle className="detail-icon" />
                    <span>Alert: {earthquake.alert.toUpperCase()}</span>
                  </div>
                )}
              </div>

              <div className="earthquake-actions">
                <a 
                  href={earthquake.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="usgs-link"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink className="link-icon" />
                  View on USGS
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Last Updated */}
      {lastUpdated && (
        <div className="last-updated">
          <Clock className="update-icon" />
          <span>Last updated: {new Date(lastUpdated).toLocaleString()}</span>
        </div>
      )}

      {/* Data Source Info */}
      <div className="data-source-info">
        <h4>📊 Enhanced Data Sources:</h4>
        <ul>
          <li><strong>🇺🇸 USGS Earthquake Catalog:</strong> Global real-time seismic data</li>
          <li><strong>🇮🇳 Indian Meteorological Department (IMD):</strong> Indian regional earthquake data</li>
          <li><strong>🇮🇳 National Centre for Seismology (NCS):</strong> Indian seismic monitoring</li>
          <li><strong>🇮🇳 Geological Survey of India (GSI):</strong> Regional geological data</li>
          <li><strong>🌍 EMSC India Region:</strong> European-Mediterranean Seismological Centre</li>
          <li><strong>📍 Location-based filtering:</strong> Dynamic search around selected location</li>
          <li><strong>🔄 Live updates:</strong> Fresh data from multiple monitoring networks</li>
        </ul>
      </div>
    </div>
  );
};

export default RecentEarthquakes;
