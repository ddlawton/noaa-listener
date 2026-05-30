"""Main application entry point."""

import sys
import signal
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from noaa_listener.config import get_config
from noaa_listener.logger import get_logger
from noaa_listener.database import Database
from noaa_listener.ingestion.ingestor import DataIngestor

logger = get_logger(__name__)


class NOAAListener:
    """Main application class."""
    
    def __init__(self):
        """Initialize NOAA Listener application."""
        self.config = get_config()
        self.db = Database(self.config)
        self.ingestor = DataIngestor(self.config, self.db)
        self.scheduler = BlockingScheduler()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown()
        sys.exit(0)
    
    def initialize(self) -> bool:
        """Initialize the application.
        
        Returns:
            True if initialization successful
        """
        logger.info("Initializing NOAA Listener")
        logger.info(f"Location: {self.config.location_name} ({self.config.latitude}, {self.config.longitude})")
        
        # Validate configuration
        try:
            self.config.validate()
        except ValueError as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
        
        # Test database connection
        if not self.db.test_connection():
            logger.error("Database connection failed")
            return False
        
        # Initialize ingestor
        if not self.ingestor.initialize():
            logger.error("Ingestor initialization failed")
            return False
        
        logger.info("Initialization complete")
        return True
    
    def run_forecast_update(self) -> None:
        """Run a forecast data update cycle."""
        logger.info("Starting forecast update cycle")
        
        try:
            # Ingest all forecast types
            self.ingestor.ingest_forecasts()
            
            # Ingest current conditions
            self.ingestor.ingest_current_conditions()
            
            # Clean up old data
            self.ingestor.cleanup_old_data()
            
            logger.info("Forecast update cycle complete")
            
        except Exception as e:
            logger.error(f"Error during forecast update: {e}")
    
    def start(self) -> None:
        """Start the application with scheduled updates."""
        logger.info("Starting NOAA Listener")
        
        # Run initial forecast update
        self.run_forecast_update()
        
        # Schedule regular forecast updates
        self.scheduler.add_job(
            func=self.run_forecast_update,
            trigger=IntervalTrigger(minutes=self.config.forecast_update_interval),
            id='forecast_update',
            name='Fetch forecast data',
            replace_existing=True
        )
        
        logger.info(f"Scheduled forecast updates every {self.config.forecast_update_interval} minutes")
        
        # Start the scheduler
        try:
            logger.info("Scheduler started, press Ctrl+C to exit")
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")
    
    def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        logger.info("Shutting down NOAA Listener")
        
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        
        self.ingestor.close()
        logger.info("Shutdown complete")


def main():
    """Main entry point."""
    try:
        app = NOAAListener()
        
        if not app.initialize():
            logger.error("Failed to initialize application")
            sys.exit(1)
        
        app.start()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
