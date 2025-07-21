FROM python:3.11

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache gcc musl-dev

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

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Change ownership of app directory including data directory
RUN chown -R appuser:appgroup /app
RUN chown -R appuser:appgroup /app/data
RUN chmod -R 777 /app/data

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_PORT=3300
ENV DATABASE_PATH=/app/data/weather_data.db

# Expose the port
EXPOSE 3300

# Create a script to run both loader and webserver
COPY docker-entrypoint.sh /app/
USER root
RUN chmod +x /app/docker-entrypoint.sh
USER appuser

# Default command
CMD ["/app/docker-entrypoint.sh"]
