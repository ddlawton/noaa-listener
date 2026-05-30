"""Tests for data validation module."""

import pytest
from datetime import datetime, timedelta, timezone

from noaa_listener.ingestion.validators import (
    validate_temperature,
    validate_wind_speed,
    validate_pressure,
    validate_humidity,
    validate_observation,
    ValidationError
)


class TestTemperatureValidation:
    """Test temperature validation."""
    
    def test_valid_temperature(self):
        """Test valid temperature values."""
        assert validate_temperature(20.0) == 20.0
        assert validate_temperature(0.0) == 0.0
        assert validate_temperature(-40.0) == -40.0
        assert validate_temperature(50.0) == 50.0
    
    def test_invalid_temperature_too_hot(self):
        """Test temperature that's too high."""
        with pytest.raises(ValidationError, match="out of range"):
            validate_temperature(100.0)
    
    def test_invalid_temperature_too_cold(self):
        """Test temperature that's too low."""
        with pytest.raises(ValidationError, match="out of range"):
            validate_temperature(-100.0)
    
    def test_none_temperature(self):
        """Test None temperature value."""
        assert validate_temperature(None) is None


class TestWindSpeedValidation:
    """Test wind speed validation."""
    
    def test_valid_wind_speed(self):
        """Test valid wind speed values."""
        assert validate_wind_speed(0.0) == 0.0
        assert validate_wind_speed(10.0) == 10.0
        assert validate_wind_speed(50.0) == 50.0
        assert validate_wind_speed(100.0) == 100.0
    
    def test_invalid_wind_speed_too_high(self):
        """Test wind speed that's too high."""
        with pytest.raises(ValidationError, match="out of range"):
            validate_wind_speed(200.0)
    
    def test_invalid_wind_speed_negative(self):
        """Test negative wind speed."""
        with pytest.raises(ValidationError, match="out of range"):
            validate_wind_speed(-10.0)
    
    def test_none_wind_speed(self):
        """Test None wind speed value."""
        assert validate_wind_speed(None) is None


class TestPressureValidation:
    """Test pressure validation."""
    
    def test_valid_pressure(self):
        """Test valid pressure values."""
        assert validate_pressure(101325.0) == 101325.0  # Standard atmospheric pressure
        assert validate_pressure(90000.0) == 90000.0
        assert validate_pressure(105000.0) == 105000.0
    
    def test_invalid_pressure_too_high(self):
        """Test pressure that's too high."""
        with pytest.raises(ValidationError, match="out of range"):
            validate_pressure(120000.0)
    
    def test_invalid_pressure_too_low(self):
        """Test pressure that's too low."""
        with pytest.raises(ValidationError, match="out of range"):
            validate_pressure(50000.0)
    
    def test_none_pressure(self):
        """Test None pressure value."""
        assert validate_pressure(None) is None


class TestHumidityValidation:
    """Test humidity validation."""
    
    def test_valid_humidity(self):
        """Test valid humidity values."""
        assert validate_humidity(0.0) == 0.0
        assert validate_humidity(50.0) == 50.0
        assert validate_humidity(100.0) == 100.0
    
    def test_invalid_humidity_too_high(self):
        """Test humidity above 100%."""
        with pytest.raises(ValidationError, match="out of range"):
            validate_humidity(110.0)
    
    def test_invalid_humidity_negative(self):
        """Test negative humidity."""
        with pytest.raises(ValidationError, match="out of range"):
            validate_humidity(-10.0)
    
    def test_none_humidity(self):
        """Test None humidity value."""
        assert validate_humidity(None) is None


class TestObservationValidation:
    """Test observation validation."""
    
    def test_valid_observation(self):
        """Test observation with valid data."""
        obs = {
            'station_id': 'TEST',
            'observation_time': datetime.now(timezone.utc) - timedelta(hours=1),
            'temperature': 20.0,
            'dewpoint': 10.0,
            'wind_speed': 5.0,
            'relative_humidity': 65.0,
            'barometric_pressure': 101325.0
        }
        
        warnings = validate_observation(obs, strict=False)
        assert len(warnings) == 0
    
    def test_observation_with_invalid_temperature(self):
        """Test observation with invalid temperature."""
        obs = {
            'station_id': 'TEST',
            'observation_time': datetime.now(timezone.utc) - timedelta(hours=1),
            'temperature': 999.0,  # Invalid
            'wind_speed': 5.0
        }
        
        warnings = validate_observation(obs, strict=False)
        assert len(warnings) > 0
        assert any('temperature' in w.lower() for w in warnings)
    
    def test_observation_with_future_timestamp(self):
        """Test observation with future timestamp."""
        obs = {
            'station_id': 'TEST',
            'observation_time': datetime.now(timezone.utc) + timedelta(hours=1),  # Future
            'temperature': 20.0
        }
        
        warnings = validate_observation(obs, strict=False)
        assert len(warnings) > 0
        assert any('future' in w.lower() for w in warnings)
    
    def test_observation_with_multiple_issues(self):
        """Test observation with multiple validation issues."""
        obs = {
            'station_id': 'TEST',
            'observation_time': datetime.now(timezone.utc) - timedelta(hours=1),
            'temperature': 999.0,  # Invalid
            'wind_speed': -10.0,  # Invalid
            'relative_humidity': 150.0  # Invalid
        }
        
        warnings = validate_observation(obs, strict=False)
        # Each invalid field produces one warning
        assert len(warnings) >= 1
        assert any('temperature' in w.lower() or 'wind' in w.lower() or 'humidity' in w.lower() for w in warnings)
    
    def test_strict_mode_raises_exception(self):
        """Test that strict mode raises exception on first error."""
        obs = {
            'station_id': 'TEST',
            'observation_time': datetime.now(timezone.utc) - timedelta(hours=1),
            'temperature': 999.0  # Invalid
        }
        
        with pytest.raises(ValidationError):
            validate_observation(obs, strict=True)
    
    def test_observation_with_none_values(self):
        """Test observation with None values (should be valid)."""
        obs = {
            'station_id': 'TEST',
            'observation_time': datetime.now(timezone.utc) - timedelta(hours=1),
            'temperature': None,
            'wind_speed': None,
            'relative_humidity': None
        }
        
        warnings = validate_observation(obs, strict=False)
        assert len(warnings) == 0
