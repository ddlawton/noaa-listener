"""Unit tests for data parsers."""

import pytest
from datetime import datetime, timezone
from noaa_listener.ingestion.parsers import (
    parse_iso_datetime,
    extract_value,
    parse_station_data,
    parse_forecast_period,
    parse_cdo_data,
    aggregate_cdo_records
)


class TestParsers:
    """Test data parsing functions."""
    
    def test_parse_iso_datetime_with_z(self):
        """Test parsing ISO datetime with Z suffix."""
        dt_str = "2024-01-15T12:30:00Z"
        result = parse_iso_datetime(dt_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 30
    
    def test_parse_iso_datetime_with_timezone(self):
        """Test parsing ISO datetime with timezone."""
        dt_str = "2024-01-15T12:30:00-08:00"
        result = parse_iso_datetime(dt_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
    
    def test_parse_iso_datetime_invalid(self):
        """Test parsing invalid datetime returns None."""
        result = parse_iso_datetime("invalid")
        assert result is None
    
    def test_parse_iso_datetime_none(self):
        """Test parsing None returns None."""
        result = parse_iso_datetime(None)
        assert result is None
    
    def test_extract_value_from_dict(self):
        """Test extracting value from dict object."""
        value_obj = {'value': 25.5, 'unitCode': 'C'}
        result = extract_value(value_obj)
        assert result == 25.5
    
    def test_extract_value_from_number(self):
        """Test extracting value from direct number."""
        result = extract_value(42.0)
        assert result == 42.0
    
    def test_extract_value_none(self):
        """Test extracting value from None."""
        result = extract_value(None)
        assert result is None
    
    def test_parse_station_data(self):
        """Test parsing station metadata."""
        station_data = {
            'stationIdentifier': 'KSFO',
            'name': 'San Francisco Airport',
            'latitude': 37.6213,
            'longitude': -122.3790,
            'elevation': {'value': 3},
            'timeZone': 'America/Los_Angeles',
            'state': 'CA'
        }
        
        result = parse_station_data(station_data)
        
        assert result['station_id'] == 'KSFO'
        assert result['name'] == 'San Francisco Airport'
        assert result['latitude'] == 37.6213
        assert result['longitude'] == -122.3790
        assert result['elevation'] == 3
        assert result['timezone'] == 'America/Los_Angeles'
        assert result['state'] == 'CA'
    
    def test_parse_forecast_period(self):
        """Test parsing forecast period."""
        period = {
            'number': 1,
            'name': 'Tonight',
            'startTime': '2024-01-15T18:00:00-08:00',
            'endTime': '2024-01-16T06:00:00-08:00',
            'temperature': 55,
            'temperatureUnit': 'F',
            'windSpeed': '5 to 10 mph',
            'windDirection': 'NW',
            'shortForecast': 'Partly Cloudy',
            'isDaytime': False
        }
        
        generated_at = datetime.now(timezone.utc)
        result = parse_forecast_period(
            period, 'MTR', 10, 20, 'KSFO', generated_at
        )
        
        assert result['station_id'] == 'KSFO'
        assert result['grid_id'] == 'MTR'
        assert result['period_number'] == 1
        assert result['period_name'] == 'Tonight'
        assert result['temperature'] == 55
        assert result['wind_speed'] == '5 to 10 mph'
        assert result['is_daytime'] is False
    
    def test_parse_cdo_data_temperature(self):
        """Test parsing CDO temperature data."""
        data_record = {
            'station': 'GHCND:USW00023234',
            'date': '2024-01-15T00:00:00',
            'datatype': 'TMAX',
            'value': 15.5,
            'attributes': 'T'
        }
        
        result = parse_cdo_data(data_record)
        
        assert result['station_id'] == 'GHCND:USW00023234'
        assert result['temp_max'] == 15.5
        assert result['data_source'] == 'CDO'
        assert result['temp_avg'] is None  # Different datatype
    
    def test_parse_cdo_data_precipitation(self):
        """Test parsing CDO precipitation data."""
        data_record = {
            'station': 'GHCND:USW00023234',
            'date': '2024-01-15T00:00:00',
            'datatype': 'PRCP',
            'value': 5.2,
            'attributes': ''
        }
        
        result = parse_cdo_data(data_record)
        
        assert result['precipitation'] == 5.2
    
    def test_aggregate_cdo_records(self):
        """Test aggregating CDO records by timestamp."""
        records = [
            {
                'station_id': 'STATION1',
                'observation_time': datetime(2024, 1, 15, 0, 0),
                'temp_max': 20.0,
                'temp_min': None,
                'precipitation': None,
                'data_source': 'CDO',
                'quality_flags': None,
                'temp_avg': None,
                'wind_speed_avg': None,
                'wind_speed_max': None,
                'wind_direction': None,
                'wind_gust': None,
                'snow_depth': None,
                'snow_fall': None,
                'pressure': None,
                'humidity': None,
                'visibility': None,
                'cloud_cover': None,
                'solar_radiation': None
            },
            {
                'station_id': 'STATION1',
                'observation_time': datetime(2024, 1, 15, 0, 0),
                'temp_max': None,
                'temp_min': 10.0,
                'precipitation': 5.0,
                'data_source': 'CDO',
                'quality_flags': None,
                'temp_avg': None,
                'wind_speed_avg': None,
                'wind_speed_max': None,
                'wind_direction': None,
                'wind_gust': None,
                'snow_depth': None,
                'snow_fall': None,
                'pressure': None,
                'humidity': None,
                'visibility': None,
                'cloud_cover': None,
                'solar_radiation': None
            }
        ]
        
        result = aggregate_cdo_records(records)
        
        assert len(result) == 1  # Two records merged into one
        assert result[0]['temp_max'] == 20.0
        assert result[0]['temp_min'] == 10.0
        assert result[0]['precipitation'] == 5.0
