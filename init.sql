-- NOAA Weather Data Schema
-- Optimized for forecast and historical weather data storage

-- Enable TimescaleDB extension if available (optional, for better time-series performance)
-- CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Stations table: Store metadata about weather stations
CREATE TABLE IF NOT EXISTS stations (
    id SERIAL PRIMARY KEY,
    station_id TEXT UNIQUE NOT NULL,
    name TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    elevation REAL,
    timezone TEXT,
    state TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_stations_station_id ON stations (station_id);
CREATE INDEX IF NOT EXISTS idx_stations_location ON stations (latitude, longitude);


-- Unified observations table: Stores both historical and current conditions
CREATE TABLE IF NOT EXISTS observations (
    id SERIAL PRIMARY KEY,
    station_id TEXT NOT NULL,
    observation_time TIMESTAMPTZ NOT NULL,

    -- Temperature
    temperature REAL,
    temp_avg REAL,
    temp_max REAL,
    temp_min REAL,
    dewpoint REAL,
    heat_index REAL,
    wind_chill REAL,

    -- Wind
    wind_speed REAL,
    wind_speed_avg REAL,
    wind_speed_max REAL,
    wind_direction REAL,
    wind_gust REAL,

    -- Atmospheric
    barometric_pressure REAL,
    sea_level_pressure REAL,
    pressure REAL,
    humidity REAL,
    relative_humidity REAL,

    -- Precipitation
    precipitation REAL,
    precipitation_last_hour REAL,
    precipitation_last_3hr REAL,
    precipitation_last_6hr REAL,
    snow_depth REAL,
    snow_fall REAL,

    -- Visibility and sky
    visibility REAL,
    cloud_cover REAL,
    sky_cover REAL,
    cloud_layers JSONB,

    -- Solar
    solar_radiation REAL,

    -- Weather description
    text_description TEXT,
    icon_url TEXT,
    raw_message TEXT,

    -- Data quality
    data_source TEXT,
    quality_flags JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (station_id, observation_time, data_source)
);
CREATE INDEX IF NOT EXISTS idx_observations_station_time ON observations (station_id, observation_time DESC);
CREATE INDEX IF NOT EXISTS idx_observations_data_source ON observations (data_source);

-- Forecast data: Store 7-day forecast periods
CREATE TABLE IF NOT EXISTS forecast_periods (
    id SERIAL PRIMARY KEY,
    station_id TEXT NOT NULL,
    grid_id TEXT NOT NULL,
    grid_x INTEGER NOT NULL,
    grid_y INTEGER NOT NULL,
    
    -- Forecast metadata
    generated_at TIMESTAMPTZ NOT NULL,  -- When the forecast was generated
    period_number INTEGER NOT NULL,
    period_name TEXT,  -- e.g., "Tonight", "Monday", etc.
    
    -- Time range for this forecast period
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    
    -- Temperature (in Celsius)
    temperature REAL,
    temperature_unit TEXT,
    temperature_trend TEXT,
    
    -- Wind
    wind_speed TEXT,  -- Often in text format like "5 to 10 mph"
    wind_direction TEXT,
    
    -- Conditions
    short_forecast TEXT,
    detailed_forecast TEXT,
    
    -- Probabilities
    precipitation_probability REAL,  -- in percent
    
    -- Additional data
    dewpoint REAL,
    relative_humidity REAL,
    
    is_daytime BOOLEAN,
    icon_url TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (station_id, generated_at, period_number)
);
CREATE INDEX IF NOT EXISTS idx_forecast_periods_station_time ON forecast_periods (station_id, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_forecast_periods_generated ON forecast_periods (generated_at DESC);

-- Hourly forecast data: More granular forecast data
CREATE TABLE IF NOT EXISTS forecast_hourly (
    id SERIAL PRIMARY KEY,
    station_id TEXT NOT NULL,
    grid_id TEXT NOT NULL,
    grid_x INTEGER NOT NULL,
    grid_y INTEGER NOT NULL,
    
    -- Forecast metadata
    generated_at TIMESTAMPTZ NOT NULL,
    forecast_time TIMESTAMPTZ NOT NULL,  -- The hour being forecasted
    
    -- Temperature (in Celsius)
    temperature REAL,
    dewpoint REAL,
    
    -- Wind (in m/s and degrees)
    wind_speed REAL,
    wind_direction REAL,
    wind_gust REAL,
    
    -- Atmospheric
    relative_humidity REAL,  -- in percent
    pressure REAL,  -- in hPa
    
    -- Precipitation
    precipitation_probability REAL,  -- in percent
    quantitative_precipitation REAL,  -- in mm
    
    -- Sky conditions
    sky_cover REAL,  -- in percent
    cloud_base REAL,  -- in meters
    
    -- Visibility and weather
    visibility REAL,  -- in meters
    weather_summary TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (station_id, generated_at, forecast_time)
);
CREATE INDEX IF NOT EXISTS idx_forecast_hourly_station_time ON forecast_hourly (station_id, forecast_time DESC);
CREATE INDEX IF NOT EXISTS idx_forecast_hourly_generated ON forecast_hourly (generated_at DESC);

-- Gridded forecast data: Raw gridded forecast data from NWS
CREATE TABLE IF NOT EXISTS forecast_gridded (
    id SERIAL PRIMARY KEY,
    grid_id TEXT NOT NULL,
    grid_x INTEGER NOT NULL,
    grid_y INTEGER NOT NULL,
    
    -- Forecast metadata
    generated_at TIMESTAMPTZ NOT NULL,
    valid_time_start TIMESTAMPTZ NOT NULL,
    valid_time_end TIMESTAMPTZ NOT NULL,
    
    -- Temperature (in Celsius)
    temperature REAL,
    dewpoint REAL,
    max_temperature REAL,
    min_temperature REAL,
    apparent_temperature REAL,
    
    -- Wind (in m/s and degrees)
    wind_speed REAL,
    wind_direction REAL,
    wind_gust REAL,
    
    -- Atmospheric
    relative_humidity REAL,
    pressure REAL,
    
    -- Precipitation
    precipitation_probability REAL,
    quantitative_precipitation REAL,
    ice_accumulation REAL,
    snowfall_amount REAL,
    
    -- Sky and visibility
    sky_cover REAL,
    visibility REAL,
    
    -- Additional conditions
    weather TEXT,
    hazards JSONB,
    
    -- Solar and heat
    heat_index REAL,
    wind_chill REAL,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (grid_id, grid_x, grid_y, generated_at, valid_time_start)
);
CREATE INDEX IF NOT EXISTS idx_forecast_gridded_grid ON forecast_gridded (grid_id, grid_x, grid_y, valid_time_start DESC);
CREATE INDEX IF NOT EXISTS idx_forecast_gridded_generated ON forecast_gridded (generated_at DESC);



-- Data fetch log: Track API calls and data ingestion
CREATE TABLE IF NOT EXISTS data_fetch_log (
    id SERIAL PRIMARY KEY,
    fetch_type TEXT NOT NULL,  -- 'forecast', 'hourly', 'gridded', 'historical', 'current'
    data_source TEXT NOT NULL,  -- 'NWS' or 'CDO'
    station_id TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    records_fetched INTEGER,
    records_inserted INTEGER,
    records_updated INTEGER,
    status TEXT NOT NULL,  -- 'success', 'partial', 'failed'
    error_message TEXT,
    fetch_duration_seconds REAL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_data_fetch_log_created ON data_fetch_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_fetch_log_type_status ON data_fetch_log (fetch_type, status);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for stations table
CREATE TRIGGER update_stations_updated_at
    BEFORE UPDATE ON stations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE stations IS 'Weather station metadata';
COMMENT ON TABLE observations IS 'Unified table for historical and current weather observations';
COMMENT ON TABLE forecast_periods IS '7-day forecast data by period';
COMMENT ON TABLE forecast_hourly IS 'Hourly forecast data';
COMMENT ON TABLE forecast_gridded IS 'Raw gridded forecast data from NWS';
COMMENT ON TABLE data_fetch_log IS 'Log of data fetching operations';
