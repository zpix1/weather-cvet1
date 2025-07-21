# Weather Dashboard - Docker Setup

This guide explains how to run the Weather Dashboard using Docker.

## Prerequisites

- Docker and Docker Compose installed
- Access to a Home Assistant instance with sensors for temperature and humidity

## Quick Start

### 1. Create Environment File

Create a `.env` file in the project root with your Home Assistant configuration:

```bash
# Home Assistant Configuration (REQUIRED)
HOME_ASSISTANT_TOKEN=your_home_assistant_long_lived_access_token
HOME_ASSISTANT_SENSOR=sensor.your_temperature_sensor
HOME_ASSISTANT_SENSOR_HUMIDITY=sensor.your_humidity_sensor
HOME_ASSISTANT_URL=https://your-home-assistant-url.com

# Flask Configuration (Optional - defaults provided)
FLASK_HOST=0.0.0.0
FLASK_PORT=8080
FLASK_DEBUG=false

# Database Configuration (Optional - defaults provided)
DATABASE_PATH=/app/data/weather_data.db
UPDATE_INTERVAL=300
```

### 2. Run with Docker Compose (Recommended)

```bash
docker-compose up -d
```

The application will be available at `http://localhost:3300`

### 3. Run with Docker Only

```bash
# Build the image
docker build -t weather-dashboard .

# Run the container
docker run -d \
  --name weather-dashboard \
  -p 3300:8080 \
  -e HOME_ASSISTANT_TOKEN="your_token" \
  -e HOME_ASSISTANT_SENSOR="sensor.your_temperature_sensor" \
  -e HOME_ASSISTANT_SENSOR_HUMIDITY="sensor.your_humidity_sensor" \
  -e HOME_ASSISTANT_URL="https://your-home-assistant-url.com" \
  -v weather_data:/app/data \
  weather-dashboard
```

## Environment Variables

### Required Variables

| Variable                         | Description                                 | Example                                     |
| -------------------------------- | ------------------------------------------- | ------------------------------------------- |
| `HOME_ASSISTANT_TOKEN`           | Long-lived access token from Home Assistant | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`   |
| `HOME_ASSISTANT_SENSOR`          | Temperature sensor entity ID                | `sensor.pushok_hardware_pok005_temperatura` |
| `HOME_ASSISTANT_SENSOR_HUMIDITY` | Humidity sensor entity ID                   | `sensor.pushok_hardware_pok005_vlazhnost`   |
| `HOME_ASSISTANT_URL`             | Home Assistant base URL                     | `https://your-ha-instance.com`              |

### Optional Variables

| Variable          | Default                     | Description                    |
| ----------------- | --------------------------- | ------------------------------ |
| `FLASK_HOST`      | `0.0.0.0`                   | Flask server host              |
| `FLASK_PORT`      | `8080`                      | Flask server port (internal)   |
| `FLASK_DEBUG`     | `false`                     | Enable debug mode              |
| `DATABASE_PATH`   | `/app/data/weather_data.db` | SQLite database path           |
| `UPDATE_INTERVAL` | `300`                       | Data fetch interval in seconds |

## Data Persistence

The Docker setup uses a named volume `weather_data` to persist the SQLite database across container restarts.

## Health Checks

The container includes health checks that verify the application is responding correctly.

## Troubleshooting

### Container won't start

- Check that all required environment variables are set
- Verify Home Assistant URL is accessible
- Check Docker logs: `docker logs weather-dashboard`

### No data appearing

- Verify sensor entity IDs exist in Home Assistant
- Check that the access token has appropriate permissions
- Monitor logs for API connection errors

### Port conflicts

- Change the external port in docker-compose.yml or docker run command
- The internal port (8080) should remain unchanged

## Logs

View application logs:

```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f weather-dashboard
```

## Stopping the Application

```bash
# Docker Compose
docker-compose down

# Docker
docker stop weather-dashboard
docker rm weather-dashboard
```
