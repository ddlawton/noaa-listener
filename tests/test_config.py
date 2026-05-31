"""Unit tests for configuration module."""

import os
import pytest
import yaml
from unittest.mock import patch, mock_open
from noaa_listener.config import Config


@pytest.fixture
def mock_config_yaml():
    """Mock config.yaml content."""
    return """
location:
  latitude: 37.7749
  longitude: -122.4194
  name: "Test Location"

fetching:
  forecast_update_interval: 60
  historical:
    start_date: "2022-01-01"
  forecast_retention_days: 30

api:
  nws:
    base_url: "https://api.weather.gov"
    user_agent: "Test-Agent/1.0"
    timeout: 30
    max_retries: 3
    retry_delay: 5
  cdo:
    base_url: "https://www.ncdc.noaa.gov/cdo-web/api/v2"
    timeout: 30
    max_retries: 3
    retry_delay: 5
    limit: 1000

database:
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30
  batch_size: 500

logging:
  format: "%(asctime)s - [%(correlation_id)s] - %(name)s - %(levelname)s - %(message)s"
  date_format: "%Y-%m-%d %H:%M:%S"
  file: "logs/noaa_listener.log"
  max_file_size: 10
  backup_count: 5
"""


@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    env_vars = {
        'POSTGRES_HOST': 'test-host',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'test_db',
        'POSTGRES_USER': 'test_user',
        'POSTGRES_PASSWORD': 'test_pass',
        'NOAA_CDO_API_TOKEN': 'test_token',
        'LOG_LEVEL': 'DEBUG'
    }
    return env_vars


