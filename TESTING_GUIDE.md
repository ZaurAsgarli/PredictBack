# Master Testing Guide - PredictHub SDF2

**Complete manual verification guide for the entire system.**

This guide walks you through verifying that the blockchain → indexer → database → ML pipeline works end-to-end.

**Estimated Time**: 5-10 minutes

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] PostgreSQL running (via Docker or local)
- [ ] Redis running (via Docker or local)
- [ ] Ganache or local blockchain node running
- [ ] Python 3.11+ with virtual environment activated
- [ ] Node.js 18+ installed
- [ ] Contract deployed and address in `.env`

---

## SECTION 1: The Setup

### Step 1.1: Start Database & Redis

**Option A: Docker (Recommended)**

```bash
docker-compose up -d db redis
```

**Verify:**
```bash
# Check PostgreSQL
docker-compose exec db pg_isready
# Should output: /var/run/postgresql:5432 - accepting connections

# Check Redis
docker-compose exec redis redis-cli ping
# Should output: PONG
```

**Option B: Local**

```bash
# Start PostgreSQL (if not running)
pg_ctl start

# Start Redis (if not running)
redis-server
```

---

### Step 1.2: Deploy Smart Contract

```bash
cd contracts

# Install dependencies (if not done)
npm install

# Start local blockchain (Ganache)
# In a separate terminal:
ganache-cli --port 8545

# Deploy contract
npx hardhat run scripts/deploy_and_export.js --network localhost
```

**Expected Output:**
```
PredictionMarket deployed to: 0x...
ABI saved to build/abi.json
ABI copied to backend utils/abis/contract.json
Deployment info saved to deployed/contract.json
```

**Verify Contract Address:**
```bash
# Check deployment file
cat deployed/contract.json

# Update backend .env
echo "CONTRACT_ADDRESS=0x..." >> ../backend/.env
```

---

### Step 1.3: Setup Backend Database

```bash
cd backend

# Run migrations
python manage.py migrate

# Seed knowledge tags
python manage.py seed_knowledge_tags

# Verify database
python manage.py dbshell
```

**In psql shell:**
```sql
-- Check tables exist
\dt

-- Check knowledge tags seeded
SELECT COUNT(*) FROM markets_knowledgetag;
-- Should return > 0

-- Exit
\q
```

---

### Step 1.4: Start Backend Server

```bash
# In backend directory
cd backend
python manage.py runserver
```

**Verify:**
- Open browser: http://localhost:8000/
- Should see JSON response with API endpoints

---

### Step 1.5: Start Indexer

**In a NEW terminal:**

```bash
cd backend
python manage.py listen_events --poll-interval 12
```

**Expected Output:**
```
[INFO] Starting event listener
[INFO] Connected to blockchain at http://localhost:8545
[INFO] Listening for events from block: 12345
```

**Keep this terminal open** - you'll see event processing logs here.

---

## SECTION 2: The Unit Tests

### Step 2.1: Smart Contract Tests

```bash
cd contracts

# Run all Brownie tests
brownie test
```

**Expected Result:**
```
======================= 39 passed, 1 warning in 10.87s ========================
```

**Verify:**
- ✅ 21 success path tests pass
- ✅ 18 error path tests pass
- ✅ All revert cases work correctly

---

### Step 2.2: Backend Tests

```bash
cd backend

# Run Django tests
pytest

# Or with coverage
pytest --cov=. --cov-report=html
```

**Expected Result:**
```
======================== test session starts =========================
collected X items
... passed
```

---

### Step 2.3: ML Integration Tests

```bash
cd backend

# Verify ML models can save to database
python manage.py verify_ml_db_integration --test-all
```

**Expected Output:**
```
[TEST] Model 1: Trade Risk Prediction Integration
✅ Model 1: Prediction saved to database
   Prediction ID: 1
   Score: 0.75
   Risk Level: LOW

[TEST] Model 4: Market Manipulation Integration
✅ Model 4: Prediction saved to database

[TEST] Model 5: Platform Health Integration
✅ Model 5: Prediction saved to database

[VERIFY] Database Storage Verification
✅ Database integration verified - predictions are being stored!
```

---

## SECTION 3: The "Golden Flow" (Manual Verification)

This section verifies the complete flow: **Blockchain Event → Indexer → Database → API → ML**

---

### 🎯 Test Scenario: User Creates Market & Adds Liquidity

---

### Step 3.1: Create Market on Blockchain

**Using Brownie Console:**

