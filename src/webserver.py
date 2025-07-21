#!/usr/bin/env python3
"""
Web server that displays current temperature and humidity data from SQLite database.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import sys
import pytz
from flask import Flask, render_template, send_file
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import base64

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
            # Ensure the directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
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
    
    def get_24h_data(self):
        """Fetch the last 24 hours of temperature and humidity data."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get data from the last 24 hours
            now = datetime.now(self.tz)
            yesterday = now - timedelta(hours=24)
            
            cursor.execute('''
                SELECT temperature, humidity, timestamp
                FROM sensor_data
                WHERE datetime(timestamp) >= datetime(?)
                ORDER BY timestamp ASC
            ''', (yesterday.astimezone(pytz.UTC).isoformat(),))
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return None
                
            timestamps = []
            temperatures = []
            humidities = []
            
            for temp, hum, timestamp_str in results:
                # Parse timestamp and convert to local timezone
                utc_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if utc_time.tzinfo is None:
                    utc_time = pytz.UTC.localize(utc_time)
                local_time = utc_time.astimezone(self.tz)
                
                timestamps.append(local_time)
                temperatures.append(temp)
                humidities.append(hum)
            
            return {
                'timestamps': timestamps,
                'temperatures': temperatures,
                'humidities': humidities
            }
            
        except Exception as e:
            print(f"Error fetching 24h data: {e}")
            return None
    
    def generate_plot(self):
        """Generate a plot of the last 24 hours data."""
        data = self.get_24h_data()
        if not data:
            return None
            
        # Create the plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        fig.suptitle('Weather Data - Last 24 Hours', fontsize=16, fontweight='bold')
        
        # Temperature plot
        ax1.plot(data['timestamps'], data['temperatures'], 'r-', linewidth=2, label='Temperature')
        ax1.set_ylabel('Temperature (°C)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.set_title('Temperature', fontsize=14)
        
        # Humidity plot
        ax2.plot(data['timestamps'], data['humidities'], 'b-', linewidth=2, label='Humidity')
        ax2.set_ylabel('Humidity (%)', fontsize=12)
        ax2.set_xlabel('Time', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.set_title('Humidity', fontsize=14)
        
        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax2.xaxis.set_major_locator(mdates.HourLocator(interval=4))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save to bytes
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        return img_buffer

@app.route('/')
def index():
    """Main route that displays the weather data."""
    server = WeatherWebServer()
    data = server.get_latest_data()
    
    # Add plot URL if data is available
    if not data.get('error'):
        data['plot_url'] = '/plot'
    
    return render_template('index.html', **data)

@app.route('/plot')
def plot():
    """Route that serves the 24-hour plot."""
    server = WeatherWebServer()
    plot_buffer = server.generate_plot()
    
    if plot_buffer:
        return send_file(plot_buffer, mimetype='image/png')
    else:
        # Return a simple "no data" image
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, 'No data available for the last 24 hours', 
                ha='center', va='center', fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        return send_file(img_buffer, mimetype='image/png')

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
