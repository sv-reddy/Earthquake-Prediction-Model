import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import TectonicPlatesPage from './pages/TectonicPlatesPage';
import StressAnalysisPage from './pages/StressAnalysisPage';
import LocationService from './services/locationService';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [currentLocation, setCurrentLocation] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize with user's current location
  useEffect(() => {
    const initializeLocation = async () => {
      try {
        const position = await LocationService.getCurrentLocation();
        const locationInfo = await LocationService.reverseGeocode(
          position.latitude, 
          position.longitude
        );
        
        setCurrentLocation({
          latitude: position.latitude,
          longitude: position.longitude,
          name: locationInfo.name
        });
      } catch (error) {
        console.error('Could not get current location:', error);
        // Default to a major city if location access is denied
        setCurrentLocation({
          latitude: 37.7749,
          longitude: -122.4194,
          name: 'San Francisco, CA, USA'
        });
      } finally {
        setIsLoading(false);
      }
    };

    initializeLocation();
  }, []);

  const handleLocationChange = (location) => {
    setCurrentLocation(location);
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };

  const renderActiveComponent = () => {
    if (isLoading || !currentLocation) {
      return (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Initializing earthquake prediction system...</p>
        </div>
      );
    }

    switch (activeTab) {
      case 'home':
        return <HomePage location={currentLocation} />;
      case 'tectonic':
        return <TectonicPlatesPage location={currentLocation} />;
      case 'stress':
        return <StressAnalysisPage location={currentLocation} />;
      default:
        return <HomePage location={currentLocation} />;
    }
  };

  return (
    <div className="App">
      <Navbar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        onLocationChange={handleLocationChange}
        currentLocation={currentLocation}
      />
      <main className="main-content">
        {renderActiveComponent()}
      </main>
    </div>
  );
}

export default App;
