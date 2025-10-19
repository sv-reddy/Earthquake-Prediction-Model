// Location service for getting user location and geocoding
export class LocationService {
  static async getCurrentLocation() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported by this browser'));
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy
          });
        },
        (error) => {
          let errorMessage = 'Unable to retrieve location';
          switch (error.code) {
            case error.PERMISSION_DENIED:
              errorMessage = 'Location access denied by user';
              break;
            case error.POSITION_UNAVAILABLE:
              errorMessage = 'Location information unavailable';
              break;
            case error.TIMEOUT:
              errorMessage = 'Location request timed out';
              break;
          }
          reject(new Error(errorMessage));
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 300000 // 5 minutes
        }
      );
    });
  }

  // Geocode location name to coordinates using OpenStreetMap Nominatim
  static async geocodeLocation(locationName) {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(locationName)}&limit=5`
      );
      
      if (!response.ok) {
        throw new Error('Geocoding request failed');
      }

      const data = await response.json();
      
      if (data.length === 0) {
        throw new Error('Location not found');
      }

      return data.map(result => ({
        name: result.display_name,
        latitude: parseFloat(result.lat),
        longitude: parseFloat(result.lon),
        type: result.type,
        importance: result.importance
      }));
    } catch (error) {
      console.error('Geocoding error:', error);
      throw error;
    }
  }

  // Reverse geocode coordinates to location name
  static async reverseGeocode(latitude, longitude) {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`
      );
      
      if (!response.ok) {
        throw new Error('Reverse geocoding request failed');
      }

      const data = await response.json();
      
      return {
        name: data.display_name,
        address: data.address,
        latitude: latitude,
        longitude: longitude
      };
    } catch (error) {
      console.error('Reverse geocoding error:', error);
      throw error;
    }
  }

  // Get timezone for a location
  static async getTimezone(latitude, longitude) {
    try {
      // Using a free timezone API
      const response = await fetch(
        `http://worldtimeapi.org/api/timezone`
      );
      
      if (!response.ok) {
        throw new Error('Timezone request failed');
      }

      const timezones = await response.json();
      
      // Simple approach: return UTC offset based on longitude
      const utcOffset = Math.round(longitude / 15);
      const timezone = timezones.find(tz => tz.includes(`${utcOffset}`)) || 'UTC';
      
      return {
        timezone: timezone,
        utcOffset: utcOffset
      };
    } catch (error) {
      console.error('Timezone error:', error);
      // Fallback to simple calculation
      return {
        timezone: 'UTC',
        utcOffset: 0
      };
    }
  }

  // Calculate distance between two coordinates
  static calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in kilometers
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  // Format coordinates for display
  static formatCoordinates(latitude, longitude) {
    const formatDegree = (degree, isLatitude) => {
      const direction = isLatitude 
        ? (degree >= 0 ? 'N' : 'S')
        : (degree >= 0 ? 'E' : 'W');
      
      const absValue = Math.abs(degree);
      const degrees = Math.floor(absValue);
      const minutes = Math.floor((absValue - degrees) * 60);
      const seconds = ((absValue - degrees - minutes / 60) * 3600).toFixed(1);
      
      return `${degrees}°${minutes}'${seconds}"${direction}`;
    };

    return {
      decimal: `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`,
      dms: `${formatDegree(latitude, true)}, ${formatDegree(longitude, false)}`
    };
  }

  // Validate coordinates
  static isValidCoordinates(latitude, longitude) {
    return (
      typeof latitude === 'number' &&
      typeof longitude === 'number' &&
      latitude >= -90 &&
      latitude <= 90 &&
      longitude >= -180 &&
      longitude <= 180
    );
  }
}

export default LocationService;
