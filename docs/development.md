# Development Guide

## Architecture

### Components

```
noaa_listener/
├── api/                    # External API clients
│   ├── base.py            # Retry logic, rate limiting
│   ├── nws_client.py      # NOAA/NWS API
│   └── cdo_client.py      # NOAA CDO API
├── ingestion/             # Data processing
│   ├── parsers.py         # API response parsing
│   ├── validators.py      # Data quality validation
│   └── ingestor.py        # Orchestration
├── config.py              # Configuration management
├── database.py            # Database operations
├── logger.py              # Logging + correlation IDs
└── main.py                # Entry point + scheduling
```

### Data Flow

1. **Scheduler** (APScheduler) triggers fetches hourly
2. **API Clients** fetch data with retry logic
3. **Parsers** convert API responses to database records
4. **Validators** check data quality (log warnings, continue)
5. **Database** bulk inserts with deduplication
6. **Cleanup** removes old forecast data

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- uv (recommended) or pip

### Installation

```bash
# Clone and navigate
cd noaa-listener

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .

# Set up database
psql -U postgres -f init.sql

# Configure
cp .env.example .env
# Edit .env: set database credentials, API token, and location
```

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### With Coverage

```bash
pytest tests/ --cov=noaa_listener --cov-report=html
open htmlcov/index.html
```

### Specific Test Files

```bash
pytest tests/test_validators.py -v
pytest tests/test_parsers.py -v
```

### Test Structure

```
tests/
├── conftest.py              # Fixtures (db session, mock responses)
├── test_config.py           # Config loading
├── test_api_clients.py      # API client mocking
├── test_parsers.py          # Parser logic
├── test_validators.py       # Validation ranges
└── test_database.py         # Database operations
```

## Code Quality

### Formatting

```bash
black noaa_listener tests
```

### Linting

```bash
flake8 noaa_listener --max-line-length=120 --ignore=E203,W503
```

### Type Checking (optional)

```bash
mypy noaa_listener
```

## Debugging

### Enable Debug Logging

In `.env`:
```bash
LOG_LEVEL=DEBUG
```

Or in code:
```python
import logging
logging.getLogger("noaa_listener").setLevel(logging.DEBUG)
```

### Correlation IDs

Every scheduled fetch gets a correlation ID for tracing:

```python
from noaa_listener.logger import set_correlation_id

set_correlation_id("my-debug-session")
# All logs now include: correlation_id=my-debug-session
```

Search logs:
```bash
grep "correlation_id=abc123" logs/noaa_listener.log
```

### Database Inspection

```sql
-- Check recent fetches
SELECT * FROM data_fetch_log ORDER BY fetch_time DESC LIMIT 10;

-- Check latest observations
SELECT * FROM observations ORDER BY observed_at DESC LIMIT 10;

-- Find validation issues
SELECT * FROM observations WHERE quality_flag IS NOT NULL;
```

## Contributing

### Adding a New Data Source

1. Create client in `noaa_listener/api/new_client.py`:
   ```python
   from .base import BaseAPIClient
   
   class NewClient(BaseAPIClient):
       def fetch_data(self):
           # Implementation
   ```

2. Add parser in `noaa_listener/ingestion/parsers.py`:
   ```python
   def parse_new_data(data):
       # Parse and validate
       return records
   ```

3. Integrate in `noaa_listener/ingestion/ingestor.py`:
   ```python
   def ingest_new_data(self):
       data = self.new_client.fetch_data()
       records = parse_new_data(data)
       self.db.bulk_insert(records)
   ```

4. Add tests in `tests/test_new_feature.py`

### Adding Validation Rules

Edit `noaa_listener/ingestion/validators.py`:

```python
def validate_new_field(value):
    """Validate new field."""
    if not (MIN_VALUE <= value <= MAX_VALUE):
        return False
    return True
```

Add tests in `tests/test_validators.py`.

## Release Process

1. Update version in `pyproject.toml`
2. Commit changes
3. Tag release:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
4. GitHub Actions builds and pushes Docker image with version tag
