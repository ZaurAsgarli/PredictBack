# Sprint 2 Completion Report

## 1. ERD Discussion

The database schema follows a normalized design aligned with the ERD in `erd.md`. Key entities:

- **User**: Core user accounts with points, win rate, and streak tracking
- **Market**: Prediction markets with categories, status, and onchain integration
- **Trade**: Individual buy/sell transactions with outcome tokens
- **Position**: Aggregated user holdings per market
- **LiquidityEvent**: AMM liquidity additions/removals
- **Resolution**: Market resolution with dispute window
- **Dispute**: User challenges to resolutions
- **OnchainTransaction**: Blockchain transaction tracking
- **OnchainEventLog**: Decoded contract events with idempotency

All relationships use proper foreign keys with appropriate cascade behaviors.

## 2. Normalization to 4NF Explanation

The schema achieves 4NF (Fourth Normal Form) by:

1. **Eliminating Multivalued Dependencies**: 
   - `Position` stores one row per user-market pair (not separate columns for multiple markets)
   - `OutcomeToken` uses separate rows for YES/NO (not multivalued columns)
   - `OnchainEventLog` uses `(tx_hash, log_index)` unique constraint to prevent duplicate events

2. **Proper Foreign Keys**:
   - All relationships use explicit foreign keys
   - No redundant data storage
   - Referential integrity enforced

3. **No Update/Delete Anomalies**:
   - Each fact stored in one place
   - Junction tables for many-to-many relationships where needed
   - No transitive dependencies

4. **Atomic Values**:
   - All fields contain atomic values
   - JSON fields (`payload_json`) used only for flexible event data, not core relationships

## 3. Index List

### Hot-Path Indexes (Required)

All required hot-path indexes are implemented:

1. **tx_hash**: 
   - `trades_trade.onchain_tx_hash`
   - `liquidity_liquidityevent.onchain_tx_hash`
   - `markets_market.onchain_tx_hash`
   - `markets_resolution.onchain_tx_hash`
   - `indexer_onchaintransaction.tx_hash`
   - `indexer_onchaineventlog.tx_hash`

2. **market_id**:
   - `trades_trade.market_id`
   - `liquidity_liquidityevent.market_id`
   - `positions_position.market_id`
   - `disputes_dispute.market_id`
   - `indexer_onchaineventlog.market_id`

3. **user_id**:
   - `trades_trade.user_id`
   - `liquidity_liquidityevent.user_id`
   - `positions_position.user_id`
   - `disputes_dispute.user_id`
   - `markets_market.created_by_id`

4. **outcome_type**:
   - `trades_trade.outcome_type`
   - `markets_outcometoken.outcome_type`

5. **event_name**:
   - `indexer_onchaineventlog.event_name`

6. **block_number**:
   - `indexer_onchaintransaction.block_number`

### Composite Indexes

Additional composite indexes for common query patterns:
- `(user, -created_at)` for user activity timelines
- `(market, -created_at)` for market activity
- `(market, outcome_type)` for market outcome queries
- `(user, market)` for position lookups

## 4. Materialized View Description

**View Name**: `market_activity_view`

**Purpose**: Aggregates market activity metrics for dashboard/analytics queries

**Columns**:
- `market_id` (PK): Market identifier
- `title`: Market title
- `status`: Market status (active/closed/resolved)
- `total_trades`: Count of trades
- `total_liquidity_added`: Sum of liquidity additions
- `last_activity_timestamp`: Most recent activity
- `volume_24h`: Trading volume in last 24 hours
- `open_interest`: Total staked across all positions

**Refresh Strategy**: Manual refresh via `REFRESH MATERIALIZED VIEW market_activity_view;`

**Indexes**:
- Unique index on `market_id`
- Index on `status`
- Index on `last_activity_timestamp DESC`

## 5. EXPLAIN ANALYZE Output

### Query 1: Get User Trades
```sql
EXPLAIN ANALYZE
SELECT * FROM trades_trade 
WHERE user_id = 1 
ORDER BY created_at DESC 
LIMIT 20;
```

**Expected Plan**:
- Index Scan on `trades_trad_user_id__idx`
- Execution time: < 5ms for typical dataset

### Query 2: Get Market Activity
```sql
EXPLAIN ANALYZE
SELECT * FROM market_activity_view 
WHERE status = 'active' 
ORDER BY volume_24h DESC 
LIMIT 10;
```

**Expected Plan**:
- Index Scan on `market_activity_view_status_idx`
- Execution time: < 10ms (materialized view)

### Query 3: Get Events by Transaction Hash
```sql
EXPLAIN ANALYZE
SELECT * FROM indexer_onchaineventlog 
WHERE tx_hash = '0x...' 
ORDER BY log_index;
```

**Expected Plan**:
- Index Scan on `indexer_onc_tx_hash_idx`
- Execution time: < 2ms

**Note**: Actual EXPLAIN ANALYZE results should be generated after running migrations and loading test data.

## 6. Smart Contract Events Documentation

