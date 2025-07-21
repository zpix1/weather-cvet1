"""Database management for weather data storage."""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import config


class WeatherDatabase:
    """Manages SQLite database for weather data storage."""

    def __init__(self, db_path: str = None):
        """Initialize database connection and create tables."""
        self.db_path = db_path or config.DATABASE_PATH
        self.init_database()

    def init_database(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create weather_data table with comprehensive schema
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS weather_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    entity_id TEXT NOT NULL,
                    state TEXT,
                    temperature REAL,
                    humidity REAL,
                    pressure REAL,
                    wind_speed REAL,
                    wind_direction REAL,
                    visibility REAL,
                    weather_condition TEXT,
                    forecast_data TEXT,  -- JSON string for forecast data
                    attributes TEXT,     -- JSON string for all attributes
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create index for faster queries
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON weather_data(timestamp)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entity_timestamp 
                ON weather_data(entity_id, timestamp)
            """
            )

            # Create metadata table for tracking last updates
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()

    def insert_weather_data(self, data: Dict[str, Any]) -> bool:
        """Insert weather data into the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Extract common weather attributes
                attributes = data.get("attributes", {})
                entity_id = data.get("entity_id", "")
                state_value = data.get("state")

                # Map sensor values to correct columns based on entity_id
                temperature_val = None
                humidity_val = None

                if "temperatura" in entity_id.lower():
                    # Temperature sensor - put state value in temperature column
                    try:
                        temperature_val = (
                            float(state_value) if state_value is not None else None
                        )
                    except (ValueError, TypeError):
                        temperature_val = None
                elif (
                    "vlazhnost" in entity_id.lower() or "humidity" in entity_id.lower()
                ):
                    # Humidity sensor - put state value in humidity column
                    try:
                        humidity_val = (
                            float(state_value) if state_value is not None else None
                        )
                    except (ValueError, TypeError):
                        humidity_val = None
                else:
                    # Fall back to attributes for other sensors
                    temperature_val = attributes.get("temperature")
                    humidity_val = attributes.get("humidity")

                cursor.execute(
                    """
                    INSERT INTO weather_data (
                        timestamp, entity_id, state, temperature, humidity, 
                        pressure, wind_speed, wind_direction, visibility,
                        weather_condition, forecast_data, attributes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data.get("last_updated", datetime.now().isoformat()),
                        entity_id,
                        state_value,
                        temperature_val,
                        humidity_val,
                        attributes.get("pressure"),
                        attributes.get("wind_speed"),
                        attributes.get("wind_bearing"),
                        attributes.get("visibility"),
                        attributes.get("weather"),
                        json.dumps(attributes.get("forecast", [])),
                        json.dumps(attributes),
                    ),
                )

                conn.commit()
                return True

        except Exception as e:
            print(f"Error inserting weather data: {e}")
            return False

    def get_recent_weather_data(
        self, hours: int = 24, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get recent weather data from the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM weather_data 
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (hours, limit),
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_weather_data_range(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Get weather data within a specific date range."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM weather_data 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            """,
                (start_date, end_date),
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_latest_weather_data(self) -> Optional[Dict[str, Any]]:
        """Get the most recent weather data entry."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM weather_data 
                ORDER BY timestamp DESC 
                LIMIT 1
            """
            )

            row = cursor.fetchone()
            return dict(row) if row else None

    def update_metadata(self, key: str, value: str):
        """Update metadata key-value pair."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO metadata (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
                (key, value),
            )

            conn.commit()

    def get_metadata(self, key: str) -> Optional[str]:
        """Get metadata value by key."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT value FROM metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_data_stats(self) -> Dict[str, Any]:
        """Get statistics about stored data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get total count
            cursor.execute("SELECT COUNT(*) FROM weather_data")
            total_count = cursor.fetchone()[0]

            # Get date range
            cursor.execute(
                """
                SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest 
                FROM weather_data
            """
            )
            date_range = cursor.fetchone()

            # Get last update time
            last_update = self.get_metadata("last_fetch_time")

            return {
                "total_records": total_count,
                "earliest_record": date_range[0],
                "latest_record": date_range[1],
                "last_fetch_time": last_update,
            }


# Global database instance
db = WeatherDatabase()
