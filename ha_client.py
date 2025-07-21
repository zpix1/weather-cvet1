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

    def get_weather_forecast(
        self, entity_id: str = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get weather forecast data."""
        entity_id = entity_id or self.sensor_entity
        try:
            # Try to get forecast from weather entity attributes
            state_data = self.get_entity_state(entity_id)
            if state_data and "attributes" in state_data:
                forecast = state_data["attributes"].get("forecast", [])
                if forecast:
                    return forecast

            # If no forecast in attributes, try to call weather.get_forecasts service
            response = requests.post(
                f"{self.base_url}/api/services/weather/get_forecasts",
                headers=self.headers,
                json={"type": "daily", "entity_id": entity_id},
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                if entity_id in result:
                    return result[entity_id].get("forecast", [])

            return []

        except Exception as e:
            print(f"Error fetching weather forecast: {e}")
            return []

    def get_humidity_state(self) -> Optional[Dict[str, Any]]:
        """Get current humidity sensor state."""
        return self.get_entity_state(self.humidity_sensor_entity)

    def get_humidity_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get humidity sensor historical data."""
        return self.get_entity_history(self.humidity_sensor_entity, hours)

    def bulk_fetch_weather_data(self, hours: int = 48) -> Dict[str, Any]:
        """Fetch comprehensive weather data including current state, history, and forecast."""
        print(f"Fetching weather data for the last {hours} hours...")

        data = {
            "current_state": None,
            "current_humidity": None,
            "history": [],
            "humidity_history": [],
            "forecast": [],
            "fetch_time": datetime.now().isoformat(),
            "success": False,
        }

        try:
            # Get current temperature state
            current_state = self.get_entity_state()
            if current_state:
                data["current_state"] = current_state
                print("✓ Temperature state fetched")

            # Get current humidity state
            current_humidity = self.get_humidity_state()
            if current_humidity:
                data["current_humidity"] = current_humidity
                print("✓ Humidity state fetched")

            # Get temperature historical data
            history = self.get_entity_history(hours=hours)
            if history:
                data["history"] = history
                print(f"✓ Temperature historical data fetched: {len(history)} records")

            # Get humidity historical data
            humidity_history = self.get_humidity_history(hours=hours)
            if humidity_history:
                data["humidity_history"] = humidity_history
                print(
                    f"✓ Humidity historical data fetched: {len(humidity_history)} records"
                )

            # Get forecast
            forecast = self.get_weather_forecast()
            if forecast:
                data["forecast"] = forecast
                print(f"✓ Forecast data fetched: {len(forecast)} records")

            data["success"] = True
            print("✓ Weather data fetch completed successfully")

        except Exception as e:
            print(f"Error in bulk fetch: {e}")
            data["error"] = str(e)

        return data

    def get_all_weather_entities(self) -> List[Dict[str, Any]]:
        """Get all weather-related entities from data source."""
        try:
            response = requests.get(
                f"{self.base_url}/api/states", headers=self.headers, timeout=10
            )

            if response.status_code == 200:
                all_states = response.json()
                # Filter for weather-related entities
                weather_entities = []
                for state in all_states:
                    entity_id = state.get("entity_id", "")
                    if (
                        entity_id.startswith("weather.")
                        or entity_id.startswith("sensor.")
                        and any(
                            term in entity_id.lower()
                            for term in [
                                "weather",
                                "temperature",
                                "humidity",
                                "pressure",
                                "wind",
                            ]
                        )
                    ):
                        weather_entities.append(state)

                return weather_entities

            return []

        except Exception as e:
            print(f"Error fetching weather entities: {e}")
            return []


# Global weather data client instance
ha_client = HomeAssistantClient()
