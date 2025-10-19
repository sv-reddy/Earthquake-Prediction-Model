import axios from 'axios';

// Tectonic Plates Service using GitHub GeoJSON data
export class TectonicPlatesService {
  static plateDataURL = 'https://raw.githubusercontent.com/fraxen/tectonicplates/master/GeoJSON/PB2002_plates.json';
  static boundariesURL = 'https://raw.githubusercontent.com/fraxen/tectonicplates/master/GeoJSON/PB2002_boundaries.json';

  // Cached data to avoid repeated API calls
  static plateDataCache = null;
  static boundariesCache = null;

  // Load tectonic plates data
  static async loadPlatesData() {
    if (this.plateDataCache) {
      return this.plateDataCache;
    }

    try {
      const response = await axios.get(this.plateDataURL);
      this.plateDataCache = response.data;
      return this.plateDataCache;
    } catch (error) {
      console.error('Error loading tectonic plates data:', error);
      // Return fallback data for major plates
      return this.getFallbackPlatesData();
    }
  }

  // Load plate boundaries data
  static async loadBoundariesData() {
    if (this.boundariesCache) {
      return this.boundariesCache;
    }

    try {
      const response = await axios.get(this.boundariesURL);
      this.boundariesCache = response.data;
      return this.boundariesCache;
    } catch (error) {
      console.error('Error loading plate boundaries data:', error);
      return this.getFallbackBoundariesData();
    }
  }

  // Find the tectonic plate for a given location
  static async getPlateForLocation(latitude, longitude) {
    try {
      const platesData = await this.loadPlatesData();
      
      for (const feature of platesData.features) {
        if (this.isPointInPolygon(latitude, longitude, feature.geometry)) {
          return {
            name: feature.properties.PlateName || 'Unknown Plate',
            code: feature.properties.Code || 'UNK',
            movement: this.getPlateMovement(feature.properties.Code),
            stressLevel: this.calculatePlateStress(feature.properties.Code, latitude, longitude)
          };
        }
      }

      return {
        name: 'Unknown Plate',
        code: 'UNK',
        movement: { velocity: 0, direction: 'N/A' },
        stressLevel: 'Low'
      };
    } catch (error) {
      console.error('Error finding plate for location:', error);
      return null;
    }
  }

  // Get nearby plate boundaries and their characteristics
  static async getNearbyBoundaries(latitude, longitude, radiusKm = 500) {
    try {
      const boundariesData = await this.loadBoundariesData();
      const nearbyBoundaries = [];

      for (const feature of boundariesData.features) {
        const distance = this.getDistanceToBoundary(latitude, longitude, feature.geometry);
        
        if (distance <= radiusKm) {
          nearbyBoundaries.push({
            type: feature.properties.Type || 'Unknown',
            name: feature.properties.Name || 'Unnamed Boundary',
            distance: distance,
            riskLevel: this.getBoundaryRiskLevel(feature.properties.Type, distance),
            characteristics: this.getBoundaryCharacteristics(feature.properties.Type)
          });
        }
      }

      return nearbyBoundaries.sort((a, b) => a.distance - b.distance);
    } catch (error) {
      console.error('Error finding nearby boundaries:', error);
      return [];
    }
  }

  // Check if a point is inside a polygon
  static isPointInPolygon(latitude, longitude, geometry) {
    if (!geometry || !geometry.coordinates) return false;

    // Handle different geometry types
    if (geometry.type === 'Polygon') {
      return this.pointInPolygon(latitude, longitude, geometry.coordinates[0]);
    } else if (geometry.type === 'MultiPolygon') {
      for (const polygon of geometry.coordinates) {
        if (this.pointInPolygon(latitude, longitude, polygon[0])) {
          return true;
        }
      }
    }
    return false;
  }

  // Ray casting algorithm for point-in-polygon test
  static pointInPolygon(latitude, longitude, polygon) {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i][1], yi = polygon[i][0];
      const xj = polygon[j][1], yj = polygon[j][0];
      
