# Sprint 2 Diagnosis Report

## Issues Identified

### 1. Database Configuration
- ❌ SQLite still referenced in `settings.py` (USE_SQLITE flag)
- ❌ `db.sqlite3` file exists and should be removed/ignored
- ⚠️ PostgreSQL config uses hardcoded values instead of env vars
- ✅ docker-compose.yml has PostgreSQL but needs pgAdmin

### 2. Database Schema & Migrations
- ⚠️ Migrations exist but may be inconsistent
- ✅ Models appear to match ERD
- ⚠️ Missing indexes for: user_id (in some tables), block_number (comprehensive)
- ✅ Materialized view SQL exists but needs migration

### 3. Smart Contract
- ⚠️ Contract uses `TradePlaced` but requirement mentions `TradeExecuted` - keeping TradePlaced as it's already implemented
- ⚠️ Hardhat config needs Sepolia network setup
- ⚠️ Deploy script needs environment variable support
- ✅ Tests exist (10+)
- ✅ ABI exists in utils/abi/

### 4. Indexer/ETL
- ⚠️ Services exist but need proper structure (listener.py, backfill.py, event_decoder.py)
- ✅ Idempotent saving implemented (unique constraint on tx_hash + log_index)
- ⚠️ WebSocket listener needs proper implementation
- ✅ Logging infrastructure exists

### 5. Environment Variables
- ⚠️ Missing .env.example with all required vars
- ⚠️ Settings need to use env vars for PostgreSQL

### 6. Indexes Required
- ✅ tx_hash - exists in multiple tables
- ✅ market_id - exists
- ⚠️ user_id - needs verification in all tables
- ✅ outcome_type - exists
- ✅ event_name - exists
- ✅ block_number - exists

## Fix Plan

1. Remove all SQLite references
2. Update settings.py to use PostgreSQL from env vars
3. Update docker-compose.yml to add pgAdmin
4. Delete/reset migrations and create fresh ones
5. Add all required indexes
6. Create materialized view migration
7. Fix smart contract deployment script
8. Restructure indexer services
9. Create .env.example
10. Generate deliverables

