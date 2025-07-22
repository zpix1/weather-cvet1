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
from flask import Flask, render_template, send_file, request
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import base64

# Set matplotlib timezone to Novosibirsk
matplotlib.rcParams['timezone'] = 'Asia/Novosibirsk'

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
        # Initialize user requests table
        self._init_user_requests_table()
    
    def _init_user_requests_table(self):
        """Initialize the user_requests table if it doesn't exist."""
        try:
            # Ensure the directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    ip_address TEXT NOT NULL,
                    method TEXT NOT NULL,
                    url TEXT NOT NULL,
                    user_agent TEXT,
                    referer TEXT
                )
            ''')
            
            # Create index for faster queries by timestamp and IP
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_requests_timestamp 
                ON user_requests(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_requests_ip_date 
                ON user_requests(ip_address, date(timestamp))
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error initializing user_requests table: {e}")
    
    def log_user_request(self, ip_address, method, url, user_agent=None, referer=None):
        """Log a user request to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Use UTC timestamp for consistency
            timestamp = datetime.now(pytz.UTC).isoformat()
            
            cursor.execute('''
                INSERT INTO user_requests (timestamp, ip_address, method, url, user_agent, referer)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, ip_address, method, url, user_agent, referer))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error logging user request: {e}")
    
    def get_daily_visitor_stats(self, days=30):
        """Get daily visitor statistics for the last N days."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get visitor stats grouped by date
            cursor.execute('''
                SELECT 
                    date(datetime(timestamp, 'localtime')) as visit_date,
                    COUNT(DISTINCT ip_address) as unique_visitors,
                    COUNT(*) as total_requests
                FROM user_requests
                WHERE datetime(timestamp) >= datetime('now', '-{} days')
                GROUP BY date(datetime(timestamp, 'localtime'))
                ORDER BY visit_date DESC
            '''.format(days))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'date': result[0],
                    'unique_visitors': result[1],
                    'total_requests': result[2]
                }
                for result in results
            ]
            
        except Exception as e:
            print(f"Error getting daily visitor stats: {e}")
            return []
    
    def format_relative_time(self, timestamp):
        """Format a timestamp as relative time (e.g., '5 minutes ago', '2 hours ago')."""
        if not timestamp:
            return None
            
        now = datetime.now(self.tz)
        diff = now - timestamp
        
        # Handle future times (shouldn't happen, but just in case)
        if diff.total_seconds() < 0:
            return "только что"
        
        total_seconds = int(diff.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds} сек. назад" if total_seconds != 1 else "1 сек. назад"
        elif total_seconds < 3600:  # Less than 1 hour
            minutes = total_seconds // 60
            return f"{minutes} мин. назад" if minutes != 1 else "1 мин. назад"
        elif total_seconds < 86400:  # Less than 1 day
            hours = total_seconds // 3600
            return f"{hours} ч. назад" if hours != 1 else "1 ч. назад"
        elif total_seconds < 2592000:  # Less than 30 days
            days = total_seconds // 86400
            return f"{days} дн. назад" if days != 1 else "1 дн. назад"
        else:
            months = total_seconds // 2592000
            return f"{months} мес. назад" if months != 1 else "1 мес. назад"
    
    def get_latest_data(self):
        """Fetch the latest temperature and humidity data from the database."""
        try:
            # Ensure the directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get latest temperature
            cursor.execute('''
                SELECT value, timestamp
                FROM temperature_data
                ORDER BY datetime(timestamp) DESC
                LIMIT 1
            ''')
            temp_result = cursor.fetchone()
            
            # Get latest humidity
            cursor.execute('''
                SELECT value, timestamp
                FROM humidity_data
                ORDER BY datetime(timestamp) DESC
                LIMIT 1
            ''')
            humidity_result = cursor.fetchone()
            
            conn.close()
            
            if temp_result or humidity_result:
                temperature = round(temp_result[0], 1) if temp_result else None
                humidity = round(humidity_result[0], 1) if humidity_result else None
                
                # Use the most recent timestamp for last_update
                temp_time = None
                humidity_time = None
                
                if temp_result:
                    temp_timestamp_str = temp_result[1]
                    if isinstance(temp_timestamp_str, str):
                        temp_time = datetime.fromisoformat(temp_timestamp_str)
                    else:
                        temp_time = temp_timestamp_str
                    # Handle both timezone-aware and naive timestamps
                    if temp_time.tzinfo is None:
                        temp_time = pytz.UTC.localize(temp_time)
                    else:
                        temp_time = temp_time.astimezone(pytz.UTC)
                
                if humidity_result:
                    humidity_timestamp_str = humidity_result[1]
                    if isinstance(humidity_timestamp_str, str):
                        humidity_time = datetime.fromisoformat(humidity_timestamp_str)
                    else:
                        humidity_time = humidity_timestamp_str
                    # Handle both timezone-aware and naive timestamps
                    if humidity_time.tzinfo is None:
                        humidity_time = pytz.UTC.localize(humidity_time)
                    else:
                        humidity_time = humidity_time.astimezone(pytz.UTC)
                
                # Use the most recent timestamp
                latest_time = None
                if temp_time and humidity_time:
                    latest_time = max(temp_time, humidity_time)
                elif temp_time:
                    latest_time = temp_time
                elif humidity_time:
                    latest_time = humidity_time
                
                if latest_time:
                    local_time = latest_time.astimezone(self.tz)
                    last_update = local_time.strftime('%Y-%m-%d %H:%M:%S %Z')
                    last_update_relative = self.format_relative_time(local_time)
                    last_update_full = last_update
                else:
                    last_update = None
                    last_update_relative = None
                    last_update_full = None
                
                return {
                    'temperature': temperature,
                    'humidity': humidity,
                    'last_update': last_update,
                    'last_update_relative': last_update_relative,
                    'last_update_full': last_update_full,
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
            # Log the actual error for debugging but don't expose details to users
            print(f"Database error in get_latest_data: {e}")
            return {
                'temperature': None,
                'humidity': None,
                'last_update': None,
                'error': 'Database connection error. Please try again later.'
            }
        except Exception as e:
            # Log the actual error for debugging but don't expose details to users
            print(f"Error in get_latest_data: {e}")
            return {
                'temperature': None,
                'humidity': None,
                'last_update': None,
                'error': 'An error occurred while retrieving data. Please try again later.'
            }
    
    def get_data_by_date_range(self, data_type, start_date, end_date):
        """Fetch temperature or humidity data for a specific date range."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Validate and determine which table to query
            if data_type not in ['temperature', 'humidity']:
                raise ValueError(f"Invalid data_type: {data_type}")
            
            table_name = f"{data_type}_data"
            
            # Convert timezone-aware dates to UTC for database comparison
            # Database stores naive UTC timestamps
            start_utc = start_date.astimezone(pytz.UTC).replace(tzinfo=None)
            end_utc = end_date.astimezone(pytz.UTC).replace(tzinfo=None)

            print(f"Fetching {data_type} data from {start_utc} to {end_utc} in table {table_name}")
            
            # Use safe string formatting for table name since SQLite doesn't support parameterized table names
            # Use SQLite datetime() function for proper timestamp comparison
            query = f'''
                SELECT value, timestamp
                FROM {table_name}
                WHERE datetime(timestamp) >= datetime(?) AND datetime(timestamp) <= datetime(?)
                ORDER BY datetime(timestamp) ASC
            '''
            cursor.execute(query, (start_utc.isoformat(), end_utc.isoformat()))
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return None
                
            timestamps = []
            values = []
            
            for value, timestamp_str in results:
                # Parse timestamp - handle both timezone-aware and naive timestamps
                if isinstance(timestamp_str, str):
                    utc_time = datetime.fromisoformat(timestamp_str)
                else:
                    utc_time = timestamp_str
                
                # Handle both timezone-aware and naive timestamps
                if utc_time.tzinfo is None:
                    utc_time = pytz.UTC.localize(utc_time)
                else:
                    utc_time = utc_time.astimezone(pytz.UTC)
                
                local_time = utc_time.astimezone(self.tz)
                
                timestamps.append(local_time)
                values.append(value)
            
            # Extend the plot to the current time with the last known value
            if timestamps and values:
                last_timestamp = timestamps[-1]
                last_value = values[-1]
                
                # If the last data point is before the end time, add a point at end time
                if last_timestamp < end_date:
                    timestamps.append(end_date)
                    values.append(last_value)
            
            return {
                'timestamps': timestamps,
                'values': values
            }
            
        except Exception as e:
            # Log the actual error for debugging but don't expose details to users
            print(f"Error fetching {data_type} data: {e}")
            return None
    
    def get_date_range_for_period(self, period):
        """Get start and end dates for a given period."""
        # Validate period parameter
        if period not in ['24h', 'week', 'month']:
            period = '24h'  # Default to safe value
            
        now = datetime.now(self.tz)
        
        if period == '24h':
            start_date = now - timedelta(hours=24)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        else:
            # Default to 24 hours (should not reach here due to validation above)
            start_date = now - timedelta(hours=24)
        
        return start_date, now

    def _format_plot_axis(self, ax, start_date, end_date):
        """Format x-axis for plots with proper date/time formatting."""
        # Set x-axis limits to show the full date range with no gaps
        ax.set_xlim(start_date, end_date)
        
        # Format x-axis based on date range
        date_diff = (end_date - start_date).days
        if date_diff <= 1:
            # Less than or equal to 1 day - show hours
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, date_diff * 4)))
        elif date_diff <= 7:
            # 1-7 days - show days and hours
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        else:
            # More than 7 days - show just dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, date_diff // 7)))
        
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    def _save_plot_to_buffer(self, fig):
        """Save matplotlib figure to bytes buffer."""
        plt.tight_layout()
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        return img_buffer

    def generate_plot(self, data_type, start_date, end_date):
        """Generate a plot for the specified data type and date range."""
        if data_type == 'temp_hum':
            return self.generate_combined_plot(start_date, end_date)
        
        data = self.get_data_by_date_range(data_type, start_date, end_date)
        if not data:
            return self.generate_no_data_plot(f"N/A")
            
        # Calculate statistics
        values = data['values']
        mean_val = sum(values) / len(values)
        min_val = min(values)
        max_val = max(values)
        
        # Create the plot
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Determine plot properties based on data type
        if data_type == 'temperature':
            color = 'red'
            ylabel = ''
            unit = '°C'
            title = f'Температура, {unit} (с {start_date.strftime("%Y-%m-%d")} до {end_date.strftime("%Y-%m-%d")})'
        elif data_type == 'humidity':
            color = 'blue'
            ylabel = ''
            unit = '%'
            title = f'Влажность, {unit} (с {start_date.strftime("%Y-%m-%d")} до {end_date.strftime("%Y-%m-%d")})'
        else:
            color = 'black'
            ylabel = 'Значение'
            unit = ''
            title = f'{data_type} (с {start_date.strftime("%Y-%m-%d")} до {end_date.strftime("%Y-%m-%d")})'

        # Plot the data with horizontal connections between points
        ax.plot(data['timestamps'], data['values'], color=color, linewidth=2, drawstyle='steps-post')
        
        # Add horizontal lines for mean, min, max
        ax.axhline(y=mean_val, color='orange', linestyle=':', alpha=1, linewidth=1, label=f'Среднее: {mean_val:.1f}{unit}')
        ax.axhline(y=min_val, color='lightblue', linestyle='-', alpha=1, linewidth=1, label=f'Мин: {min_val:.1f}{unit}')
        ax.axhline(y=max_val, color='lightcoral', linestyle='-', alpha=1, linewidth=1, label=f'Макс: {max_val:.1f}{unit}')
        
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=10)
        
        # Format axis and save
        self._format_plot_axis(ax, start_date, end_date)
        return self._save_plot_to_buffer(fig)

    def generate_combined_plot(self, start_date, end_date):
        """Generate a combined plot showing both temperature and humidity."""
        # Get data for both temperature and humidity
        temp_data = self.get_data_by_date_range('temperature', start_date, end_date)
        humidity_data = self.get_data_by_date_range('humidity', start_date, end_date)
        
        if not temp_data and not humidity_data:
            return self.generate_no_data_plot("Нет данных для отображения")
        
        # Create the plot with dual y-axes
        fig, ax1 = plt.subplots(figsize=(12, 8))
        ax2 = ax1.twinx()
        
        # Plot humidity first (so it appears below temperature visually)
        if humidity_data:
            humidity_values = humidity_data['values']
            humidity_mean = sum(humidity_values) / len(humidity_values)
            
            ax2.plot(humidity_data['timestamps'], humidity_values, 
                    color='lightblue', linewidth=1, drawstyle='steps-post', 
                    alpha=0.7, label=f'Влажность (сред: {humidity_mean:.1f}%)')
            
            ax2.set_ylabel('Влажность, %', color='blue', fontsize=12)
            ax2.tick_params(axis='y', labelcolor='blue')
            
            # Set humidity y-axis limits to create visual hierarchy
            humidity_min, humidity_max = min(humidity_values), max(humidity_values)
            humidity_range = humidity_max - humidity_min
            ax2.set_ylim(humidity_min - humidity_range * 0.1, humidity_max + humidity_range * 0.1)
        
        # Plot temperature on top (visually dominant)
        if temp_data:
            temp_values = temp_data['values']
            temp_mean = sum(temp_values) / len(temp_values)
            
            ax1.plot(temp_data['timestamps'], temp_values, 
                    color='red', linewidth=1, drawstyle='steps-post', 
                    label=f'Температура (сред: {temp_mean:.1f}°C)')
            
            ax1.set_ylabel('Температура, °C', color='red', fontsize=12)
            ax1.tick_params(axis='y', labelcolor='red')
            
            # Set temperature y-axis limits
            temp_min, temp_max = min(temp_values), max(temp_values)
            temp_range = temp_max - temp_min
            ax1.set_ylim(temp_min - temp_range * 0.1, temp_max + temp_range * 0.1)
        
        # Set title
        title = f'Температура и влажность (с {start_date.strftime("%Y-%m-%d")} до {end_date.strftime("%Y-%m-%d")})'
        ax1.set_title(title, fontsize=14)
        
        # Add grid and legend
        ax1.grid(True, alpha=0.3)
        
        # Combine legends from both axes, with temperature first
        lines1 = ax1.get_lines()
        lines2 = ax2.get_lines()
        labels1 = [l.get_label() for l in lines1]
        labels2 = [l.get_label() for l in lines2]
        
        if lines1 or lines2:
            # Put temperature legend first (top), then humidity (bottom)
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=10)
        
        # Format axis and save using shared methods
        self._format_plot_axis(ax1, start_date, end_date)
        return self._save_plot_to_buffer(fig)

    def generate_no_data_plot(self, message):
        """Generate a plot showing no data message."""
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        return self._save_plot_to_buffer(fig)

