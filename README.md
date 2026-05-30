# NOAA Weather Listener

Python service that fetches and stores weather data from NOAA APIs into PostgreSQL. Runs as a Docker container with scheduled hourly updates.

## Features

- **Data Sources**: NWS API (forecasts/current) + CDO API (historical)
- **Coverage**: 7-day forecasts, hourly forecasts, current conditions, historical observations
- **Reliability**: Automatic retries, rate limiting, error handling, hourly scheduled updates
- **Storage**: PostgreSQL with unified observations table, automated cleanup
- **Validation**: Data quality checks with configurable ranges
- **Monitoring**: Correlation IDs for request tracing, comprehensive logging

## Quick Start

1. **Get a CDO API token**: https://www.ncdc.noaa.gov/cdo-web/token

2. **Configure**:
   ```bash
   cp .env.example .env
   # Edit .env: set POSTGRES_PASSWORD, NOAA_CDO_API_TOKEN,
   #            LOCATION_LATITUDE, LOCATION_LONGITUDE, and LOCATION_NAME
   ```

3. **Run**:
   ```bash
   docker-compose up -d
   docker-compose logs -f noaa_listener
   ```

4. **Backfill historical data** (optional):
   ```bash
   docker-compose exec noaa_listener python scripts/backfill_historical.py --start-date 2024-01-01
   ```

## Configuration

**Environment variables** (`.env`):
- `POSTGRES_*`: Database connection details
- `NOAA_CDO_API_TOKEN`: Your CDO API token
- `LOG_LEVEL`: DEBUG, INFO, WARNING, or ERROR (optional)

**Application config** (`config.yaml`):
- `location`: Your coordinates and name
- `fetching.forecast_update_interval`: Update frequency in minutes (default: 60)
- `api`: Timeout and retry settings
- `database.batch_size`: Bulk insert size (default: 500)

See [docs/configuration.md](docs/configuration.md) for details.

## Database Schema

Main tables:
- `stations`: Weather station metadata
- `observations`: Unified historical and current observations (with `data_source` field)
- `forecast_periods`: 7-day forecast data
- `forecast_hourly`: Hourly forecast data
- `forecast_gridded`: Gridded forecast values
- `data_fetch_log`: API fetch operation audit log

See [docs/database.md](docs/database.md) for schema details and example queries.

## CI/CD

GitHub Actions workflows automatically:
- Run tests, linting, and formatting checks on every push
- Build and push Docker images to GitHub Container Registry on main branch
- Tag with commit SHA, branch name, and `latest`

Pull the latest image:
```bash
docker pull ghcr.io/ddlawton/noaa-listener:latest
```

## Development

**Setup**:
```bash
uv pip install -e .
cp .env.example .env  # Edit with your settings
psql -U postgres -f init.sql
```

**Run**:
```bash
python -m noaa_listener.main
```

**Test**:
```bash
pytest tests/ -v
```

**Format/Lint**:
```bash
black noaa_listener tests
flake8 noaa_listener --max-line-length=120
```

See [docs/development.md](docs/development.md) for architecture and contributing guidelines.

## Deployment

**Docker Compose** (recommended):
```bash
docker-compose up -d
```

**Kubernetes/TrueNAS Scale**:
See [docs/deployment.md](docs/deployment.md) for Kubernetes manifests and TrueNAS Scale setup.



## Troubleshooting

**Database connection issues**:
```bash
docker-compose logs postgres
docker-compose exec postgres psql -U postgres -d noaa_weather -c "SELECT 1"
```

**API errors**:
```bash
docker-compose logs noaa_listener
# Check data_fetch_log table for fetch status
```

**No data ingesting**:
1. Verify latitude/longitude in `config.yaml`
2. Check API token validity
3. Review logs for specific errors

## License

Personal use. Comply with NOAA API terms of service.