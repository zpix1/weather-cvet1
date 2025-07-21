"""API client for weather data fetching."""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from config import config


class HomeAssistantClient:
    """Client for interacting with weather data API."""

    def __init__(self):
        """Initialize the weather data client."""
        self.base_url = config.HOME_ASSISTANT_URL.rstrip("/")
        self.token = config.HOME_ASSISTANT_TOKEN
        self.sensor_entity = config.HOME_ASSISTANT_SENSOR
        self.humidity_sensor_entity = config.HOME_ASSISTANT_SENSOR_HUMIDITY

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def test_connection(self) -> bool:
        """Test connection to data source."""
        try:
            response = requests.get(
                f"{self.base_url}/api/", headers=self.headers, timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to connect to data source: {e}")
            return False

    def get_entity_state(self, entity_id: str = None) -> Optional[Dict[str, Any]]:
        """Get current state of a specific entity."""
        entity_id = entity_id or self.sensor_entity
        try:
            response = requests.get(
                f"{self.base_url}/api/states/{entity_id}",
                headers=self.headers,
                timeout=10,
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get entity state: {response.status_code}")
                return None

        except Exception as e:
            print(f"Error fetching entity state: {e}")
            return None

    def get_entity_history(
        self, entity_id: str = None, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical data for an entity."""
        entity_id = entity_id or self.sensor_entity
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        try:
            # Format timestamps for HA API
            start_timestamp = start_time.isoformat()
            end_timestamp = end_time.isoformat()

            response = requests.get(
                f"{self.base_url}/api/history/period/{start_timestamp}",
                headers=self.headers,
                params={"filter_entity_id": entity_id, "end_time": end_timestamp},
                timeout=30,
            )

            if response.status_code == 200:
                history_data = response.json()
                # HA returns nested arrays, flatten for the specific entity
                if history_data and len(history_data) > 0:
                    return history_data[0]  # First (and should be only) entity
                return []
            else:
                print(f"Failed to get entity history: {response.status_code}")
                return []

        except Exception as e:
            print(f"Error fetching entity history: {e}")
            return []

    def get_humidity_state(self) -> Optional[Dict[str, Any]]:
        """Get current humidity sensor state."""
        return self.get_entity_state(self.humidity_sensor_entity)

    def get_humidity_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get humidity sensor historical data."""
        return self.get_entity_history(self.humidity_sensor_entity, hours)


# Global weather data client instance
ha_client = HomeAssistantClient()
