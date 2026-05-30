"""Database connection and operations."""

from contextlib import contextmanager
from typing import Generator, Optional, List, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from noaa_listener.config import get_config
from noaa_listener.logger import get_logger

logger = get_logger(__name__)


class Database:
    """Database connection manager."""
    
    def __init__(self, config: Optional[object] = None):
        """Initialize database connection.
        
        Args:
            config: Configuration object (if None, will load default)
        """
        self.config = config or get_config()
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self._connect()
    
    def _connect(self) -> None:
        """Create database engine and session factory."""
        try:
            self.engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=self.config.db_pool_size,
                max_overflow=self.config.db_max_overflow,
                pool_timeout=self.config.db_pool_timeout,
                pool_pre_ping=True,
                echo=False
            )
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session context manager.
        
        Yields:
            SQLAlchemy session
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test database connection.
        
        Returns:
            True if connection is successful
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    # Station operations
    def upsert_station(self, session: Session, station_data: Dict[str, Any]) -> int:
        """Insert or update station data.
        
        Args:
            session: Database session
            station_data: Station information
            
        Returns:
            Station ID
        """
        query = text("""
            INSERT INTO stations (station_id, name, latitude, longitude, elevation, timezone, state)
            VALUES (:station_id, :name, :latitude, :longitude, :elevation, :timezone, :state)
            ON CONFLICT (station_id) 
            DO UPDATE SET
                name = EXCLUDED.name,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                elevation = EXCLUDED.elevation,
                timezone = EXCLUDED.timezone,
                state = EXCLUDED.state,
                updated_at = NOW()
            RETURNING id
        """)
        result = session.execute(query, station_data)
        return result.scalar()
    
    def get_station_by_id(self, session: Session, station_id: str) -> Optional[Dict[str, Any]]:
        """Get station by ID.
        
        Args:
            session: Database session
            station_id: Station identifier
            
        Returns:
            Station data or None
        """
        query = text("SELECT * FROM stations WHERE station_id = :station_id")
        result = session.execute(query, {"station_id": station_id})
        row = result.fetchone()
        return dict(row._mapping) if row else None
    
    # Unified observations
    def insert_observations(self, session: Session, observations: List[Dict[str, Any]]) -> int:
        """Insert observations (historical or current) in bulk.
        
        Args:
            session: Database session
            observations: List of observation records
        Returns:
            Number of records inserted
        """
        if not observations:
            return 0
        query = text("""
            INSERT INTO observations (
                station_id, observation_time, temperature, temp_avg, temp_max, temp_min, dewpoint, heat_index, wind_chill,
                wind_speed, wind_speed_avg, wind_speed_max, wind_direction, wind_gust,
                barometric_pressure, sea_level_pressure, pressure, humidity, relative_humidity,
                precipitation, precipitation_last_hour, precipitation_last_3hr, precipitation_last_6hr, snow_depth, snow_fall,
                visibility, cloud_cover, sky_cover, cloud_layers, solar_radiation,
                text_description, icon_url, raw_message, data_source, quality_flags
            )
            VALUES (
                :station_id, :observation_time, :temperature, :temp_avg, :temp_max, :temp_min, :dewpoint, :heat_index, :wind_chill,
                :wind_speed, :wind_speed_avg, :wind_speed_max, :wind_direction, :wind_gust,
                :barometric_pressure, :sea_level_pressure, :pressure, :humidity, :relative_humidity,
                :precipitation, :precipitation_last_hour, :precipitation_last_3hr, :precipitation_last_6hr, :snow_depth, :snow_fall,
                :visibility, :cloud_cover, :sky_cover, :cloud_layers, :solar_radiation,
                :text_description, :icon_url, :raw_message, :data_source, :quality_flags
            )
            ON CONFLICT (station_id, observation_time, data_source) DO NOTHING
        """)
        result = session.execute(query, observations)
        return result.rowcount
    
    # Forecast periods
    def insert_forecast_periods(self, session: Session, forecasts: List[Dict[str, Any]]) -> int:
        """Insert forecast period data in bulk.
        
        Args:
            session: Database session
            forecasts: List of forecast records
            
        Returns:
            Number of records inserted
        """
        if not forecasts:
            return 0
        
        query = text("""
            INSERT INTO forecast_periods (
                station_id, grid_id, grid_x, grid_y, generated_at,
                period_number, period_name, start_time, end_time,
                temperature, temperature_unit, temperature_trend,
                wind_speed, wind_direction, short_forecast, detailed_forecast,
                precipitation_probability, dewpoint, relative_humidity,
                is_daytime, icon_url
            )
            VALUES (
                :station_id, :grid_id, :grid_x, :grid_y, :generated_at,
                :period_number, :period_name, :start_time, :end_time,
                :temperature, :temperature_unit, :temperature_trend,
                :wind_speed, :wind_direction, :short_forecast, :detailed_forecast,
                :precipitation_probability, :dewpoint, :relative_humidity,
                :is_daytime, :icon_url
            )
            ON CONFLICT (station_id, generated_at, period_number) DO NOTHING
        """)
        
        result = session.execute(query, forecasts)
        return result.rowcount
    
    # Hourly forecast
    def insert_forecast_hourly(self, session: Session, forecasts: List[Dict[str, Any]]) -> int:
        """Insert hourly forecast data in bulk.
        
        Args:
            session: Database session
            forecasts: List of hourly forecast records
            
        Returns:
            Number of records inserted
        """
        if not forecasts:
            return 0
        
        query = text("""
            INSERT INTO forecast_hourly (
                station_id, grid_id, grid_x, grid_y, generated_at, forecast_time,
                temperature, dewpoint, wind_speed, wind_direction, wind_gust,
                relative_humidity, pressure, precipitation_probability,
                quantitative_precipitation, sky_cover, cloud_base,
                visibility, weather_summary
            )
            VALUES (
                :station_id, :grid_id, :grid_x, :grid_y, :generated_at, :forecast_time,
                :temperature, :dewpoint, :wind_speed, :wind_direction, :wind_gust,
                :relative_humidity, :pressure, :precipitation_probability,
                :quantitative_precipitation, :sky_cover, :cloud_base,
                :visibility, :weather_summary
            )
            ON CONFLICT (station_id, generated_at, forecast_time) DO NOTHING
        """)
        
        result = session.execute(query, forecasts)
        return result.rowcount
    
    # Gridded forecast
    def insert_forecast_gridded(self, session: Session, forecasts: List[Dict[str, Any]]) -> int:
        """Insert gridded forecast data in bulk.
        
        Args:
            session: Database session
            forecasts: List of gridded forecast records
            
        Returns:
            Number of records inserted
        """
        if not forecasts:
            return 0
        
        query = text("""
            INSERT INTO forecast_gridded (
                grid_id, grid_x, grid_y, generated_at, valid_time_start, valid_time_end,
                temperature, dewpoint, max_temperature, min_temperature, apparent_temperature,
                wind_speed, wind_direction, wind_gust, relative_humidity, pressure,
                precipitation_probability, quantitative_precipitation,
                ice_accumulation, snowfall_amount, sky_cover, visibility,
                weather, hazards, heat_index, wind_chill
            )
            VALUES (
                :grid_id, :grid_x, :grid_y, :generated_at, :valid_time_start, :valid_time_end,
                :temperature, :dewpoint, :max_temperature, :min_temperature, :apparent_temperature,
                :wind_speed, :wind_direction, :wind_gust, :relative_humidity, :pressure,
                :precipitation_probability, :quantitative_precipitation,
                :ice_accumulation, :snowfall_amount, :sky_cover, :visibility,
                :weather, :hazards, :heat_index, :wind_chill
            )
            ON CONFLICT (grid_id, grid_x, grid_y, generated_at, valid_time_start) DO NOTHING
        """)
        
        result = session.execute(query, forecasts)
        return result.rowcount
    

    
    # Data fetch logging
    def log_data_fetch(self, session: Session, log_data: Dict[str, Any]) -> None:
        """Log a data fetch operation.
        
        Args:
            session: Database session
            log_data: Fetch operation metadata
        """
        query = text("""
            INSERT INTO data_fetch_log (
                fetch_type, data_source, station_id, start_time, end_time,
                records_fetched, records_inserted, records_updated,
                status, error_message, fetch_duration_seconds
            )
            VALUES (
                :fetch_type, :data_source, :station_id, :start_time, :end_time,
                :records_fetched, :records_inserted, :records_updated,
                :status, :error_message, :fetch_duration_seconds
            )
        """)
        session.execute(query, log_data)
    
    # Cleanup operations
    def cleanup_old_forecasts(self, session: Session, retention_days: int) -> int:
        """Delete forecast data older than retention period.
        
        Args:
            session: Database session
            retention_days: Number of days to keep
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        tables = ['forecast_periods', 'forecast_hourly', 'forecast_gridded']
        total_deleted = 0
        
        for table in tables:
            query = text(f"DELETE FROM {table} WHERE generated_at < :cutoff_date")
            result = session.execute(query, {"cutoff_date": cutoff_date})
            deleted = result.rowcount
            total_deleted += deleted
            logger.info(f"Deleted {deleted} old records from {table}")
        
        return total_deleted
    
    def close(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
