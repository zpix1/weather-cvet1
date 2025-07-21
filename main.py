#!/usr/bin/env python3
"""
Weather Dashboard - Main Entry Point

A comprehensive weather monitoring system that collects, stores, and visualizes
weather data using SQLite and Plotly.

Features:
- Real-time weather data collection
- SQLite database for historical data storage
- Interactive Plotly charts for data visualization
- Modern web interface with status monitoring
- Background data fetching with scheduled updates
- Optimized for performance with no API calls on initial load
"""

import sys
import signal
from config import config
from app import app
from data_fetcher import start_data_fetcher, stop_data_fetcher


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    print("\nShutting down weather dashboard...")
    stop_data_fetcher()
    sys.exit(0)


def main():
    """Main entry point for the weather dashboard."""
    try:
        # Validate configuration
        print("🌤️  Weather Dashboard Starting...")
        print("=" * 50)

        config.validate()
        print("✓ Configuration validated")

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start the data fetcher
        print("✓ Starting background data fetcher...")
        start_data_fetcher()

        # Start the web server
        print(f"✓ Starting web server on {config.FLASK_HOST}:{config.FLASK_PORT}")
        print("=" * 50)
        print(
            f"🌐 Dashboard available at: http://{config.FLASK_HOST}:{config.FLASK_PORT}"
        )
        print("📊 Features:")
        print("   - Real-time weather monitoring")
        print("   - Historical data visualization")
        print("   - Data collection and storage")
        print("   - SQLite data storage")
        print("=" * 50)

        # Run the Flask application
        app.run(
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            debug=config.FLASK_DEBUG,
            use_reloader=False,  # Disable reloader to prevent data fetcher duplication
        )

    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print(
            "\nPlease check your .env file and ensure the following variables are set:"
        )
        print("  - Data source connection parameters")
        print("  - Sensor entity configurations")
        print("  - API endpoint URLs")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n👋 Shutdown requested by user")
        stop_data_fetcher()

    except Exception as e:
        print(f"❌ Failed to start weather dashboard: {e}")
        stop_data_fetcher()
        sys.exit(1)


if __name__ == "__main__":
    main()
