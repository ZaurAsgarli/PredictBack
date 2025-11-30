FROM python:3.11-slim

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

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Create logs directory
RUN mkdir -p logs ml_logs

# Set execute permissions
RUN chmod +x manage.py || true

EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

