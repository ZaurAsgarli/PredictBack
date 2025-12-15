# Generated migration for Materialized View: Volume by Tag

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0003_knowledgetag'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE MATERIALIZED VIEW IF NOT EXISTS market_volume_by_tag AS
            SELECT 
                kt.id as tag_id,
                kt.name as tag_name,
                kt.slug as tag_slug,
                COUNT(DISTINCT m.id) as market_count,
                COUNT(DISTINCT t.id) as trade_count,
                COALESCE(SUM(t.amount_staked), 0) as total_volume,
                COALESCE(AVG(t.amount_staked), 0) as avg_trade_size,
                MAX(t.created_at) as last_trade_at
            FROM markets_knowledgetag kt
            LEFT JOIN markets_marketknowledgetag mkt ON kt.id = mkt.tag_id
            LEFT JOIN markets_market m ON mkt.market_id = m.id
            LEFT JOIN trades_trade t ON m.id = t.market_id
            GROUP BY kt.id, kt.name, kt.slug;
            
            CREATE UNIQUE INDEX IF NOT EXISTS market_volume_by_tag_tag_id_idx 
            ON market_volume_by_tag(tag_id);
            
            CREATE INDEX IF NOT EXISTS market_volume_by_tag_tag_slug_idx 
            ON market_volume_by_tag(tag_slug);
            """,
            reverse_sql="DROP MATERIALIZED VIEW IF EXISTS market_volume_by_tag;"
        ),
    ]

