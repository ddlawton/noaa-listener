"""Historical data backfill script."""

import sys
import argparse
from datetime import datetime

from noaa_listener.config import get_config
from noaa_listener.logger import get_logger
from noaa_listener.database import Database
from noaa_listener.ingestion.ingestor import DataIngestor

logger = get_logger(__name__)


def main():
    """Main entry point for historical backfill."""
    parser = argparse.ArgumentParser(
        description='Backfill historical weather data from NOAA CDO API'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date for backfill (YYYY-MM-DD), defaults to config value'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date for backfill (YYYY-MM-DD), defaults to today'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = get_config(args.config)
        
        # Validate configuration
        try:
            config.validate()
        except ValueError as e:
            logger.error(f"Configuration validation failed: {e}")
            sys.exit(1)
        
        # Set dates
        start_date = args.start_date or config.historical_start_date
        end_date = args.end_date or datetime.utcnow().strftime('%Y-%m-%d')
        
        logger.info(f"Starting historical data backfill from {start_date} to {end_date}")
        logger.info(f"Location: {config.location_name} ({config.latitude}, {config.longitude})")
        
        # Initialize database and ingestor
        db = Database(config)
        if not db.test_connection():
            logger.error("Database connection failed")
            sys.exit(1)
        
        ingestor = DataIngestor(config, db)
        
        # Initialize (fetch grid info and stations)
        if not ingestor.initialize():
            logger.error("Failed to initialize ingestor")
            sys.exit(1)
        
        # Run historical data ingestion
        logger.info("Starting historical data ingestion...")
        success = ingestor.ingest_historical_data(start_date, end_date)
        
        if success:
            logger.info("Historical data backfill completed successfully")
        else:
            logger.error("Historical data backfill failed")
            sys.exit(1)
        
        # Clean up
        ingestor.close()
        
    except KeyboardInterrupt:
        logger.info("Backfill interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during backfill: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
