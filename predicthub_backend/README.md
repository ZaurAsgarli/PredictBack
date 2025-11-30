# PredictHub Backend

Django backend for the PredictHub prediction market platform with blockchain event indexing and ML model integration.

---

## 🏗️ Architecture

### Core Components

1. **Indexer** (`indexer/`): Bridges blockchain events to database
2. **API** (`markets/`, `trades/`, etc.): REST endpoints for frontend
3. **ML Services** (`ml/`): Data science models for risk analysis
4. **Event Processing**: Real-time blockchain event synchronization

---

## 🔄 Indexer Logic

### Event Listener (`indexer/services/listener.py`)

The indexer listens to blockchain events and syncs them to PostgreSQL.

**How it works:**

1. **WebSocket/Polling**: Connects to blockchain node (WebSocket preferred, polling fallback)
2. **Event Subscription**: Subscribes to contract events:
   - `UserCreated`
   - `MarketCreated`
   - `TradeExecuted` (aliased as `TransactionCreated`)
   - `LiquidityAdded`
   - `MarketResolved`

3. **Event Processing**: For each event:
   - Decodes event data using ABI
   - Checks for duplicates (idempotency)
   - Maps to Django models
   - Saves to database

**Example Flow:**

```
Blockchain: UserCreated(address user) emitted
    ↓
Listener: Catches event at block 12345
    ↓
Decoder: Decodes address = 0xABC...
    ↓
Processor: Creates/updates User in database
    ↓
Database: users_user table updated
```

### Event Processor (`indexer/services.py`)

The `EventProcessor` class handles mapping events to database models:

- **`_process_user_created()`**: Creates user in `users_user` table
- **`_process_market_created()`**: Creates market in `markets_market` table
- **`_process_trade_executed()`**: Creates trade in `trades_trade` table
- **`_process_liquidity_added()`**: Creates liquidity event in `liquidity_liquidityevent` table
- **`_process_market_resolved()`**: Updates market resolution status

**Idempotency**: Uses `transaction_hash` + `log_index` to prevent duplicate processing.

---

## 🚀 Running the Server

### Development Mode

```bash
# 1. Activate virtual environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Run migrations
python manage.py migrate

# 3. Seed knowledge tags
python manage.py seed_knowledge_tags

# 4. Start Django server
python manage.py runserver

# 5. Start indexer (in another terminal)
python manage.py listen_events --poll-interval 12
```

### Docker Mode

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f indexer
docker-compose logs -f web
```

### Production Mode

```bash
# Use Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Use systemd for indexer
systemctl start predicthub-indexer
```

---

## 📡 API Endpoints

### Core Endpoints

#### Markets

- `GET /api/markets/` - List all markets (paginated)
- `GET /api/markets/{id}/` - Get market details
- `POST /api/markets/create/` - Create market (admin)
- `GET /api/markets/{id}/trades/` - Get market trades

#### Trades

- `POST /api/markets/{id}/trade/` - Place a trade
- `GET /api/trades/` - List all trades
- `GET /api/trades/user/` - Get user's trades

#### Positions

- `GET /api/positions/` - List positions
- `GET /api/positions/user/` - Get user positions

#### Indexer

- `POST /api/indexer/webhook/` - Webhook for events
- `POST /api/indexer/rpc/` - JSON-RPC 2.0 endpoint

**JSON-RPC Methods:**
- `get_indexer_status` - Get indexer health
- `get_latest_block` - Get latest indexed block
- `get_event_count` - Get event counts
- `get_user_by_address` - Get user by wallet address
- `get_market_by_onchain_id` - Get market by on-chain ID
- `list_recent_events` - List recent events

#### ML Endpoints

- `POST /api/ml/risk/predict/` - Predict trade risk
- `GET /api/ml/exposure/user/{id}/` - Get user exposure
- `GET /api/ml/manipulation/market/{id}/` - Get manipulation analysis
- `GET /api/ml/health/` - Get platform health

### Authentication

Most endpoints require JWT authentication:

```bash
# Login
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Use token
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/markets/
```

---

## 🔍 Indexer Management

### Start Indexer

```bash
# Development (polling mode)
python manage.py listen_events --poll-interval 12

