# pgAdmin Setup Instructions

## Access pgAdmin

1. **Start Docker services:**
   ```bash
   docker-compose up -d db pgadmin
   ```

2. **Access pgAdmin Web UI:**
   - Open browser: http://localhost:5050
   - Login with:
     - Email: `admin@gmail.com` (or from `.env` `PGADMIN_EMAIL`)
     - Password: `admin` (or from `.env` `PGADMIN_PASSWORD`)

## Connect to PostgreSQL Database

1. **Right-click on "Servers"** in the left panel
2. **Select "Register" → "Server"**

3. **In the "General" tab:**
   - Name: `PredictHub DB` (or any name you prefer)

4. **In the "Connection" tab:**
   - Host name/address: `db` (Docker service name)
   - Port: `5432`
   - Maintenance database: `predicthub_db`
   - Username: `postgres` (or from `.env` `POSTGRES_USER`)
   - Password: `postgres` (or from `.env` `POSTGRES_PASSWORD`)
   - ✅ Check "Save password"

5. **Click "Save"**

## Verify Connection

1. Expand the server connection
2. Expand "Databases" → `predicthub_db`
3. Expand "Schemas" → "public" → "Tables"
4. You should see all tables:
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

## View Materialized View

1. Expand "Schemas" → "public" → "Materialized Views"
2. You should see: `market_activity_view`

## Troubleshooting

- **Connection refused**: Ensure `db` service is running: `docker-compose ps`
- **Authentication failed**: Check `.env` file for correct `POSTGRES_USER` and `POSTGRES_PASSWORD`
- **Can't see tables**: Run migrations: `docker-compose exec web python manage.py migrate`

