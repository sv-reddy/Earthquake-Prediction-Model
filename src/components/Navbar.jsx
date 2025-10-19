import React, { useState, useEffect } from 'react';
import { Search, MapPin, Home, Globe, BarChart3, Menu, X } from 'lucide-react';
import LocationService from '../services/locationService';
import './Navbar.css';

const Navbar = ({ activeTab, onTabChange, onLocationChange, currentLocation }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [locationError, setLocationError] = useState('');

  // Extract city and country from location name
  const formatLocationDisplay = (locationName) => {
    if (!locationName) return '';
    
    const parts = locationName.split(',').map(part => part.trim());
    
    // Try to find city and country from the location parts
    // Usually the first part is the most specific (city/town)
    // and the last part is the country
    if (parts.length >= 2) {
      const city = parts[0];
      const country = parts[parts.length - 1];
      return `${city}, ${country}`;
    }
    
    // If we can't parse it properly, return the original name
    return locationName;
  };

  const navItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'tectonic', label: 'Tectonic Plates', icon: Globe },
    { id: 'stress', label: 'Stress Analysis', icon: BarChart3 }
  ];

  const handleSearch = async (query) => {
    if (query.length < 3) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    setIsSearching(true);
    setLocationError('');

    try {
      const results = await LocationService.geocodeLocation(query);
      setSearchResults(results.slice(0, 5)); // Limit to 5 results
      setShowResults(true);
    } catch (error) {
      setLocationError('Location search failed');
      setSearchResults([]);
      setShowResults(false);
    } finally {
      setIsSearching(false);
    }
  };

  const handleLocationSelect = (location) => {
    setSearchQuery(location.name);
    setShowResults(false);
    onLocationChange({
      latitude: location.latitude,
      longitude: location.longitude,
      name: location.name
    });
  };

  const handleCurrentLocation = async () => {
    setLocationError('');
    try {
      const position = await LocationService.getCurrentLocation();
      const locationInfo = await LocationService.reverseGeocode(
        position.latitude, 
        position.longitude
      );
      
      setSearchQuery(locationInfo.name);
      onLocationChange({
        latitude: position.latitude,
        longitude: position.longitude,
        name: locationInfo.name
      });
    } catch (error) {
      setLocationError(error.message);
    }
  };

  useEffect(() => {
    const delayedSearch = setTimeout(() => {
      if (searchQuery) {
        handleSearch(searchQuery);
      }
    }, 300);

    return () => clearTimeout(delayedSearch);
  }, [searchQuery]);

  // Close results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest('.search-container')) {
        setShowResults(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  return (
    <nav className="navbar">
      <div className="navbar-container">
        {/* Logo and Brand */}
        <div className="navbar-brand">
          <Globe className="brand-icon" />
          <span className="brand-text">EarthQuake Predictor</span>
        </div>

        {/* Search Section */}
        <div className="search-container">
          <div className="search-input-wrapper">
            <Search className="search-icon" />
            <input
              type="text"
              placeholder="Enter location (country/state/city)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            <button
              onClick={handleCurrentLocation}
              className="location-btn"
              title="Use current location"
            >
              <MapPin className="location-icon" />
            </button>
          </div>

          {/* Search Results */}
          {showResults && searchResults.length > 0 && (
            <div className="search-results">
              {searchResults.map((result, index) => (
                <div
                  key={index}
                  className="search-result-item"
                  onClick={() => handleLocationSelect(result)}
                >
                  <MapPin className="result-icon" />
                  <div className="result-content">
                    <span className="result-name">{result.name}</span>
                    <span className="result-type">{result.type}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Search Loading */}
          {isSearching && (
            <div className="search-loading">Searching...</div>
          )}

          {/* Location Error */}
          {locationError && (
            <div className="location-error">{locationError}</div>
          )}
        </div>

        {/* Desktop Navigation */}
        <div className="desktop-nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            >
              <item.icon className="nav-icon" />
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        {/* Mobile Menu Toggle */}
        <button
          className="mobile-menu-toggle"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        >
          {isMobileMenuOpen ? <X /> : <Menu />}
        </button>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <div className="mobile-nav">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  onTabChange(item.id);
                  setIsMobileMenuOpen(false);
                }}
                className={`mobile-nav-item ${activeTab === item.id ? 'active' : ''}`}
              >
                <item.icon className="nav-icon" />
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Current Location Display */}
      {currentLocation && (
        <div className="current-location">
          <MapPin className="current-location-icon" />
          <span>{formatLocationDisplay(currentLocation.name)}</span>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