```bash
cd contracts
brownie console
```

**In Brownie console:**

```python
# Get contract
from brownie import PredictionMarket
prediction_market = PredictionMarket[-1]  # Latest deployed

# Create a market
from brownie import chain
end_time = chain.time() + 86400  # 24 hours from now
tx = prediction_market.createMarket("Test Market: Will Bitcoin hit $100k?", end_time, {'from': accounts[1]})

# Verify event emitted
print(f"Market ID: {prediction_market.marketCounter()}")
print(f"Transaction: {tx.txid}")

# Note the market ID (e.g., 1)
market_id = prediction_market.marketCounter()
```

**Expected Output:**
```
Transaction sent: 0x...
PredictionMarket.createMarket confirmed
Market ID: 1
```

**Exit Brownie console:**
```python
exit()
```

---

### Step 3.2: Verification (Indexer Log)

**Check the indexer terminal** (where you ran `listen_events`):

**Expected Log:**
```
[INFO] Event detected: MarketCreated
[INFO] Processing event: MarketCreated at block 12345
[INFO] Event processed successfully: MarketCreated
[INFO] Event detected: UserCreated
[INFO] Processing event: UserCreated
[INFO] Event processed successfully: UserCreated
```

**✅ If you see these logs, the indexer is working!**

---

### Step 3.3: Verification (Database)

**Open a new terminal:**

```bash
cd backend
python manage.py dbshell
```

**Run SQL queries:**

```sql
-- Check market was created
SELECT 
    id,
    title,
    onchain_market_id,
    creator_id,
    created_at
FROM markets_market
WHERE onchain_market_id = 1;  -- Use your market ID
```

**Expected Result:**
```
 id | title                              | onchain_market_id | creator_id | created_at
----+------------------------------------+-------------------+------------+-------------------
  1 | Test Market: Will Bitcoin hit $100k? |                 1 |           2 | 2024-01-01 12:00:00
```

```sql
-- Check user was created
SELECT 
    id,
    username,
    wallet_address,
    date_joined
FROM users_user
WHERE username LIKE '0x%'
ORDER BY date_joined DESC
LIMIT 1;
```

**Expected Result:**
```
 id | username | wallet_address | date_joined
----+----------+----------------+-------------------
  2 | 0x...    | 0x...          | 2024-01-01 12:00:00
```

```sql
-- Check event was logged
SELECT 
    event_name,
    block_number,
    transaction_hash,
    created_at
FROM indexer_onchaineventlog
WHERE event_name = 'MarketCreated'
ORDER BY created_at DESC
LIMIT 1;
```

**Expected Result:**
```
 event_name    | block_number | transaction_hash | created_at
---------------+--------------+------------------+-------------------
 MarketCreated |        12345 | 0x...            | 2024-01-01 12:00:00
```

**Exit psql:**
```sql
\q
```

**✅ If all queries return data, the indexer → database sync is working!**

---

### Step 3.4: Add Liquidity on Blockchain

**Back in Brownie console:**

```bash
brownie console
```

```python
from brownie import PredictionMarket
prediction_market = PredictionMarket[-1]

# Add liquidity (use your market ID from Step 3.1)
market_id = 1  # Replace with your market ID
amount = "10 ether"
tx = prediction_market.addLiquidity(market_id, amount, {'from': accounts[2]})

print(f"Liquidity ID: {prediction_market.liquidityCounter()}")
print(f"Transaction: {tx.txid}")

exit()
```

**Expected Output:**
```
Transaction sent: 0x...
PredictionMarket.addLiquidity confirmed
Liquidity ID: 1
```

---

### Step 3.5: Verification (Indexer Log - Liquidity)

**Check indexer terminal again:**

**Expected Log:**
```
[INFO] Event detected: LiquidityAdded
[INFO] Processing event: LiquidityAdded at block 12346
[INFO] Event processed successfully: LiquidityAdded
[INFO] Event detected: UserCreated
[INFO] Processing event: UserCreated
```

**✅ Indexer is processing liquidity events!**

---

### Step 3.6: Verification (Database - Liquidity)

**Back in psql:**

```bash
cd backend
python manage.py dbshell
```

```sql
-- Check liquidity event
SELECT 
    id,
    market_id,
    user_id,
    amount,
    onchain_liquidity_id,
    created_at
FROM liquidity_liquidityevent
WHERE onchain_liquidity_id = 1;  -- Use your liquidity ID
```

