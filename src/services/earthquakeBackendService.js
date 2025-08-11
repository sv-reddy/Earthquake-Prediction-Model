/**
 * Real-time Earthquake Data Service
 * Connects to Python FastAPI backend for dynamic earthquake data
 */

const API_BASE_URL = 'http://localhost:8000';

class EarthquakeBackendService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  /**
   * Get earthquakes specifically from Indian sources
   */
  async getIndianEarthquakes(latitude, longitude, options = {}) {
    try {
      const params = new URLSearchParams({
        latitude: latitude.toString(),
        longitude: longitude.toString(),
        radius_km: (options.radiusKm || 500).toString(),
        source: 'indian'
      });

      const response = await fetch(`${this.baseURL}/earthquakes/recent?${params}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data || [],
        count: data.length || 0,
        dataSources: ['Indian Regional', 'EMSC India']
      };
    } catch (error) {
      console.error('Error fetching Indian earthquakes:', error);
      return {
        success: false,
        error: error.message,
        data: []
      };
    }
  }

  /**
   * Get comprehensive earthquake data (USGS + Indian sources)
   */
  async getComprehensiveEarthquakes(latitude, longitude, options = {}) {
    try {
      const params = new URLSearchParams({
        latitude: latitude.toString(),
        longitude: longitude.toString(),
        radius_km: (options.radiusKm || 500).toString(),
        source: 'auto'  // This will auto-select based on location
      });

      const response = await fetch(`${this.baseURL}/earthquakes/recent?${params}`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const earthquakes = await response.json();
      return {
        success: true,
        data: earthquakes || [],
        dataSources: ['USGS', 'Regional']
      };
    } catch (error) {
      console.error('Error fetching comprehensive earthquakes:', error);
      return {
        success: false,
        error: error.message,
        data: []
      };
    }
  }

  /**
   * Get recent earthquakes for a specific location
   */
  async getRecentEarthquakes(latitude, longitude, options = {}) {
    try {
      const {
        radiusKm = 500,
        days = 7,
        minMagnitude = 2.5
      } = options;

      const params = new URLSearchParams({
        latitude: latitude.toString(),
        longitude: longitude.toString(),
        radius_km: radiusKm.toString(),
        days: days.toString(),
        min_magnitude: minMagnitude.toString()
      });

      const response = await fetch(`${this.baseURL}/earthquakes/recent?${params}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data.earthquakes || [],
        count: data.count || 0,
        searchParameters: data.search_parameters,
        lastUpdated: data.last_updated
      };
    } catch (error) {
      console.error('Error fetching recent earthquakes:', error);
      return {
        success: false,
        error: error.message,
        data: []
      };
    }
  }

  /**
   * Get comprehensive stress analysis for a location
   */
  async getStressAnalysis(latitude, longitude, options = {}) {
    try {
      const requestData = {
        latitude,
        longitude,
        radius_km: options.radiusKm || 500,
        days: options.days || 30,
        min_magnitude: options.minMagnitude || 2.5
      };

      const response = await fetch(`${this.baseURL}/analysis/stress`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data
      };
    } catch (error) {
      console.error('Error fetching stress analysis:', error);
      return {
        success: false,
        error: error.message,
        data: null
      };
    }
  }

  /**
   * Get earthquakes by location with full details
   */
  async getEarthquakesByLocation(latitude, longitude, options = {}) {
    try {
      const requestData = {
        latitude,
        longitude,
        radius_km: options.radiusKm || 500,
        days: options.days || 30,
        min_magnitude: options.minMagnitude || 2.5
      };

      const response = await fetch(`${this.baseURL}/earthquakes/location`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const earthquakes = await response.json();
      return {
        success: true,
        data: earthquakes
      };
    } catch (error) {
      console.error('Error fetching earthquakes by location:', error);
      return {
        success: false,
        error: error.message,
        data: []
      };
    }
  }

  /**
   * Get ML-based earthquake predictions for a location
   */
  async getEarthquakePredictions(latitude, longitude, options = {}) {
    try {
      const requestData = {
        latitude,
        longitude,
        radius_km: options.radiusKm || 500,
        days: options.days || 30,
        min_magnitude: options.minMagnitude || 2.5
      };

      const response = await fetch(`${this.baseURL}/predictions/ml`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        probability24h: data.probability_24h || 0,
        predictedMagnitude: data.predicted_magnitude || 0,
        confidence: data.confidence || 0,
        riskLevel: data.risk_level || 'Low',
        modelInfo: data.model_info,
        lastUpdated: data.timestamp
      };
    } catch (error) {
      console.error('Error fetching earthquake predictions:', error);
      return {
        success: false,
        error: error.message,
        probability24h: 0,
        predictedMagnitude: 0,
        confidence: 0,
        riskLevel: 'Unknown'
      };
    }
  }

  /**
   * Check if backend API is healthy
   */
  async checkHealth() {
    try {
      const response = await fetch(`${this.baseURL}/health`);
      return response.ok;
    } catch (error) {
      console.error('Backend health check failed:', error);
      return false;
    }
  }

  /**
   * Format earthquake data for display
   */
  formatEarthquakeData(earthquake) {
    return {
      id: `eq_${earthquake.latitude}_${earthquake.longitude}_${earthquake.time}`,
      magnitude: earthquake.magnitude,
      place: earthquake.place,
      time: new Date(earthquake.time).toLocaleString(),
      location: {
        latitude: earthquake.latitude,
        longitude: earthquake.longitude
      },
      depth: earthquake.depth,
      distanceKm: earthquake.distance_km,
      url: earthquake.url,
      alert: earthquake.alert,
      tsunami: earthquake.tsunami,
      severity: this.getMagnitudeSeverity(earthquake.magnitude),
      timeAgo: this.getTimeAgo(earthquake.time)
    };
  }

  /**
   * Get magnitude severity level
   */
  getMagnitudeSeverity(magnitude) {
    if (magnitude >= 7.0) return { level: 'Major', color: '#DC143C', icon: '🔴' };
    if (magnitude >= 6.0) return { level: 'Strong', color: '#FF4500', icon: '🟠' };
    if (magnitude >= 5.0) return { level: 'Moderate', color: '#FFA500', icon: '🟡' };
    if (magnitude >= 4.0) return { level: 'Light', color: '#DAA520', icon: '🟢' };
    if (magnitude >= 3.0) return { level: 'Minor', color: '#228B22', icon: '🔵' };
    return { level: 'Micro', color: '#696969', icon: '⚪' };
  }

  /**
   * Get human-readable time difference
   */
  getTimeAgo(dateString) {
    const now = new Date();
    const eventTime = new Date(dateString);
    const diffMs = now - eventTime;
    
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMinutes < 60) {
      return `${diffMinutes} minutes ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hours ago`;
    } else {
      return `${diffDays} days ago`;
    }
  }

  /**
   * Get earthquake risk level for a location
   */
  getLocationRiskLevel(earthquakes) {
    if (!earthquakes || earthquakes.length === 0) {
      return { level: 'Low', color: '#228B22' };
    }

    const highMagnitude = earthquakes.filter(eq => eq.magnitude >= 5.0).length;
    const recentEvents = earthquakes.filter(eq => {
      const eventTime = new Date(eq.time);
      const daysDiff = (new Date() - eventTime) / (1000 * 60 * 60 * 24);
      return daysDiff <= 7;
    }).length;

    if (highMagnitude > 2 || recentEvents > 10) {
      return { level: 'High', color: '#DC143C' };
    } else if (highMagnitude > 0 || recentEvents > 5) {
      return { level: 'Moderate', color: '#FFA500' };
    } else if (earthquakes.length > 3) {
      return { level: 'Low-Moderate', color: '#DAA520' };
    } else {
      return { level: 'Low', color: '#228B22' };
    }
  }
}

export default new EarthquakeBackendService();