class TestConfig:
    """Test configuration loading and access."""
    
    @patch('noaa_listener.config.yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('noaa_listener.config.load_dotenv')
    @patch.dict(os.environ, {'NOAA_CDO_API_TOKEN': 'test_token'}, clear=True)
    def test_config_loads_yaml(self, mock_dotenv, mock_exists, mock_file, mock_yaml_load):
        """Test that configuration loads from YAML file."""
        mock_exists.return_value = True
        # Set up the mock to return a config dict directly
        config_dict = {
            'location': {
                'latitude': 37.7749,
                'longitude': -122.4194,
                'name': 'Test Location'
            },
            'api': {
                'nws': {'base_url': 'https://api.weather.gov'},
                'cdo': {}
            },
            'database': {},
            'logging': {},
            'fetching': {}
        }
        mock_yaml_load.return_value = config_dict
        
        config = Config('config.yaml')
        
        assert config.latitude == 37.7749
        assert config.longitude == -122.4194
        assert config.location_name == "Test Location"
    
    @patch('pathlib.Path.exists')
    @patch('noaa_listener.config.load_dotenv')
    def test_config_file_not_found(self, mock_dotenv, mock_exists):
        """Test that missing config file raises error."""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            Config('missing.yaml')
    
    @patch('noaa_listener.config.yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('noaa_listener.config.load_dotenv')
    @patch.dict(os.environ, {
        'POSTGRES_HOST': 'test-host',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'test_db',
        'POSTGRES_USER': 'test_user',
        'POSTGRES_PASSWORD': 'test_pass',
        'NOAA_CDO_API_TOKEN': 'test_token',
        'LOG_LEVEL': 'DEBUG'
    }, clear=True)
    def test_env_vars_override(self, mock_dotenv, mock_exists, mock_file, mock_yaml_load):
        """Test that environment variables are loaded."""
        mock_exists.return_value = True
        config_dict = {
            'location': {'latitude': 37.7749, 'longitude': -122.4194},
            'api': {'nws': {}, 'cdo': {}},
            'database': {},
            'logging': {},
            'fetching': {}
        }
        mock_yaml_load.return_value = config_dict
        
        config = Config('config.yaml')
        
        assert config.db_host == 'test-host'
        assert config.db_port == 5432
        assert config.db_name == 'test_db'
        assert config.db_user == 'test_user'
        assert config.db_password == 'test_pass'
        assert config.cdo_api_token == 'test_token'
        assert config.log_level == 'DEBUG'
    
    @patch('noaa_listener.config.yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('noaa_listener.config.load_dotenv')
    def test_missing_api_token_raises_error(self, mock_dotenv, mock_exists, mock_file, mock_yaml_load):
        """Test that missing API token raises error."""
        mock_exists.return_value = True
        config_dict = {
            'location': {'latitude': 37.7749, 'longitude': -122.4194},
            'api': {'nws': {}, 'cdo': {}},
            'database': {},
            'logging': {},
            'fetching': {}
        }
        mock_yaml_load.return_value = config_dict
        
        with patch.dict(os.environ, {}, clear=True):
            config = Config('config.yaml')
            with pytest.raises(ValueError):
                _ = config.cdo_api_token
    
    @patch('noaa_listener.config.yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('noaa_listener.config.load_dotenv')
    @patch.dict(os.environ, {'NOAA_CDO_API_TOKEN': 'test_token'}, clear=True)
    def test_database_url_construction(self, mock_dotenv, mock_exists, mock_file, mock_yaml_load):
        """Test database URL construction."""
        mock_exists.return_value = True
        config_dict = {
            'location': {'latitude': 37.7749, 'longitude': -122.4194},
            'api': {'nws': {}, 'cdo': {}},
            'database': {},
            'logging': {},
            'fetching': {}
        }
        mock_yaml_load.return_value = config_dict
        
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'testdb',
            'POSTGRES_USER': 'user',
            'POSTGRES_PASSWORD': 'pass',
            'NOAA_CDO_API_TOKEN': 'test_token'
        }, clear=True):
            config = Config('config.yaml')
            expected_url = "postgresql://user:pass@localhost:5432/testdb"
            assert config.database_url == expected_url
    
    @patch('noaa_listener.config.yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('noaa_listener.config.load_dotenv')
    @patch.dict(os.environ, {'NOAA_CDO_API_TOKEN': 'test_token', 'POSTGRES_HOST': 'localhost', 'POSTGRES_DB': 'testdb', 'POSTGRES_USER': 'user'}, clear=True)
    def test_nws_base_url_from_config(self, mock_dotenv, mock_exists, mock_file, mock_yaml_load):
        """Test that NWS base URL is loaded from config."""
        mock_exists.return_value = True
        config_dict = {
            'location': {'latitude': 37.7749, 'longitude': -122.4194},
            'api': {
                'nws': {'base_url': 'https://api.weather.gov'},
                'cdo': {}
            },
            'database': {},
            'logging': {},
            'fetching': {}
        }
        mock_yaml_load.return_value = config_dict
        
        config = Config('config.yaml')
        assert config.nws_base_url == "https://api.weather.gov"
    
    @patch('noaa_listener.config.yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('noaa_listener.config.load_dotenv')
    @patch.dict(os.environ, {'NOAA_CDO_API_TOKEN': 'test_token', 'POSTGRES_HOST': 'localhost', 'POSTGRES_DB': 'testdb', 'POSTGRES_USER': 'user'}, clear=True)
    def test_config_validation_success(self, mock_dotenv, mock_exists, mock_file, mock_yaml_load):
        """Test that valid configuration passes validation."""
        mock_exists.return_value = True
        config_dict = {
            'location': {'latitude': 37.7749, 'longitude': -122.4194},
            'api': {
                'nws': {'base_url': 'https://api.weather.gov'},
                'cdo': {}
            },
            'database': {},
            'logging': {},
            'fetching': {}
        }
        mock_yaml_load.return_value = config_dict
        
        config = Config('config.yaml')
        # Should not raise
        config.validate()
    
    @patch('noaa_listener.config.yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('noaa_listener.config.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_config_validation_missing_token(self, mock_dotenv, mock_exists, mock_file, mock_yaml_load):
        """Test that validation fails with missing API token."""
        mock_exists.return_value = True
        config_dict = {
            'location': {'latitude': 37.7749, 'longitude': -122.4194},
            'api': {
                'nws': {'base_url': 'https://api.weather.gov'},
                'cdo': {}
            },
            'database': {},
            'logging': {},
            'fetching': {}
        }
        mock_yaml_load.return_value = config_dict
        
        config = Config('config.yaml')
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config.validate()