**Expected Result:**
```
 id | market_id | user_id | amount | onchain_liquidity_id | created_at
----+-----------+---------+--------+----------------------+-------------------
  1 |         1 |       3 |  10.00 |                    1 | 2024-01-01 12:05:00
```

```sql
-- Check market liquidity updated
SELECT 
    id,
    title,
    liquidity_pool
FROM markets_market
WHERE id = 1;
```

**Expected Result:**
```
 id | title                              | liquidity_pool
----+------------------------------------+----------------
  1 | Test Market: Will Bitcoin hit $100k? |        10.00
```

**Exit:**
```sql
\q
```

**✅ Database is synced with blockchain!**

---

### Step 3.7: Verification (API)

**Test API endpoints:**

```bash
# Get markets
curl http://localhost:8000/api/markets/

# Get specific market
curl http://localhost:8000/api/markets/1/

# Get liquidity events
curl http://localhost:8000/api/liquidity/
```

**Expected Response (markets):**
```json
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "title": "Test Market: Will Bitcoin hit $100k?",
      "onchain_market_id": 1,
      "liquidity_pool": "10.00",
      "status": "active"
    }
  ]
}
```

**Or open in browser:**
- http://localhost:8000/api/markets/
- http://localhost:8000/api/liquidity/

**✅ API is returning indexed data!**

---

### Step 3.8: Place a Trade & Verify ML Integration

**In Brownie console:**

```bash
brownie console
```

```python
from brownie import PredictionMarket
prediction_market = PredictionMarket[-1]

# Place a trade
market_id = 1
outcome = True  # YES
amount = "1 ether"
tx = prediction_market.placeTrade(market_id, outcome, amount, {'from': accounts[3]})

print(f"Trade ID: {prediction_market.tradeCounter()}")
exit()
```

---

### Step 3.9: Verification (ML Model)

**Test ML API:**

```bash
# Predict trade risk
curl -X POST http://localhost:8000/api/ml/risk/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 4,
    "amount_staked": 100.0,
    "created_at": "2024-01-01T12:10:00Z"
  }'
```

**Expected Response:**
```json
{
  "score": 0.75,
  "label": 1,
  "risk_level": "LOW"
}
```

**Verify in Database:**

```bash
python manage.py dbshell
```

```sql
-- Check ML prediction was saved
SELECT 
    id,
    user_id,
    score,
    label,
    risk_level,
    created_at
FROM ml_traderiskprediction
ORDER BY created_at DESC
LIMIT 1;
```

**Expected Result:**
```
 id | user_id | score | label | risk_level | created_at
----+---------+-------+-------+------------+-------------------
  1 |       4 |  0.75 |     1 | LOW        | 2024-01-01 12:10:00
```

**✅ ML model is saving predictions to database!**

---

### Step 3.10: Verification (Complete Flow Summary)

**Run final verification queries:**

```sql
-- Summary: All components working
SELECT 
    'Markets' as component,
    COUNT(*) as count
FROM markets_market
WHERE onchain_market_id IS NOT NULL

UNION ALL

SELECT 
    'Trades',
    COUNT(*)
FROM trades_trade
WHERE onchain_trade_id IS NOT NULL

UNION ALL

SELECT 
    'Liquidity Events',
    COUNT(*)
FROM liquidity_liquidityevent
WHERE onchain_liquidity_id IS NOT NULL

UNION ALL

SELECT 
    'ML Predictions',
    COUNT(*)
FROM ml_traderiskprediction

UNION ALL

SELECT 
    'Indexed Events',
    COUNT(*)
FROM indexer_onchaineventlog;
```

**Expected Result:**
```
 component         | count
-------------------+-------
 Markets           |     1
 Trades            |     1
 Liquidity Events  |     1
 ML Predictions    |     1
 Indexed Events    |     3
```

**✅ All components are working!**

---

## SECTION 4: Advanced Verification

### Step 4.1: Verify Materialized View

```sql
-- Refresh and query materialized view
REFRESH MATERIALIZED VIEW market_volume_by_tag;

SELECT 
    tag_name,
    market_count,
    total_volume
FROM market_volume_by_tag
ORDER BY total_volume DESC;
```

**✅ Dashboard view is working!**

---

### Step 4.2: Verify JSON-RPC Server

```bash
# Test RPC endpoint
curl -X POST http://localhost:8000/api/indexer/rpc/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "get_indexer_status",
    "params": {},
    "id": 1
  }'
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "running",
    "latest_block": 12350,
    "events_processed": 3
  },
  "id": 1
}
```

