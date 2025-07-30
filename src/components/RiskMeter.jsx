import React from 'react';
import './RiskMeter.css';

const RiskMeter = ({ score, size = 150 }) => {
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDasharray = circumference;
  
  // Convert score (0-100) to percentage for the circle
  const percentage = Math.min(Math.max(score, 0), 100);
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  const getRiskLevel = (score) => {
    if (score < 20) return { level: 'Low', color: '#228B22' };
    if (score < 40) return { level: 'Moderate', color: '#DAA520' };
    if (score < 60) return { level: 'High', color: '#FFA500' };
    if (score < 80) return { level: 'very high', color: '#D2691E' };
    return { level: 'Critical', color: '#DC143C' };
  };

  const riskInfo = getRiskLevel(score);

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
          stroke={riskInfo.color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          className="risk-meter-progress"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        
        {/* Risk level markers */}
        {[0, 20, 40, 60, 80, 100].map((value, index) => {
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
        <div className="risk-score" style={{ color: riskInfo.color }}>
          {score.toFixed(1)}
        </div>
        <div className="risk-level" style={{ color: riskInfo.color }}>
          {riskInfo.level}
        </div>
        <div className="risk-label">24-H probability of occurence </div>
      </div>
    </div>
  );
};

export default RiskMeter;
