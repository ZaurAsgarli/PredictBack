# Database Documentation

PostgreSQL database schema for PredictHub prediction market platform.

---

## 🗄️ Schema Overview

### Normalization: 4NF (Fourth Normal Form)

The database schema is normalized to **4NF** to eliminate:
- Redundant data
- Multi-valued dependencies
- Join dependencies

**Key Design Principles:**
- Each table represents a single entity
- No redundant columns
- Proper foreign key relationships
- Junction tables for many-to-many relationships

---

## 📊 Core Tables

### Users (`users_user`)

Stores user accounts (both on-chain and off-chain).

```sql
CREATE TABLE users_user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE,
    email VARCHAR(255) UNIQUE,
    password VARCHAR(128),
    wallet_address VARCHAR(42),  -- Blockchain address
    total_points DECIMAL(10,2),
    win_rate DECIMAL(5,2),
    streak INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Indexed by**: `username`, `email`, `wallet_address`

### Markets (`markets_market`)

Stores prediction markets.

```sql
CREATE TABLE markets_market (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    onchain_market_id INTEGER,  -- Links to blockchain
    creator_id INTEGER REFERENCES users_user(id),
    category_id INTEGER,
    status VARCHAR(20),  -- active, closed, resolved
    resolution_outcome BOOLEAN,  -- true=YES, false=NO
    liquidity_pool DECIMAL(12,2),
    ends_at TIMESTAMP,
    created_at TIMESTAMP
);
```

**Indexed by**: `onchain_market_id`, `creator_id`, `status`, `ends_at`

### Trades (`trades_trade`)

Stores individual trades.

```sql
CREATE TABLE trades_trade (
    id SERIAL PRIMARY KEY,
    market_id INTEGER REFERENCES markets_market(id),
    user_id INTEGER REFERENCES users_user(id),
    outcome_type VARCHAR(3),  -- YES or NO
    trade_type VARCHAR(4),    -- buy or sell
    amount_staked DECIMAL(12,2),
    tokens_amount DECIMAL(12,2),
    price_at_execution DECIMAL(5,4),
    onchain_trade_id INTEGER,  -- Links to blockchain
    created_at TIMESTAMP
);
```

**Indexed by**: `market_id`, `user_id`, `onchain_trade_id`, `created_at`

### Liquidity (`liquidity_liquidityevent`)

Stores liquidity provision events.

```sql
CREATE TABLE liquidity_liquidityevent (
    id SERIAL PRIMARY KEY,
    market_id INTEGER REFERENCES markets_market(id),
    user_id INTEGER REFERENCES users_user(id),
    event_type VARCHAR(10),  -- add or remove
    amount DECIMAL(12,2),
    onchain_liquidity_id INTEGER,  -- Links to blockchain
    created_at TIMESTAMP
);
```

**Indexed by**: `market_id`, `user_id`, `onchain_liquidity_id`

### Knowledge Tags (`markets_knowledgetag`)

Categorizes markets by topic.

```sql
CREATE TABLE markets_knowledgetag (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    slug VARCHAR(100) UNIQUE,
    description TEXT,
    created_at TIMESTAMP
);
```

**Junction Table** (`markets_marketknowledgetag`):
```sql
CREATE TABLE markets_marketknowledgetag (
    id SERIAL PRIMARY KEY,
    market_id INTEGER REFERENCES markets_market(id),
    tag_id INTEGER REFERENCES markets_knowledgetag(id),
    created_at TIMESTAMP,
    UNIQUE(market_id, tag_id)
);
```

---

## 📈 Materialized Views

### Market Volume by Tag (`market_volume_by_tag`)

Aggregates trading volume by knowledge tag for dashboard display.

```sql
CREATE MATERIALIZED VIEW market_volume_by_tag AS
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
```

**Indexes:**
- `market_volume_by_tag_tag_id_idx` (unique)
- `market_volume_by_tag_tag_slug_idx`

**Refresh:**
```sql
REFRESH MATERIALIZED VIEW market_volume_by_tag;
```

**Usage:**
```sql
SELECT * FROM market_volume_by_tag ORDER BY total_volume DESC;
```

---

## 🔄 Migrations

### Running Migrations

```bash
# Apply all migrations
python manage.py migrate

# Create new migration
python manage.py makemigrations

# Show migration status
python manage.py showmigrations