**✅ RPC server is working!**

---

### Step 4.3: Verify Platform Health (Model 5)

```bash
# Get platform health
curl http://localhost:8000/api/ml/health/
```

**Expected Response:**
```json
{
  "platform_stress_level": 0.25,
  "systemic_risk_index": 0.15,
  "health_status": "HEALTHY",
  "alert_level": "LOW"
}
```

**Verify in Database:**

```sql
SELECT 
    health_status,
    alert_level,
    platform_stress_level,
    created_at
FROM ml_platformhealthmetric
ORDER BY created_at DESC
LIMIT 1;
```

**✅ Platform health monitoring is working!**

---

## ✅ Final Checklist

After completing all steps, verify:

- [ ] **Smart Contract**: Market created, liquidity added, trade placed
- [ ] **Indexer**: Events logged in terminal
- [ ] **Database**: Data appears in tables (markets, trades, liquidity, users)
- [ ] **API**: Endpoints return data
- [ ] **ML Models**: Predictions saved to database
- [ ] **Materialized View**: Dashboard view queryable
- [ ] **RPC Server**: JSON-RPC endpoint responds

---

## 🐛 Troubleshooting

### Indexer Not Processing Events

**Check:**
1. Contract address in `backend/.env` matches deployed contract
2. Web3 provider URL is correct
3. Blockchain node is running
4. Check indexer logs for errors

**Fix:**
```bash
# Verify contract address
cd backend
python manage.py shell
>>> from utils.contracts import get_contract_service
>>> service = get_contract_service()
>>> print(service.contract_address)
```

### Database Not Updating

**Check:**
1. Migrations are applied: `cd backend && python manage.py migrate`
2. Indexer is running: Check terminal logs
3. Events are being emitted: Check blockchain explorer

**Fix:**
```sql
-- Check if events are being logged
SELECT COUNT(*) FROM indexer_onchaineventlog;
```

### ML Predictions Not Saving

**Check:**
1. ML models exist: `ls ml/models/*.pkl`
2. Database tables exist: `cd backend && python manage.py migrate ml`
3. API is calling storage service

**Fix:**
```bash
# Verify ML integration
cd backend
python manage.py verify_ml_db_integration --test-all
```

---

## 📊 Expected Results Summary

After completing the Golden Flow, you should have:

| Component | Expected Count |
|-----------|----------------|
| Markets (on-chain) | 1 |
| Markets (database) | 1 |
| Trades (on-chain) | 1 |
| Trades (database) | 1 |
| Liquidity Events (on-chain) | 1 |
| Liquidity Events (database) | 1 |
| Users (database) | 2+ (from events) |
| Indexed Events | 4+ (MarketCreated, UserCreated x2, LiquidityAdded, TradeExecuted) |
| ML Predictions | 1+ |

---

## 🎯 Success Criteria

**System is working correctly if:**

1. ✅ Blockchain events are emitted
2. ✅ Indexer logs show event processing
3. ✅ Database tables contain synced data
4. ✅ API endpoints return the data
5. ✅ ML models save predictions
6. ✅ All unit tests pass

**If all criteria are met, the SDF2 system is fully functional!** 🎉

---

## 📚 Next Steps

- **Production Deployment**: See `backend/README.md`
- **API Documentation**: http://localhost:8000/swagger/
- **Admin Panel**: http://localhost:8000/admin/
- **Monitoring**: Use JSON-RPC endpoint for health checks

---

## 🔗 Quick Reference

### Key Commands

```bash
# Start services
docker-compose up -d db redis
cd backend && python manage.py runserver
cd backend && python manage.py listen_events

# Run tests
cd contracts && brownie test
cd backend && pytest

# Verify
cd backend && python manage.py verify_ml_db_integration --test-all
```

### Key URLs

- API Root: http://localhost:8000/
- Swagger: http://localhost:8000/swagger/
- Admin: http://localhost:8000/admin/
- GraphQL: http://localhost:8000/graphql/

### Key SQL Queries

```sql
-- Check indexed events
SELECT * FROM indexer_onchaineventlog ORDER BY created_at DESC LIMIT 10;

-- Check markets
SELECT * FROM markets_market WHERE onchain_market_id IS NOT NULL;

-- Check ML predictions
SELECT * FROM ml_traderiskprediction ORDER BY created_at DESC LIMIT 10;
```

---

**End of Testing Guide** ✅

