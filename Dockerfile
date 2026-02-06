# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS builder
WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_NO_CACHE=1

# Виртуалка в отдельной папке — её потом просто копируем в runtime-образ
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# uv нужен только на стадии сборки
RUN pip install --no-cache-dir uv

# Копируем только lock-файлы — это улучшает кеширование слоёв
COPY pyproject.toml uv.lock ./

# Ставим только зависимости (без dev) и не пытаемся "инсталлить" сам проект
RUN uv sync --frozen --no-dev --no-install-project


FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    FLASK_PORT=3300 \
    DATABASE_PATH=/app/data/weather_data.db \
    PATH="/opt/venv/bin:$PATH"

# Готовая виртуалка с зависимостями
COPY --from=builder /opt/venv /opt/venv

# Только исходники приложения
COPY src/ ./src/
COPY pyproject.toml ./

# Пользователь + директория под БД одним слоем
RUN addgroup --system --gid 1001 appgroup \
 && adduser  --system --uid 1001 --ingroup appgroup --home /home/appuser appuser \
 && mkdir -p /app/data \
 && chown -R appuser:appgroup /app \
 && chmod 755 /app/data

USER appuser

EXPOSE 3300