# Rollback migration
python manage.py migrate app_name migration_number
```

### Key Migrations

1. **Initial Schema** (`0001_initial.py`): Creates all core tables
2. **Knowledge Tags** (`0003_knowledgetag.py`): Adds tag system
3. **Materialized View** (`0004_create_volume_by_tag_view.py`): Creates dashboard view

### Seed Data

```bash
# Seed knowledge tags
python manage.py seed_knowledge_tags

# Seed sample markets (if script exists)
python manage.py seed_markets
```

---

## 🔍 Common Queries

### Check Indexed Events

```sql
SELECT 
    event_name,
    COUNT(*) as count,
    MAX(created_at) as latest
FROM indexer_onchaineventlog
GROUP BY event_name
ORDER BY count DESC;
```

### Find Markets with Trades

```sql
SELECT 
    m.id,
    m.title,
    COUNT(t.id) as trade_count,
    SUM(t.amount_staked) as total_volume
FROM markets_market m
LEFT JOIN trades_trade t ON m.id = t.market_id
GROUP BY m.id, m.title
HAVING COUNT(t.id) > 0
ORDER BY total_volume DESC;
```

### User Trading Activity

```sql
SELECT 
    u.username,
    COUNT(t.id) as trade_count,
    SUM(t.amount_staked) as total_staked,
    AVG(t.price_at_execution) as avg_price
FROM users_user u
JOIN trades_trade t ON u.id = t.user_id
GROUP BY u.id, u.username
ORDER BY total_staked DESC;
```

### Materialized View Query

```sql
-- Get top tags by volume
SELECT 
    tag_name,
    market_count,
    trade_count,
    total_volume,
    avg_trade_size
FROM market_volume_by_tag
ORDER BY total_volume DESC
LIMIT 10;
```

---

## 🔐 Indexes

### Performance Indexes

All foreign keys are automatically indexed. Additional indexes:

```sql
-- Market queries
CREATE INDEX idx_markets_status ON markets_market(status);
CREATE INDEX idx_markets_ends_at ON markets_market(ends_at);
CREATE INDEX idx_markets_onchain_id ON markets_market(onchain_market_id);

-- Trade queries
CREATE INDEX idx_trades_created_at ON trades_trade(created_at);
CREATE INDEX idx_trades_market_user ON trades_trade(market_id, user_id);

-- User queries
CREATE INDEX idx_users_wallet ON users_user(wallet_address);
```

---

## 🧪 Testing Database

### Verify Schema

```bash
python manage.py dbshell
```

```sql
-- List all tables
\dt

-- Describe table
\d markets_market

-- Check indexes
\di

-- Check materialized view
\d market_volume_by_tag
```

### Verify 4NF

```sql
-- Check for redundant columns (should return 0)
SELECT COUNT(*) FROM information_schema.columns
WHERE table_name = 'markets_market'
AND column_name IN ('creator_name', 'creator_email');  -- Should not exist

-- Check junction tables exist for many-to-many
SELECT * FROM markets_marketknowledgetag LIMIT 1;
```

---

## 📊 Database Statistics

### Table Sizes

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Row Counts

```sql
SELECT 
    'users_user' as table_name, COUNT(*) as row_count FROM users_user
UNION ALL
SELECT 'markets_market', COUNT(*) FROM markets_market
UNION ALL
SELECT 'trades_trade', COUNT(*) FROM trades_trade
UNION ALL
SELECT 'liquidity_liquidityevent', COUNT(*) FROM liquidity_liquidityevent;
```

---

## 🔧 Maintenance

### Refresh Materialized View

```sql
-- Manual refresh
REFRESH MATERIALIZED VIEW CONCURRENTLY market_volume_by_tag;

-- Schedule refresh (via Celery or cron)
-- Add to celery beat schedule
```

### Vacuum & Analyze

```sql
-- Optimize tables
VACUUM ANALYZE markets_market;
VACUUM ANALYZE trades_trade;
VACUUM ANALYZE liquidity_liquidityevent;
```

### Backup

```bash
# Full backup
pg_dump -U postgres predicthub_db > backup.sql

# Restore
psql -U postgres predicthub_db < backup.sql
```

---

## 📚 Related Documentation

- **Backend**: See `../README.md`
- **Migrations**: See `../markets/migrations/`
- **Models**: See `../markets/models.py`, `../trades/models.py`, etc.

---

## 🚀 Quick Commands

```bash
# Connect to database
python manage.py dbshell

# Run migrations
python manage.py migrate

# Create migration
python manage.py makemigrations

# Seed tags
python manage.py seed_knowledge_tags

# Check migration status
python manage.py showmigrations
```

