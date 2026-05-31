"""Data ingestion orchestrator for NOAA data."""

from typing import Optional
from datetime import datetime, timedelta
from itertools import groupby
import time

from noaa_listener.api.nws_client import NWSClient
from noaa_listener.api.cdo_client import CDOClient
from noaa_listener.database import Database
from noaa_listener.ingestion.parsers import (
    parse_station_data,
    parse_forecast_period,
    parse_hourly_forecast,
    parse_gridded_forecast_values,
    parse_observation,
    parse_cdo_data,
    aggregate_cdo_records
)
import noaa_listener.config as config_module
from noaa_listener.logger import get_logger

logger = get_logger(__name__)

# Station priority constants for historical data backfill
STATION_PRIORITY_AIRPORT = 0  # Airport/ASOS stations (highest quality)
STATION_PRIORITY_COOP = 1     # COOP network stations (good quality)
STATION_PRIORITY_OTHER = 2    # Other stations
STATION_PRIORITY_VOLUNTEER = 3 # Volunteer stations (often sparse data)


class DataIngestor:
    """Orchestrates data fetching and storage."""
    
    def __init__(self, config: Optional[object] = None, db: Optional[Database] = None):
        """Initialize data ingestor.
        
        Args:
            config: Configuration object
            db: Database connection
        """
        self.config = config or config_module.get_config()
        self.db = db or Database(self.config)
        self.nws_client = NWSClient(self.config)
        self.cdo_client = CDOClient(self.config)
        self.grid_info = None
        self.station_id = None
    
    def initialize(self) -> bool:
        """Initialize the ingestor by fetching grid metadata.
        
        Returns:
            True if initialization successful
        """
        logger.info(f"Initializing for location: {self.config.latitude}, {self.config.longitude}")
        
        # Get grid information
        point_data = self.nws_client.get_point_metadata(
            self.config.latitude,
            self.config.longitude
        )
        
        if not point_data:
            logger.error("Failed to get grid metadata")
            return False
        
        self.grid_info = {
            'grid_id': point_data.get('gridId'),
            'grid_x': point_data.get('gridX'),
            'grid_y': point_data.get('gridY'),
            'forecast_url': point_data.get('forecast'),
            'forecast_hourly_url': point_data.get('forecastHourly'),
            'forecast_grid_data_url': point_data.get('forecastGridData'),
            'stations_url': point_data.get('observationStations'),
            'timezone': point_data.get('timeZone'),
            'radar_station': point_data.get('radarStation')
        }
        
        logger.info(f"Grid info: {self.grid_info['grid_id']}/{self.grid_info['grid_x']},{self.grid_info['grid_y']}")
        
        # Fetch and store stations
        stations = self.nws_client.get_stations(
            self.grid_info['grid_id'],
            self.grid_info['grid_x'],
            self.grid_info['grid_y']
        )
        
        if stations:
            with self.db.get_session() as session:
                for station in stations:
                    parsed_station = parse_station_data(station)
                    self.db.upsert_station(session, parsed_station)
                    
                    # Use first station as primary
                    if self.station_id is None:
                        self.station_id = parsed_station['station_id']
                        logger.info(f"Primary station: {self.station_id}")
        
        return True
    
    def ingest_forecasts(self) -> bool:
        """Ingest all types of forecast data.
        
        Returns:
            True if successful
        """
        if not self.grid_info:
            logger.error("Grid info not initialized")
            return False
        
        success = True
        generated_at = datetime.utcnow()
        
        # 7-day forecast
        if not self._ingest_forecast_periods(generated_at):
            success = False
        
        # Hourly forecast
        if not self._ingest_hourly_forecast(generated_at):
            success = False
        
        # Gridded forecast
        if not self._ingest_gridded_forecast(generated_at):
            success = False
        
        return success
    
    def _ingest_forecast_periods(self, generated_at: datetime) -> bool:
        """Ingest 7-day forecast periods.
        
        Args:
            generated_at: Timestamp of forecast generation
            
        Returns:
            True if successful
        """
        start_time = time.time()
        
        try:
            forecast_data = self.nws_client.get_forecast(
                self.grid_info['grid_id'],
                self.grid_info['grid_x'],
                self.grid_info['grid_y']
            )
            
            if not forecast_data:
                logger.error("Failed to fetch forecast periods")
                return False
            
            periods = forecast_data.get('periods', [])
            parsed_periods = []
            
            for period in periods:
                parsed = parse_forecast_period(
                    period,
                    self.grid_info['grid_id'],
                    self.grid_info['grid_x'],
                    self.grid_info['grid_y'],
                    self.station_id or '',
                    generated_at
                )
                parsed_periods.append(parsed)
            
            with self.db.get_session() as session:
                inserted = self.db.insert_forecast_periods(session, parsed_periods)
                
                # Log the operation
                self.db.log_data_fetch(session, {
                    'fetch_type': 'forecast',
                    'data_source': 'NWS',
                    'station_id': self.station_id,
                    'start_time': None,
                    'end_time': None,
                    'records_fetched': len(parsed_periods),
                    'records_inserted': inserted,
                    'records_updated': 0,
                    'status': 'success',
                    'error_message': None,
                    'fetch_duration_seconds': time.time() - start_time
                })
            
            logger.info(f"Ingested {inserted} forecast periods")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting forecast periods: {e}")
            
            with self.db.get_session() as session:
                self.db.log_data_fetch(session, {
                    'fetch_type': 'forecast',
                    'data_source': 'NWS',
                    'station_id': self.station_id,
                    'start_time': None,
                    'end_time': None,
                    'records_fetched': 0,
                    'records_inserted': 0,
                    'records_updated': 0,
                    'status': 'failed',
                    'error_message': str(e),
                    'fetch_duration_seconds': time.time() - start_time
                })
            
            return False
    
    def _ingest_hourly_forecast(self, generated_at: datetime) -> bool:
        """Ingest hourly forecast data.
        
        Args:
            generated_at: Timestamp of forecast generation
            
        Returns:
            True if successful
        """
        start_time = time.time()
        
        try:
            forecast_data = self.nws_client.get_hourly_forecast(
                self.grid_info['grid_id'],
                self.grid_info['grid_x'],
                self.grid_info['grid_y']
            )
            
            if not forecast_data:
                logger.error("Failed to fetch hourly forecast")
                return False
            
            periods = forecast_data.get('periods', [])
            parsed_periods = []
            
            for period in periods:
                parsed = parse_hourly_forecast(
                    period,
                    self.grid_info['grid_id'],
                    self.grid_info['grid_x'],
                    self.grid_info['grid_y'],
                    self.station_id or '',
                    generated_at
                )
                parsed_periods.append(parsed)
            
            with self.db.get_session() as session:
                inserted = self.db.insert_forecast_hourly(session, parsed_periods)
                
                self.db.log_data_fetch(session, {
                    'fetch_type': 'hourly',
                    'data_source': 'NWS',
                    'station_id': self.station_id,
                    'start_time': None,
                    'end_time': None,
                    'records_fetched': len(parsed_periods),
                    'records_inserted': inserted,
                    'records_updated': 0,
                    'status': 'success',
                    'error_message': None,
                    'fetch_duration_seconds': time.time() - start_time
                })
            
            logger.info(f"Ingested {inserted} hourly forecast periods")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting hourly forecast: {e}")
            
            with self.db.get_session() as session:
                self.db.log_data_fetch(session, {
                    'fetch_type': 'hourly',
                    'data_source': 'NWS',
                    'station_id': self.station_id,
                    'start_time': None,
                    'end_time': None,
                    'records_fetched': 0,
                    'records_inserted': 0,
                    'records_updated': 0,
                    'status': 'failed',
                    'error_message': str(e),
                    'fetch_duration_seconds': time.time() - start_time
                })
            
            return False
    
    def _ingest_gridded_forecast(self, generated_at: datetime) -> bool:
        """Ingest gridded forecast data.
        
        Args:
            generated_at: Timestamp of forecast generation
            
        Returns:
            True if successful
        """
        start_time = time.time()
        
        try:
            gridded_data = self.nws_client.get_gridded_forecast(
                self.grid_info['grid_id'],
                self.grid_info['grid_x'],
                self.grid_info['grid_y']
            )
            
            if not gridded_data:
                logger.error("Failed to fetch gridded forecast")
                return False
            
            parsed_records = parse_gridded_forecast_values(
                gridded_data,
                self.grid_info['grid_id'],
                self.grid_info['grid_x'],
                self.grid_info['grid_y'],
                generated_at
            )
            
            with self.db.get_session() as session:
                inserted = self.db.insert_forecast_gridded(session, parsed_records)
                
                self.db.log_data_fetch(session, {
                    'fetch_type': 'gridded',
                    'data_source': 'NWS',
                    'station_id': self.station_id,
                    'start_time': None,
                    'end_time': None,
                    'records_fetched': len(parsed_records),
                    'records_inserted': inserted,
                    'records_updated': 0,
                    'status': 'success',
                    'error_message': None,
                    'fetch_duration_seconds': time.time() - start_time
                })
            
            logger.info(f"Ingested {inserted} gridded forecast records")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting gridded forecast: {e}")
            
            with self.db.get_session() as session:
                self.db.log_data_fetch(session, {
                    'fetch_type': 'gridded',
                    'data_source': 'NWS',
                    'station_id': self.station_id,
                    'start_time': None,
                    'end_time': None,
                    'records_fetched': 0,
                    'records_inserted': 0,
                    'records_updated': 0,
                    'status': 'failed',
                    'error_message': str(e),
                    'fetch_duration_seconds': time.time() - start_time
                })
            
            return False
    
    def ingest_current_conditions(self) -> bool:
        """Ingest current conditions from nearby stations.
        Returns:
            True if successful
        """
        if not self.station_id:
            logger.error("No station ID available")
            return False
        start_time = time.time()
        try:
            obs_data = self.nws_client.get_latest_observation(self.station_id)
            if not obs_data:
                logger.warning(f"No observation data available for {self.station_id}")
                return False
            parsed_obs = parse_observation(obs_data, self.station_id)
            with self.db.get_session() as session:
                inserted = self.db.insert_observations(session, [parsed_obs])
                self.db.log_data_fetch(session, {
                    'fetch_type': 'current',
                    'data_source': 'NWS',
                    'station_id': self.station_id,
                    'start_time': None,
                    'end_time': None,
                    'records_fetched': 1,
                    'records_inserted': inserted,
                    'records_updated': 0,
                    'status': 'success',
                    'error_message': None,
                    'fetch_duration_seconds': time.time() - start_time
                })
            logger.info(f"Ingested current conditions")
            return True
        except KeyError as e:
            logger.error(f"Data parsing error for current conditions: {e} - data may be malformed")
            return False
        except ValueError as e:
            logger.error(f"Data validation error for current conditions: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error ingesting current conditions: {e}", exc_info=True)
            # Log failed attempt to database
            try:
                with self.db.get_session() as session:
                    self.db.log_data_fetch(session, {
                        'fetch_type': 'current',
                        'data_source': 'NWS',
                        'station_id': self.station_id,
                        'start_time': None,
                        'end_time': None,
                        'records_fetched': 0,
                        'records_inserted': 0,
                        'records_updated': 0,
                        'status': 'failed',
                        'error_message': str(e),
                        'fetch_duration_seconds': time.time() - start_time
                    })
            except Exception:
                pass  # Don't fail if we can't log the error
            return False
    
    def ingest_historical_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> bool:
        """Ingest historical data from CDO API.
        
        Args:
            start_date: Start date (YYYY-MM-DD), defaults to config
            end_date: End date (YYYY-MM-DD), defaults to today
            
        Returns:
            True if successful
        """
        start_date = start_date or self.config.historical_start_date
        end_date = end_date or datetime.utcnow().strftime('%Y-%m-%d')
        
        logger.info(f"Ingesting historical data from {start_date} to {end_date}")
        
        # Find CDO stations near our location
        cdo_stations = self.cdo_client.find_stations(
            self.config.latitude,
            self.config.longitude,
            radius=50.0
        )
        
        if not cdo_stations:
            logger.error("No CDO stations found")
            return False
        
        # Prioritize stations: airports (GHCND:USW*), COOP (GHCND:USC*), then others
        # Filter out volunteer stations that often have sparse data
        def station_priority(station):
            station_id = station.get('id', '')
            if 'USW' in station_id:  # Airport/ASOS stations
                return STATION_PRIORITY_AIRPORT
            elif 'USC' in station_id:  # COOP stations
                return STATION_PRIORITY_COOP
            elif 'US1' in station_id:  # Volunteer stations
                return STATION_PRIORITY_VOLUNTEER
            else:
                return STATION_PRIORITY_OTHER
        
        # Sort by priority, then by most recent data (descending)
        sorted_stations = sorted(cdo_stations, key=lambda s: (
            station_priority(s),
            s.get('maxdate', '0000-00-00')  # Most recent data first (string comparison works for ISO dates)
        ), reverse=False)  # Keep priority ascending but maxdate will be handled separately
        
        # Further sort within same priority by maxdate descending
        final_stations = []
        for priority, group in groupby(sorted_stations, key=station_priority):
            group_list = sorted(list(group), key=lambda s: s.get('maxdate', '0000-00-00'), reverse=True)
            final_stations.extend(group_list)
        sorted_stations = final_stations
        
        logger.info(f"Prioritized {len(sorted_stations)} stations for data retrieval")
        
        # Try up to 10 stations
        for cdo_station in sorted_stations[:10]:
            station_id = cdo_station.get('id')
            max_date = cdo_station.get('maxdate', 'unknown')
            logger.info(f"Attempting to fetch data from CDO station: {station_id} (max_date: {max_date})")
            
            if self._ingest_historical_from_station(station_id, start_date, end_date):
                return True
        
        logger.error("Failed to ingest historical data from any station")
        return False
    
    def _ingest_historical_from_station(
        self,
        station_id: str,
        start_date: str,
        end_date: str
    ) -> bool:
        """Ingest historical data from a specific CDO station.
        
        Args:
            station_id: CDO station ID
            start_date: Start date
            end_date: End date
            
        Returns:
            True if successful
        """
        start_time = time.time()
        
        # Define data types we're interested in (comparable to Tempest)
        data_types = [
            'TAVG', 'TMAX', 'TMIN',  # Temperature
            'PRCP',  # Precipitation
            'SNOW', 'SNWD',  # Snow
            'AWND', 'WSF2', 'WSF5',  # Wind speed
            'WDF2', 'WDF5'  # Wind direction
        ]
        
        try:
            # Fetch data in chunks
            all_data = self.cdo_client.get_data_by_date_range(
                dataset_id='GHCND',
                station_id=station_id,
                start_date=start_date,
                end_date=end_date,
                data_types=data_types,
                chunk_days=365
            )
            
            if not all_data:
                logger.warning(f"No data available from station {station_id}")
                return False
            
            # Parse and aggregate records
            parsed_records = [parse_cdo_data(record) for record in all_data]
            aggregated_records = aggregate_cdo_records(parsed_records)
            
            # Insert in batches
            batch_size = self.config.db_batch_size
            total_inserted = 0
            
            with self.db.get_session() as session:
                for i in range(0, len(aggregated_records), batch_size):
                    batch = aggregated_records[i:i + batch_size]
                    inserted = self.db.insert_observations(session, batch)
                    total_inserted += inserted
                self.db.log_data_fetch(session, {
                    'fetch_type': 'historical',
                    'data_source': 'CDO',
                    'station_id': station_id,
                    'start_time': datetime.strptime(start_date, '%Y-%m-%d'),
                    'end_time': datetime.strptime(end_date, '%Y-%m-%d'),
                    'records_fetched': len(all_data),
                    'records_inserted': total_inserted,
                    'records_updated': 0,
                    'status': 'success',
                    'error_message': None,
                    'fetch_duration_seconds': time.time() - start_time
                })
            logger.info(f"Ingested {total_inserted} historical records from {station_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting historical data: {e}")
            
            with self.db.get_session() as session:
                self.db.log_data_fetch(session, {
                    'fetch_type': 'historical',
                    'data_source': 'CDO',
                    'station_id': station_id,
                    'start_time': datetime.strptime(start_date, '%Y-%m-%d'),
                    'end_time': datetime.strptime(end_date, '%Y-%m-%d'),
                    'records_fetched': 0,
                    'records_inserted': 0,
                    'records_updated': 0,
                    'status': 'failed',
                    'error_message': str(e),
                    'fetch_duration_seconds': time.time() - start_time
                })
            
            return False
    
    def cleanup_old_data(self) -> None:
        """Clean up old forecast data based on retention policy."""
        logger.info(f"Cleaning up forecast data older than {self.config.forecast_retention_days} days")
        
        try:
            with self.db.get_session() as session:
                deleted = self.db.cleanup_old_forecasts(
                    session,
                    self.config.forecast_retention_days
                )
                logger.info(f"Cleaned up {deleted} old forecast records")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def close(self) -> None:
        """Close all connections."""
        self.nws_client.close()
        self.cdo_client.close()
        self.db.close()