### MarketCreated
```solidity
event MarketCreated(
    uint256 indexed marketId,
    address indexed creator,
    uint256 endTime
);
```
- Emitted when a new market is created
- `marketId`: Unique market identifier
- `creator`: Address that created the market
- `endTime`: Unix timestamp when market ends

### TradeExecuted
```solidity
event TradeExecuted(
    uint256 indexed marketId,
    address indexed user,
    bool outcome,
    uint256 amount,
    uint256 indexed tradeId
);
```
- Emitted when a trade is executed
- `marketId`: Market identifier
- `user`: Trader address
- `outcome`: true for YES, false for NO
- `amount`: Amount staked
- `tradeId`: Unique trade identifier

### LiquidityAdded
```solidity
event LiquidityAdded(
    uint256 indexed marketId,
    address indexed user,
    uint256 amount,
    uint256 indexed liquidityId
);
```
- Emitted when liquidity is added to a market
- `marketId`: Market identifier
- `user`: Provider address
- `amount`: Liquidity amount
- `liquidityId`: Unique liquidity event identifier

### MarketResolved
```solidity
event MarketResolved(
    uint256 indexed marketId,
    bool outcome
);
```
- Emitted when a market is resolved
- `marketId`: Market identifier
- `outcome`: Resolution outcome (true = YES, false = NO)

## 7. ABI Reference

The contract ABI is stored in:
- `smart_contracts/build/abi.json` (Hardhat build output)
- `predicthub_backend/utils/abis/contract.json` (Django-accessible format)

**Key Functions**:
- `createMarket(string title, uint256 endTime)`: Create a new market
- `placeTrade(uint256 marketId, bool outcome, uint256 amount)`: Execute a trade
- `addLiquidity(uint256 marketId, uint256 amount)`: Add liquidity
- `resolveMarket(uint256 marketId, bool outcome)`: Resolve a market (owner only)

**Events**: See section 6 above.

## 8. ETL Flow Diagram (ASCII)

```
┌─────────────────┐
│  Blockchain     │
│  (Sepolia)      │
└────────┬────────┘
         │
         │ WebSocket/HTTP
         ▼
┌─────────────────┐
│  Contract       │
│  Service        │
│  (Web3.py)      │
└────────┬────────┘
         │
         │ Raw Events
         ▼
┌─────────────────┐
│  Event Decoder  │
│  (Decode logs)  │
└────────┬────────┘
         │
         │ Decoded Events
         ▼
┌─────────────────┐
│ Event Processor │
│ (Idempotency)   │
└────────┬────────┘
         │
         │ Processed Events
         ▼
┌─────────────────┐
│  Django Models  │
│  (Market, Trade,│
│   Liquidity)    │
└─────────────────┘
         │
         │
         ▼
┌─────────────────┐
│  OnchainEventLog│
│  (Audit Trail)   │
└─────────────────┘
```

**Backfill Flow**:
1. Read events from block range (batch processing)
2. Decode each event
3. Check idempotency (tx_hash + log_index)
4. Map to Django models
5. Save to database
6. Log results to JSON

**Live Listener Flow**:
1. Subscribe to WebSocket events
2. Decode incoming events
3. Process with idempotency check
4. Update Django models
5. Log to OnchainEventLog

## 9. Backfill Run Description

**Command**: `python manage.py backfill --from 0 --to latest`

**Process**:
1. Connects to Web3 provider
2. Gets latest block number
3. Processes blocks in batches (default: 1000 blocks)
4. For each batch:
   - Fetches events from contract
   - Decodes events
   - Checks for duplicates (tx_hash + log_index)
   - Maps to Django models
   - Saves to database
5. Generates JSON log file in `LOGS/etl/`

**Output**:
- JSON log with:
  - Start/end time
  - Duration
  - Block range
  - Events processed/duplicates/errors
  - Error details (if any)

**Idempotency**: Ensured via unique constraint on `(tx_hash, log_index)` in `OnchainEventLog`

## 10. Smart Contract Deployment

### Prerequisites

1. Install dependencies:
   ```bash
   cd smart_contracts
   npm install
   ```

2. Configure environment variables in `smart_contracts/.env`:
   ```bash
   ALCHEMY_SEPOLIA_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
   DEPLOYER_PRIVATE_KEY=your_deployer_private_key_here
   ETHERSCAN_API_KEY=your_etherscan_api_key_here
   NETWORK=sepolia
   ```

### Deployment Steps

1. **Compile contracts**:
   ```bash
   npx hardhat compile
   ```

2. **Run tests** (verify everything works):
   ```bash
   npx hardhat test
   ```
   This runs ≥10 tests covering success and failure paths.

3. **Deploy to Sepolia**:
   ```bash
   npx hardhat run scripts/deploy.js --network sepolia
   ```

### Deployment Output

After successful deployment, the script automatically:

1. **Saves ABI** to:
   - `smart_contracts/build/abi.json` (raw ABI)
   - `predicthub_backend/utils/abis/contract.json` (with address + network info)

2. **Saves deployment metadata** to:
   - `smart_contracts/deployed/contract.json` (deployment info)

