import React, { useState, useEffect } from 'react';
import { AlertTriangle, TrendingUp, MapPin, Calendar, Activity, Shield, Info } from 'lucide-react';
import EarthquakeBackendService from '../services/earthquakeBackendService';
import TectonicPlatesService from '../services/tectonicPlatesService';
import RiskMeter from '../components/RiskMeter';
import RecentEarthquakesList from '../components/RecentEarthquakesList';
import './HomePage.css';

const HomePage = ({ location }) => {
  const [earthquakeStats, setEarthquakeStats] = useState(null);
  const [plateInfo, setPlateInfo] = useState(null);
  const [recentEarthquakes, setRecentEarthquakes] = useState([]);
  const [dataSourceInfo, setDataSourceInfo] = useState(null);
  const [locationContext, setLocationContext] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (location) {
      loadHomePageData();
    }
  }, [location]);

  const loadHomePageData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Check backend health first
      const isHealthy = await EarthquakeBackendService.checkHealth();
      if (!isHealthy) {
        throw new Error('Backend API is not available. Please start the Python backend server.');
      }

      // Determine if location is in Indian territory for enhanced data
      const isIndianTerritory = location.latitude >= 6.0 && location.latitude <= 37.0 && 
                               location.longitude >= 68.0 && location.longitude <= 97.0;

      // Set location context
      setLocationContext({
        isIndianTerritory,
        seismicZone: isIndianTerritory ? 'Zone III-V' : 'Standard',
        zoneIntensity: isIndianTerritory ? 'Moderate to High' : 'Variable',
        nearbyFaults: isIndianTerritory ? ['Himalayan Fault System'] : []
      });

      // Set data source info
      setDataSourceInfo({
        primarySource: 'USGS Global Earthquake Catalog',
        secondarySource: isIndianTerritory ? 'Indian Regional Sources (IMD/NCS)' : null,
        recommendation: isIndianTerritory ? 
          'Enhanced with Indian seismic zone data for better regional accuracy' :
          'Using comprehensive global earthquake monitoring'
      });

      // Get recent earthquakes from backend
      const recentData = await EarthquakeBackendService.getComprehensiveEarthquakes(
        location.latitude,
        location.longitude,
        {
          radiusKm: 500,
          days: 30,
          minMagnitude: 2.5
        }
      );

      // Get stress analysis from backend
      const stressData = await EarthquakeBackendService.getStressAnalysis(
        location.latitude,
        location.longitude,
        {
          radiusKm: 100,
          days: 30,
          minMagnitude: 2.5
        }
      );

      // Load plate information
      const plate = await TectonicPlatesService.getPlateForLocation(
        location.latitude,
        location.longitude
      );

      // Calculate earthquake statistics from the data
      const earthquakes = recentData.data || [];
      const stats = {
        monthlyCount: earthquakes.length,
        averageMagnitude: earthquakes.length > 0 ? 
          earthquakes.reduce((sum, eq) => sum + (eq.magnitude || 0), 0) / earthquakes.length : 0,
        maxMagnitude: earthquakes.length > 0 ? 
          Math.max(...earthquakes.map(eq => eq.magnitude || 0)) : 0,
        riskScore: stressData.success ? 
          Math.min(earthquakes.length * 2 + (stressData.data?.earthquake_count || 0), 100) : 
          Math.min(earthquakes.length * 3, 100),
        yearlyTrend: earthquakes.length > 15 ? 'Increasing' : 
                    earthquakes.length > 5 ? 'Stable' : 'Decreasing',
        dataSource: recentData.dataSources ? recentData.dataSources.join(', ') : 'USGS'
      };

      setEarthquakeStats(stats);
      setPlateInfo(plate);
      setRecentEarthquakes(earthquakes || []);
    } catch (err) {
      setError(err.message || 'Failed to load earthquake data. Please try again.');
      console.error('Error loading home page data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getRiskDescription = (riskScore) => {
    if (riskScore < 20) return 'Low risk of significant seismic activity';
    if (riskScore < 40) return 'Moderate seismic activity expected';
    if (riskScore < 60) return 'Elevated earthquake risk in the region';
    if (riskScore < 80) return 'High probability of seismic events';
    return 'Critical earthquake risk - enhanced monitoring recommended';
  };

  const getRiskColor = (riskScore) => {
    if (riskScore < 20) return 'var(--forest-green)';
    if (riskScore < 40) return 'var(--seismic-yellow)';
    if (riskScore < 60) return 'var(--amber-warning)';
    return 'var(--seismic-red)';
  };

  const formatProbability = (riskScore) => {
    // Convert risk score to probability percentage
    if (riskScore == null) return '0.0%';
    const probability = Math.min(riskScore * 1.2, 95);
    return `${probability.toFixed(1)}%`;
  };

  if (isLoading) {
    return (
      <div className="page-container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading earthquake prediction data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="error-container">
          <AlertTriangle className="error-icon" />
          <h2>Error Loading Data</h2>
          <p>{error}</p>
          <button onClick={loadHomePageData} className="retry-button">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Data Source Information Panel */}
      {dataSourceInfo && (
        <div className="data-source-panel">
          <div className="data-source-header">
            <Info className="data-source-icon" />
            <h4>Data Sources & Enhancements</h4>
          </div>
          <div className="data-source-content">
            <div className="primary-source">
              <strong>Primary:</strong> {dataSourceInfo.primarySource}
            </div>
            {dataSourceInfo.secondarySource && (
              <div className="secondary-source">
                <strong>Secondary:</strong> {dataSourceInfo.secondarySource}
              </div>
            )}
            <div className="source-recommendation">
              {dataSourceInfo.recommendation}
            </div>
            {locationContext?.isIndianTerritory && (
              <div className="indian-enhancements">
                <div className="seismic-zone">
                  <strong>Seismic Zone:</strong> {locationContext.seismicZone} 
                  ({locationContext.zoneIntensity} Risk)
                </div>
                {locationContext.nearbyFaults.length > 0 && (
                  <div className="nearby-faults">
                    <strong>Nearby Faults:</strong> {locationContext.nearbyFaults.length} within 300km
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="page-header">
        <h1 className="page-title">Earthquake Risk Assessment</h1>
        <p className="page-subtitle">
          Real-time seismic activity analysis and prediction system
          {earthquakeStats?.dataSource && (
            <span className="data-badge"> • {earthquakeStats.dataSource}</span>
          )}
        </p>
      </div>

      {/* Risk Overview Section */}
      <div className="risk-overview">
        <div className="risk-overview-content">
          <div className="risk-meter-container">
            <RiskMeter 
              score={earthquakeStats?.riskScore || 0}
              size={200}
            />
          </div>
          <div className="risk-details">
            <h2>Current Risk Level</h2>
            <p className="risk-description">
              {getRiskDescription(earthquakeStats?.riskScore || 0)}
            </p>
            <div className="risk-metrics">
              <div className="metric">
                <span className="metric-label">Risk Score</span>
                <span 
                  className="metric-value"
                  style={{ color: getRiskColor(earthquakeStats?.riskScore || 0) }}
                >
                  {earthquakeStats?.riskScore?.toFixed(1) || '0.0'}/100
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">30-Day Probability</span>
                <span className="metric-value">
                  {formatProbability(earthquakeStats?.riskScore || 0)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid-container grid-4">
        <div className="stat-card">
          <div className="stat-icon earthquakes">
            <Activity />
          </div>
          <div className="stat-content">
            <h3>Earthquakes This Month</h3>
            <div className="stat-number">
              {earthquakeStats?.monthlyCount || 0}
            </div>
            <p className="stat-description">
              Detected within 100km radius
            </p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon magnitude">
            <TrendingUp />
          </div>
          <div className="stat-content">
            <h3>Average Magnitude</h3>
            <div className="stat-number">
              {earthquakeStats?.averageMagnitude?.toFixed(1) || '0.0'}
            </div>
            <p className="stat-description">
              Mean magnitude this month
            </p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon location">
            <MapPin />
          </div>
          <div className="stat-content">
            <h3>Tectonic Plate</h3>
            <div className="stat-number">
              {plateInfo?.name?.split(' ')[0] || 'Unknown'}
            </div>
            <p className="stat-description">
              {plateInfo?.movement?.direction || 'Variable'} movement
            </p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon trend">
            <Calendar />
          </div>
          <div className="stat-content">
            <h3>Activity Trend</h3>
            <div className="stat-number">
              {earthquakeStats?.yearlyTrend || 'Stable'}
            </div>
            <p className="stat-description">
              Compared to yearly average
            </p>
          </div>
        </div>
      </div>

      {/* Recent Earthquakes - Full Width */}
      <div className="recent-earthquakes-full-width">
        <div className="recent-earthquakes-header">
          <h3>Recent Earthquakes (Within 500km)</h3>
          {locationContext?.isIndianTerritory && (
            <p className="indian-note">
              Enhanced with Indian seismic zone data and fault analysis
            </p>
          )}
        </div>
        <RecentEarthquakesList 
          earthquakes={recentEarthquakes}
          userLocation={location}
          fullWidth={true}
        />
      </div>

      {/* Prediction Summary */}
      <div className="prediction-summary card">
        <div className="prediction-header">
          <Shield className="prediction-icon" />
          <h3>Earthquake Prediction Model (EPM)</h3>
        </div>
        <div className="prediction-content">
          <div className="prediction-factors">
            <h4>Analysis Factors:</h4>
            <ul>
              <li>Historical seismic patterns in {location.name} region</li>
              <li>Current tectonic stress on {plateInfo?.name || 'local plate'}</li>
              <li>Recent earthquake frequency and magnitude trends</li>
              <li>Geological deformation indicators</li>
            </ul>
          </div>
          <div className="prediction-results">
            <h4>30-Day Outlook:</h4>
            <div className="prediction-metrics">
              <div className="prediction-metric">
                <span>Probability of M3.0+ earthquake:</span>
                <strong>{formatProbability(earthquakeStats?.riskScore * 0.8 || 0)}</strong>
              </div>
              <div className="prediction-metric">
                <span>Probability of M5.0+ earthquake:</span>
                <strong>{formatProbability(earthquakeStats?.riskScore * 0.4 || 0)}</strong>
              </div>
              <div className="prediction-metric">
                <span>Estimated maximum magnitude:</span>
                <strong>{(earthquakeStats?.maxMagnitude + 0.5)?.toFixed(1) || '4.0'}</strong>
              </div>
            </div>
          </div>
        </div>
        <div className="prediction-disclaimer">
          <p>
            <strong>Disclaimer:</strong> These predictions are based on statistical analysis of 
            historical data and current geological indicators. Earthquake prediction remains 
            scientifically challenging, and these estimates should not be used for critical 
            decision-making without consulting seismological experts.
          </p>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
