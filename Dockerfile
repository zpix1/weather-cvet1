FROM python:3.11

# Set working directory
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml ./
COPY uv.lock ./
COPY src/ ./src/

# Install dependencies using uv
RUN uv sync --frozen

# Create directory for database
RUN mkdir -p /app/data

# Copy entrypoint script and set permissions
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Create non-root user
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m appuser

# Change ownership of app directory including data directory
RUN chown -R appuser:appgroup /app
RUN chmod -R 755 /app/data

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_PORT=3300
ENV DATABASE_PATH=/app/data/weather_data.db

# Expose the port
EXPOSE 3300

# Default command
CMD ["/app/docker-entrypoint.sh"]
