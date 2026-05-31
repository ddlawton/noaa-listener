# Configuration Reference

## Environment Variables

Configure via `.env` file:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=noaa_weather
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here

# NOAA APIs
NOAA_CDO_API_TOKEN=your_token_here

# Location
LOCATION_LATITUDE=37.7749
LOCATION_LONGITUDE=-122.4194
LOCATION_NAME=San Francisco, CA

# Optional
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## Application Configuration

Edit `config.yaml`:

### Fetching

```yaml
fetching:
  forecast_update_interval: 60  # Minutes between forecast updates
  historical_update_interval: 1440  # Minutes between historical updates (daily)
  data_retention_days: 30  # Keep forecast data for this many days
```

### API Settings

```yaml
api:
  timeout: 30  # Seconds
  max_retries: 3
  retry_backoff_factor: 2.0  # Exponential backoff multiplier
  rate_limit_delay: 1.0  # Seconds to wait between API calls
```

### Database

```yaml
database:
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30
  pool_recycle: 3600
  batch_size: 500  # Records per bulk insert
```

### Logging

```yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s"
  file: logs/noaa_listener.log
  max_bytes: 10485760  # 10MB
  backup_count: 5
```

## Station Selection

The CDO API requires a station ID. The application automatically finds the nearest station based on your coordinates. To specify a station manually:

```yaml
location:
  station_id: "GHCND:USW00023234"  # Optional: override auto-detection
```

Find stations at: https://www.ncdc.noaa.gov/cdo-web/datasets

## Data Quality Validation

Validation ranges (hardcoded in `noaa_listener/ingestion/validators.py`):

| Field | Valid Range | Unit |
|-------|-------------|------|
| Temperature | -90 to 60 | °C |
| Wind Speed | 0 to 113 | m/s |
| Pressure | 87000 to 108400 | Pa |
| Humidity | 0 to 100 | % |

Invalid values are logged as warnings but still stored with a `quality_flag`.
