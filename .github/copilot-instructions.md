# Copilot Instructions for Earthquake Prediction Web App

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Project Context
This is a React-based earthquake prediction web application built with Vite. The app uses real-time data from various APIs to predict earthquake probabilities and provide seismic activity analysis.

## Key Features
- Real-time earthquake data from USGS API
- Tectonic plates visualization with movement data
- GNSS deformation indicators from NASA/JPL
- Stress analysis using satellite imagery data
- Location-based risk assessment
- Interactive maps and data visualization

## Tech Stack
- React with Vite
- Leaflet for interactive maps
- Recharts for data visualization
- Axios for API calls
- Lucide React for icons

## Color Scheme
Use earth-toned colors throughout the application:
- Primary: Earth browns (#8B4513, #A0522D)
- Secondary: Geological grays (#696969, #2F4F4F)
- Accent: Seismic reds/oranges (#CD853F, #D2691E)
- Success: Forest greens (#228B22, #006400)
- Warning: Amber (#FFA500, #FF8C00)

## API Integrations
- USGS Earthquake Catalog API for seismic data
- NASA/JPL GNSS Data Products for deformation
- GitHub GeoJSON repositories for tectonic plates
- ESA Sentinel-1 data proxies for stress analysis

## Code Standards
- Use functional components with hooks
- Implement proper error handling for API calls
- Follow responsive design principles
- Use semantic HTML and accessibility best practices
- Implement loading states for all async operations
