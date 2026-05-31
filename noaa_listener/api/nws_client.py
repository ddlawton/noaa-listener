"""NOAA National Weather Service API client."""

from typing import Optional, Dict, Any, List
from noaa_listener.api.base import BaseAPIClient
import noaa_listener.config as config_module
from noaa_listener.logger import get_logger

logger = get_logger(__name__)


class NWSClient(BaseAPIClient):
    """Client for NOAA National Weather Service API."""
    
    def __init__(self, config: Optional[object] = None):
        """Initialize NWS API client.
        
        Args:
            config: Configuration object (if None, will load default)
        """
        self.config = config or config_module.get_config()
        
        headers = {
            'User-Agent': self.config.nws_user_agent,
            'Accept': 'application/geo+json'
        }
        
        super().__init__(
            base_url=self.config.nws_base_url,
            timeout=self.config.nws_timeout,
            max_retries=self.config.nws_max_retries,
            retry_delay=self.config.nws_retry_delay,
            headers=headers
        )
    
    def get_point_metadata(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Get grid metadata for a point.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Point metadata including grid information
        """
        endpoint = f"/points/{latitude:.4f},{longitude:.4f}"
        logger.info(f"Fetching point metadata for {latitude}, {longitude}")
        
        response = self.get(endpoint)
        if response and 'properties' in response:
            logger.info(f"Successfully fetched point metadata")
            return response['properties']
        
        logger.error(f"Failed to fetch point metadata")
        return None
    
    def get_forecast(self, grid_id: str, grid_x: int, grid_y: int) -> Optional[Dict[str, Any]]:
        """Get 7-day forecast for a grid point.
        
        Args:
            grid_id: Grid identifier
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            
        Returns:
            Forecast data
        """
        endpoint = f"/gridpoints/{grid_id}/{grid_x},{grid_y}/forecast"
        logger.info(f"Fetching forecast for grid {grid_id}/{grid_x},{grid_y}")
        
        response = self.get(endpoint)
        if response and 'properties' in response:
            logger.info(f"Successfully fetched forecast with {len(response['properties'].get('periods', []))} periods")
            return response['properties']
        
        logger.error(f"Failed to fetch forecast")
        return None
    
    def get_hourly_forecast(self, grid_id: str, grid_x: int, grid_y: int) -> Optional[Dict[str, Any]]:
        """Get hourly forecast for a grid point.
        
        Args:
            grid_id: Grid identifier
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            
        Returns:
            Hourly forecast data
        """
        endpoint = f"/gridpoints/{grid_id}/{grid_x},{grid_y}/forecast/hourly"
        logger.info(f"Fetching hourly forecast for grid {grid_id}/{grid_x},{grid_y}")
        
        response = self.get(endpoint)
        if response and 'properties' in response:
            logger.info(f"Successfully fetched hourly forecast with {len(response['properties'].get('periods', []))} periods")
            return response['properties']
        
        logger.error(f"Failed to fetch hourly forecast")
        return None
    
    def get_gridded_forecast(self, grid_id: str, grid_x: int, grid_y: int) -> Optional[Dict[str, Any]]:
        """Get raw gridded forecast data for a grid point.
        
        Args:
            grid_id: Grid identifier
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            
        Returns:
            Gridded forecast data
        """
        endpoint = f"/gridpoints/{grid_id}/{grid_x},{grid_y}"
        logger.info(f"Fetching gridded forecast for grid {grid_id}/{grid_x},{grid_y}")
        
        response = self.get(endpoint)
        if response and 'properties' in response:
            logger.info(f"Successfully fetched gridded forecast data")
            return response['properties']
        
        logger.error(f"Failed to fetch gridded forecast")
        return None
    
    def get_stations(self, grid_id: str, grid_x: int, grid_y: int) -> Optional[List[Dict[str, Any]]]:
        """Get observation stations for a grid point.
        
        Args:
            grid_id: Grid identifier
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            
        Returns:
            List of station information
        """
        endpoint = f"/gridpoints/{grid_id}/{grid_x},{grid_y}/stations"
        logger.info(f"Fetching stations for grid {grid_id}/{grid_x},{grid_y}")
        
        response = self.get(endpoint)
        if response and 'features' in response:
            stations = []
            for feature in response['features']:
                if 'properties' in feature:
                    station_data = feature['properties']
                    # Extract coordinates from geometry
                    if 'geometry' in feature and 'coordinates' in feature['geometry']:
                        coords = feature['geometry']['coordinates']
                        station_data['longitude'] = coords[0]
                        station_data['latitude'] = coords[1]
                    stations.append(station_data)
            
            logger.info(f"Successfully fetched {len(stations)} stations")
            return stations
        
        logger.error(f"Failed to fetch stations")
        return None
    
    def get_latest_observation(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Get latest observation from a station.
        
        Args:
            station_id: Station identifier
            
        Returns:
            Latest observation data
        """
        endpoint = f"/stations/{station_id}/observations/latest"
        logger.info(f"Fetching latest observation from station {station_id}")
        
        response = self.get(endpoint)
        if response and 'properties' in response:
            logger.info(f"Successfully fetched latest observation")
            return response['properties']
        
        logger.error(f"Failed to fetch latest observation")
        return None
    
    def get_observations(self, station_id: str, start: Optional[str] = None, end: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get observations from a station for a time range.
        
        Args:
            station_id: Station identifier
            start: Start time (ISO format)
            end: End time (ISO format)
            
        Returns:
            List of observations
        """
        endpoint = f"/stations/{station_id}/observations"
        params = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        
        logger.info(f"Fetching observations from station {station_id}")
        
        response = self.get(endpoint, params=params)
        if response and 'features' in response:
            observations = [f['properties'] for f in response['features'] if 'properties' in f]
            logger.info(f"Successfully fetched {len(observations)} observations")
            return observations
        
        logger.error(f"Failed to fetch observations")
        return None
