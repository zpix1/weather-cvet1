"""Flask web application for weather data visualization."""

import json
import os
import io
import base64
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_file
import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure

from config import config
from database import db
from data_fetcher import data_fetcher, start_data_fetcher, stop_data_fetcher


app = Flask(__name__)

# Chart presets configuration
CHART_PRESETS = {
    "24h": {"hours": 24, "title": "Последние 24 часа"},
    "3d": {"hours": 72, "title": "Последние 3 дня"},
    "1m": {"hours": 720, "title": "Последний месяц"},
}


@app.route("/")
def index():
    """Main dashboard page."""
    preset = request.args.get("preset", "24h")
    chart_type = request.args.get("type", "temperature")

    # Validate preset
    if preset not in CHART_PRESETS:
        preset = "24h"

    return render_template("index.html", preset=preset, chart_type=chart_type)


@app.route("/api/weather/current")
def get_current_weather():
    """Get the most recent weather data."""
    try:
        # Get recent data to find latest temperature and humidity
        recent_data = db.get_recent_weather_data(hours=1, limit=100)

        latest_data = {}
        temp_data = None
        humidity_data = None

        # Find latest temperature and humidity readings
        for record in recent_data:
            if (
                "temperatura" in record["entity_id"].lower()
                and record["temperature"] is not None
            ):
                if not temp_data or record["timestamp"] > temp_data["timestamp"]:
                    temp_data = record
            elif (
                "vlazhnost" in record["entity_id"].lower()
                and record["humidity"] is not None
            ):
                if (
                    not humidity_data
                    or record["timestamp"] > humidity_data["timestamp"]
                ):
                    humidity_data = record

        if temp_data or humidity_data:
            if temp_data:
                latest_data["temperature"] = temp_data["temperature"]
                latest_data["timestamp"] = temp_data["timestamp"]
            if humidity_data:
                latest_data["humidity"] = humidity_data["humidity"]
                if not latest_data.get("timestamp") or humidity_data[
                    "timestamp"
                ] > latest_data.get("timestamp", ""):
                    latest_data["timestamp"] = humidity_data["timestamp"]

            # Calculate time since last update with proper timezone handling
            timestamp_str = latest_data["timestamp"]
            if "Z" in timestamp_str:
                timestamp_str = timestamp_str.replace("Z", "+00:00")

            last_update = datetime.fromisoformat(timestamp_str)
            # Convert to naive datetime in local timezone for proper comparison
            if last_update.tzinfo is not None:
                # Convert UTC to local time
                import time

                utc_offset = time.timezone if (time.daylight == 0) else time.altzone
                local_offset = -utc_offset / 3600  # Convert to hours
                last_update = last_update.replace(tzinfo=None) + timedelta(
                    hours=local_offset
                )

            current_time = datetime.now()
            time_diff = current_time - last_update
            latest_data["time_since_update"] = {
                "seconds": int(time_diff.total_seconds()),
                "human_readable": format_time_diff(time_diff),
            }

            return jsonify({"success": True, "data": latest_data})
        else:
            return jsonify({"success": False, "error": "No weather data available"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/weather/history")
def get_weather_history():
    """Get historical weather data for plotting."""
    try:
        # Get query parameters
        hours = request.args.get("hours", 168, type=int)  # Default to 1 week
        limit = request.args.get(
            "limit", 5000, type=int
        )  # Increased limit for month data
        chart_type = request.args.get("type", "temperature")

        # Allow up to 1 month of data
        hours = min(hours, 720)  # Max 1 month (30 days)
        limit = min(limit, 10000)  # Max 10000 records for month data

        # Get data from database using the database layer
        all_data = db.get_recent_weather_data(hours=hours, limit=limit)

        # Filter data based on chart type
        chart_data = []
        for record in all_data:
            if chart_type == "temperature":
                if (
                    "temperatura" in record["entity_id"].lower()
                    and record["temperature"] is not None
                ):
                    chart_data.append(
                        {
                            "timestamp": record["timestamp"],
                            "temperature": record["temperature"],
                            "entity_id": record["entity_id"],
                        }
                    )
            elif chart_type == "humidity":
                if (
                    "vlazhnost" in record["entity_id"].lower()
                    and record["humidity"] is not None
                ):
                    chart_data.append(
                        {
                            "timestamp": record["timestamp"],
                            "humidity": record["humidity"],
                            "entity_id": record["entity_id"],
                        }
                    )

        # Sort by timestamp ascending
        chart_data.sort(key=lambda x: x["timestamp"])

        return jsonify(
            {
                "success": True,
                "data": chart_data,
                "count": len(chart_data),
                "hours": hours,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/weather/forecast")
def get_weather_forecast():
    """Get weather forecast data."""
    try:
        forecast_json = db.get_metadata("latest_forecast")
        if forecast_json:
            forecast_data = json.loads(forecast_json)
            return jsonify({"success": True, "data": forecast_data})
        else:
            return jsonify({"success": False, "error": "No forecast data available"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/weather/chart-data")
def get_chart_data():
    """Get formatted data for Plotly charts."""
    try:
        hours = request.args.get("hours", 168, type=int)  # Default to 1 week
        chart_type = request.args.get("type", "temperature")

        # Get historical data with increased limit for month data
        weather_data = db.get_recent_weather_data(hours=hours, limit=10000)

        # Prepare data for Plotly
        timestamps = []
        values = []

        for record in weather_data:
            # Keep original timestamps - frontend will handle timezone conversion
            timestamps.append(record["timestamp"])

            if chart_type == "temperature":
                values.append(record.get("temperature"))
            elif chart_type == "humidity":
                values.append(record.get("humidity"))

        chart_data = {
            "x": timestamps,
            "y": values,
            "type": chart_type,
            "hours": hours,
            "count": len(values),
        }

        return jsonify({"success": True, "data": chart_data})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/weather/chart/<preset>/<chart_type>.png")
def get_weather_chart(preset, chart_type):
    """Generate and serve weather chart as PNG image."""
    try:
        # Validate inputs
        if preset not in CHART_PRESETS:
            preset = "24h"
        if chart_type not in ["temperature", "humidity"]:
            chart_type = "temperature"

        hours = CHART_PRESETS[preset]["hours"]
        title = CHART_PRESETS[preset]["title"]

        # Get weather data
        weather_data = db.get_recent_weather_data(hours=hours, limit=10000)

        # Filter and prepare data
        timestamps = []
        values = []

        for record in weather_data:
            timestamp_str = record["timestamp"]
            if "Z" in timestamp_str:
                timestamp_str = timestamp_str.replace("Z", "+00:00")

            try:
                dt = datetime.fromisoformat(timestamp_str)
                if dt.tzinfo is not None:
                    # Convert UTC to local time
                    import time

                    utc_offset = time.timezone if (time.daylight == 0) else time.altzone
                    local_offset = -utc_offset / 3600
                    dt = dt.replace(tzinfo=None) + timedelta(hours=local_offset)

                if chart_type == "temperature":
                    if (
                        "temperatura" in record["entity_id"].lower()
                        and record["temperature"] is not None
                    ):
                        timestamps.append(dt)
                        values.append(record["temperature"])
                elif chart_type == "humidity":
                    if (
                        "vlazhnost" in record["entity_id"].lower()
                        and record["humidity"] is not None
                    ):
                        timestamps.append(dt)
                        values.append(record["humidity"])
            except Exception as e:
                continue

        # Sort by timestamp
        data_pairs = list(zip(timestamps, values))
        data_pairs.sort(key=lambda x: x[0])
        timestamps, values = zip(*data_pairs) if data_pairs else ([], [])

        # Create matplotlib figure
        plt.style.use("default")
        # Configure font for Russian text support
        plt.rcParams["font.family"] = ["DejaVu Sans", "Arial", "sans-serif"]
        plt.rcParams["axes.unicode_minus"] = False

        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor("white")

        if timestamps and values:
            # Plot data
            ax.plot(
                timestamps,
                values,
                linewidth=2,
                color="#2563eb",
                marker="",
                markersize=3,
            )

            # Customize chart
            if chart_type == "temperature":
                ax.set_ylabel("Температура (°C)", fontsize=12)
                chart_title = f"Температура - {title}"
            else:
                ax.set_ylabel("Влажность (%)", fontsize=12)
                chart_title = f"Влажность - {title}"

            ax.set_title(chart_title, fontsize=14, fontweight="bold", pad=20)
            ax.set_xlabel("Время", fontsize=12)

            # Format x-axis
            if hours <= 24:
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
            elif hours <= 72:
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))

            plt.xticks(rotation=45)

            # Add grid
            ax.grid(True, alpha=0.3)
            ax.set_axisbelow(True)

        else:
            ax.text(
                0.5,
                0.5,
                "Нет данных для отображения",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=14,
            )
            ax.set_title(
                f"{chart_type.title()} - {title}", fontsize=14, fontweight="bold"
            )

        # Adjust layout
        plt.tight_layout()

        # Save to BytesIO
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=100, bbox_inches="tight")
        img_buffer.seek(0)
        plt.close(fig)

        return send_file(img_buffer, mimetype="image/png")

    except Exception as e:
        # Return error image
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(
            0.5,
            0.5,
            f"Ошибка генерации графика: {str(e)}",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=12,
        )
        ax.set_title("Ошибка", fontsize=14)

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=100, bbox_inches="tight")
        img_buffer.seek(0)
        plt.close(fig)

        return send_file(img_buffer, mimetype="image/png")


def format_time_diff(time_diff):
    """Format timedelta for human readable display."""
    total_seconds = int(time_diff.total_seconds())

    if total_seconds < 60:
        return f"{total_seconds} сек. назад"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes} мин. назад"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours} ч. назад"
    else:
        days = total_seconds // 86400
        return f"{days} дн. назад"


@app.before_request
def before_first_request():
    """Initialize the application."""
    if not hasattr(app, "_started"):
        print("Starting weather data fetcher...")
        start_data_fetcher()
        app._started = True


def create_app():
    """Application factory."""
    return app


if __name__ == "__main__":
    try:
        config.validate()
        start_data_fetcher()
        app.run(
            host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG
        )
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        stop_data_fetcher()
        print("Application stopped")
