"""NOAA Climate Data Online (CDO) API client."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from noaa_listener.api.base import BaseAPIClient
import noaa_listener.config as config_module
from noaa_listener.logger import get_logger

logger = get_logger(__name__)


class CDOClient(BaseAPIClient):
    """Client for NOAA Climate Data Online API."""
    
    def __init__(self, config: Optional[object] = None):
        """Initialize CDO API client.
        
        Args:
            config: Configuration object (if None, will load default)
        """
        self.config = config or config_module.get_config()
        
        headers = {
            'token': self.config.cdo_api_token
        }
        
        super().__init__(
            base_url=self.config.cdo_base_url,
            timeout=self.config.cdo_timeout,
            max_retries=self.config.cdo_max_retries,
            retry_delay=self.config.cdo_retry_delay,
            headers=headers
        )
    
    def find_stations(
        self,
        latitude: float,
        longitude: float,
        radius: float = 50.0,
        dataset_id: str = 'GHCND'
    ) -> Optional[List[Dict[str, Any]]]:
        """Find weather stations near a location.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius: Search radius in kilometers
            dataset_id: Dataset identifier (default: GHCND - Global Historical Climatology Network Daily)
            
        Returns:
            List of stations
        """
        # Calculate bounding box from radius (approximate: 1 degree ≈ 111km)
        lat_offset = radius / 111.0
        lon_offset = radius / (111.0 * abs(latitude / 90.0) if latitude != 0 else 111.0)
        
        min_lat = latitude - lat_offset
        max_lat = latitude + lat_offset
        min_lon = longitude - lon_offset
        max_lon = longitude + lon_offset
        
        endpoint = "/stations"
        params = {
            'extent': f"{min_lat},{min_lon},{max_lat},{max_lon}",
            'datasetid': dataset_id,
            'limit': self.config.cdo_limit
        }
        
        logger.info(f"Finding stations near {latitude}, {longitude} within {radius}km")
        
        all_stations = []
        offset = 1
        
        while True:
            params['offset'] = offset
            response = self.get(endpoint, params=params)
            
            if not response or 'results' not in response:
                break
            
            stations = response['results']
            all_stations.extend(stations)
            
            # Check if there are more results
            metadata = response.get('metadata', {})
            result_set = metadata.get('resultset', {})
            count = result_set.get('count', 0)
            
            if offset + len(stations) >= count:
                break
            
            offset += self.config.cdo_limit
        
        logger.info(f"Found {len(all_stations)} stations")
        return all_stations
    
    def get_datasets(self) -> Optional[List[Dict[str, Any]]]:
        """Get available datasets.
        
        Returns:
            List of available datasets
        """
        endpoint = "/datasets"
        params = {'limit': self.config.cdo_limit}
        
        logger.info("Fetching available datasets")
        response = self.get(endpoint, params=params)
        
        if response and 'results' in response:
            datasets = response['results']
            logger.info(f"Found {len(datasets)} datasets")
            return datasets
        
        logger.error("Failed to fetch datasets")
        return None
    
    def get_data_categories(self, dataset_id: str = 'GHCND') -> Optional[List[Dict[str, Any]]]:
        """Get available data categories for a dataset.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            List of data categories
        """
        endpoint = "/datacategories"
        params = {
            'datasetid': dataset_id,
            'limit': self.config.cdo_limit
        }
        
        logger.info(f"Fetching data categories for dataset {dataset_id}")
        response = self.get(endpoint, params=params)
        
        if response and 'results' in response:
            categories = response['results']
            logger.info(f"Found {len(categories)} data categories")
            return categories
        
        logger.error("Failed to fetch data categories")
        return None
    
    def get_data_types(self, dataset_id: str = 'GHCND') -> Optional[List[Dict[str, Any]]]:
        """Get available data types for a dataset.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            List of data types
        """
        endpoint = "/datatypes"
        params = {
            'datasetid': dataset_id,
            'limit': self.config.cdo_limit
        }
        
        logger.info(f"Fetching data types for dataset {dataset_id}")
        
        all_types = []
        offset = 1
        
        while True:
            params['offset'] = offset
            response = self.get(endpoint, params=params)
            
            if not response or 'results' not in response:
                break
            
            data_types = response['results']
            all_types.extend(data_types)
            
            # Check if there are more results
            metadata = response.get('metadata', {})
            result_set = metadata.get('resultset', {})
            count = result_set.get('count', 0)
            
            if offset + len(data_types) >= count:
                break
            
            offset += self.config.cdo_limit
        
        logger.info(f"Found {len(all_types)} data types")
        return all_types
    
    def get_data(
        self,
        dataset_id: str,
        station_id: str,
        start_date: str,
        end_date: str,
        data_types: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get historical weather data.
        
        Args:
            dataset_id: Dataset identifier (e.g., 'GHCND')
            station_id: Station identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            data_types: List of data type IDs to fetch (if None, fetches all)
            
        Returns:
            List of data records
        """
        endpoint = "/data"
        params = {
            'datasetid': dataset_id,
            'stationid': station_id,
            'startdate': start_date,
            'enddate': end_date,
            'limit': self.config.cdo_limit,
            'units': 'metric'
        }
        
        if data_types:
            params['datatypeid'] = ','.join(data_types)
        
        logger.info(f"Fetching data for station {station_id} from {start_date} to {end_date}")
        
        all_data = []
        offset = 1
        
        while True:
            params['offset'] = offset
            response = self.get(endpoint, params=params)
            
            if not response or 'results' not in response:
                break
            
            data = response['results']
            all_data.extend(data)
            
            # Check if there are more results
            metadata = response.get('metadata', {})
            result_set = metadata.get('resultset', {})
            count = result_set.get('count', 0)
            
            if offset + len(data) >= count:
                break
            
            offset += self.config.cdo_limit
        
        logger.info(f"Fetched {len(all_data)} data records")
        return all_data
    
    def get_data_by_date_range(
        self,
        dataset_id: str,
        station_id: str,
        start_date: str,
        end_date: str,
        data_types: Optional[List[str]] = None,
        chunk_days: int = 365
    ) -> List[Dict[str, Any]]:
        """Get historical data by chunking large date ranges.
        
        The CDO API has limits on date range size, so this method
        chunks the request into smaller date ranges.
        
        Args:
            dataset_id: Dataset identifier
            station_id: Station identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            data_types: List of data type IDs to fetch
            chunk_days: Number of days per chunk
            
        Returns:
            Combined list of data records
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        all_data = []
        current_start = start
        
        while current_start < end:
            current_end = min(current_start + timedelta(days=chunk_days), end)
            
            chunk_data = self.get_data(
                dataset_id=dataset_id,
                station_id=station_id,
                start_date=current_start.strftime('%Y-%m-%d'),
                end_date=current_end.strftime('%Y-%m-%d'),
                data_types=data_types
            )
            
            if chunk_data:
                all_data.extend(chunk_data)
            
            current_start = current_end + timedelta(days=1)
        
        logger.info(f"Fetched total of {len(all_data)} records across date range")
        return all_data
