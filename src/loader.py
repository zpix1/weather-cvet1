#!/usr/bin/env python3
"""
Data loader that fetches temperature and humidity sensors from Home Assistant
and stores them in SQLite database.
"""

import os
import sqlite3
import requests
import json
from datetime import datetime
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
        """Initialize the SQLite database with the required table."""
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                temperature REAL,
                humidity REAL
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
    
    def store_data(self, temperature, humidity):
        """Store temperature and humidity data in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sensor_data (temperature, humidity)
            VALUES (?, ?)
        ''', (temperature, humidity))
        
        conn.commit()
        conn.close()
    
    def run(self):
        """Fetch sensor data and store it in the database."""
        print(f"Fetching sensor data at {datetime.now()}")
        
        # Fetch temperature and humidity
        temperature = self.fetch_sensor_state(self.temp_sensor)
        humidity = self.fetch_sensor_state(self.humidity_sensor)
        
        if temperature is not None and humidity is not None:
            self.store_data(temperature, humidity)
            print(f"Stored data: Temperature={temperature}°C, Humidity={humidity}%")
        else:
            print("Failed to fetch sensor data")
            return False
        
        return True
    
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
        
        # Check if we should run once or continuously
        run_mode = os.getenv('LOADER_MODE', 'continuous')
        
        if run_mode == 'once':
            success = loader.run()
            if success:
                print("Data loading completed successfully")
            else:
                print("Data loading failed")
                sys.exit(1)
        else:
            # Run continuously every 2 minutes
            loader.run_continuously(interval_minutes=2)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
