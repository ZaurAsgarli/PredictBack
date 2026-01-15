#!/bin/bsh
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
    
    # Seed data if database is empty (first-time setup)
    echo "Checking if data seeding is needed..."
    USERS_COUNT=$(python -c "import django; django.setup(); from backend_api.api.users.models import User; print(User.objects.count())" 2>/dev/null || echo "0")
    
    if [ "$USERS_COUNT" -lt "10" ]; then
        echo ""
        echo "=========================================="
        echo "🚀 ULTIMATE DATA SEEDING PROTOCOL"
        echo "=========================================="
        
        # Step 1: Sync real markets from Polymarket API
        echo ""
        echo "📡 Step 1: Fetching real markets from Polymarket..."
        python -c "
import django; django.setup()
from backend_api.api.markets.polymarket_service import PolymarketService
count = PolymarketService().sync_markets()
print(f'   Synced {count} real markets from Polymarket API')
" || echo "   Polymarket sync failed (will use synthetic markets instead)"
        
        # Step 2: Run seed_ultimate (users, markets, trades, positions, disputes, liquidity)
        echo ""
        echo "👥 Step 2: Creating users, trades, positions, disputes..."
        python manage.py seed_ultimate || echo "   seed_ultimate failed"
        
        # Step 3: Run seed_logs (ML predictions, on-chain events, more security logs)
        echo ""
        echo "🔐 Step 3: Creating ML predictions, on-chain events, security logs..."
        python manage.py seed_logs --security-count=100 --high-risk-users=30 || echo "   seed_logs failed"
        
        echo ""
        echo "=========================================="
        echo "✅ DATA SEEDING COMPLETE!"
        echo "=========================================="
        echo ""
    else
        echo "Database already has $USERS_COUNT users, skipping seeding."
    fi
    
    # Collect static files
    echo "Collecting static files..."
    python manage.py collectstatic --noinput || true
fi

# Execute the command passed to the container
exec "$@"

