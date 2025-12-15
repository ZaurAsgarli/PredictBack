FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install system dependencies (including netcat for health checks)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools first to ensure correct versions
RUN pip install --upgrade pip setuptools==80.9.0

# Copy requirements from backend_api
COPY backend_api/requirements.txt /app/backend_api/requirements.txt
RUN pip install --no-cache-dir -r /app/backend_api/requirements.txt

# Copy ALL modules (context is repo root now)
COPY backend_api/ /app/backend_api/
COPY ml_service/ /app/ml_service/
COPY security_engine/ /app/security_engine/
COPY smart_contracts/ /app/smart_contracts/

# Copy entrypoint
COPY backend_api/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Create logs directories
RUN mkdir -p /app/backend_api/logs /app/backend_api/LOGS /app/ml_service/logs

# Set execute permissions
RUN chmod +x /app/backend_api/manage.py || true

EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

