# How to Check Your PostgreSQL Database

Multiple methods to access and inspect your PostgreSQL database.

## Method 1: pgAdmin (Visual - Recommended) 🌟

### Step 1: Access pgAdmin
1. Make sure containers are running:
   ```bash
   docker-compose up -d
   ```

2. Open browser: **http://localhost:5050**

3. Login:
   - **Email:** `admin@gmail.com` (or from `.env` `PGADMIN_EMAIL`)
   - **Password:** `admin` (or from `.env` `PGADMIN_PASSWORD`)

### Step 2: Connect to Database
1. Right-click **"Servers"** → **"Register"** → **"Server"**

2. **General Tab:**
   - Name: `PredictHub DB`

3. **Connection Tab:**
   - **Host name/address:** `db` (Docker service name)
   - **Port:** `5432`
   - **Maintenance database:** `predicthub_db`
   - **Username:** `postgres` (or from `.env`)
   - **Password:** `postgres` (or from `.env`)
   - ✅ Check **"Save password"**

4. Click **"Save"**

### Step 3: Browse Database
- Expand: **Servers** → **PredictHub DB** → **Databases** → **predicthub_db** → **Schemas** → **public** → **Tables**

You'll see all your tables:
- `users`
- `markets_market`
- `markets_marketcategory`
- `trades_trade`
- `positions_position`
- `liquidity_liquidityevent`
- `disputes_dispute`
- `indexer_onchaintransaction`
- `indexer_onchaineventlog`
- etc.

### View Data
- Right-click any table → **"View/Edit Data"** → **"All Rows"**

### Run Queries
- Right-click database → **"Query Tool"**
- Type SQL queries:
  ```sql
  SELECT * FROM markets_market;
  SELECT COUNT(*) FROM users;
  SELECT * FROM trades_trade LIMIT 10;
  ```

---

## Method 2: psql Command Line

### Connect via Docker
```bash
docker-compose exec db psql -U postgres -d predicthub_db
```

### Useful Commands in psql:
```sql
-- List all tables
\dt

-- List all databases
\l

-- Describe a table
\d markets_market

-- Count records
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM markets_market;
SELECT COUNT(*) FROM trades_trade;

-- View data
SELECT * FROM markets_market LIMIT 10;
SELECT * FROM users;

-- Exit
\q
```

### Quick One-Line Queries
```bash
# Count users
docker-compose exec db psql -U postgres -d predicthub_db -c "SELECT COUNT(*) FROM users;"

# List all tables
docker-compose exec db psql -U postgres -d predicthub_db -c "\dt"

# View markets
docker-compose exec db psql -U postgres -d predicthub_db -c "SELECT id, title, status FROM markets_market;"
```

---

## Method 3: Django Shell

### Access Django Shell
```bash
docker-compose exec web python manage.py shell
```

### Check Database in Python
```python
from django.db import connection
from markets.models import Market, MarketCategory
from users.models import User
from trades.models import Trade

# Count records
print(f"Users: {User.objects.count()}")
print(f"Markets: {Market.objects.count()}")
print(f"Categories: {MarketCategory.objects.count()}")
print(f"Trades: {Trade.objects.count()}")

# List all tables
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cursor.fetchall()
    for table in tables:
        print(table[0])

# View specific data
for market in Market.objects.all()[:5]:
    print(f"{market.id}: {market.title} - {market.status}")

# Raw SQL query
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM markets_market")
    count = cursor.fetchone()[0]
    print(f"Total markets: {count}")

exit()
```

---

## Method 4: Quick Verification Script

### Run Verification
```bash
docker-compose exec web python manage.py shell < check_setup.py
```

This will show:
- Database connection status
- All table counts
- Superuser status
- Migration status

---

## Method 5: Direct SQL Queries

### Using docker-compose exec
```bash
# List all tables
docker-compose exec db psql -U postgres -d predicthub_db -c "\dt"

# Count records in each table
docker-compose exec db psql -U postgres -d predicthub_db -c "
SELECT 
    schemaname,
    tablename,
    (SELECT COUNT(*) FROM information_schema.tables t2 
     WHERE t2.table_schema = t1.schemaname 
     AND t2.table_name = t1.tablename) as row_count
FROM pg_tables t1
WHERE schemaname = 'public'
ORDER BY tablename;
"

# View market data
docker-compose exec db psql -U postgres -d predicthub_db -c "
SELECT id, title, status, liquidity_pool, created_at 
FROM markets_market 
ORDER BY created_at DESC 
LIMIT 5;
"
```

---

## Quick Reference: Database Connection Info

From your `docker-compose.yml`:

- **Host (from Docker):** `db`
- **Host (from local machine):** `localhost`
- **Port:** `5432`
- **Database:** `predicthub_db` (or from `.env` `POSTGRES_DB`)
- **Username:** `postgres` (or from `.env` `POSTGRES_USER`)
- **Password:** `postgres` (or from `.env` `POSTGRES_PASSWORD`)

---

## Common Queries

### Check All Tables and Row Counts
```sql
SELECT 
    table_name,
    (SELECT COUNT(*) 
     FROM information_schema.tables t2 
     WHERE t2.table_schema = 'public' 
     AND t2.table_name = t.table_name) as estimated_rows
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

### View Recent Markets
```sql
SELECT id, title, status, created_at 
FROM markets_market 
ORDER BY created_at DESC 
LIMIT 10;
```

### View User Statistics
```sql
SELECT 
    username, 
    email, 
    total_points, 
    win_rate, 
    streak,
    created_at
FROM users
ORDER BY total_points DESC;
```

### Check Materialized View
```sql
SELECT * FROM market_activity_view LIMIT 10;
```

---

## Troubleshooting

### Can't connect to database
```bash
# Check if database container is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Authentication failed
- Check your `.env` file for correct credentials
- Default: `postgres` / `postgres`

### Tables not showing
```bash
# Run migrations
docker-compose exec web python manage.py migrate
```

### pgAdmin not accessible
- Check if pgAdmin container is running: `docker-compose ps pgadmin`
- Check port 5050 is not in use
- Access: http://localhost:5050

---

## Recommended: Use pgAdmin

**pgAdmin is the easiest way** to visually browse your database, run queries, and view data. It's already configured in your docker-compose.yml!

Just:
1. Start containers: `docker-compose up -d`
2. Open: http://localhost:5050
3. Login and connect to database

Happy database exploring! 🎉