# Production (WebSocket mode)
# Set WEB3_PROVIDER_WS in .env
python manage.py listen_events
```

### Check Indexer Status

```bash
# Via Django admin
http://localhost:8000/admin/indexer/recent-events/

# Via JSON-RPC
curl -X POST http://localhost:8000/api/indexer/rpc/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "get_indexer_status",
    "params": {},
    "id": 1
  }'
```

### Backfill Historical Events

```bash
python manage.py backfill_events --from-block 0 --to-block 100000
```

---

## 🗄️ Database Integration

### Event → Database Mapping

| Event | Database Table | Model Method |
|-------|---------------|--------------|
| `UserCreated` | `users_user` | `_process_user_created()` |
| `MarketCreated` | `markets_market` | `_process_market_created()` |
| `TradeExecuted` | `trades_trade` | `_process_trade_executed()` |
| `LiquidityAdded` | `liquidity_liquidityevent` | `_process_liquidity_added()` |
| `MarketResolved` | `markets_market` | `_process_market_resolved()` |

### Verification

```sql
-- Check indexed events
SELECT event_name, COUNT(*) 
FROM indexer_onchaineventlog 
GROUP BY event_name;

-- Check users created from blockchain
SELECT username, email, date_joined 
FROM users_user 
WHERE username LIKE '0x%';

-- Check markets
SELECT onchain_market_id, title, created_at 
FROM markets_market 
WHERE onchain_market_id IS NOT NULL;
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Database
POSTGRES_DB=predicthub_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Blockchain
WEB3_PROVIDER_URL=http://localhost:8545
WEB3_PROVIDER_WS=ws://localhost:8545  # Optional, for WebSocket
CONTRACT_ADDRESS=0x...
PRIVATE_KEY=your-private-key  # For sending transactions

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Contract ABI Location

The indexer reads the contract ABI from:
- `utils/abis/contract.json` (created by deployment script)

This file contains:
```json
{
  "abi": [...],
  "address": "0x...",
  "network": "sepolia",
  "chainId": "11155111"
}
```

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_api.py
pytest tests/test_models.py

# With coverage
pytest --cov=. --cov-report=html
```

### Test Indexer

```bash
# Test event processing
python manage.py shell
>>> from indexer.services import EventProcessor
>>> processor = EventProcessor()
>>> # Create test event data
>>> result = processor.process_event(test_event_data)
```

---

## 📊 Monitoring

### Logs

Indexer logs are written to:
- Console (stdout)
- Django logging system
- `LOGS/etl/` directory (if configured)

### Health Checks

```bash
# Check indexer heartbeat
curl http://localhost:8000/admin/indexer/heartbeat/

# Check system health via RPC
curl -X POST http://localhost:8000/api/indexer/rpc/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"get_system_health","params":{},"id":1}'
```

---

## 🐛 Troubleshooting

### Indexer Not Processing Events

1. **Check contract address**:
   ```bash
   python manage.py shell
   >>> from utils.contracts import get_contract_service
   >>> service = get_contract_service()
   >>> print(service.contract_address)
   ```

2. **Check Web3 connection**:
   ```bash
   >>> service.is_connected()
   True
   ```

3. **Check latest block**:
   ```bash
   >>> service.get_latest_block()
   12345
   ```

### Events Not Appearing in Database

1. **Check event logs**:
   ```sql
   SELECT * FROM indexer_onchaineventlog 
   ORDER BY created_at DESC LIMIT 10;
   ```

2. **Check for errors**:
   ```bash
   docker-compose logs indexer | grep ERROR
   ```

3. **Verify event processor**:
   ```bash
   python manage.py shell
   >>> from indexer.services import EventProcessor
   >>> processor = EventProcessor()
   >>> # Test with sample event
   ```

---

## 📚 Related Documentation

- **Database Schema**: See `db_docs/README.md`
- **ML Models**: See `ml/README.md`
- **Smart Contracts**: See `../smart_contracts/README.md`
- **Testing Guide**: See `../TESTING_GUIDE.md`

---

## 🚀 Quick Commands

```bash
# Start everything
docker-compose up -d

# Run migrations
python manage.py migrate

# Start indexer
python manage.py listen_events

# Check status
curl http://localhost:8000/api/indexer/rpc/ -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"get_indexer_status","params":{},"id":1}'

# View API docs
open http://localhost:8000/swagger/
```

