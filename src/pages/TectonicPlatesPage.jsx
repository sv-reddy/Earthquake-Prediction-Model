import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import { Globe, Navigation, Layers, Info, Zap, TrendingUp } from 'lucide-react';
import TectonicPlatesService from '../services/tectonicPlatesService';
import 'leaflet/dist/leaflet.css';
import './TectonicPlatesPage.css';

// Fix for default markers in react-leaflet
import L from 'leaflet';
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const MapController = ({ center, zoom }) => {
  const map = useMap();
  
  useEffect(() => {
    map.setView(center, zoom);
  }, [map, center, zoom]);
  
  return null;
};

const TectonicPlatesPage = ({ location }) => {
  const [platesData, setPlatesData] = useState(null);
  const [currentPlate, setCurrentPlate] = useState(null);
  const [hoveredPlateData, setHoveredPlateData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (location) {
      loadTectonicData();
    }
  }, [location]);

  const loadTectonicData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Load tectonic plates data
      const [plates, plate] = await Promise.all([
        TectonicPlatesService.loadPlatesData(),
        TectonicPlatesService.getPlateForLocation(location.latitude, location.longitude)
      ]);

      setPlatesData(plates);
      setCurrentPlate(plate);
    } catch (err) {
      setError('Failed to load tectonic data. Please try again.');
      console.error('Error loading tectonic data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getPlateStyle = (feature) => {
    const plateName = feature.properties.PlateName;
    const plateCode = feature.properties.Code;
    
    // Define distinct colors for different tectonic plates
    const plateColors = {
      'PA': { fill: '#FF6B6B', border: '#E53E3E' }, // Pacific - Red
      'NA': { fill: '#4ECDC4', border: '#319795' }, // North American - Teal
      'EU': { fill: '#45B7D1', border: '#3182CE' }, // Eurasian - Blue
      'AF': { fill: '#96CEB4', border: '#38A169' }, // African - Green
      'SA': { fill: '#FFEAA7', border: '#D69E2E' }, // South American - Yellow
      'AU': { fill: '#DDA0DD', border: '#9F7AEA' }, // Australian - Purple
      'AN': { fill: '#87CEEB', border: '#4299E1' }, // Antarctic - Light Blue
      'IN': { fill: '#F7931E', border: '#DD6B20' }, // Indian - Orange
      'CA': { fill: '#FF69B4', border: '#D53F8C' }, // Caribbean - Pink
      'CO': { fill: '#32CD32', border: '#48BB78' }, // Cocos - Lime Green
      'NZ': { fill: '#FF4500', border: '#C05621' }, // Nazca - Orange Red
      'AR': { fill: '#8A2BE2', border: '#6B46C1' }, // Arabian - Blue Violet
      'PH': { fill: '#FFB6C1', border: '#ED64A6' }, // Philippine - Light Pink
      'JF': { fill: '#20B2AA', border: '#2C7A7B' }, // Juan de Fuca - Light Sea Green
      'default': { fill: '#8B4513', border: '#654321' } // Default brown
    };
    
    const colors = plateColors[plateCode] || plateColors.default;
    const isHovered = hoveredPlateData && hoveredPlateData.name === plateName;
    
    return {
      fillColor: colors.fill,
      weight: isHovered ? 3 : 2,
      opacity: 1,
      color: colors.border,
      dashArray: '0',
      fillOpacity: isHovered ? 0.8 : 0.6
    };
  };

  const onPlateClick = (feature, layer) => {
    // Removed click functionality - now only hover shows information
  };

  const onPlateHover = (feature, layer) => {
    const plateName = feature.properties.PlateName;
    const plateCode = feature.properties.Code;
    
    if (plateName) {
      const movement = TectonicPlatesService.getPlateMovement(plateCode);
      // Use a default location for stress calculation if user location not available
      const lat = location ? location.latitude : 0;
      const lon = location ? location.longitude : 0;
      const stressLevel = TectonicPlatesService.calculatePlateStress(plateCode, lat, lon);
      const movementIcon = getMovementIcon(movement.direction);
      
      // Update analysis panel with real-time hovered plate data
      setHoveredPlateData({
        name: plateName,
        code: plateCode,
        movement: movement,
        stressLevel: stressLevel
      });
      
      // Show plate movement information on hover tooltip
      layer.bindTooltip(`
        <div class="plate-tooltip">
          <h4>${plateName}</h4>
          <p><strong>Movement:</strong> ${movementIcon} ${movement.direction}</p>
          <p><strong>Speed:</strong> ${movement.velocity} mm/year</p>
        </div>
      `, {
        permanent: false,
        direction: 'top',
        className: 'custom-tooltip'
      }).openTooltip();
    }
  };

  const onPlateHoverOut = (feature, layer) => {
    layer.closeTooltip();
    // Reset to current location plate when not hovering
    setHoveredPlateData(null);
  };

  const getMovementIcon = (direction) => {
    const icons = {
      'North': '↑', 'Northeast': '↗', 'East': '→', 'Southeast': '↘',
      'South': '↓', 'Southwest': '↙', 'West': '←', 'Northwest': '↖'
    };
    return icons[direction] || '•';
  };

  const getStressColor = (stressLevel) => {
    const colors = {
      'Low': '#228B22',
      'Moderate': '#DAA520',
      'High': '#FFA500',
      'Very High': '#DC143C',
      'Critical': '#8B0000'
    };
    return colors[stressLevel] || '#696969';
  };

  if (isLoading) {
    return (
      <div className="page-container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading tectonic plates data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="error-container">
          <Globe className="error-icon" />
          <h2>Error Loading Tectonic Data</h2>
          <p>{error}</p>
          <button onClick={loadTectonicData} className="retry-button">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="tectonic-plates-page">
      <div className="page-header">
        <h1 className="page-title">Tectonic Plates Analysis</h1>
        <p className="page-subtitle">
          Interactive visualization of tectonic plates movement and stress analysis
        </p>
      </div>

      {/* Main Content Layout - Full Width Map */}
      <div className="main-content-layout">
        {/* Interactive Map - Full width */}
        <div className="map-section-full">
          <MapContainer
          center={[20, 0]}
          zoom={2}
          style={{ height: '500px', width: '100%' }}
          className="tectonic-map"
          scrollWheelZoom={false}
          dragging={false}
          touchZoom={false}
          doubleClickZoom={false}
          boxZoom={false}
          keyboard={false}
        >
          <MapController 
            center={[20, 0]} 
            zoom={2} 
          />
          
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            subdomains="abcd"
          />

          {/* Tectonic Plates Layer - Always visible */}
          {platesData && (
            <GeoJSON
              data={platesData}
              style={getPlateStyle}
              onEachFeature={(feature, layer) => {
                layer.on({
                  mouseover: () => onPlateHover(feature, layer),
                  mouseout: () => onPlateHoverOut(feature, layer)
                });
              }}
            />
          )}
          </MapContainer>
        </div>

        {/* Analysis Section - 20% width */}
        <div className="analysis-section">
          <div className="analysis-card">
            <h3>Plate Analysis</h3>
            {hoveredPlateData ? (
              <div className="analysis-content">
                <div className="analysis-header">
                  <h4 className="plate-name">
                    {hoveredPlateData.name}
                    <span className="hover-indicator">(Hovered)</span>
                  </h4>
                </div>
                
                <div className="analysis-metric">
                  <div className="metric-header">
                    <TrendingUp className="metric-icon" />
                    <span>Movement</span>
                  </div>
                  <div className="metric-data">
                    <span className="direction">
                      {getMovementIcon(hoveredPlateData.movement.direction)} {hoveredPlateData.movement.direction}
                    </span>
                    <span className="velocity">{hoveredPlateData.movement.velocity} mm/year</span>
                  </div>
                </div>
                
                <div className="analysis-metric">
                  <div className="metric-header">
                    <Zap className="metric-icon" />
                    <span>Stress Level</span>
                  </div>
                  <div className="metric-data">
                    <span 
                      className="stress-value"
                      style={{ color: getStressColor(hoveredPlateData.stressLevel) }}
                    >
                      {hoveredPlateData.stressLevel}
                    </span>
                  </div>
                </div>

                <div className="analysis-metric">
                  <div className="metric-header">
                    <Info className="metric-icon" />
                    <span>Real-time Data</span>
                  </div>
                  <div className="metric-data">
                    <span className="risk-info">
                      Live data from hovered plate - each plate has unique movement patterns and stress levels
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="no-data-state">
                <Globe className="no-data-icon" />
                <p>Hover over any tectonic plate to see detailed analysis</p>
                <p className="instruction-text">Each plate is color-coded for easy identification</p>
              </div>
            )}
          </div>
          
          {/* Plate Color Legend */}
          <div className="analysis-card">
            <h3>Plate Legend</h3>
            <div className="legend-content">
              {[
                { code: 'PA', name: 'Pacific', color: '#FF6B6B' },
                { code: 'NA', name: 'North American', color: '#4ECDC4' },
                { code: 'EU', name: 'Eurasian', color: '#45B7D1' },
                { code: 'AF', name: 'African', color: '#96CEB4' },
                { code: 'SA', name: 'South American', color: '#FFEAA7' },
                { code: 'AU', name: 'Australian', color: '#DDA0DD' },
                { code: 'AN', name: 'Antarctic', color: '#87CEEB' },
                { code: 'IN', name: 'Indian', color: '#F7931E' }
              ].map((plate, index) => (
                <div key={index} className="legend-item">
                  <div 
                    className="legend-color"
                    style={{ backgroundColor: plate.color }}
                  ></div>
                  <span className="legend-name">{plate.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TectonicPlatesPage;
