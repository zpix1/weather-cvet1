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
                    # Convert UTC to Novosibirsk time (UTC+7)
                    novosibirsk_offset = 7  # Novosibirsk is UTC+7
                    dt = dt.replace(tzinfo=None) + timedelta(hours=novosibirsk_offset)

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

            ax.set_title(chart_title, fontsize=14, pad=20)
            ax.set_xlabel("Время", fontsize=12)

            # Add vertical lines at 00:00 for each day
            if timestamps:
                # Calculate date range
                start_date = min(timestamps).date()
                end_date = max(timestamps).date()

                # Add vertical lines at midnight for each day
                current_date = start_date
                while current_date <= end_date:
                    midnight = datetime.combine(current_date, datetime.min.time())
                    if min(timestamps) <= midnight <= max(timestamps):
                        ax.axvline(
                            x=midnight,
                            color="gray",
                            linestyle="--",
                            alpha=0.5,
                            linewidth=1,
                        )
                    current_date += timedelta(days=1)

            # Format x-axis with custom tick locations and labels
            if hours <= 24:
                # For 24h view, ensure midnight times are included as major ticks
                midnight_times = []
                regular_times = []

                if timestamps:
                    start_time = min(timestamps)
                    end_time = max(timestamps)

                    # Add midnight times within the range
                    current_date = start_time.date()
                    while current_date <= end_time.date():
                        midnight = datetime.combine(current_date, datetime.min.time())
                        if start_time <= midnight <= end_time:
                            midnight_times.append(midnight)
                        current_date += timedelta(days=1)

                    # Add regular 4-hour interval times
                    current_time = start_time.replace(minute=0, second=0, microsecond=0)
                    current_time = current_time.replace(
                        hour=(current_time.hour // 4) * 4
                    )
                    while current_time <= end_time:
                        if current_time not in midnight_times:
                            regular_times.append(current_time)
                        current_time += timedelta(hours=4)

                    # Combine and sort all tick locations
                    all_ticks = sorted(midnight_times + regular_times)
                    ax.set_xticks(all_ticks)

                # Custom formatter that shows date at midnight, time otherwise
                def custom_formatter_24h(x, pos):
                    dt = mdates.num2date(x)
                    if dt.hour == 0 and dt.minute == 0:
                        return dt.strftime("%d.%m\n00:00")
                    else:
                        return dt.strftime("%H:%M")

                ax.xaxis.set_major_formatter(plt.FuncFormatter(custom_formatter_24h))

            elif hours <= 72:
                # For 3-day view, ensure midnight times are included as major ticks
                midnight_times = []
                regular_times = []

                if timestamps:
                    start_time = min(timestamps)
                    end_time = max(timestamps)

                    # Add midnight times within the range
                    current_date = start_time.date()
                    while current_date <= end_time.date():
                        midnight = datetime.combine(current_date, datetime.min.time())
                        if start_time <= midnight <= end_time:
                            midnight_times.append(midnight)
                        current_date += timedelta(days=1)

                    # Add regular 12-hour interval times
                    current_time = start_time.replace(minute=0, second=0, microsecond=0)
                    current_time = current_time.replace(
                        hour=(current_time.hour // 12) * 12
                    )
                    while current_time <= end_time:
                        if current_time not in midnight_times:
                            regular_times.append(current_time)
                        current_time += timedelta(hours=12)

                    # Combine and sort all tick locations
                    all_ticks = sorted(midnight_times + regular_times)
                    ax.set_xticks(all_ticks)

                def custom_formatter_3d(x, pos):
                    dt = mdates.num2date(x)
                    if dt.hour == 0 and dt.minute == 0:
                        return dt.strftime("%d.%m\n00:00")
                    else:
                        return dt.strftime("%H:%M")

                ax.xaxis.set_major_formatter(plt.FuncFormatter(custom_formatter_3d))

            else:
                # For month view, use daily intervals with dates at midnight
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
                ax.xaxis.set_minor_locator(mdates.DayLocator(interval=1))

                def custom_formatter_month(x, pos):
                    dt = mdates.num2date(x)
                    return dt.strftime("%d.%m")

                ax.xaxis.set_major_formatter(plt.FuncFormatter(custom_formatter_month))

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
