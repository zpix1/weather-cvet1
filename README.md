# Weather Dashboard

A comprehensive weather monitoring system that integrates with Home Assistant to collect, store, and visualize weather data using SQLite and Plotly.

![Weather Dashboard](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 🌟 Features

- **Real-time weather monitoring** - Continuous data collection from Home Assistant
- **Historical data storage** - SQLite database for persistent weather history
- **Interactive visualizations** - Plotly charts for temperature, humidity, pressure, and wind speed
- **Modern web interface** - Responsive dashboard with status monitoring
- **Background data fetching** - Scheduled updates with configurable intervals
- **Performance optimized** - No API calls required for initial page load
- **Offline resilience** - Stores comprehensive data for when sensors go offline
- **Time tracking** - Displays time since last update in the UI

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Home Assistant instance with API access
- Weather sensor entity in Home Assistant

### Installation

1. **Clone and setup the project:**

   ```bash
   cd weather-cvet1
   ```

2. **Configure environment variables:**
   Create a `.env` file in the project root:

   ```env
   # Required: Home Assistant Configuration
   HOME_ASSISTANT_TOKEN=your_long_lived_access_token_here
   HOME_ASSISTANT_SENSOR=sensor.your_weather_sensor_entity_id

   # Optional: Database configuration
   DATABASE_PATH=weather_data.db

   # Optional: Update interval in seconds (default: 300 = 5 minutes)
   UPDATE_INTERVAL=300

   # Optional: Web server configuration
   FLASK_HOST=0.0.0.0
   FLASK_PORT=5000
   FLASK_DEBUG=False
   ```

3. **Install dependencies:**

   ```bash
   uv sync
   ```

4. **Run the application:**

   ```bash
   uv run python main.py
   ```

5. **Access the dashboard:**
   Open your browser to `http://localhost:5000`

## 🔧 Configuration

### Home Assistant Setup

1. **Create a Long-Lived Access Token:**

   - Go to your Home Assistant profile
   - Scroll down to "Long-Lived Access Tokens"
   - Click "CREATE TOKEN"
   - Copy the token to your `.env` file

2. **Find your weather sensor entity ID:**
   - Go to Developer Tools > States in Home Assistant
   - Find your weather sensor (e.g., `weather.home`, `sensor.temperature`)
   - Copy the entity ID to your `.env` file

### Environment Variables

| Variable                | Required | Default                 | Description                                                                  |
| ----------------------- | -------- | ----------------------- | ---------------------------------------------------------------------------- |
| `HOME_ASSISTANT_TOKEN`  | ✅       | -                       | Long-lived access token from Home Assistant                                  |
| `HOME_ASSISTANT_SENSOR` | ✅       | -                       | Entity ID of your weather sensor                                             |
| `HOME_ASSISTANT_URL`    | ✅       | `http://localhost:8123` | URL of your Home Assistant instance (also accepts `HOME_ASSISTANT_API_BASE`) |
| `DATABASE_PATH`         | ❌       | `weather_data.db`       | Path to SQLite database file                                                 |
| `UPDATE_INTERVAL`       | ❌       | `300`                   | Data fetch interval in seconds                                               |
| `FLASK_HOST`            | ❌       | `0.0.0.0`               | Web server host                                                              |
| `FLASK_PORT`            | ❌       | `5000`                  | Web server port                                                              |
| `FLASK_DEBUG`           | ❌       | `False`                 | Enable Flask debug mode                                                      |

## 🏗️ Architecture

### Components

- **`main.py`** - Application entry point with graceful startup/shutdown
- **`config.py`** - Configuration management and environment variable loading
- **`database.py`** - SQLite database operations and schema management
- **`ha_client.py`** - Home Assistant API client for weather data fetching
- **`data_fetcher.py`** - Background scheduler for continuous data collection
- **`app.py`** - Flask web application with REST API endpoints
- **`templates/index.html`** - Modern responsive web interface

### Data Flow

1. **Background Fetcher** collects weather data from Home Assistant API
2. **SQLite Database** stores historical weather records with timestamps
3. **Web API** serves current and historical data without external API calls
4. **Frontend** displays real-time charts and status information
5. **Scheduler** ensures continuous data collection with configurable intervals

### Database Schema

```sql
CREATE TABLE weather_data (
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
    forecast_data TEXT,  -- JSON string
    attributes TEXT,     -- JSON string
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 📊 Dashboard Features

### Real-time Metrics

- Current temperature, humidity, pressure, and wind speed
- Connection status indicators for Home Assistant and data fetcher
- Time since last update with human-readable formatting

### Interactive Charts

- **Temperature trends** over time
- **Humidity levels** with historical data
- **Pressure variations** for weather pattern analysis
- **Wind speed** monitoring
- Configurable time ranges (6 hours to 1 week)

### System Monitoring

- Database statistics and record counts
- Background job scheduling information
- Home Assistant connection status
- Force fetch capability for immediate updates

## 🛠️ API Endpoints

| Endpoint                  | Method | Description                                                   |
| ------------------------- | ------ | ------------------------------------------------------------- |
| `/`                       | GET    | Main dashboard page                                           |
| `/api/weather/current`    | GET    | Latest weather data with time since update                    |
| `/api/weather/history`    | GET    | Historical weather data (supports `hours` and `limit` params) |
| `/api/weather/forecast`   | GET    | Weather forecast data                                         |
| `/api/weather/chart-data` | GET    | Formatted data for Plotly charts                              |
| `/api/status`             | GET    | System status and statistics                                  |
| `/api/fetch`              | POST   | Force immediate data fetch                                    |

## 🔍 Troubleshooting

### Common Issues

1. **"HOME_ASSISTANT_TOKEN environment variable is required"**

   - Ensure your `.env` file exists and contains the required variables
   - Check that the token is valid and hasn't expired

2. **"Failed to connect to Home Assistant"**

   - Verify the Home Assistant URL is correct and accessible
   - Check that the API is enabled in Home Assistant
   - Ensure the token has the necessary permissions

3. **"No weather data available"**

   - Verify the sensor entity ID is correct
   - Check that the sensor is active and reporting data in Home Assistant
   - Try forcing a fetch using the dashboard button

4. **Charts not displaying**
   - Check browser console for JavaScript errors
   - Ensure there's historical data in the database
   - Try refreshing the page or clearing browser cache

### Logs and Debugging

- Enable debug mode by setting `FLASK_DEBUG=True` in your `.env` file
- Check console output for detailed error messages
- Use the system status page to monitor data fetcher health
- SQLite database can be inspected using any SQLite browser

## 📦 Dependencies

- **Flask** - Web framework
- **Plotly** - Interactive charting library
- **Requests** - HTTP client for Home Assistant API
- **APScheduler** - Background task scheduling
- **Pandas** - Data manipulation
- **Python-dotenv** - Environment variable management
- **SQLite3** - Database (built into Python)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Home Assistant community for the excellent automation platform
- Plotly team for the powerful visualization library
- Contributors to all the open-source dependencies
