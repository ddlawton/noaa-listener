"""Configuration management for NOAA Listener."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv


class Config:
    """Configuration manager for NOAA Listener."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        # Load environment variables
        load_dotenv()
        
        # Load YAML configuration
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_yaml_config()
        
    def _load_yaml_config(self) -> None:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
    
    # Location Configuration
    @property
    def latitude(self) -> float:
        """Get configured latitude from environment variable."""
        lat_str = os.getenv('LOCATION_LATITUDE', '0.0')
        return float(lat_str)
    
    @property
    def longitude(self) -> float:
        """Get configured longitude from environment variable."""
        lon_str = os.getenv('LOCATION_LONGITUDE', '0.0')
        return float(lon_str)
    
    @property
    def location_name(self) -> str:
        """Get location name from environment variable."""
        return os.getenv('LOCATION_NAME', 'Unknown')
    
    # Fetching Configuration
    @property
    def forecast_update_interval(self) -> int:
        """Get forecast update interval in minutes."""
        return self._config.get('fetching', {}).get('forecast_update_interval', 60)
    
    @property
    def historical_start_date(self) -> str:
        """Get historical data start date."""
        return self._config.get('fetching', {}).get('historical', {}).get('start_date', '2022-01-01')
    
    @property
    def historical_end_date(self) -> str:
        """Get historical data end date (None means today)."""
        return self._config.get('fetching', {}).get('historical', {}).get('end_date')
    
    @property
    def forecast_retention_days(self) -> int:
        """Get forecast data retention period in days."""
        return self._config.get('fetching', {}).get('forecast_retention_days', 30)
    
    # API Configuration - NWS
    @property
    def nws_base_url(self) -> str:
        """Get NWS API base URL."""
        return self._config.get('api', {}).get('nws', {}).get('base_url', 'https://api.weather.gov')
    
    @property
    def nws_user_agent(self) -> str:
        """Get NWS API user agent."""
        return self._config.get('api', {}).get('nws', {}).get('user_agent', 'NOAA-Listener/1.0')
    
    @property
    def nws_timeout(self) -> int:
        """Get NWS API timeout in seconds."""
        return self._config.get('api', {}).get('nws', {}).get('timeout', 30)
    
    @property
    def nws_max_retries(self) -> int:
        """Get NWS API max retries."""
        return self._config.get('api', {}).get('nws', {}).get('max_retries', 3)
    
    @property
    def nws_retry_delay(self) -> int:
        """Get NWS API retry delay in seconds."""
        return self._config.get('api', {}).get('nws', {}).get('retry_delay', 5)
    
    # API Configuration - CDO
    @property
    def cdo_base_url(self) -> str:
        """Get CDO API base URL."""
        return self._config.get('api', {}).get('cdo', {}).get('base_url', 'https://www.ncdc.noaa.gov/cdo-web/api/v2')
    
    @property
    def cdo_timeout(self) -> int:
        """Get CDO API timeout in seconds."""
        return self._config.get('api', {}).get('cdo', {}).get('timeout', 30)
    
    @property
    def cdo_max_retries(self) -> int:
        """Get CDO API max retries."""
        return self._config.get('api', {}).get('cdo', {}).get('max_retries', 3)
    
    @property
    def cdo_retry_delay(self) -> int:
        """Get CDO API retry delay in seconds."""
        return self._config.get('api', {}).get('cdo', {}).get('retry_delay', 5)
    
    @property
    def cdo_limit(self) -> int:
        """Get CDO API records limit per request."""
        return self._config.get('api', {}).get('cdo', {}).get('limit', 1000)
    
    # Database Configuration
    @property
    def db_host(self) -> str:
        """Get database host."""
        return os.getenv('POSTGRES_HOST', 'localhost')
    
    @property
    def db_port(self) -> int:
        """Get database port."""
        return int(os.getenv('POSTGRES_PORT', '5432'))
    
    @property
    def db_name(self) -> str:
        """Get database name."""
        return os.getenv('POSTGRES_DB', 'noaa_weather')
    
    @property
    def db_user(self) -> str:
        """Get database user."""
        return os.getenv('POSTGRES_USER', 'postgres')
    
    @property
    def db_password(self) -> str:
        """Get database password."""
        return os.getenv('POSTGRES_PASSWORD', '')
    
    @property
    def db_pool_size(self) -> int:
        """Get database connection pool size."""
        return self._config.get('database', {}).get('pool_size', 5)
    
    @property
    def db_max_overflow(self) -> int:
        """Get database max overflow connections."""
        return self._config.get('database', {}).get('max_overflow', 10)
    
    @property
    def db_pool_timeout(self) -> int:
        """Get database pool timeout in seconds."""
        return self._config.get('database', {}).get('pool_timeout', 30)
    
    @property
    def db_batch_size(self) -> int:
        """Get database batch insert size."""
        return self._config.get('database', {}).get('batch_size', 100)
    
    # API Tokens
    @property
    def cdo_api_token(self) -> str:
        """Get NOAA CDO API token."""
        token = os.getenv('NOAA_CDO_API_TOKEN', '')
        if not token:
            raise ValueError("NOAA_CDO_API_TOKEN environment variable is required")
        return token
    
    # Logging Configuration
    @property
    def log_level(self) -> str:
        """Get log level."""
        return os.getenv('LOG_LEVEL', 'INFO').upper()
    
    @property
    def log_format(self) -> str:
        """Get log format string."""
        return self._config.get('logging', {}).get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    @property
    def log_date_format(self) -> str:
        """Get log date format string."""
        return self._config.get('logging', {}).get('date_format', '%Y-%m-%d %H:%M:%S')
    
    @property
    def log_file(self) -> str:
        """Get log file path."""
        return self._config.get('logging', {}).get('file', 'logs/noaa_listener.log')
    
    @property
    def log_max_file_size(self) -> int:
        """Get max log file size in bytes."""
        size_mb = self._config.get('logging', {}).get('max_file_size', 10)
        return size_mb * 1024 * 1024
    
    @property
    def log_backup_count(self) -> int:
        """Get number of backup log files."""
        return self._config.get('logging', {}).get('backup_count', 5)
    
    @property
    def database_url(self) -> str:
        """Get SQLAlchemy database URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    def validate(self) -> None:
        """Validate configuration at startup.
        
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        errors = []
        
        # Validate location
        if not -90 <= self.latitude <= 90:
            errors.append(f"Invalid latitude: {self.latitude} (must be between -90 and 90)")
        if not -180 <= self.longitude <= 180:
            errors.append(f"Invalid longitude: {self.longitude} (must be between -180 and 180)")
        
        # Validate API token
        try:
            if not self.cdo_api_token:
                errors.append("NOAA_CDO_API_TOKEN environment variable is required")
        except ValueError as e:
            errors.append(str(e))
        
        # Validate database config
        if not self.db_host:
            errors.append("POSTGRES_HOST environment variable is required")
        if not self.db_name:
            errors.append("POSTGRES_DB environment variable is required")
        if not self.db_user:
            errors.append("POSTGRES_USER environment variable is required")
        
        # Validate numeric values
        if self.forecast_update_interval <= 0:
            errors.append(f"Invalid forecast_update_interval: {self.forecast_update_interval} (must be > 0)")
        if self.db_pool_size <= 0:
            errors.append(f"Invalid db_pool_size: {self.db_pool_size} (must be > 0)")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors))


# Global configuration instance
_config: Config = None


def get_config(config_path: str = "config.yaml") -> Config:
    """Get or create global configuration instance.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
