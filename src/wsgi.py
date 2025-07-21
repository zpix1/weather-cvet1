#!/usr/bin/env python3
"""
WSGI entry point for the weather web server.
This file is used by Gunicorn to serve the Flask application.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file if it exists
env_path = project_root / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Import the Flask app from webserver module
from src.webserver import app

# This is what Gunicorn will use
application = app

if __name__ == "__main__":
    # For development - you can still run this directly
    port = int(os.getenv('FLASK_PORT', 3300))
    app.run(host='0.0.0.0', port=port, debug=False)
