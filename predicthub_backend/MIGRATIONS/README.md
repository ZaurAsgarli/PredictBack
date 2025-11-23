# Migrations Directory

This directory contains documentation about database migrations for Sprint 2.

## New Migrations Created

### Markets App
- `0003_add_onchain_fields.py` - Adds `onchain_market_id` and `onchain_tx_hash` to Market model
- `0004_create_market_activity_view.py` - Creates PostgreSQL materialized view `market_activity_view`

### Trades App
- `0003_add_onchain_fields.py` - Adds `onchain_tx_hash` and `onchain_trade_id` to Trade model

### Liquidity App
- `0004_add_onchain_fields.py` - Adds `onchain_tx_hash` and `onchain_liquidity_id` to LiquidityEvent model

## Running Migrations

```bash
python manage.py migrate
```

## Materialized View Refresh

After data changes, refresh the materialized view:

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY market_activity_view;
```

Or via Django:

```python
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY market_activity_view;")
```

## Index Summary

New indexes added:
- `markets_mar_onchain__idx` - Market onchain_market_id
- `markets_mar_onchain__idx` - Market onchain_tx_hash
- `markets_res_onchain__idx` - Resolution onchain_tx_hash
- `trades_trad_onchain__idx` - Trade onchain_tx_hash
- `trades_trad_market__idx` - Trade (market_id, outcome_type)
- `liquidity_li_onchain__idx` - LiquidityEvent onchain_tx_hash
- `liquidity_li_market__idx` - LiquidityEvent (market_id, event_type)

