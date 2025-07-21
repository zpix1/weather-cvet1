#!/usr/bin/env python3
"""
Web server that displays current temperature and humidity data from SQLite database.
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
import sys
import pytz
from flask import Flask, render_template

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure Flask to use templates from src/templates
template_dir = Path(__file__).parent / 'templates'
app = Flask(__name__, template_folder=str(template_dir))

class WeatherWebServer:
    def __init__(self):
        # Use DATABASE_PATH env var if available (for Docker), otherwise use project root
        db_path_env = os.getenv('DATABASE_PATH')
        if db_path_env:
            self.db_path = Path(db_path_env)
        else:
            self.db_path = project_root / 'weather_data.db'
        # Novosibirsk timezone
        self.tz = pytz.timezone('Asia/Novosibirsk')
    
    def get_latest_data(self):
        """Fetch the latest temperature and humidity data from the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT temperature, humidity, timestamp
                FROM sensor_data
                ORDER BY timestamp DESC
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                temperature, humidity, timestamp_str = result
                
                # Parse timestamp and convert to Novosibirsk timezone
                utc_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if utc_time.tzinfo is None:
                    utc_time = pytz.UTC.localize(utc_time)
                
                local_time = utc_time.astimezone(self.tz)
                
                return {
                    'temperature': round(temperature, 1),
                    'humidity': round(humidity, 1),
                    'last_update': local_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
                    'error': None
                }
            else:
                return {
                    'temperature': None,
                    'humidity': None,
                    'last_update': None,
                    'error': 'No data available. Run the loader first.'
                }
                
        except sqlite3.Error as e:
            return {
                'temperature': None,
                'humidity': None,
                'last_update': None,
                'error': f'Database error: {e}'
            }
        except Exception as e:
            return {
                'temperature': None,
                'humidity': None,
                'last_update': None,
                'error': f'Error: {e}'
            }

@app.route('/')
def index():
    """Main route that displays the weather data."""
    server = WeatherWebServer()
    data = server.get_latest_data()
    
    return render_template('index.html', **data)

def main():
    """Main function to run the web server."""
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
        
        # Get port from environment or use default
        port = int(os.getenv('FLASK_PORT', 3300))
        
        print(f"Starting weather web server on port {port}")
        print(f"Open http://localhost:{port} in your browser")
        
        app.run(host='0.0.0.0', port=port, debug=True)
        
    except Exception as e:
        print(f"Error starting web server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
