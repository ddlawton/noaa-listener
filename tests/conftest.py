"""Test fixtures and configuration."""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()
    config.latitude = 37.7749
    config.longitude = -122.4194
    config.location_name = "Test Location"
    config.forecast_update_interval = 60
    config.historical_start_date = "2022-01-01"
    config.historical_end_date = None
    config.forecast_retention_days = 30
    config.nws_user_agent = "Test/1.0"
    config.nws_timeout = 30
    config.nws_max_retries = 3
    config.nws_retry_delay = 5
    config.cdo_base_url = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
    config.cdo_timeout = 30
    config.cdo_max_retries = 3
    config.cdo_retry_delay = 5
    config.cdo_limit = 1000
    config.cdo_api_token = "test_token"
    config.db_host = "localhost"
    config.db_port = 5432
    config.db_name = "test_db"
    config.db_user = "test_user"
    config.db_password = "test_pass"
    config.db_pool_size = 5
    config.db_max_overflow = 10
    config.db_pool_timeout = 30
    config.db_batch_size = 100
    config.database_url = "postgresql://test_user:test_pass@localhost:5432/test_db"
    config.log_level = "INFO"
    config.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    config.log_date_format = "%Y-%m-%d %H:%M:%S"
    config.log_file = "logs/test.log"
    config.log_max_file_size = 10 * 1024 * 1024
    config.log_backup_count = 5
    return config


@pytest.fixture
def sample_nws_point_data():
    """Sample NWS point metadata."""
    return {
        'gridId': 'MTR',
        'gridX': 10,
        'gridY': 20,
        'forecast': 'https://api.weather.gov/gridpoints/MTR/10,20/forecast',
        'forecastHourly': 'https://api.weather.gov/gridpoints/MTR/10,20/forecast/hourly',
        'forecastGridData': 'https://api.weather.gov/gridpoints/MTR/10,20',
        'observationStations': 'https://api.weather.gov/gridpoints/MTR/10,20/stations',
        'timeZone': 'America/Los_Angeles',
        'radarStation': 'KMUX'
    }


@pytest.fixture
def sample_nws_station():
    """Sample NWS station data."""
    return {
        'stationIdentifier': 'KSFO',
        'name': 'San Francisco International Airport',
        'latitude': 37.6213,
        'longitude': -122.3790,
        'elevation': {'value': 3.9624, 'unitCode': 'wmoUnit:m'},
        'timeZone': 'America/Los_Angeles',
        'state': 'CA'
    }


@pytest.fixture
def sample_nws_forecast_period():
    """Sample NWS forecast period."""
    return {
        'number': 1,
        'name': 'Tonight',
        'startTime': '2024-01-15T18:00:00-08:00',
        'endTime': '2024-01-16T06:00:00-08:00',
        'isDaytime': False,
        'temperature': 55,
        'temperatureUnit': 'F',
        'temperatureTrend': None,
        'windSpeed': '5 to 10 mph',
        'windDirection': 'NW',
        'icon': 'https://api.weather.gov/icons/land/night/few?size=medium',
        'shortForecast': 'Mostly Clear',
        'detailedForecast': 'Mostly clear, with a low around 55.',
        'probabilityOfPrecipitation': {'value': None},
        'dewpoint': {'value': 10.0},
        'relativeHumidity': {'value': 75}
    }


@pytest.fixture
def sample_cdo_station():
    """Sample CDO station data."""
    return {
        'id': 'GHCND:USW00023234',
        'name': 'SAN FRANCISCO DOWNTOWN',
        'latitude': 37.7749,
        'longitude': -122.4194,
        'elevation': 16.0,
        'mindate': '2000-01-01',
        'maxdate': '2024-12-31'
    }


@pytest.fixture
def sample_cdo_data():
    """Sample CDO weather data."""
    return {
        'date': '2024-01-15T00:00:00',
        'datatype': 'TMAX',
        'station': 'GHCND:USW00023234',
        'attributes': 'T',
        'value': 18.3
    }
