#!/bin/sh

# Function to run the loader
run_loader() {
    echo "Running loader to fetch sensor data..."
    export LOADER_MODE=once
    ls -la .
    uv run python src/loader.py
}

# Function to run the loader continuously
run_loader_continuous() {
    echo "Running loader continuously (every 2 minutes)..."
    export LOADER_MODE=continuous
    uv run python src/loader.py
}

# Function to start the web server
start_webserver() {
    echo "Starting web server..."
    uv run python src/webserver.py
}

# Check if we should run the loader first
if [ "$SKIP_INITIAL_LOAD" != "true" ]; then
    run_loader
fi

# Check the mode - default is webserver
MODE=${MODE:-webserver}

case "$MODE" in
    "loader")
        echo "Running in loader mode..."
        run_loader_continuous
        ;;
    "loader-once")
        echo "Running in loader-once mode..."
        run_loader
        ;;
    "webserver")
        echo "Running in webserver mode..."
        start_webserver
        ;;
    "both")
        echo "Running in both mode..."
        # Run loader first
        run_loader
        # Then start webserver in background and loader continuously
        start_webserver &
        run_loader_continuous
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo "Available modes: loader, loader-once, webserver, both"
        exit 1
        ;;
esac
