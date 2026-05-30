"""Example database queries for NOAA weather data."""

-- Get latest forecast periods
SELECT 
    period_name,
    start_time,
    temperature,
    wind_speed,
    wind_direction,
    short_forecast,
    precipitation_probability
FROM forecast_periods
WHERE station_id = 'YOUR_STATION_ID'
    AND generated_at = (SELECT MAX(generated_at) FROM forecast_periods)
ORDER BY period_number;

-- Get hourly forecast for next 24 hours
SELECT 
    forecast_time,
    temperature,
    wind_speed,
    wind_direction,
    precipitation_probability,
    relative_humidity
FROM forecast_hourly
WHERE station_id = 'YOUR_STATION_ID'
    AND generated_at = (SELECT MAX(generated_at) FROM forecast_hourly)
    AND forecast_time >= NOW()
    AND forecast_time <= NOW() + INTERVAL '24 hours'
ORDER BY forecast_time;

-- Get historical temperature trends (monthly averages)
SELECT 
    DATE_TRUNC('month', timestamp) as month,
    AVG(temp_avg) as avg_temperature,
    MAX(temp_max) as max_temperature,
    MIN(temp_min) as min_temperature,
    COUNT(*) as observation_count
FROM historical_observations
WHERE station_id = 'YOUR_STATION_ID'
    AND timestamp >= NOW() - INTERVAL '1 year'
GROUP BY DATE_TRUNC('month', timestamp)
ORDER BY month DESC;

-- Compare forecast accuracy (temperature)
WITH latest_forecast AS (
    SELECT 
        forecast_time,
        temperature as forecast_temp
    FROM forecast_hourly
    WHERE station_id = 'YOUR_STATION_ID'
        AND generated_at >= NOW() - INTERVAL '7 days'
)
SELECT 
    h.timestamp,
    h.temp_avg as actual_temp,
    f.forecast_temp,
    ABS(h.temp_avg - f.forecast_temp) as error
FROM historical_observations h
JOIN latest_forecast f ON DATE_TRUNC('hour', h.timestamp) = f.forecast_time
WHERE h.station_id = 'YOUR_STATION_ID'
    AND h.timestamp >= NOW() - INTERVAL '7 days'
ORDER BY h.timestamp DESC;

-- Get current conditions summary
SELECT 
    station_id,
    observation_time,
    temperature,
    dewpoint,
    relative_humidity,
    wind_speed,
    wind_direction,
    barometric_pressure,
    text_description
FROM current_conditions
WHERE observation_time = (SELECT MAX(observation_time) FROM current_conditions)
ORDER BY station_id;

-- Wind analysis (historical)
SELECT 
    DATE_TRUNC('day', timestamp) as day,
    AVG(wind_speed_avg) as avg_wind_speed,
    MAX(wind_speed_max) as max_wind_speed,
    AVG(wind_direction) as predominant_direction
FROM historical_observations
WHERE station_id = 'YOUR_STATION_ID'
    AND timestamp >= NOW() - INTERVAL '30 days'
    AND wind_speed_avg IS NOT NULL
GROUP BY DATE_TRUNC('day', timestamp)
ORDER BY day DESC;

-- Precipitation summary
SELECT 
    DATE_TRUNC('day', timestamp) as day,
    SUM(precipitation) as total_precipitation,
    COUNT(*) FILTER (WHERE precipitation > 0) as rainy_periods
FROM historical_observations
WHERE station_id = 'YOUR_STATION_ID'
    AND timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', timestamp)
ORDER BY day DESC;

-- Data fetch log summary
SELECT 
    fetch_type,
    data_source,
    COUNT(*) as fetch_count,
    SUM(records_inserted) as total_records,
    AVG(fetch_duration_seconds) as avg_duration,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_fetches,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_fetches
FROM data_fetch_log
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY fetch_type, data_source
ORDER BY fetch_type, data_source;

-- Compare NOAA data with Tempest (if you have both databases)
-- This query assumes you have a Tempest database connection
-- You would run this using a database link or by joining data externally
WITH noaa_daily AS (
    SELECT 
        DATE_TRUNC('day', timestamp) as day,
        AVG(temp_avg) as noaa_temp,
        AVG(wind_speed_avg) as noaa_wind,
        SUM(precipitation) as noaa_precip
    FROM historical_observations
    WHERE timestamp >= NOW() - INTERVAL '30 days'
    GROUP BY DATE_TRUNC('day', timestamp)
)
SELECT 
    day,
    noaa_temp,
    noaa_wind,
    noaa_precip
FROM noaa_daily
ORDER BY day DESC;

-- Find data gaps
SELECT 
    station_id,
    DATE_TRUNC('day', timestamp) as day,
    COUNT(*) as observation_count
FROM historical_observations
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY station_id, DATE_TRUNC('day', timestamp)
HAVING COUNT(*) < 24  -- Less than expected daily observations
ORDER BY day DESC, station_id;

-- Weather extremes
SELECT 
    'Max Temperature' as metric,
    MAX(temp_max) as value,
    timestamp as occurred_at
FROM historical_observations
WHERE station_id = 'YOUR_STATION_ID'
    AND timestamp >= NOW() - INTERVAL '1 year'
GROUP BY timestamp
ORDER BY value DESC
LIMIT 1;

UNION ALL

SELECT 
    'Min Temperature' as metric,
    MIN(temp_min) as value,
    timestamp as occurred_at
FROM historical_observations
WHERE station_id = 'YOUR_STATION_ID'
    AND timestamp >= NOW() - INTERVAL '1 year'
GROUP BY timestamp
ORDER BY value ASC
LIMIT 1;

UNION ALL

SELECT 
    'Max Wind Speed' as metric,
    MAX(wind_speed_max) as value,
    timestamp as occurred_at
FROM historical_observations
WHERE station_id = 'YOUR_STATION_ID'
    AND timestamp >= NOW() - INTERVAL '1 year'
GROUP BY timestamp
ORDER BY value DESC
LIMIT 1;
