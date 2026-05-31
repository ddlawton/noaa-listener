"""Unit tests for API clients."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from noaa_listener.api.base import BaseAPIClient
from noaa_listener.api.nws_client import NWSClient
from noaa_listener.api.cdo_client import CDOClient


class TestBaseAPIClient:
    """Test base API client functionality."""
    
    def test_initialization(self):
        """Test client initialization."""
        client = BaseAPIClient(
            base_url="https://api.example.com",
            timeout=30,
            max_retries=3,
            retry_delay=5
        )
        
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.retry_delay == 5
    
    @patch('requests.Session.request')
    def test_successful_get_request(self, mock_request):
        """Test successful GET request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response
        
        client = BaseAPIClient(base_url="https://api.example.com")
        result = client.get("/endpoint")
        
        assert result == {"data": "test"}
        mock_request.assert_called_once()
    
    @patch('requests.Session.request')
    def test_rate_limit_retry(self, mock_request):
        """Test rate limit handling with retry."""
        # First request returns 429, second succeeds
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {}
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"data": "success"}
        
        mock_request.side_effect = [mock_response_429, mock_response_200]
        
        with patch('time.sleep'):  # Skip actual sleep
            client = BaseAPIClient(base_url="https://api.example.com", max_retries=3)
            result = client.get("/endpoint")
        
        assert result == {"data": "success"}
        assert mock_request.call_count == 2
    
    @patch('requests.Session.request')
    def test_max_retries_exceeded(self, mock_request):
        """Test that max retries stops attempts."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_request.return_value = mock_response
        
        with patch('time.sleep'):
            client = BaseAPIClient(base_url="https://api.example.com", max_retries=2)
            result = client.get("/endpoint")
        
        assert result is None
        assert mock_request.call_count == 3  # Initial + 2 retries


class TestNWSClient:
    """Test NWS API client."""
    
    @patch('noaa_listener.config.get_config')
    def test_initialization(self, mock_config):
        """Test NWS client initialization."""
        mock_cfg = Mock()
        mock_cfg.nws_user_agent = "Test/1.0"
        mock_cfg.nws_timeout = 30
        mock_cfg.nws_max_retries = 3
        mock_cfg.nws_retry_delay = 5
        mock_config.return_value = mock_cfg
        
        client = NWSClient()
        
        assert 'User-Agent' in client.default_headers
        # User agent comes from config, just verify it exists
    
    @patch('noaa_listener.config.get_config')
    @patch('noaa_listener.api.base.BaseAPIClient.get')
    def test_get_point_metadata(self, mock_get, mock_config):
        """Test fetching point metadata."""
        mock_cfg = Mock()
        mock_cfg.nws_user_agent = "Test/1.0"
        mock_cfg.nws_timeout = 30
        mock_cfg.nws_max_retries = 3
        mock_cfg.nws_retry_delay = 5
        mock_config.return_value = mock_cfg
        
        mock_get.return_value = {
            'properties': {
                'gridId': 'ABC',
                'gridX': 10,
                'gridY': 20
            }
        }
        
        client = NWSClient()
        result = client.get_point_metadata(37.7749, -122.4194)
        
        assert result is not None
        assert result['gridId'] == 'ABC'
        assert result['gridX'] == 10
        assert result['gridY'] == 20
    
    @patch('noaa_listener.config.get_config')
    @patch('noaa_listener.api.base.BaseAPIClient.get')
    def test_get_forecast(self, mock_get, mock_config):
        """Test fetching forecast."""
        mock_cfg = Mock()
        mock_cfg.nws_user_agent = "Test/1.0"
        mock_cfg.nws_timeout = 30
        mock_cfg.nws_max_retries = 3
        mock_cfg.nws_retry_delay = 5
        mock_config.return_value = mock_cfg
        
        mock_get.return_value = {
            'properties': {
                'periods': [
                    {'number': 1, 'name': 'Tonight', 'temperature': 55}
                ]
            }
        }
        
        client = NWSClient()
        result = client.get_forecast('ABC', 10, 20)
        
        assert result is not None
        assert len(result['periods']) == 1
        assert result['periods'][0]['temperature'] == 55


class TestCDOClient:
    """Test CDO API client."""
    
    @patch('noaa_listener.config.get_config')
    def test_initialization(self, mock_config):
        """Test CDO client initialization."""
        mock_cfg = Mock()
        mock_cfg.cdo_api_token = "test_token"
        mock_cfg.cdo_base_url = "https://api.example.com"
        mock_cfg.cdo_timeout = 30
        mock_cfg.cdo_max_retries = 3
        mock_cfg.cdo_retry_delay = 5
        mock_cfg.cdo_limit = 1000
        mock_config.return_value = mock_cfg
        
        client = CDOClient()
        
        assert 'token' in client.default_headers
        # Token comes from config, just verify it exists
    
    @patch('noaa_listener.config.get_config')
    @patch('noaa_listener.api.base.BaseAPIClient.get')
    def test_find_stations(self, mock_get, mock_config):
        """Test finding stations."""
        mock_cfg = Mock()
        mock_cfg.cdo_api_token = "test_token"
        mock_cfg.cdo_base_url = "https://api.example.com"
        mock_cfg.cdo_timeout = 30
        mock_cfg.cdo_max_retries = 3
        mock_cfg.cdo_retry_delay = 5
        mock_cfg.cdo_limit = 1000
        mock_config.return_value = mock_cfg
        
        mock_get.return_value = {
            'results': [
                {'id': 'STATION1', 'name': 'Test Station'}
            ],
            'metadata': {
                'resultset': {'count': 1}
            }
        }
        
        client = CDOClient()
        result = client.find_stations(37.7749, -122.4194)
        
        assert result is not None
        assert len(result) == 1
        assert result[0]['id'] == 'STATION1'
    
    @patch('noaa_listener.config.get_config')
    @patch('noaa_listener.api.base.BaseAPIClient.get')
    def test_get_data(self, mock_get, mock_config):
        """Test fetching historical data."""
        mock_cfg = Mock()
        mock_cfg.cdo_api_token = "test_token"
        mock_cfg.cdo_base_url = "https://api.example.com"
        mock_cfg.cdo_timeout = 30
        mock_cfg.cdo_max_retries = 3
        mock_cfg.cdo_retry_delay = 5
        mock_cfg.cdo_limit = 1000
        mock_config.return_value = mock_cfg
        
        mock_get.return_value = {
            'results': [
                {'datatype': 'TMAX', 'value': 25.0, 'date': '2024-01-01T00:00:00'}
            ],
            'metadata': {
                'resultset': {'count': 1}
            }
        }
        
        client = CDOClient()
        result = client.get_data('GHCND', 'STATION1', '2024-01-01', '2024-01-02')
        
        assert result is not None
        assert len(result) == 1
        assert result[0]['datatype'] == 'TMAX'