def get_client_ip():
    """Get the real client IP address, considering proxy headers."""
    # Check for X-Forwarded-For header (common with proxies/load balancers)
    if 'X-Forwarded-For' in request.headers:
        # X-Forwarded-For can contain multiple IPs, get the first one
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    # Check for X-Real-IP header (nginx proxy)
    elif 'X-Real-IP' in request.headers:
        return request.headers['X-Real-IP']
    # Fallback to remote_addr
    else:
        return request.remote_addr

def log_request_info():
    """Log client IP and request headers."""
    client_ip = get_client_ip()
    headers_str = "; ".join([f"{name}={value}" for name, value in request.headers])
    print(f"Request: IP={client_ip} Method={request.method} URL={request.url} Headers=[{headers_str}]")
    
    # Also log to database
    server = WeatherWebServer()
    user_agent = request.headers.get('User-Agent')
    referer = request.headers.get('Referer')
    server.log_user_request(client_ip, request.method, request.url, user_agent, referer)

@app.route('/')
def index():
    """Main route that displays the weather data."""
    log_request_info()
    
    server = WeatherWebServer()
    data = server.get_latest_data()
    
    # Get plot parameters from query string
    plot_type = request.args.get('plot_type', 'temperature')
    period = request.args.get('period', '24h')
    
    # Validate plot_type parameter
    if plot_type not in ['temperature', 'humidity', 'temp_hum']:
        plot_type = 'temperature'  # Default to safe value
    
    # Validate period parameter
    if period not in ['24h', 'week', 'month']:
        period = '24h'  # Default to safe value
    
    # Add plot parameters to template data
    data['plot_type'] = plot_type
    data['period'] = period
    
    return render_template('index.html', **data)

