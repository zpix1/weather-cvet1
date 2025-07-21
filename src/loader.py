#!/usr/bin/env python3
"""
Data loader that fetches temperature and humidity sensors from Home Assistant
and stores them in SQLite database.
"""

import os
import sqlite3
import requests
import json
import calendar
from datetime import datetime, timedelta
import sys
import time
from pathlib import Path

# Add the project root to the path so we can import from src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class HomeAssistantLoader:
    def __init__(self):
        # Load environment variables
        self.token = os.getenv('HOME_ASSISTANT_TOKEN')
        self.api_base = os.getenv('HOME_ASSISTANT_API_BASE')
        self.temp_sensor = os.getenv('HOME_ASSISTANT_SENSOR_TEMPERATURE')
        self.humidity_sensor = os.getenv('HOME_ASSISTANT_SENSOR_HUMIDITY')
        
        if not all([self.token, self.api_base, self.temp_sensor, self.humidity_sensor]):
            raise ValueError("Missing required environment variables. Please check your .env file.")
        
        # Ensure API base URL ends with /api
        if not self.api_base.endswith('/api'):
            self.api_base = self.api_base.rstrip('/') + '/api'
        
        # Use DATABASE_PATH env var if available (for Docker), otherwise use project root
        db_path_env = os.getenv('DATABASE_PATH')
        if db_path_env:
            self.db_path = Path(db_path_env)
        else:
            self.db_path = project_root / 'weather_data.db'
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with separate tables for temperature and humidity."""
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS temperature_data (
                timestamp DATETIME PRIMARY KEY,
                value REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS humidity_data (
                timestamp DATETIME PRIMARY KEY,
                value REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def fetch_sensor_state(self, entity_id):
        """Fetch the current state of a Home Assistant sensor."""
        url = f"{self.api_base}/states/{entity_id}"
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Return the state value as float
            return float(data['state'])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching sensor {entity_id}: {e}")
            return None
        except (ValueError, KeyError) as e:
            print(f"Error parsing sensor data for {entity_id}: {e}")
            return None
    
    def store_temperature(self, value, timestamp=None):
        """Store temperature data in the database with unique timestamp."""
        if timestamp is None:
            timestamp = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO temperature_data (timestamp, value)
                VALUES (?, ?)
            ''', (timestamp, value))
            
            conn.commit()
            return cursor.rowcount > 0  # Return True if row was inserted
        except sqlite3.Error as e:
            print(f"Database error storing temperature: {e}")
            return False
        finally:
            conn.close()
    
    def store_humidity(self, value, timestamp=None):
        """Store humidity data in the database with unique timestamp."""
        if timestamp is None:
            timestamp = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO humidity_data (timestamp, value)
                VALUES (?, ?)
            ''', (timestamp, value))
            
            conn.commit()
            return cursor.rowcount > 0  # Return True if row was inserted
        except sqlite3.Error as e:
            print(f"Database error storing humidity: {e}")
            return False
        finally:
            conn.close()
    
    def fetch_historical_data(self, entity_id, start_time, end_time, max_days=10):
        """Fetch historical data for a sensor from Home Assistant, splitting into chunks if needed."""
        all_historical_data = []
        current_start = start_time
        
        while current_start < end_time:
            # Calculate chunk end time (max_days from current_start or end_time, whichever is earlier)
            chunk_end = min(current_start + timedelta(days=max_days), end_time)
            
            print(f"Fetching {entity_id} data from {current_start.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}")
            
            url = f"{self.api_base}/history/period/{current_start.isoformat()}"
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            params = {
                'filter_entity_id': entity_id,
                'end_time': chunk_end.isoformat()
            }
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # Extract data points
                if data and len(data) > 0:
                    for state_change in data[0]:  # First entity's data
                        try:
                            timestamp_str = state_change['last_changed']
                            # Parse ISO format timestamp
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).replace(tzinfo=None)
                            value = float(state_change['state'])
                            all_historical_data.append((timestamp, value))
                        except (ValueError, KeyError) as e:
                            continue  # Skip invalid data points
                
                print(f"  Fetched {len(data[0]) if data and len(data) > 0 else 0} records")
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching historical data for {entity_id} ({current_start} to {chunk_end}): {e}")
            except Exception as e:
                print(f"Error parsing historical data for {entity_id} ({current_start} to {chunk_end}): {e}")
            
            # Move to next chunk
            current_start = chunk_end
            
            # Small delay to be nice to the API
            time.sleep(0.5)
        
        print(f"Total fetched for {entity_id}: {len(all_historical_data)} records")
        print("Last timestamp fetched:", all_historical_data[-1][0] if all_historical_data else "None")
        return all_historical_data
    
    def load_last_month_data(self):
        """Load data from last month and store it in the database."""
        now = datetime.now()
        start_time = (now - timedelta(days=30))
        end_time = now

        print(f"Loading data from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
        
        # Fetch historical data for both sensors
        print("Fetching temperature data...")
        temp_data = self.fetch_historical_data(self.temp_sensor, start_time, end_time)
        
        print("Fetching humidity data...")
        humidity_data = self.fetch_historical_data(self.humidity_sensor, start_time, end_time)
        
        # Store data using helper method
        print("Storing fetched data:")
        temp_stored, temp_skipped = self.store_sensor_data(temp_data, self.store_temperature, "Temperature")
        humidity_stored, humidity_skipped = self.store_sensor_data(humidity_data, self.store_humidity, "Humidity")

        print(f"Historical data loading completed:")
        
        # Print earliest dates stored
        earliest_temp = self.get_earliest_timestamp('temperature_data')
        earliest_humidity = self.get_earliest_timestamp('humidity_data')
        
        if earliest_temp:
            print(f"  Earliest temperature data: {earliest_temp.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("  No temperature data in database")
            
        if earliest_humidity:
            print(f"  Earliest humidity data: {earliest_humidity.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("  No humidity data in database")
        
        return temp_stored + humidity_stored

    def run(self):
        """Fetch recent historical data and store it in the database."""
        print(f"Fetching recent sensor data at {datetime.now()}")
        
        # Fetch last hour of data to get the most recent readings
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        # Fetch and store temperature data
        temp_data = self.fetch_historical_data(self.temp_sensor, start_time, end_time)
        temp_stored, _ = self.store_sensor_data(temp_data, self.store_temperature, "Temperature")
        
        # Fetch and store humidity data  
        humidity_data = self.fetch_historical_data(self.humidity_sensor, start_time, end_time)
        humidity_stored, _ = self.store_sensor_data(humidity_data, self.store_humidity, "Humidity")
        
        if temp_stored > 0 or humidity_stored > 0:
            print(f"Stored recent data - Temperature: {temp_stored}, Humidity: {humidity_stored}")
            return True
        else:
            print("No new data to store")
            return True  # Still return True as this is normal
    
    def run_continuously(self, interval_minutes=2):
        """Run the loader continuously at specified intervals."""
        print(f"Starting continuous data collection every {interval_minutes} minutes")
        print("Press Ctrl+C to stop")
        
        while True:
            try:
                success = self.run()
                if not success:
                    print("Data loading failed, will retry in next cycle")
                
                print(f"Waiting {interval_minutes} minutes until next run...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\nStopping data collection...")
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
                print(f"Will retry in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
    
    def get_earliest_timestamp(self, table_name):
        """Get the earliest timestamp from a given table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'SELECT MIN(timestamp) FROM {table_name}')
            result = cursor.fetchone()
            if result and result[0]:
                return datetime.fromisoformat(result[0]) if isinstance(result[0], str) else result[0]
            return None
        except sqlite3.Error as e:
            print(f"Database error getting earliest timestamp from {table_name}: {e}")
            return None
        finally:
            conn.close()

    def store_sensor_data(self, sensor_data, store_function, sensor_type):
        """Helper method to store sensor data and return statistics."""
        stored = 0
        skipped = 0
        
        for timestamp, value in sensor_data:
            success = store_function(value, timestamp)
            if success:
                stored += 1
            else:
                skipped += 1
        
        print(f"  {sensor_type} - Stored: {stored}, Skipped: {skipped}")
        return stored, skipped

def main():
    """Main function to run the loader."""
    try:
        # Load .env file
        env_path = project_root / '.env'
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
        
        loader = HomeAssistantLoader()
        
        # Always load last month's data first
        print("Loading historical data from last month...")
        loader.load_last_month_data()
        loader.run_continuously(interval_minutes=2)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
