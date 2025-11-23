# Indexer Documentation

The indexer is responsible for syncing blockchain events from the PredictionMarket smart contract to the Django database.

## Architecture

The indexer consists of:

1. **Contract Service** (`utils/contracts.py`): Web3 connection and contract interaction
2. **Event Processor** (`indexer/services.py`): Processes events and maps to Django models
3. **Management Commands**: `listen_events` and `backfill`

## Setup

### 1. Configure Environment Variables

Add to your `.env` file:

```bash
WEB3_PROVIDER_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
CONTRACT_ADDRESS=0x...
CONTRACT_ABI_PATH=/path/to/smart_contracts/build/abi.json
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Live Event Listening

Start the event listener to process new events in real-time:

```bash
python manage.py listen_events
```

Options:
- `--poll-interval`: Polling interval in seconds (default: 12)
- `--from-block`: Start from specific block number (default: latest - 100)

Example:
```bash
python manage.py listen_events --poll-interval 6 --from-block 5000000
```

### Historical Backfill

Backfill historical events from a block range:

```bash
python manage.py backfill --from-block 5000000 --to-block 5100000
```

Options:
- `--from-block`: Start block (required)
- `--to-block`: End block (default: latest)
- `--batch-size`: Blocks per batch (default: 1000)

Example:
```bash
python manage.py backfill --from-block 5000000 --to-block 5100000 --batch-size 500
```

## Event Processing

The indexer processes the following events:

### MarketCreated
- Creates a new `Market` record
- Links via `onchain_market_id`

### TradeExecuted
- Creates a new `Trade` record
- Updates user positions

### LiquidityAdded
- Creates a new `LiquidityEvent` record
- Updates market liquidity pool

### MarketResolved
- Updates market status to 'resolved'
- Creates a `Resolution` record

## Idempotency

Events are deduplicated using:
- `tx_hash` + `log_index` unique constraint
- Duplicate detection in `OnchainEventLog.duplicate` field

## Error Handling

- Failed transactions are marked with status 'FAILED'
- Processing errors are logged
- Retry logic can be added for transient failures

## Monitoring

### Admin Panel

Access monitoring views in Django admin:
- `/admin/indexer/recent-events/` - Recent blockchain events
- `/admin/indexer/backfill-status/` - Backfill job status
- `/admin/indexer/heartbeat/` - Indexer health status

### Logs

ETL logs are stored in:
```
LOGS/etl/backfill_<from>_<to>_<timestamp>.json
```

Log format:
```json
{
  "start_time": "2024-01-01T00:00:00",
  "end_time": "2024-01-01T01:00:00",
  "duration_seconds": 3600,
  "from_block": 5000000,
  "to_block": 5100000,
  "total_blocks": 100001,
  "total_events_found": 150,
  "total_events_processed": 148,
  "errors": []
}
```

## Database Models

### OnchainTransaction
Stores blockchain transaction metadata.

### OnchainEventLog
Stores individual event logs with:
- Event name
- Transaction hash and log index
- Decoded payload (JSON)
- Processing status

## Troubleshooting

### Web3 Connection Issues
- Check `WEB3_PROVIDER_URL` is correct
- Verify network connectivity
- Check API key validity

### Missing Events
- Run backfill for historical blocks
- Check event filters in contract service
- Verify contract address is correct

### Duplicate Events
- Check `OnchainEventLog.duplicate` field
- Verify unique constraint on `(tx_hash, log_index)`

## Performance

- Batch processing for backfill (configurable batch size)
- Indexed queries on `tx_hash`, `event_name`, `market_id`
- Efficient event filtering using Web3 event logs

## Future Enhancements

- WebSocket subscriptions for real-time events
- Automatic retry for failed events
- Event replay functionality
- Multi-chain support

