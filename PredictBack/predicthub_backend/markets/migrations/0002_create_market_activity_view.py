# Generated migration for creating materialized view
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0001_initial'),
        ('trades', '0001_initial'),
        ('liquidity', '0001_initial'),
        ('positions', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE MATERIALIZED VIEW IF NOT EXISTS market_activity_view AS
            SELECT 
                m.id AS market_id,
                m.title,
                m.status,
                COUNT(DISTINCT t.id) AS total_trades,
                COALESCE(SUM(CASE WHEN le.event_type = 'add' THEN le.amount ELSE 0 END), 0) AS total_liquidity_added,
                GREATEST(
                    COALESCE(MAX(t.created_at), '1970-01-01'::timestamp),
                    COALESCE(MAX(le.created_at), '1970-01-01'::timestamp)
                ) AS last_activity_timestamp,
                COALESCE(SUM(CASE 
                    WHEN t.created_at >= NOW() - INTERVAL '24 hours' 
                    THEN t.amount_staked 
                    ELSE 0 
                END), 0) AS volume_24h,
                COALESCE(SUM(DISTINCT p.total_staked), 0) AS open_interest
            FROM markets_market m
            LEFT JOIN trades_trade t ON t.market_id = m.id
            LEFT JOIN liquidity_liquidityevent le ON le.market_id = m.id
            LEFT JOIN positions_position p ON p.market_id = m.id
            GROUP BY m.id, m.title, m.status;
            
            CREATE UNIQUE INDEX IF NOT EXISTS market_activity_view_market_id_idx 
            ON market_activity_view (market_id);
            
            CREATE INDEX IF NOT EXISTS market_activity_view_status_idx 
            ON market_activity_view (status);
            
            CREATE INDEX IF NOT EXISTS market_activity_view_last_activity_idx 
            ON market_activity_view (last_activity_timestamp DESC);
            """,
            reverse_sql="DROP MATERIALIZED VIEW IF EXISTS market_activity_view CASCADE;"
        ),
    ]

