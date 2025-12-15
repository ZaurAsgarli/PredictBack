#!/bin/bash
set -e

# Set Python path
export PYTHONPATH=/app

# Wait for database to be ready (only if db host is set)
if [ -n "$POSTGRES_HOST" ] && [ "$POSTGRES_HOST" != "localhost" ]; then
    echo "Waiting for database at $POSTGRES_HOST..."
    while ! nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
        sleep 0.1
    done
    echo "Database is ready!"
    
    # Run migrations
    echo "Running migrations..."
    python manage.py migrate --noinput || true
    
    # Collect static files
    echo "Collecting static files..."
    python manage.py collectstatic --noinput || true
fi

# Execute the command passed to the container
exec "$@"
