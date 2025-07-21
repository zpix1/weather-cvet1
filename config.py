"""Configuration management for the weather website."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class."""

    # Home Assistant configuration
    HOME_ASSISTANT_TOKEN: str = os.getenv("HOME_ASSISTANT_TOKEN", "")
    HOME_ASSISTANT_SENSOR: str = os.getenv("HOME_ASSISTANT_SENSOR", "")
    HOME_ASSISTANT_SENSOR_HUMIDITY: str = os.getenv(
        "HOME_ASSISTANT_SENSOR_HUMIDITY", ""
    )
    HOME_ASSISTANT_URL: str = os.getenv(
        "HOME_ASSISTANT_URL",
        os.getenv("HOME_ASSISTANT_API_BASE", "http://localhost:8123"),
    )

    # Database configuration
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "weather_data.db")

    # Update interval in seconds (default: 5 minutes)
    UPDATE_INTERVAL: int = int(os.getenv("UPDATE_INTERVAL", "300"))

    # Flask configuration
    FLASK_HOST: str = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "8080"))
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        if not cls.HOME_ASSISTANT_TOKEN:
            raise ValueError("HOME_ASSISTANT_TOKEN environment variable is required")
        if not cls.HOME_ASSISTANT_SENSOR:
            raise ValueError("HOME_ASSISTANT_SENSOR environment variable is required")
        if not cls.HOME_ASSISTANT_SENSOR_HUMIDITY:
            raise ValueError(
                "HOME_ASSISTANT_SENSOR_HUMIDITY environment variable is required"
            )
        return True


# Global config instance
config = Config()
