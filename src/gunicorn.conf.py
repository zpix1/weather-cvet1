# Gunicorn configuration file
# You can override these settings with command line arguments

import os

# Server socket
bind = f"0.0.0.0:{os.getenv('FLASK_PORT', '3300')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', '4'))
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'weather-server'

# Server mechanics
preload_app = True
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment and configure if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
