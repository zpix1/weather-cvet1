# Weather Monitor

A simple Python application that fetches temperature and humidity sensor data from Home Assistant and displays it via a web interface.

## Files

- `src/loader.py` - Fetches sensor data from Home Assistant and stores it in SQLite database
- `src/webserver.py` - Web server that displays the latest sensor data
- `.env` - Configuration file with Home Assistant credentials and settings

## Setup

1. Make sure you have uv installed. If not, install it:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies:
```bash
uv sync
```

3. Configure your Home Assistant credentials in `.env` file:
```
HOME_ASSISTANT_TOKEN=your_token_here
HOME_ASSISTANT_SENSOR_TEMPERATURE=sensor.your_temp_sensor
HOME_ASSISTANT_SENSOR_HUMIDITY=sensor.your_humidity_sensor
HOME_ASSISTANT_API_BASE=https://your-ha-instance.com/
FLASK_PORT=3300
```

## Usage

### 1. Run the data loader
```bash
uv run python src/loader.py
```
This fetches the current temperature and humidity from Home Assistant and stores it in `weather_data.db`.

### 2. Start the web server
```bash
uv run python src/webserver.py
```
This starts a web server on the configured port (default: 3300).

### 3. View the data
Open your browser to `http://localhost:3300` to see the current temperature and humidity data with Novosibirsk timezone.

## Features

- Fetches data from Home Assistant sensors
- Stores data in SQLite database with timestamps
- Beautiful responsive web interface
- Displays temperature and humidity with last update time
- Auto-refresh every 5 minutes
- Timezone support for Novosibirsk (Asia/Novosibirsk)

## Automation

You can set up a cron job to run the loader periodically:
```bash
# Run every 5 minutes
*/5 * * * * /path/to/python /path/to/src/loader.py
```
