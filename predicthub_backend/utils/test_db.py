"""
Database connectivity test script
Run this in Django shell: python manage.py shell < utils/test_db.py
Or: from utils.test_db import test_database; test_database()
"""
from django.db import connection


def test_database():
    """Test database connectivity and list all tables"""
    try:
        with connection.cursor() as cursor:
            # Test connection
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ PostgreSQL Connection Successful!")
            print(f"   Version: {version[0]}")
            
            # List all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            print(f"\n✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table[0]}")
            
            # Check for expected tables
            expected_tables = [
                'users',
                'markets_market',
                'markets_marketcategory',
                'markets_outcometoken',
                'markets_pricehistory',
                'markets_resolution',
                'trades_trade',
                'positions_position',
                'liquidity_liquidityevent',
                'disputes_dispute',
                'indexer_onchaintransaction',
                'indexer_onchaineventlog',
            ]
            
            existing_tables = [t[0] for t in tables]
            missing = [t for t in expected_tables if t not in existing_tables]
            
            if missing:
                print(f"\n⚠️  Missing tables: {', '.join(missing)}")
            else:
                print(f"\n✅ All expected tables exist!")
            
            # Check materialized view
            cursor.execute("""
                SELECT matviewname 
                FROM pg_matviews 
                WHERE schemaname = 'public';
            """)
            views = cursor.fetchall()
            
            if views:
                print(f"\n✅ Materialized views:")
                for view in views:
                    print(f"   - {view[0]}")
            else:
                print(f"\n⚠️  No materialized views found")
            
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == '__main__':
    test_database()