      if (((yi > latitude) !== (yj > latitude)) &&
          (longitude < (xj - xi) * (latitude - yi) / (yj - yi) + xi)) {
        inside = !inside;
      }
    }
    return inside;
  }

  // Calculate distance to nearest boundary
  static getDistanceToBoundary(latitude, longitude, geometry) {
    let minDistance = Infinity;

    if (geometry.type === 'LineString') {
      minDistance = Math.min(minDistance, this.distanceToLineString(latitude, longitude, geometry.coordinates));
    } else if (geometry.type === 'MultiLineString') {
      for (const lineString of geometry.coordinates) {
        minDistance = Math.min(minDistance, this.distanceToLineString(latitude, longitude, lineString));
      }
    }

    return minDistance;
  }

  // Calculate distance from point to line string
  static distanceToLineString(latitude, longitude, coordinates) {
    let minDistance = Infinity;

    for (let i = 0; i < coordinates.length - 1; i++) {
      const distance = this.distanceToSegment(
        latitude, longitude,
        coordinates[i][1], coordinates[i][0],
        coordinates[i + 1][1], coordinates[i + 1][0]
      );
      minDistance = Math.min(minDistance, distance);
    }

    return minDistance;
  }

  // Calculate distance from point to line segment
  static distanceToSegment(lat, lon, lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in km
    
    // Convert to radians
    const φ1 = lat * Math.PI / 180;
    const φ2 = lat1 * Math.PI / 180;
    const φ3 = lat2 * Math.PI / 180;
    const Δλ1 = (lon - lon1) * Math.PI / 180;
    const Δλ2 = (lon2 - lon1) * Math.PI / 180;

    // Distance from point to start of segment
    const d1 = Math.acos(Math.sin(φ1) * Math.sin(φ2) + Math.cos(φ1) * Math.cos(φ2) * Math.cos(Δλ1)) * R;
    
    // Distance from point to end of segment
    const d2 = Math.acos(Math.sin(φ1) * Math.sin(φ3) + Math.cos(φ1) * Math.cos(φ3) * Math.cos(Δλ2 - Δλ1)) * R;

    return Math.min(d1, d2);
  }

  // Get plate movement data (simplified model)
  static getPlateMovement(plateCode) {
    const plateMovements = {
      'PA': { velocity: 65, direction: 'Northwest' }, // Pacific
      'NA': { velocity: 25, direction: 'Southwest' }, // North American
      'EU': { velocity: 15, direction: 'Northeast' }, // Eurasian
      'AF': { velocity: 20, direction: 'Northeast' }, // African
      'SA': { velocity: 35, direction: 'West' },      // South American
      'AU': { velocity: 70, direction: 'North' },     // Australian
      'AN': { velocity: 10, direction: 'Variable' },  // Antarctic
      'IN': { velocity: 50, direction: 'Northeast' }, // Indian
      'CA': { velocity: 45, direction: 'Southeast' }, // Caribbean
      'CO': { velocity: 40, direction: 'Northeast' }, // Cocos
      'NZ': { velocity: 55, direction: 'Northeast' }  // Nazca
    };

    return plateMovements[plateCode] || { velocity: 20, direction: 'Variable' };
  }

  // Calculate plate stress based on location and plate characteristics
  static calculatePlateStress(plateCode, latitude, longitude) {
    // Simplified stress calculation based on known seismic zones
    const seismicZones = [
      { lat: 35, lon: -120, radius: 200, stress: 'High' },   // California
      { lat: 35, lon: 140, radius: 300, stress: 'High' },    // Japan
      { lat: -15, lon: -75, radius: 400, stress: 'High' },   // Peru-Chile
      { lat: 40, lon: 30, radius: 250, stress: 'High' },     // Turkey-Greece
      { lat: -6, lon: 130, radius: 300, stress: 'Very High' } // Indonesia
    ];

    for (const zone of seismicZones) {
      const distance = this.calculateDistance(latitude, longitude, zone.lat, zone.lon);
      if (distance <= zone.radius) {
        return zone.stress;
      }
    }

    // Default stress based on plate type
    const highStressPlates = ['PA', 'IN', 'CO', 'NZ'];
    return highStressPlates.includes(plateCode) ? 'Moderate' : 'Low';
  }

  // Calculate distance between two points
  static calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  // Get boundary risk level
  static getBoundaryRiskLevel(boundaryType, distance) {
    const riskFactors = {
      'Transform': distance < 50 ? 'Very High' : distance < 100 ? 'High' : 'Moderate',
      'Convergent': distance < 100 ? 'High' : distance < 200 ? 'Moderate' : 'Low',
      'Divergent': distance < 150 ? 'Moderate' : 'Low',
      'Subduction': distance < 75 ? 'Very High' : distance < 150 ? 'High' : 'Moderate'
    };

    return riskFactors[boundaryType] || 'Low';
  }

  // Get boundary characteristics
  static getBoundaryCharacteristics(boundaryType) {
    const characteristics = {
      'Transform': {
        description: 'Plates slide past each other horizontally',
        earthquakeType: 'Strike-slip earthquakes',
        typicalMagnitude: '6.0-7.5',
        depth: 'Shallow (0-15 km)'
      },
      'Convergent': {
        description: 'Plates collide and compress',
        earthquakeType: 'Thrust earthquakes',
        typicalMagnitude: '7.0-9.0+',
        depth: 'Variable (0-700 km)'
      },
      'Divergent': {
        description: 'Plates move apart',
        earthquakeType: 'Normal earthquakes',
        typicalMagnitude: '4.0-6.0',
        depth: 'Shallow (0-15 km)'
      },
      'Subduction': {
        description: 'One plate slides under another',
        earthquakeType: 'Megathrust earthquakes',
        typicalMagnitude: '8.0-9.5',
        depth: 'Deep (15-700 km)'
      }
    };

    return characteristics[boundaryType] || {
      description: 'Unknown boundary type',
      earthquakeType: 'Various',
      typicalMagnitude: 'Variable',
      depth: 'Variable'
    };
  }

  // Fallback data for major plates
  static getFallbackPlatesData() {
    return {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: { PlateName: "Pacific Plate", Code: "PA" },
          geometry: {
            type: "Polygon",
            coordinates: [[[-180, -60], [180, -60], [180, 65], [-180, 65], [-180, -60]]]
          }
        }
        // Add more fallback plates as needed
      ]
    };
  }

  // Fallback boundaries data
  static getFallbackBoundariesData() {
    return {
      type: "FeatureCollection",
      features: []
    };
  }
}

export default TectonicPlatesService;
