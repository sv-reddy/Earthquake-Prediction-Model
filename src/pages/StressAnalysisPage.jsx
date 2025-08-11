import React, { useState, useEffect } from 'react';
import { Activity, AlertTriangle, Info } from 'lucide-react';
import GNSSService from '../services/gnssService';
import RealIndianGeologicalService from '../services/realIndianGeologicalService';
import EarthquakeBackendService from '../services/earthquakeBackendService';
import RecentEarthquakes from '../components/RecentEarthquakes';
import './StressAnalysisPage.css';

const StressAnalysisPage = ({ location }) => {
  const [gnssStations, setGnssStations] = useState([]);
  const [selectedStation, setSelectedStation] = useState(null);
  const [deformationData, setDeformationData] = useState(null);
  const [stressAnalysis, setStressAnalysis] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState('6months');
  const [realTimeStress, setRealTimeStress] = useState(null);
  const [selectedEarthquake, setSelectedEarthquake] = useState(null);

  useEffect(() => {
    if (location) {
      loadStressData();
      loadRealTimeStressData();
    }
  }, [location, timeRange]);

  const loadStressData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Get nearby GNSS stations
      const stations = await GNSSService.getNearbyGNSSStations(
        location.latitude,
        location.longitude,
        200 // 200km radius
      );

      setGnssStations(stations);

      if (stations.length > 0) {
        // Select the closest active station
        const activeStations = stations.filter(station => station.status === 'active');
        const closestStation = activeStations.length > 0 ? activeStations[0] : stations[0];
        setSelectedStation(closestStation);

        // Load deformation data for the selected station
        await loadDeformationData(closestStation.id);
      }
    } catch (err) {
      setError('Failed to load stress analysis data. Please try again.');
      console.error('Error loading stress data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadRealTimeStressData = async () => {
    try {
      const result = await EarthquakeBackendService.getStressAnalysis(
        location.latitude,
        location.longitude,
        {
          radiusKm: 500,
          days: 30,
          minMagnitude: 2.5
        }
      );

      if (result.success) {
        setRealTimeStress(result.data);
      }
    } catch (err) {
      console.error('Error loading real-time stress data:', err);
    }
  };

  const loadDeformationData = async (stationId) => {
    try {
      const endDate = new Date().toISOString().split('T')[0];
      const daysBack = timeRange === '1month' ? 30 : timeRange === '3months' ? 90 : timeRange === '6months' ? 180 : 365;
      const startDate = new Date(Date.now() - daysBack * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

      const data = await GNSSService.getDeformationData(stationId, startDate, endDate);
      setDeformationData(data);

      // Get real stress analysis based on earthquake activity
      const realStressData = await RealIndianGeologicalService.calculateRealStressIndicators(
        location.latitude, 
        location.longitude
      );

      // Perform combined stress analysis (GNSS + real seismic data)
      const analysis = performStressAnalysis(data, realStressData);
      setStressAnalysis(analysis);
    } catch (err) {
      console.error('Error loading deformation data:', err);
      setDeformationData(null);
      setStressAnalysis(null);
    }
  };

  const performStressAnalysis = (data, realStressData) => {
    if (!data || !data.dataPoints || data.dataPoints.length === 0) return null;

    const points = data.dataPoints;
    const recentData = points.slice(-30); // Last 30 days
    const stats = data.statistics;

    // Calculate GNSS-based stress indicators
    const strainRate = calculateStrainRate(points);
    const directionConsistency = calculateDirectionConsistency(points);
    const accelerationTrend = calculateAccelerationTrend(points);
    const stressBuildup = calculateStressBuildup(points);

    // Combine with real seismic stress data
    const baseScore = realStressData ? realStressData.score : (stats?.stressLevel?.score || 0);
    const realStressLevel = realStressData ? realStressData.stressLevel : 'Unknown';

    return {
      overallStressLevel: calculateOverallStressLevel(baseScore, strainRate, accelerationTrend),
      realSeismicStress: {
        level: realStressLevel,
        score: baseScore,
        basedOn: realStressData ? realStressData.basedOn : 'GNSS data only',
        earthquakeCount: realStressData ? realStressData.earthquakeCount : 0
      },
      indicators: {
        strainRate: {
          value: strainRate,
          level: strainRate > 0.5 ? 'High' : strainRate > 0.2 ? 'Medium' : 'Low',
          description: 'Rate of ground deformation from GNSS'
        },
        directionConsistency: {
          value: directionConsistency,
          level: directionConsistency > 0.8 ? 'High' : directionConsistency > 0.5 ? 'Medium' : 'Low',
          description: 'Consistency of deformation direction'
        },
        accelerationTrend: {
          value: accelerationTrend,
          level: accelerationTrend > 0.3 ? 'Increasing' : accelerationTrend < -0.3 ? 'Decreasing' : 'Stable',
          description: 'Change in deformation rate over time'
        },
        stressBuildup: {
          value: stressBuildup,
          level: stressBuildup > 0.7 ? 'Critical' : stressBuildup > 0.4 ? 'High' : stressBuildup > 0.2 ? 'Medium' : 'Low',
          description: 'Accumulated tectonic stress from GNSS measurements'
        },
        realSeismicActivity: {
          value: baseScore,
          level: realStressLevel,
          description: 'Stress level based on recent real earthquake activity'
        }
      },
      recommendations: generateRecommendations(baseScore, strainRate, accelerationTrend, realStressData),
      lastUpdated: new Date().toISOString(),
      dataSource: realStressData ? 'GNSS + Real earthquake data' : 'GNSS data only'
    };
  };

  const calculateStrainRate = (points) => {
    if (points.length < 10) return 0;
    
    const recent = points.slice(-10);
    const older = points.slice(-20, -10);
    
    const recentAvg = recent.reduce((sum, p) => sum + Math.sqrt(p.north * p.north + p.east * p.east), 0) / recent.length;
    const olderAvg = older.reduce((sum, p) => sum + Math.sqrt(p.north * p.north + p.east * p.east), 0) / older.length;
    
    return Math.abs(recentAvg - olderAvg) / 10; // Normalized strain rate
  };

  const calculateDirectionConsistency = (points) => {
    if (points.length < 5) return 0;
    
    const vectors = points.slice(1).map((point, i) => {
      const prev = points[i];
      return Math.atan2(point.east - prev.east, point.north - prev.north);
    });
    
    const avgDirection = vectors.reduce((sum, angle) => sum + angle, 0) / vectors.length;
    const deviations = vectors.map(angle => Math.abs(angle - avgDirection));
    const avgDeviation = deviations.reduce((sum, dev) => sum + dev, 0) / deviations.length;
    
    return Math.max(0, 1 - avgDeviation / Math.PI);
  };

  const calculateAccelerationTrend = (points) => {
    if (points.length < 15) return 0;
    
    const firstThird = points.slice(0, Math.floor(points.length / 3));
    const lastThird = points.slice(-Math.floor(points.length / 3));
    
    const firstRate = firstThird.length > 1 ? 
      Math.sqrt(Math.pow(firstThird[firstThird.length - 1].north - firstThird[0].north, 2) + 
                Math.pow(firstThird[firstThird.length - 1].east - firstThird[0].east, 2)) / firstThird.length : 0;
    
    const lastRate = lastThird.length > 1 ? 
      Math.sqrt(Math.pow(lastThird[lastThird.length - 1].north - lastThird[0].north, 2) + 
                Math.pow(lastThird[lastThird.length - 1].east - lastThird[0].east, 2)) / lastThird.length : 0;
    
    return (lastRate - firstRate) / Math.max(firstRate, 0.1);
  };

  const calculateStressBuildup = (points) => {
    if (points.length === 0) return 0;
    
    const totalDisplacement = Math.sqrt(
      Math.pow(points[points.length - 1].north - points[0].north, 2) +
      Math.pow(points[points.length - 1].east - points[0].east, 2)
    );
    
    const timeSpan = points.length;
    const normalizedDisplacement = totalDisplacement / timeSpan;
    
    return Math.min(normalizedDisplacement / 10, 1); // Normalized to 0-1 scale
  };

  const calculateOverallStressLevel = (baseScore, strainRate, accelerationTrend) => {
    const stressScore = baseScore + (strainRate * 20) + (Math.abs(accelerationTrend) * 15);
    
    if (stressScore < 20) return { level: 'Low', color: '#228B22', score: stressScore };
    if (stressScore < 40) return { level: 'Moderate', color: '#DAA520', score: stressScore };
    if (stressScore < 60) return { level: 'Elevated', color: '#FFA500', score: stressScore };
    if (stressScore < 80) return { level: 'High', color: '#D2691E', score: stressScore };
    return { level: 'Critical', color: '#DC143C', score: stressScore };
  };

  const generateRecommendations = (baseScore, strainRate, accelerationTrend, realStressData) => {
    const recommendations = [];
    
    // Add real data context
    if (realStressData && realStressData.recommendations) {
      recommendations.push(...realStressData.recommendations);
    }
    
    if (baseScore > 60) {
      recommendations.push('Enhanced seismic monitoring recommended based on real earthquake data');
    }
    
    if (strainRate > 0.5) {
      recommendations.push('Significant ground deformation detected in GNSS data - increase observation frequency');
    }
    
    if (accelerationTrend > 0.3) {
      recommendations.push('Accelerating deformation trend - consider early warning protocols');
    }
    
    if (baseScore > 80 && accelerationTrend > 0.2) {
      recommendations.push('Critical stress levels with increasing trend - immediate expert consultation advised');
    }
    
    if (realStressData && realStressData.earthquakeCount > 5) {
      recommendations.push(`High seismic activity detected: ${realStressData.earthquakeCount} recent earthquakes in the region`);
    }
    
    // Add Indian-specific recommendations
    if (isLocationInIndia()) {
      recommendations.push('Consider Indian Building Code IS-1893 seismic guidelines');
      recommendations.push('Regional geological survey data available from GSI');
    }
    
    if (recommendations.length === 0) {
      recommendations.push('Current stress levels appear normal based on available real data');
      recommendations.push('Continue regular monitoring protocols');
    }
    
    return recommendations;
  };

  const handleEarthquakeSelect = (earthquake) => {
    setSelectedEarthquake(earthquake);
    // You can add more logic here, like zooming to earthquake location on a map
  };

  const isLocationInIndia = () => {
    return location.latitude >= 6.0 && location.latitude <= 37.0 && 
           location.longitude >= 68.0 && location.longitude <= 97.0;
  };

  const handleStationChange = async (stationId) => {
    const station = gnssStations.find(s => s.id === stationId);
    setSelectedStation(station);
    
    if (station) {
      await loadDeformationData(stationId);
    }
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <div className="stress-tooltip">
        <p className="tooltip-label">{`Date: ${label}`}</p>
        {payload.map((entry, index) => (
          <p key={index} className="tooltip-value">
            <span style={{ color: entry.color }}>●</span>
            {`${entry.name}: ${entry.value != null ? entry.value.toFixed(2) : '0.00'} mm`}
          </p>
        ))}
      </div>
    );
  };

  // Early return for loading state
  if (isLoading) {
    return (
      <div className="page-container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading stress analysis data...</p>
        </div>
      </div>
    );
  }

  // Early return for error state  
  if (error) {
    return (
      <div className="page-container">
        <div className="error-container">
          <AlertTriangle className="error-icon" />
          <h2>Error Loading Stress Data</h2>
          <p>{error}</p>
          <button onClick={loadStressData} className="retry-button">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="stress-analysis-page">
      <div className="page-header">
        <h1 className="page-title">Stress Analysis</h1>
        <p className="page-subtitle">
          Real-time geological stress and deformation analysis using GNSS and satellite data
        </p>
      </div>

      {/* Real-Time Stress Analysis from Backend */}
      {realTimeStress && Object.keys(realTimeStress).length > 0 && (
        <div className="real-time-stress-analysis card">
          <div className="stress-header">
            <Activity className="stress-icon" />
            <h3>Real-Time Stress Analysis</h3>
            <div className="stress-level-badge" style={{ backgroundColor: 
              realTimeStress.stress_level === 'Critical' ? '#DC143C' :
              realTimeStress.stress_level === 'High' ? '#D2691E' :
              realTimeStress.stress_level === 'Elevated' ? '#FFA500' :
              realTimeStress.stress_level === 'Moderate' ? '#DAA520' : '#228B22'
            }}>
              {realTimeStress.stress_level || 'Unknown'}
            </div>
          </div>
          <div className="stress-content">
            <div className="stress-metrics">
              <div className="metric">
                <span className="metric-label">Stress Score:</span>
                <span className="metric-value">
                  {realTimeStress.stress_score != null ? realTimeStress.stress_score.toFixed(1) : '0.0'}/100
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recent Earthquakes Component */}
      <RecentEarthquakes 
        location={location} 
        onEarthquakeSelect={handleEarthquakeSelect}
      />

      {/* Selected Earthquake Details */}
      {selectedEarthquake && (
        <div className="selected-earthquake-details card">
          <div className="earthquake-detail-header">
            <h3>📍 Selected Earthquake Details</h3>
            <button 
              onClick={() => setSelectedEarthquake(null)}
              className="close-button"
            >
              ✕
            </button>
          </div>
          <div className="earthquake-detail-content">
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">Magnitude:</span>
                <span className="detail-value magnitude-large">
                  M {selectedEarthquake.magnitude != null ? selectedEarthquake.magnitude.toFixed(1) : 'N/A'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Location:</span>
                <span className="detail-value">{selectedEarthquake.place || 'Unknown'}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Time:</span>
                <span className="detail-value">{selectedEarthquake.time || 'Unknown'}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Distance:</span>
                <span className="detail-value">
                  {selectedEarthquake.distanceKm != null ? selectedEarthquake.distanceKm.toFixed(1) : '0'} km away
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Depth:</span>
                <span className="detail-value">
                  {selectedEarthquake.depth != null ? selectedEarthquake.depth.toFixed(1) : '0'} km
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Severity:</span>
                <span className="detail-value" style={{ color: selectedEarthquake.severity?.color || '#888' }}>
                  {selectedEarthquake.severity?.level || 'Unknown'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Real Data Disclaimer */}
      <div className="real-data-disclaimer card">
        <div className="disclaimer-header">
          <Info className="disclaimer-icon" />
          <h3>Real Data Sources & Indian Context</h3>
        </div>
        <div className="disclaimer-content">
          <div className="data-sources">
            <h4>🛰️ GNSS Data Sources:</h4>
            <ul>
              <li><strong>Indian CORS Network:</strong> Survey of India's Continuously Operating Reference Stations</li>
              <li><strong>Real-time positioning:</strong> Centimeter-level accuracy from {gnssStations.length} nearby stations</li>
              <li><strong>Global IGS Network:</strong> International GNSS Service stations where available</li>
            </ul>
          </div>
          <div className="analysis-methods">
            <h4>📊 Analysis Methods:</h4>
            <ul>
              <li><strong>Stress calculations:</strong> Based on real recent earthquake activity from USGS</li>
              <li><strong>Deformation patterns:</strong> Mathematical analysis of actual GNSS measurements</li>
              <li><strong>Indian geological context:</strong> Enhanced with regional seismic zone data</li>
            </ul>
          </div>
          <div className="important-notes">
            <h4>⚠️ Important Notes:</h4>
            <ul>
              <li>Analysis requires real-time access to GNSS/IGS networks (authentication needed for full data)</li>
              <li>Indian locations benefit from enhanced regional geological data</li>
              <li>Stress levels calculated from actual seismic activity patterns</li>
              <li>Professional geological assessment recommended for critical applications</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StressAnalysisPage;
