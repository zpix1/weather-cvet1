"""Background data fetcher for continuous weather data collection."""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import config
from database import db
from ha_client import ha_client


class WeatherDataFetcher:
    """Manages background fetching and storage of weather data."""

    def __init__(self):
        """Initialize the data fetcher."""
        self.scheduler = BackgroundScheduler(daemon=True)
        self.is_running = False
        self.last_fetch_time = None
        self.fetch_lock = threading.Lock()

        # Configure jobs
        self.setup_jobs()

    def setup_jobs(self):
        """Set up scheduled jobs for data fetching."""
        # Regular weather data fetch
        self.scheduler.add_job(
            func=self.fetch_and_store_current_data,
            trigger=IntervalTrigger(seconds=config.UPDATE_INTERVAL),
            id="weather_fetch_job",
            name="Fetch current weather data",
            replace_existing=True,
        )

        # Comprehensive historical data fetch (every 12 hours to get month data)
        self.scheduler.add_job(
            func=self.fetch_and_store_historical_data,
            trigger=IntervalTrigger(hours=12),
            id="historical_fetch_job",
            name="Fetch historical weather data",
            replace_existing=True,
        )

    def start(self):
        """Start the background data fetcher."""
        if not self.is_running:
            try:
                # Validate configuration
                config.validate()

                # Test connection
                if not ha_client.test_connection():
                    print("⚠️  Warning: Could not connect to data source")
                    print("Data fetching will continue to retry...")

                # Start scheduler
                self.scheduler.start()
                self.is_running = True

                print(
                    f"✓ Data fetcher started (update interval: {config.UPDATE_INTERVAL}s)"
                )

                # Schedule initial fetch to happen after 5 seconds (non-blocking)
                self.scheduler.add_job(
                    func=self.initial_data_fetch,
                    trigger="date",
                    run_date=datetime.now() + timedelta(seconds=5),
                    id="initial_fetch_job",
                    name="Initial data fetch",
                    replace_existing=True,
                )
                print("📅 Initial data fetch scheduled for 5 seconds after startup")

            except Exception as e:
                print(f"Failed to start data fetcher: {e}")
                raise

    def stop(self):
        """Stop the background data fetcher."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            print("✓ Data fetcher stopped")

    def initial_data_fetch(self):
        """Perform initial comprehensive data fetch for the last month."""
        print("🔄 Performing background initial data fetch...")

        # Check if we already have recent data
        latest_data = db.get_latest_weather_data()
        if latest_data:
            timestamp_str = (
                latest_data["timestamp"].replace("Z", "+00:00")
                if "Z" in latest_data["timestamp"]
                else latest_data["timestamp"]
            )
            last_timestamp = datetime.fromisoformat(timestamp_str)
            # Ensure both datetimes are timezone-naive for comparison
            if last_timestamp.tzinfo is not None:
                last_timestamp = last_timestamp.replace(tzinfo=None)
            current_time = datetime.now().replace(tzinfo=None)
            time_diff = current_time - last_timestamp

            if time_diff.total_seconds() < config.UPDATE_INTERVAL * 2:
                print(
                    f"✓ Recent data found (last update: {time_diff.total_seconds():.0f}s ago)"
                )
                return

        # Fetch comprehensive data for the last month
        self.fetch_and_store_historical_data(hours=720)  # 30 days of data
        self.fetch_and_store_current_data()
        print("✅ Background initial data fetch completed")

    def fetch_and_store_current_data(self):
        """Fetch and store current weather data."""
        with self.fetch_lock:
            try:
                print("Fetching current weather data...")

                # Get current temperature state
                current_state = ha_client.get_entity_state()
                if current_state:
                    success = db.insert_weather_data(current_state)
                    if success:
                        print("✓ Temperature data stored")
                    else:
                        print("⚠️  Failed to store temperature data")
                else:
                    print("⚠️  Failed to fetch temperature data")

                # Get current humidity state
                current_humidity = ha_client.get_humidity_state()
                if current_humidity:
                    success = db.insert_weather_data(current_humidity)
                    if success:
                        print("✓ Humidity data stored")
                    else:
                        print("⚠️  Failed to store humidity data")
                else:
                    print("⚠️  Failed to fetch humidity data")

                self.last_fetch_time = datetime.now()
                db.update_metadata("last_fetch_time", self.last_fetch_time.isoformat())

            except Exception as e:
                print(f"Error in current data fetch: {e}")

    def fetch_and_store_historical_data(self, hours: int = 720):
        """Fetch and store historical weather data for the last month."""
        with self.fetch_lock:
            try:
                print(f"Fetching historical weather data ({hours} hours)...")

                # Get temperature historical data
                historical_data = ha_client.get_entity_history(hours=hours)
                if historical_data:
                    stored_count = 0
                    for data_point in historical_data:
                        if db.insert_weather_data(data_point):
                            stored_count += 1

                    print(
                        f"✓ Stored {stored_count}/{len(historical_data)} temperature records"
                    )
                else:
                    print("⚠️  No temperature historical data available")

                # Get humidity historical data
                humidity_data = ha_client.get_humidity_history(hours=hours)
                if humidity_data:
                    stored_count = 0
                    for data_point in humidity_data:
                        if db.insert_weather_data(data_point):
                            stored_count += 1

                    print(
                        f"✓ Stored {stored_count}/{len(humidity_data)} humidity records"
                    )

                    # Update metadata
                    db.update_metadata(
                        "last_historical_fetch", datetime.now().isoformat()
                    )
                else:
                    print("⚠️  No humidity historical data available")

            except Exception as e:
                print(f"Error in historical data fetch: {e}")

    def fetch_forecast_data(self):
        """Fetch and store forecast data."""
        try:
            print("Fetching forecast data...")

            forecast_data = ha_client.get_weather_forecast()
            if forecast_data:
                # Store forecast as metadata (since it's forward-looking)

                db.update_metadata("latest_forecast", json.dumps(forecast_data))
                print(f"✓ Stored forecast data ({len(forecast_data)} periods)")
            else:
                print("⚠️  No forecast data available")

        except Exception as e:
            print(f"Error in forecast data fetch: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get status information about the data fetcher."""
        stats = db.get_data_stats()

        return {
            "is_running": self.is_running,
            "last_fetch_time": (
                self.last_fetch_time.isoformat() if self.last_fetch_time else None
            ),
            "update_interval": config.UPDATE_INTERVAL,
            "database_stats": stats,
        }


# Global data fetcher instance
data_fetcher = WeatherDataFetcher()


def start_data_fetcher():
    """Start the global data fetcher."""
    data_fetcher.start()


def stop_data_fetcher():
    """Stop the global data fetcher."""
    data_fetcher.stop()
