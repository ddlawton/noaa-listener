# Database Schema

## Tables

### `stations`

Weather station metadata.

```sql
CREATE TABLE stations (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    elevation DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `observations`

Unified table for both historical observations (CDO API) and current conditions (NWS API). Replaces separate `historical_observations` and `current_conditions` tables.

```sql
CREATE TABLE observations (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(255) REFERENCES stations(id),
    observed_at TIMESTAMP NOT NULL,
    data_source VARCHAR(50) NOT NULL,  -- 'cdo', 'nws'
    temperature DECIMAL(5, 2),
    temp_max DECIMAL(5, 2),
    temp_min DECIMAL(5, 2),
    -- ... additional weather fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(station_id, observed_at, data_source)
);
```

**Key Fields**:
- `data_source`: Distinguishes between historical (`cdo`) and current (`nws`) data
- `observed_at`: Timestamp of the weather observation
- UNIQUE constraint prevents duplicates per station/time/source

### `forecast_periods`

7-day forecast data from NWS API.

```sql
CREATE TABLE forecast_periods (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(255) REFERENCES stations(id),
    forecast_time TIMESTAMP NOT NULL,
    period_number INTEGER,
    period_name VARCHAR(50),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    temperature INTEGER,
    -- ... additional forecast fields
    UNIQUE(station_id, forecast_time, period_number)
);
```

### `forecast_hourly`

Hourly forecast data from NWS API.

```sql
CREATE TABLE forecast_hourly (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(255) REFERENCES stations(id),
    forecast_time TIMESTAMP NOT NULL,
    valid_time TIMESTAMP,
    temperature DECIMAL(5, 2),
    -- ... additional hourly fields
    UNIQUE(station_id, forecast_time, valid_time)
);
```

### `forecast_gridded`

Raw gridded forecast data from NWS API.

```sql
CREATE TABLE forecast_gridded (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(255) REFERENCES stations(id),
    forecast_time TIMESTAMP NOT NULL,
    grid_id VARCHAR(10),
    grid_x INTEGER,
    grid_y INTEGER,
    -- ... gridded forecast values
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `data_fetch_log`

Audit log for API fetch operations.

```sql
CREATE TABLE data_fetch_log (
    id SERIAL PRIMARY KEY,
    fetch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_fetched INTEGER,
    error_message TEXT,
    correlation_id VARCHAR(36)
);
```

## Common Queries

### Latest Temperature Readings

```sql
SELECT station_id, observed_at, temperature, data_source
FROM observations
WHERE station_id = 'GHCND:USW00023234'
ORDER BY observed_at DESC
LIMIT 10;
```

### 7-Day Forecast

```sql
SELECT period_name, start_time, temperature, short_forecast
FROM forecast_periods
WHERE station_id = 'GHCND:USW00023234'
  AND forecast_time = (SELECT MAX(forecast_time) FROM forecast_periods)
ORDER BY period_number;
```

### Historical Temperature Trends

```sql
SELECT DATE(observed_at) as date,
       AVG(temperature) as avg_temp,
       MAX(temp_max) as high,
       MIN(temp_min) as low
FROM observations
WHERE station_id = 'GHCND:USW00023234'
  AND observed_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(observed_at)
ORDER BY date;
```

### Precipitation Summary

```sql
SELECT DATE(observed_at) as date,
       SUM(precipitation) as total_precip
FROM observations
WHERE station_id = 'GHCND:USW00023234'
  AND observed_at >= NOW() - INTERVAL '7 days'
  AND precipitation IS NOT NULL
GROUP BY DATE(observed_at)
ORDER BY date;
```

### Data Fetch Success Rate

```sql
SELECT data_type,
       COUNT(*) as total_fetches,
       SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
       ROUND(100.0 * SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM data_fetch_log
WHERE fetch_time >= NOW() - INTERVAL '7 days'
GROUP BY data_type;
```

## Indexes

Key indexes for performance:

```sql
CREATE INDEX idx_observations_station_time ON observations(station_id, observed_at DESC);
CREATE INDEX idx_observations_source ON observations(data_source);
CREATE INDEX idx_forecast_periods_station_time ON forecast_periods(station_id, forecast_time DESC);
CREATE INDEX idx_fetch_log_time ON data_fetch_log(fetch_time DESC);
```

## Data Cleanup

Old forecast data is automatically cleaned up based on `data_retention_days` config. To manually clean:

```sql
DELETE FROM forecast_periods WHERE forecast_time < NOW() - INTERVAL '30 days';
DELETE FROM forecast_hourly WHERE forecast_time < NOW() - INTERVAL '30 days';
DELETE FROM forecast_gridded WHERE forecast_time < NOW() - INTERVAL '30 days';
```
