"""
Comprehensive setup verification script.
Run with: python manage.py shell < check_setup.py
Or: docker-compose exec web python manage.py shell < check_setup.py
"""
import os
import sys

print("\n" + "="*70)
print("PREDICTHUB BACKEND - COMPLETE SETUP VERIFICATION")
print("="*70)

# Check Django setup
try:
    import django
    django.setup()
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.db import connection
    
    User = get_user_model()
    
    print("\n✓ Django is properly configured")
    print(f"  - Django version: {django.get_version()}")
    print(f"  - Database: {settings.DATABASES['default']['ENGINE']}")
    print(f"  - Debug mode: {settings.DEBUG}")
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("\n✓ Database connection: SUCCESS")
    except Exception as e:
        print(f"\n✗ Database connection: FAILED - {e}")
        sys.exit(1)
    
    # Check superuser
    print("\n" + "-"*70)
    print("SUPERUSER ACCOUNTS")
    print("-"*70)
    superusers = User.objects.filter(is_superuser=True)
    if superusers.exists():
        print(f"✓ Found {superusers.count()} superuser(s):")
        for user in superusers:
            print(f"  - Username: {user.username}")
            print(f"    Email: {user.email}")
            print(f"    Active: {user.is_active}")
            print(f"    Last login: {user.last_login or 'Never'}")
    else:
        print("✗ No superuser found!")
        print("\n  To create a superuser, run:")
        print("  docker-compose exec web python manage.py createsuperuser")
    
    # Check all models and data
    print("\n" + "-"*70)
    print("DATABASE MODELS & DATA")
    print("-"*70)
    
    from markets.models import Market, MarketCategory, OutcomeToken, PriceHistory, Resolution
    from users.models import User
    from trades.models import Trade
    from positions.models import Position
    from liquidity.models import LiquidityEvent
    from disputes.models import Dispute
    from indexer.models import OnchainTransaction, OnchainEventLog
    
    models_to_check = [
        ('Market Categories', MarketCategory),
        ('Users', User),
        ('Markets', Market),
        ('Outcome Tokens', OutcomeToken),
        ('Trades', Trade),
        ('Positions', Position),
        ('Liquidity Events', LiquidityEvent),
        ('Disputes', Dispute),
        ('Resolutions', Resolution),
        ('Price History', PriceHistory),
        ('Onchain Transactions', OnchainTransaction),
        ('Onchain Event Logs', OnchainEventLog),
    ]
    
    for name, model in models_to_check:
        count = model.objects.count()
        status = "✓" if count > 0 else "○"
        print(f"{status} {name}: {count}")
    
    # Check migrations
    print("\n" + "-"*70)
    print("MIGRATIONS STATUS")
    print("-"*70)
    from django.db.migrations.executor import MigrationExecutor
    from django.db import connections
    
    executor = MigrationExecutor(connections['default'])
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    
    if plan:
        print(f"⚠ {len(plan)} pending migration(s) detected")
        for migration, _ in plan[:5]:  # Show first 5
            print(f"  - {migration}")
        if len(plan) > 5:
            print(f"  ... and {len(plan) - 5} more")
    else:
        print("✓ All migrations are applied")
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    has_superuser = superusers.exists()
    has_data = any(model.objects.count() > 0 for _, model in models_to_check)
    migrations_ok = len(plan) == 0
    
    if has_superuser and has_data and migrations_ok:
        print("✓ Everything looks good! You're ready to go.")
        print("\n  Access points:")
        print("  - Django Admin: http://localhost:8000/admin/")
        print("  - pgAdmin: http://localhost:5050/")
        print("  - API: http://localhost:8000/api/")
    else:
        print("⚠ Some issues detected:")
        if not has_superuser:
            print("  - No superuser account. Run: docker-compose exec web python manage.py createsuperuser")
        if not has_data:
            print("  - No seed data. Run: docker-compose exec web python manage.py seed_data")
        if not migrations_ok:
            print("  - Pending migrations. Run: docker-compose exec web python manage.py migrate")
    
    print("="*70 + "\n")
    
except ImportError as e:
    print(f"\n✗ Django import failed: {e}")
    print("  Make sure you're running this inside Docker or with Django installed")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