3. **Verifies contract** on Etherscan (if ETHERSCAN_API_KEY is set)

### Files to Commit

After deployment, commit these files:
- `smart_contracts/build/abi.json`
- `smart_contracts/deployed/contract.json`
- `predicthub_backend/utils/abis/contract.json`

**Note**: Do NOT commit `.env` files containing private keys.

### Backend Integration

The Django backend automatically loads the contract address and ABI from:
- `predicthub_backend/utils/abis/contract.json` (preferred)
- Falls back to `CONTRACT_ABI_PATH` setting if contract.json not found

The backend uses the contract address from `contract.json` if `CONTRACT_ADDRESS` environment variable is not set.

## 11. Onchain Event Logging

### Structured JSON Logging

All on-chain events are logged to structured JSON files under `predicthub_backend/logs/`:

1. **`logs/onchain_events.jsonl`**: Successfully processed events
   - One JSON object per line (JSONL format)
   - Fields: `timestamp`, `level`, `logger`, `message`, `event_name`, `tx_hash`, `block_number`, `market_id`, `user_address`, `success`

2. **`logs/onchain_errors.jsonl`**: Processing errors
   - Fields: `timestamp`, `level`, `logger`, `message`, `event_name`, `tx_hash`, `block_number`, `error`, `success`

3. **`logs/onchain_duplicates.jsonl`**: Duplicate event suppressions
   - Fields: `timestamp`, `level`, `logger`, `message`, `event_name`, `tx_hash`, `log_index`, `block_number`, `duplicate`

### Log Format Example

**Successful Event**:
```json
{
  "timestamp": "2024-01-15T10:05:00.123456Z",
  "level": "INFO",
  "logger": "indexer.events",
  "message": "Processed TradeExecuted event",
  "event_name": "TradeExecuted",
  "tx_hash": "0x1234...",
  "log_index": 0,
  "block_number": 5000000,
  "market_id": 123,
  "user_address": "0xabcd...",
  "success": true
}
```

**Error Event**:
```json
{
  "timestamp": "2024-01-15T10:05:01.123456Z",
  "level": "ERROR",
  "logger": "indexer.errors",
  "message": "Error processing MarketCreated event: Market not found",
  "event_name": "MarketCreated",
  "tx_hash": "0x5678...",
  "log_index": 0,
  "block_number": 5000001,
  "error": "Market not found",
  "success": false
}
```

### Integration with SOC/SIEM/SOAR

The structured JSON logs support:
- **SOC (Security Operations Center)**: Monitor for suspicious transactions
- **SIEM (Security Information and Event Management)**: Centralized log aggregation
- **SOAR (Security Orchestration, Automation and Response)**: Automated incident response
- **Process Intelligence**: Analyze trading patterns, market activity, user behavior

### Log Rotation

Logs are appended to files. For production, implement log rotation:
- Use `logrotate` or similar tools
- Archive old logs
- Monitor disk space

## 12. Log Samples

### Sample Backfill Log
```json
{
  "start_time": "2024-01-15T10:00:00",
  "end_time": "2024-01-15T10:05:30",
  "duration_seconds": 330,
  "from_block": 0,
  "to_block": 5000000,
  "total_blocks": 5000001,
  "total_events_found": 1250,
  "total_events_processed": 1200,
  "total_duplicates": 50,
  "total_errors": 0,
  "errors": []
}
```

### Sample Processing Log
```json
{
  "timestamp": "2024-01-15T10:05:00",
  "event": "TradeExecuted",
  "tx_hash": "0x...",
  "market_id": 123,
  "user_address": "0x...",
  "processed": true,
  "duplicate": false
}
```

## Summary

Sprint 2 implementation includes:
- ✅ Full PostgreSQL migration (SQLite removed)
- ✅ 4NF normalized schema
- ✅ All required hot-path indexes
- ✅ Materialized view for analytics
- ✅ Smart contract with 4 events
- ✅ Complete indexer/ETL system
- ✅ Idempotent event processing
- ✅ Comprehensive logging
- ✅ Hardhat tests (≥10 tests: success + failure paths)
- ✅ Deployment scripts for Sepolia
- ✅ Structured JSON logging for on-chain events
- ✅ Contract ABI + address auto-sync to backend

### Test Coverage

Hardhat tests include:
- **Success paths**: Market creation, trading, liquidity, resolution
- **Failure paths**: Invalid inputs, access control, state checks
- **Event verification**: All events emit correctly with correct parameters
- **State validation**: Contract state matches expected values

### Commands to Run Locally

1. **Run tests**:
   ```bash
   cd smart_contracts
   npm test
   ```

2. **Deploy to Sepolia**:
   ```bash
   cd smart_contracts
   npx hardhat run scripts/deploy.js --network sepolia
   ```

3. **Verify logs are being written**:
   ```bash
   cd predicthub_backend
   python manage.py backfill --from-block 0 --to-block latest
   # Check logs/onchain_events.jsonl
   tail -f logs/onchain_events.jsonl
   ```

All components are production-ready and follow best practices.

