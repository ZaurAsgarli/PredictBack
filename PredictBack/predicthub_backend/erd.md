# Entity Relationship Diagram

## PredictHub Backend Database Schema

```
┌─────────────┐
│    User     │
├─────────────┤
│ id (PK)     │
│ username    │
│ email       │
│ password    │
│ total_points│
│ win_rate    │
│ streak      │
│ created_at  │
└─────────────┘
      │
      │ 1
      │
      │ *
┌─────┴─────────────┐
│      Trade        │
├───────────────────┤
│ id (PK)           │
│ user_id (FK)      │
│ market_id (FK)    │
│ outcome_type      │
│ trade_type        │
│ amount_staked     │
│ tokens_amount     │
│ price_at_execution│
│ onchain_tx_hash   │
│ onchain_trade_id  │
│ created_at        │
└───────────────────┘
      │
      │ *
      │
      │ 1
┌─────┴─────────────┐
│     Market        │
├───────────────────┤
│ id (PK)           │
│ title             │
│ description       │
│ category_id (FK)  │
│ status            │
│ resolution_outcome│
│ liquidity_pool    │
│ fee_percentage    │
│ onchain_market_id │
│ onchain_tx_hash   │
│ created_by (FK)   │
│ created_at        │
│ ends_at           │
└───────────────────┘
      │
      │ 1
      │
      │ *
┌─────┴─────────────┐
│  OutcomeToken     │
├───────────────────┤
│ id (PK)           │
│ market_id (FK)    │
│ outcome_type      │
│ price             │
│ supply            │
│ created_at        │
│ updated_at        │
└───────────────────┘

┌─────────────┐
│   Market   │
└─────┬───────┘
      │
      │ 1
      │
      │ *
┌─────┴─────────────┐
│    Position       │
├───────────────────┤
│ id (PK)           │
│ user_id (FK)      │
│ market_id (FK)    │
│ yes_tokens        │
│ no_tokens         │
│ total_staked      │
│ created_at        │
│ updated_at        │
└───────────────────┘
      │
      │ *
      │
      │ 1
┌─────┴─────────────┐
│      User         │
└───────────────────┘

┌─────────────┐
│   Market    │
└─────┬───────┘
      │
      │ 1
      │
      │ 1
┌─────┴─────────────┐
│   Resolution      │
├───────────────────┤
│ id (PK)           │
│ market_id (FK)    │
│ resolved_outcome  │
│ resolver (FK)     │
│ dispute_window    │
│ bond_amount       │
│ onchain_tx_hash   │
│ created_at        │
└───────────────────┘
      │
      │ 1
      │
      │ *
┌─────┴─────────────┐
│     Dispute       │
├───────────────────┤
│ id (PK)           │
│ market_id (FK)    │
│ user_id (FK)      │
│ bond_amount       │
│ status            │
│ reason            │
│ created_at        │
│ resolved_at       │
└───────────────────┘

┌─────────────┐
│   Market   │
└─────┬───────┘
      │
      │ 1
      │
      │ *
┌─────┴─────────────┐
│  PriceHistory      │
├───────────────────┤
│ id (PK)           │
│ market_id (FK)    │
│ yes_price         │
│ no_price          │
│ timestamp         │
└───────────────────┘

┌─────────────┐
│   Market    │
└─────┬───────┘
      │
      │ 1
      │
      │ *
┌─────┴─────────────┐
│ LiquidityEvent    │
├───────────────────┤
│ id (PK)           │
│ market_id (FK)    │
│ user_id (FK)      │
│ event_type        │
│ amount            │
│ onchain_tx_hash   │
│ onchain_liquidity_id│
│ created_at        │
└───────────────────┘

┌─────────────┐
│   Market    │
└─────┬───────┘
      │
      │ *
      │
      │ 1
┌─────┴─────────────┐
│ MarketCategory    │
├───────────────────┤
│ id (PK)           │
│ name              │
│ slug              │
│ description       │
│ created_at        │
└───────────────────┘
```

## Relationships

- **User** → **Trade** (1:N) - A user can have many trades
- **User** → **Position** (1:N) - A user can have many positions
- **User** → **Dispute** (1:N) - A user can create many disputes
- **User** → **LiquidityEvent** (1:N) - A user can create many liquidity events
- **Market** → **Trade** (1:N) - A market can have many trades
- **Market** → **Position** (1:N) - A market can have many positions
- **Market** → **OutcomeToken** (1:2) - A market has exactly 2 outcome tokens (YES/NO)
- **Market** → **Resolution** (1:1) - A market can have one resolution
- **Market** → **Dispute** (1:N) - A market can have many disputes
- **Market** → **PriceHistory** (1:N) - A market has many price history records
- **Market** → **LiquidityEvent** (1:N) - A market can have many liquidity events
- **Market** → **MarketCategory** (N:1) - Many markets belong to one category
- **Resolution** → **Dispute** (1:N) - A resolution can have many disputes

## Indexer Models

```
┌──────────────────────┐
│ OnchainTransaction   │
├──────────────────────┤
│ id (PK)              │
│ tx_hash (UNIQUE)     │
│ network              │
│ block_number         │
│ status               │
│ error_message        │
│ created_at           │
│ updated_at           │
└──────────────────────┘
      │
      │ 1
      │
      │ *
┌─────┴──────────────────┐
│ OnchainEventLog        │
├────────────────────────┤
│ id (PK)                │
│ onchain_tx (FK)        │
│ event_name             │
│ tx_hash                │
│ log_index              │
│ market_id (FK)         │
│ user_address           │
│ payload_json           │
│ processed_at           │
│ duplicate              │
│ created_at             │
└────────────────────────┘
      │
      │ *
      │
      │ 1
┌─────┴─────────────┐
│     Market        │
└───────────────────┘
```

## Materialized View

```
┌──────────────────────┐
│ market_activity_view │
├──────────────────────┤
│ market_id (PK)       │
│ title                │
│ status               │
│ total_trades         │
│ total_liquidity_added│
│ last_activity_timestamp│
│ volume_24h           │
│ open_interest        │
└──────────────────────┘
```

