"""Data quality validation for weather observations."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from noaa_listener.logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Data validation error."""
    pass


def validate_temperature(value: Optional[float], field_name: str = "temperature") -> Optional[float]:
    """Validate temperature value.
    
    Args:
        value: Temperature in Celsius
        field_name: Field name for error messages
        
    Returns:
        Validated temperature or None
        
    Raises:
        ValidationError: If value is outside reasonable range
    """
    if value is None:
        return None
    
    # Reasonable temperature range: -90°C to 60°C
    if not -90 <= value <= 60:
        raise ValidationError(f"{field_name} out of range: {value}°C (expected -90 to 60)")
    
    return value


def validate_wind_speed(value: Optional[float], field_name: str = "wind_speed") -> Optional[float]:
    """Validate wind speed value.
    
    Args:
        value: Wind speed in m/s
        field_name: Field name for error messages
        
    Returns:
        Validated wind speed or None
        
    Raises:
        ValidationError: If value is outside reasonable range
    """
    if value is None:
        return None
    
    # Reasonable wind speed range: 0 to 113 m/s (0 to ~250 mph)
    if not 0 <= value <= 113:
        raise ValidationError(f"{field_name} out of range: {value} m/s (expected 0 to 113)")
    
    return value


def validate_pressure(value: Optional[float], field_name: str = "pressure") -> Optional[float]:
    """Validate atmospheric pressure value.
    
    Args:
        value: Pressure in Pa or hPa
        field_name: Field name for error messages
        
    Returns:
        Validated pressure or None
        
    Raises:
        ValidationError: If value is outside reasonable range
    """
    if value is None:
        return None
    
    # Reasonable pressure range: 87000 to 108400 Pa (870 to 1084 hPa)
    if not 87000 <= value <= 108400:
        raise ValidationError(f"{field_name} out of range: {value} Pa (expected 87000 to 108400)")
    
    return value


def validate_humidity(value: Optional[float], field_name: str = "humidity") -> Optional[float]:
    """Validate relative humidity value.
    
    Args:
        value: Relative humidity as percentage
        field_name: Field name for error messages
        
    Returns:
        Validated humidity or None
        
    Raises:
        ValidationError: If value is outside valid range
    """
    if value is None:
        return None
    
    # Valid range: 0 to 100%
    if not 0 <= value <= 100:
        raise ValidationError(f"{field_name} out of range: {value}% (expected 0 to 100)")
    
    return value


def validate_observation(obs: Dict[str, Any], strict: bool = False) -> List[str]:
    """Validate observation data quality.
    
    Args:
        obs: Observation dictionary
        strict: If True, raise ValidationError on first failure. If False, collect all warnings.
        
    Returns:
        List of validation warning messages
        
    Raises:
        ValidationError: If strict=True and validation fails
    """
    warnings = []
    
    try:
        # Validate temperatures
        if obs.get('temperature') is not None:
            validate_temperature(obs['temperature'], 'temperature')
        if obs.get('temp_avg') is not None:
            validate_temperature(obs['temp_avg'], 'temp_avg')
        if obs.get('temp_max') is not None:
            validate_temperature(obs['temp_max'], 'temp_max')
        if obs.get('temp_min') is not None:
            validate_temperature(obs['temp_min'], 'temp_min')
        if obs.get('dewpoint') is not None:
            validate_temperature(obs['dewpoint'], 'dewpoint')
        
        # Validate wind speeds
        if obs.get('wind_speed') is not None:
            validate_wind_speed(obs['wind_speed'], 'wind_speed')
        if obs.get('wind_speed_avg') is not None:
            validate_wind_speed(obs['wind_speed_avg'], 'wind_speed_avg')
        if obs.get('wind_gust') is not None:
            validate_wind_speed(obs['wind_gust'], 'wind_gust')
        
        # Validate pressure
        if obs.get('barometric_pressure') is not None:
            validate_pressure(obs['barometric_pressure'], 'barometric_pressure')
        if obs.get('pressure') is not None:
            validate_pressure(obs['pressure'], 'pressure')
        
        # Validate humidity
        if obs.get('relative_humidity') is not None:
            validate_humidity(obs['relative_humidity'], 'relative_humidity')
        if obs.get('humidity') is not None:
            validate_humidity(obs['humidity'], 'humidity')
        
        # Check for future timestamps
        obs_time = obs.get('observation_time')
        if obs_time and isinstance(obs_time, datetime):
            if obs_time > datetime.now(timezone.utc):
                msg = f"Observation time is in the future: {obs_time}"
                if strict:
                    raise ValidationError(msg)
                warnings.append(msg)
        
    except ValidationError as e:
        if strict:
            raise
        warnings.append(str(e))
    
    return warnings
