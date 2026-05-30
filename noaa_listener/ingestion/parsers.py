"""Data parsers for NOAA API responses."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from noaa_listener.logger import get_logger
from noaa_listener.ingestion.validators import validate_observation

logger = get_logger(__name__)


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO format datetime string.
    
    Args:
        dt_str: ISO format datetime string
        
    Returns:
        datetime object or None
    """
    if not dt_str:
        return None
    
    try:
        # Handle timezone formats
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        return datetime.fromisoformat(dt_str)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
        return None


def extract_value(value_obj: Any) -> Optional[float]:
    """Extract numeric value from API response value object.
    
    Args:
        value_obj: Value object from API (could be dict with 'value' key or direct number)
        
    Returns:
        Numeric value or None
    """
    if value_obj is None:
        return None
    
    if isinstance(value_obj, dict):
        return value_obj.get('value')
    
    if isinstance(value_obj, (int, float)):
        return float(value_obj)
    
    return None


def parse_station_data(station_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse station metadata.
    
    Args:
        station_data: Raw station data from API
        
    Returns:
        Parsed station data
    """
    return {
        'station_id': station_data.get('stationIdentifier') or station_data.get('id', ''),
        'name': station_data.get('name', ''),
        'latitude': station_data.get('latitude') or station_data.get('geometry', {}).get('coordinates', [None, None])[1],
        'longitude': station_data.get('longitude') or station_data.get('geometry', {}).get('coordinates', [None, None])[0],
        'elevation': extract_value(station_data.get('elevation')),
        'timezone': station_data.get('timeZone'),
        'state': station_data.get('state')
    }


def parse_forecast_period(period: Dict[str, Any], grid_id: str, grid_x: int, grid_y: int, station_id: str, generated_at: datetime) -> Dict[str, Any]:
    """Parse a forecast period.
    
    Args:
        period: Raw forecast period data
        grid_id: Grid identifier
        grid_x: Grid X coordinate
        grid_y: Grid Y coordinate
        station_id: Associated station ID
        generated_at: When the forecast was generated
        
    Returns:
        Parsed forecast period
    """
    return {
        'station_id': station_id,
        'grid_id': grid_id,
        'grid_x': grid_x,
        'grid_y': grid_y,
        'generated_at': generated_at,
        'period_number': period.get('number'),
        'period_name': period.get('name'),
        'start_time': parse_iso_datetime(period.get('startTime')),
        'end_time': parse_iso_datetime(period.get('endTime')),
        'temperature': period.get('temperature'),
        'temperature_unit': period.get('temperatureUnit'),
        'temperature_trend': period.get('temperatureTrend'),
        'wind_speed': period.get('windSpeed'),
        'wind_direction': period.get('windDirection'),
        'short_forecast': period.get('shortForecast'),
        'detailed_forecast': period.get('detailedForecast'),
        'precipitation_probability': extract_value(period.get('probabilityOfPrecipitation')),
        'dewpoint': extract_value(period.get('dewpoint')),
        'relative_humidity': extract_value(period.get('relativeHumidity')),
        'is_daytime': period.get('isDaytime'),
        'icon_url': period.get('icon')
    }


def parse_hourly_forecast(period: Dict[str, Any], grid_id: str, grid_x: int, grid_y: int, station_id: str, generated_at: datetime) -> Dict[str, Any]:
    """Parse an hourly forecast period.
    
    Args:
        period: Raw hourly forecast data
        grid_id: Grid identifier
        grid_x: Grid X coordinate
        grid_y: Grid Y coordinate
        station_id: Associated station ID
        generated_at: When the forecast was generated
        
    Returns:
        Parsed hourly forecast
    """
    return {
        'station_id': station_id,
        'grid_id': grid_id,
        'grid_x': grid_x,
        'grid_y': grid_y,
        'generated_at': generated_at,
        'forecast_time': parse_iso_datetime(period.get('startTime')),
        'temperature': extract_value(period.get('temperature')),
        'dewpoint': extract_value(period.get('dewpoint')),
        'wind_speed': extract_value(period.get('windSpeed')),
        'wind_direction': extract_value(period.get('windDirection')),
        'wind_gust': extract_value(period.get('windGust')),
        'relative_humidity': extract_value(period.get('relativeHumidity')),
        'pressure': None,  # Not typically in hourly forecast
        'precipitation_probability': extract_value(period.get('probabilityOfPrecipitation')),
        'quantitative_precipitation': extract_value(period.get('quantitativePrecipitation')),
        'sky_cover': extract_value(period.get('skyCover')),
        'cloud_base': None,
        'visibility': extract_value(period.get('visibility')),
        'weather_summary': period.get('shortForecast')
    }


def parse_gridded_forecast_values(gridded_data: Dict[str, Any], grid_id: str, grid_x: int, grid_y: int, generated_at: datetime) -> List[Dict[str, Any]]:
    """Parse gridded forecast data into time series records.
    
    Args:
        gridded_data: Raw gridded forecast data
        grid_id: Grid identifier
        grid_x: Grid X coordinate
        grid_y: Grid Y coordinate
        generated_at: When the forecast was generated
        
    Returns:
        List of parsed gridded forecast records
    """
    records = []
    
    # Get all time series data
    properties = gridded_data
    
    # Extract temperature time series as the base
    temperature_series = properties.get('temperature', {}).get('values', [])
    
    for temp_entry in temperature_series:
        valid_time = temp_entry.get('validTime', '')
        if '/' in valid_time:
            start_time_str, duration = valid_time.split('/')
            start_time = parse_iso_datetime(start_time_str)
        else:
            start_time = parse_iso_datetime(valid_time)
        
        if not start_time:
            continue
        
        record = {
            'grid_id': grid_id,
            'grid_x': grid_x,
            'grid_y': grid_y,
            'generated_at': generated_at,
            'valid_time_start': start_time,
            'valid_time_end': start_time,  # Simplified; could parse duration
            'temperature': extract_value(temp_entry.get('value')),
            'dewpoint': None,
            'max_temperature': None,
            'min_temperature': None,
            'apparent_temperature': None,
            'wind_speed': None,
            'wind_direction': None,
            'wind_gust': None,
            'relative_humidity': None,
            'pressure': None,
            'precipitation_probability': None,
            'quantitative_precipitation': None,
            'ice_accumulation': None,
            'snowfall_amount': None,
            'sky_cover': None,
            'visibility': None,
            'weather': None,
            'hazards': None,
            'heat_index': None,
            'wind_chill': None
        }
        
        records.append(record)
    
    return records


def parse_observation(obs_data: Dict[str, Any], station_id: str) -> Dict[str, Any]:
    """Parse an observation from NWS.
    
    Args:
        obs_data: Raw observation data
        station_id: Station identifier
        
    Returns:
        Parsed observation
    """
    parsed = {
        'station_id': station_id,
        'observation_time': parse_iso_datetime(obs_data.get('timestamp')),
        'temperature': extract_value(obs_data.get('temperature')),
        'temp_avg': None,
        'temp_max': None,
        'temp_min': None,
        'dewpoint': extract_value(obs_data.get('dewpoint')),
        'heat_index': extract_value(obs_data.get('heatIndex')),
        'wind_chill': extract_value(obs_data.get('windChill')),
        'wind_speed': extract_value(obs_data.get('windSpeed')),
        'wind_speed_avg': None,
        'wind_speed_max': None,
        'wind_direction': extract_value(obs_data.get('windDirection')),
        'wind_gust': extract_value(obs_data.get('windGust')),
        'barometric_pressure': extract_value(obs_data.get('barometricPressure')),
        'sea_level_pressure': extract_value(obs_data.get('seaLevelPressure')),
        'pressure': None,
        'humidity': None,
        'relative_humidity': extract_value(obs_data.get('relativeHumidity')),
        'precipitation': None,
        'precipitation_last_hour': extract_value(obs_data.get('precipitationLastHour')),
        'precipitation_last_3hr': extract_value(obs_data.get('precipitationLast3Hours')),
        'precipitation_last_6hr': extract_value(obs_data.get('precipitationLast6Hours')),
        'snow_depth': None,
        'snow_fall': None,
        'visibility': extract_value(obs_data.get('visibility')),
        'cloud_cover': None,
        'sky_cover': None,
        'cloud_layers': json.dumps(obs_data.get('cloudLayers', [])) if obs_data.get('cloudLayers') else None,
        'solar_radiation': None,
        'text_description': obs_data.get('textDescription'),
        'icon_url': obs_data.get('icon'),
        'raw_message': obs_data.get('rawMessage'),
        'data_source': 'NWS',
        'quality_flags': None
    }
    
    # Validate data quality (non-strict mode - just log warnings)
    warnings = validate_observation(parsed, strict=False)
    if warnings:
        logger.warning(f"Data quality warnings for {station_id}: {', '.join(warnings)}")
    
    return parsed


def parse_cdo_data(data_record: Dict[str, Any]) -> Dict[str, Any]:
    """Parse CDO historical data record.
    
    Args:
        data_record: Raw CDO data record
        
    Returns:
        Parsed historical observation
    """
    # Map CDO data types to our schema fields
    datatype = data_record.get('datatype', '')
    value = data_record.get('value')
    
    record = {
        'station_id': data_record.get('station', ''),
        'observation_time': parse_iso_datetime(data_record.get('date')),
        'temperature': None,
        'temp_avg': None,
        'temp_max': None,
        'temp_min': None,
        'dewpoint': None,
        'heat_index': None,
        'wind_chill': None,
        'wind_speed': None,
        'wind_speed_avg': None,
        'wind_speed_max': None,
        'wind_direction': None,
        'wind_gust': None,
        'barometric_pressure': None,
        'sea_level_pressure': None,
        'pressure': None,
        'humidity': None,
        'relative_humidity': None,
        'precipitation': None,
        'precipitation_last_hour': None,
        'precipitation_last_3hr': None,
        'precipitation_last_6hr': None,
        'snow_depth': None,
        'snow_fall': None,
        'visibility': None,
        'cloud_cover': None,
        'sky_cover': None,
        'cloud_layers': None,
        'solar_radiation': None,
        'text_description': None,
        'icon_url': None,
        'raw_message': None,
        'data_source': 'CDO',
        'quality_flags': json.dumps({
            'attributes': data_record.get('attributes', ''),
            'datatype': datatype
        })
    }
    
    # Map specific data types
    if datatype == 'TAVG':
        record['temp_avg'] = value
    elif datatype == 'TMAX':
        record['temp_max'] = value
    elif datatype == 'TMIN':
        record['temp_min'] = value
    elif datatype == 'PRCP':
        record['precipitation'] = value
    elif datatype == 'SNOW':
        record['snow_fall'] = value
    elif datatype == 'SNWD':
        record['snow_depth'] = value
    elif datatype in ['AWND', 'WSF2', 'WSF5']:
        record['wind_speed_avg'] = value
    elif datatype == 'WDF2' or datatype == 'WDF5':
        record['wind_direction'] = value
    
    return record


def aggregate_cdo_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate CDO records by station and timestamp.
    
    Since CDO returns one record per data type, we need to aggregate
    them into single records per timestamp.
    
    Args:
        records: List of parsed CDO records
        
    Returns:
        List of aggregated records
    """
    # Group by station and timestamp
    grouped: Dict[tuple, Dict[str, Any]] = {}
    
    for record in records:
        key = (record['station_id'], record['observation_time'])
        
        if key not in grouped:
            grouped[key] = record.copy()
        else:
            # Merge non-None values
            for field, value in record.items():
                if value is not None and grouped[key][field] is None:
                    grouped[key][field] = value
    
    return list(grouped.values())
