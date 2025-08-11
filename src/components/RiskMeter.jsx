import React from 'react';
import './RiskMeter.css';

const RiskMeter = ({ 
  probability24h = 0, 
  predictedMagnitude = 0, 
  confidence = 0,
  size = 150 
}) => {
  // Always expect numeric data now (no more "No data available" strings)
  const isDataAvailable = typeof probability24h === 'number' && typeof predictedMagnitude === 'number' && probability24h > 0;
  
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDasharray = circumference;
  
  // Convert probability (0-100) to percentage for the circle
  const percentage = isDataAvailable ? Math.min(Math.max(probability24h, 0), 100) : 0;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  const getRiskLevel = (probability) => {
    if (!isDataAvailable) return { level: 'No Data', color: '#6B7280' };
    if (probability < 5) return { level: 'Very Low', color: '#228B22' };
    if (probability < 15) return { level: 'Low', color: '#32CD32' };
    if (probability < 30) return { level: 'Moderate', color: '#DAA520' };
    if (probability < 50) return { level: 'High', color: '#FFA500' };
    if (probability < 70) return { level: 'Very High', color: '#D2691E' };
    return { level: 'Critical', color: '#DC143C' };
  };

  const getMagnitudeColor = (magnitude) => {
    if (!isDataAvailable) return '#6B7280';
    if (magnitude < 3.0) return '#228B22';
    if (magnitude < 4.0) return '#DAA520';
    if (magnitude < 5.0) return '#FFA500';
    if (magnitude < 6.0) return '#D2691E';
    return '#DC143C';
  };

  const riskInfo = getRiskLevel(isDataAvailable ? probability24h : 0);

  return (
    <div className="risk-meter" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="risk-meter-svg"
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e0e0e0"
          strokeWidth="8"
          className="risk-meter-bg"
        />
        
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={isDataAvailable ? riskInfo.color : '#E5E7EB'}
          strokeWidth="8"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          className="risk-meter-progress"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        
        {/* Risk level markers - only show when data is available */}
        {isDataAvailable && [0, 10, 25, 50, 75, 100].map((value, index) => {
          const angle = (value / 100) * 360 - 90;
          const markerRadius = radius + 15;
          const x = size / 2 + markerRadius * Math.cos((angle * Math.PI) / 180);
          const y = size / 2 + markerRadius * Math.sin((angle * Math.PI) / 180);
          
          return (
            <circle
              key={index}
              cx={x}
              cy={y}
              r="2"
              fill="#8B4513"
              className="risk-meter-marker"
            />
          );
        })}
      </svg>
      
      {/* Center content */}
      <div className="risk-meter-content">        
        <div className="probability-score" style={{ color: riskInfo.color }}>
          {probability24h.toFixed(1)}%
        </div>
        <div className="probability-label">24h Probability</div>
        
        <div className="magnitude-container">
          <div className="predicted-magnitude" style={{ color: getMagnitudeColor(predictedMagnitude) }}>
            M{predictedMagnitude.toFixed(1)}
          </div>
          <div className="magnitude-label">Predicted</div>
        </div>

        {confidence > 0 && (
          <div className="confidence-container">
            <div className="confidence-score">
              {confidence.toFixed(0)}% confidence
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RiskMeter;
