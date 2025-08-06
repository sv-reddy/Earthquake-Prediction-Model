import React, { useMemo } from 'react';
import { MapPin, Clock, Zap, AlertTriangle } from 'lucide-react';
import LocationService from '../services/locationService';
import './RecentEarthquakesList.css';

// Helper functions moved outside component to avoid hoisting issues
const getTimeAgo = (date) => {
  const now = new Date();
  const diffMs = now - date;
  const diffHours = diffMs / (1000 * 60 * 60);
  const diffDays = diffMs / (1000 * 60 * 60 * 24);

  if (diffHours < 1) {
    const minutes = Math.floor(diffMs / (1000 * 60));
    return `${minutes}m ago`;
  } else if (diffHours < 24) {
    return `${Math.floor(diffHours)}h ago`;
  } else if (diffDays < 7) {
    return `${Math.floor(diffDays)}d ago`;
  } else {
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: diffDays > 365 ? 'numeric' : undefined
    });
  }
};

const getMagnitudeInfo = (magnitude) => {
  if (magnitude < 3.0) {
    return { level: 'Minor', color: '#228B22', icon: 'low' };
  } else if (magnitude < 4.0) {
    return { level: 'Light', color: '#DAA520', icon: 'low' };
  } else if (magnitude < 5.0) {
    return { level: 'Moderate', color: '#FFA500', icon: 'medium' };
  } else if (magnitude < 6.0) {
    return { level: 'Strong', color: '#D2691E', icon: 'medium' };
  } else if (magnitude < 7.0) {
    return { level: 'Major', color: '#DC143C', icon: 'high' };
  } else {
    return { level: 'Great', color: '#8B0000', icon: 'critical' };
  }
};

const RecentEarthquakesList = ({ earthquakes, userLocation, fullWidth = false }) => {
  const processedEarthquakes = useMemo(() => {
    if (!earthquakes || earthquakes.length === 0) return [];

    return earthquakes
      .map(earthquake => {
        // Handle both new backend format (EarthquakeData) and legacy USGS format
        let props, coords, id;
        
        if (earthquake.properties && earthquake.geometry) {
          // Legacy USGS GeoJSON format
          props = earthquake.properties;
          coords = earthquake.geometry.coordinates;
          id = earthquake.id;
        } else {
          // New backend EarthquakeData format
          props = {
            mag: earthquake.magnitude,
            place: earthquake.place,
            time: earthquake.time,
            tsunami: earthquake.tsunami ? 1 : 0,
            alert: earthquake.alert,
            url: earthquake.url,
            sig: 0 // significance not available in backend format
          };
          coords = [earthquake.longitude, earthquake.latitude, earthquake.depth];
          id = `${earthquake.latitude}_${earthquake.longitude}_${earthquake.time}`;
        }
        
        // Calculate distance from user location
        const distance = userLocation ? 
          LocationService.calculateDistance(
            userLocation.latitude,
            userLocation.longitude,
            coords[1], // latitude
            coords[0]  // longitude
          ) : (earthquake.distance_km || null);

        // Format time - handle both timestamp and ISO string
        let time;
        if (typeof props.time === 'string') {
          // ISO string format from backend
          time = new Date(props.time);
        } else {
          // Timestamp format from USGS
          time = new Date(props.time);
        }
        const timeAgo = getTimeAgo(time);

        // Get magnitude color and risk level
        const magnitudeInfo = getMagnitudeInfo(props.mag);

        return {
          id: id,
          magnitude: props.mag,
          location: props.place,
          time: time,
          timeAgo: timeAgo,
          distance: distance,
          depth: coords[2], // depth in km
          coordinates: { lat: coords[1], lng: coords[0] },
          magnitudeInfo: magnitudeInfo,
          tsunami: props.tsunami === 1,
          significance: props.sig || 0
        };
      })
      .sort((a, b) => b.time - a.time); // Sort by most recent first
  }, [earthquakes, userLocation]);

  const formatDistance = (distance) => {
    if (distance == null) return 'Unknown distance';
    if (distance < 1) {
      return `${(distance * 1000).toFixed(0)}m`;
    } else if (distance < 100) {
      return `${distance.toFixed(1)}km`;
    } else {
      return `${distance.toFixed(0)}km`;
    }
  };

  if (processedEarthquakes.length === 0) {
    return (
      <div className="recent-earthquakes-list">
        <div className="no-earthquakes">
          <AlertTriangle className="no-data-icon" />
          <p>No recent earthquakes within 500km</p>
          <p className="no-data-subtitle">This indicates low seismic activity in your area</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`recent-earthquakes-list ${fullWidth ? 'full-width-grid' : ''}`}>
      {processedEarthquakes.map((earthquake) => (
        <div key={earthquake.id} className="earthquake-item">
          <div className="earthquake-magnitude">
            <div 
              className={`magnitude-badge ${earthquake.magnitudeInfo.icon}`}
              style={{ borderColor: earthquake.magnitudeInfo.color }}
            >
              <span 
                className="magnitude-value"
                style={{ color: earthquake.magnitudeInfo.color }}
              >
                {earthquake.magnitude != null ? earthquake.magnitude.toFixed(1) : '0.0'}
              </span>
            </div>
            <span 
              className="magnitude-level"
              style={{ color: earthquake.magnitudeInfo.color }}
            >
              {earthquake.magnitudeInfo.level}
            </span>
          </div>

          <div className="earthquake-details">
            <div className="earthquake-location">
              <MapPin className="location-icon" />
              <span className="location-text">{earthquake.location}</span>
              {earthquake.tsunami && (
                <span className="tsunami-warning">🌊 Tsunami</span>
              )}
              {earthquake.properties?.indianSeismicZone && (
                <span className="seismic-zone-badge">
                  {earthquake.properties.indianSeismicZone}
                </span>
              )}
            </div>

            <div className="earthquake-info">
              <div className="info-item">
                <Clock className="info-icon" />
                <span>{earthquake.timeAgo}</span>
              </div>
              
              {earthquake.distance && (
                <div className="info-item">
                  <MapPin className="info-icon" />
                  <span>{formatDistance(earthquake.distance)} away</span>
                </div>
              )}
              
              <div className="info-item">
                <Zap className="info-icon" />
                <span>{earthquake.depth != null ? earthquake.depth.toFixed(1) : '0'}km deep</span>
              </div>
            </div>
          </div>

          <div className="earthquake-actions">
            <button 
              className="view-details-btn"
              onClick={() => {
                // Open USGS earthquake details page
                const usgsUrl = `https://earthquake.usgs.gov/earthquakes/eventpage/${earthquake.id}`;
                window.open(usgsUrl, '_blank');
              }}
              title="View detailed information on USGS"
            >
              Details
            </button>
          </div>
        </div>
      ))}

    </div>
  );
};

export default RecentEarthquakesList;