@app.route('/plot/<data_type>')
def plot(data_type):
    """Route that serves plots with period parameter."""
    log_request_info()
    
    server = WeatherWebServer()
    
    # Get period parameter
    period = request.args.get('period', '24h')
    
    # Validate period parameter
    if period not in ['24h', 'week', 'month']:
        period = '24h'  # Default to safe value
    
    # Validate data type
    if data_type not in ['temperature', 'humidity', 'temp_hum']:
        return "Invalid data type. Use 'temperature', 'humidity', or 'temp_hum'", 400
    
    # Get date range for the period
    start_date, end_date = server.get_date_range_for_period(period)
    
    # Generate plot
    plot_buffer = server.generate_plot(data_type, start_date, end_date)
    
    return send_file(plot_buffer, mimetype='image/png')

@app.route('/users')
def users():
    """Route that shows daily visitor statistics."""
    log_request_info()
    
    server = WeatherWebServer()
    
    # Get number of days from query parameter (default 30)
    try:
        days = int(request.args.get('days', 30))
        if days < 1 or days > 365:
            days = 30  # Default to safe value
    except ValueError:
        days = 30  # Default to safe value
    
    # Get visitor statistics
    stats = server.get_daily_visitor_stats(days)
    
    # Calculate totals
    total_unique_visitors = len(set()) if not stats else len(stats)
    total_requests = sum(stat['total_requests'] for stat in stats)
    total_unique_ips = 0
    
    # Get total unique IPs across all days
    try:
        conn = sqlite3.connect(server.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(DISTINCT ip_address) 
            FROM user_requests
            WHERE datetime(timestamp) >= datetime('now', '-{} days')
        '''.format(days))
        result = cursor.fetchone()
        total_unique_ips = result[0] if result else 0
        conn.close()
    except Exception as e:
        print(f"Error getting total unique IPs: {e}")
    
    # Prepare data for template
    template_data = {
        'stats': stats,
        'days': days,
        'total_unique_visitors': total_unique_ips,
        'total_requests': total_requests,
        'period_start': (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d') if stats else None,
        'period_end': datetime.now().strftime('%Y-%m-%d')
    }
    
    return render_template('users.html', **template_data)

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
