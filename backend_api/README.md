# PredictHub Backend

Django REST API backend for a decentralized prediction market platform. This document describes the architecture, execution flow, data stores, and production readiness considerations.

## Architecture Overview

The backend is organized into distinct layers:

```
┌─────────────────────────────────────────┐
│         API Layer (REST/GraphQL)       │
│  /api/users, /api/markets, /api/trades  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Business Logic Layer               │
│  Services, Serializers, ViewSets        │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼───┐ ┌───▼───┐ ┌───▼────┐
│  ML   │ │Security│ │Indexer │
│Service│ │ Engine │ │Service │
└───┬───┘ └───┬───┘ └───┬────┘
    │          │          │
┌───▼──────────▼──────────▼───┐
│      PostgreSQL Database     │
└─────────────────────────────┘
```

## Execution vs Settlement Distinction

**Execution**: The backend executes trades immediately upon API request. Trades are validated, ML risk assessment is performed, and positions are updated in the database synchronously.

**Settlement**: Blockchain settlement is simulated. The indexer service listens to blockchain events and syncs them to the database, but trades are not required to be on-chain before execution. The system maintains an off-chain ledger that can be reconciled with on-chain events.

**What is Simulated**:
- Blockchain transaction submission (trades execute off-chain first)
- Real-time blockchain event processing (indexer polls at intervals)
- Smart contract state (database is source of truth for positions)

**What is Real**:
- Database persistence (PostgreSQL)
- ML risk assessment (heuristic-based, not trained models)
- Security logging and rate limiting
- User authentication and authorization

## Request Lifecycle

### Trade Execution Flow

```
1. HTTP Request → POST /api/trades/
   ├─ Authentication check (JWT)
   ├─ Input validation (amount > 0, market exists, market active)
   └─ User permission check (not blocked)

2. ML Risk Assessment
   ├─ Feature extraction (user history, trade amount, velocity)
   ├─ Risk score calculation (heuristic: failed_logins * 0.2 + velocity * 0.3 + stake * 0.5)
   ├─ Circuit breaker check (score > 0.85 → REJECT)
   └─ Auto-ban check (score > 0.90 → BLOCK user)

3. Trade Execution (if risk check passes)
   ├─ Position calculation (AMM pricing)
   ├─ Database transaction (atomic)
   │  ├─ Create Trade record
   │  ├─ Update/Create Position
   │  └─ Update Market liquidity
   └─ Response to client

4. Blockchain Sync (async, via indexer)
   ├─ Indexer polls blockchain events
   ├─ EventProcessor maps events to models
   └─ Database reconciliation (if needed)
```

### Market Creation Flow

```
1. HTTP Request → POST /api/markets/create/
   ├─ Authentication check
   ├─ Input validation
   └─ Creator permission check

2. Market Creation
   ├─ Create Market record in database
   ├─ Initialize liquidity pool (if applicable)
   └─ Return market details

3. Blockchain Sync (async)
   ├─ Indexer detects MarketCreated event
   ├─ Link onchain_market_id to database record
   └─ Update market status
```

## Data Stores and Their Roles

### PostgreSQL Database

**Primary Data Store**: All application state is stored in PostgreSQL.

**Key Tables**:
- `users_user`: User accounts, roles, wallet addresses
- `markets_market`: Prediction markets, status, resolution
- `trades_trade`: All executed trades (off-chain ledger)
- `positions_position`: User positions per market
- `liquidity_liquidityevent`: Liquidity provision events
- `indexer_onchaintransaction`: Blockchain transactions
- `indexer_onchaineventlog`: Indexed blockchain events
- `ml_traderiskprediction`: ML risk predictions
- `security_logs`: Security audit trail
- `login_attempts`: Authentication attempts

**Normalization**: 4NF (Fourth Normal Form) - eliminates multi-valued dependencies and join dependencies.

**Materialized Views**: `market_volume_by_tag` - pre-aggregated analytics for dashboard.

### Redis

**Cache**: Not currently used for caching.

**Message Broker**: Used by Celery for async task queue (not actively used in current implementation).

### File System

**Logs**: Structured JSON logs in `backend_api/logs/`
- `django.log`: Application logs
- `security.log`: Security events
- `transactions.log`: Trade execution logs
- `ml_engine.log`: ML prediction logs
- `onchain_events.jsonl`: Indexed blockchain events
- `onchain_errors.jsonl`: Indexer errors
- `onchain_duplicates.jsonl`: Duplicate event suppression

**ML Logs**: `backend_api/ml_logs/` - JSONL files for ML predictions (dual logging with database).

## Failure Modes

### ML Service Failure

**Behavior**: Fail-open. If ML risk assessment fails, the trade is allowed but the error is logged.

**Location**: `backend_api/api/trades/views.py:185-188`

**Rationale**: Prevents ML service downtime from blocking all trades. Risk is acceptable because:
- Heuristic fallback is deterministic
- Security logging captures failures
- Admin can review failed assessments

### Database Connection Failure

**Behavior**: Request fails with 500 error. No partial state.

**Mitigation**: Django ORM transactions ensure atomicity. Failed requests do not create partial records.

### Indexer Failure

**Behavior**: Blockchain events are not synced to database. Trades continue to execute off-chain.

**Impact**: Database and blockchain state may diverge. Manual reconciliation required.

**Recovery**: Indexer supports backfilling historical events via management command.

### Rate Limit Exceeded

**Behavior**: Request returns 429 Too Many Requests. Event logged to `security_logs`.

**Limits**:
- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour

## Module Responsibilities

### `backend_api/api/` - API Applications

**Purpose**: REST API endpoints and business logic.

**Responsibilities**:
- HTTP request handling
- Input validation
- Business logic orchestration
- Response serialization

**Does NOT own**:
- Database models (defined in each app)
- ML model inference (calls `ml_service`)
- Security enforcement (uses `security_engine`)
- Blockchain interaction (uses `indexer`)

See `backend_api/api/README.md` for detailed app breakdown.

### `backend_api/core/` - Core Utilities

**Purpose**: Shared utilities, middleware, and Django configuration.

**Responsibilities**:
- Django settings
- URL routing
- Middleware (logging, error handling, security)
- Contract interaction utilities
- ML logging utilities

**Does NOT own**:
- Business logic (in `api/` apps)
- ML models (in `ml_service/`)
- Security models (in `security_engine/`)

See `backend_api/core/README.md` for details.

### `ml_service/` - Machine Learning

**Purpose**: ML model inference and risk assessment.

**Responsibilities**:
- Feature engineering
- Risk score calculation (heuristic-based)
- Model loading (if trained models exist)
- Prediction storage

**Does NOT own**:
- API endpoints (exposed via `backend_api/api/ml_api/`)
- Database models (defined in `ml_service.training.models`)
- Trade execution (called by `trades` app)

**Important**: Current implementation uses heuristic algorithms, not trained ML models. See `ml_service/README.md` for model details.

### `security_engine/` - Security Layer

**Purpose**: Security event logging and monitoring.

**Responsibilities**:
- Security log storage (`SecurityLog`, `LoginAttempt` models)
- Rate limit violation detection (via Django REST Framework)
- Security event serialization
- Admin dashboard data

**Does NOT own**:
- Rate limiting enforcement (Django REST Framework)
- Authentication (Django auth system)
- Authorization (Django permissions)

See `security_engine/README.md` for RBAC and enforcement details.

### `backend_api/api/indexer/` - Blockchain Indexer

**Purpose**: Sync blockchain events to database.

**Responsibilities**:
- Poll blockchain for events
- Process events via `EventProcessor`
- Store events in database
- Provide JSON-RPC interface for status

**Does NOT own**:
- Smart contract deployment (external)
- Blockchain transaction submission (simulated)
- Market/trade creation (handled by API apps)

## Production Readiness

### What Works Now

- User authentication (JWT)
- Trade execution with ML risk assessment
- Market creation and management
- Position tracking
- Security logging
- Rate limiting
- API documentation (Swagger)

### What Needs to Change

1. **Admin Authentication**: Admin endpoints use `AllowAny` in development. Must switch to `IsAdminUser` in production.
   - Location: `backend_api/api/admin/views.py`
   - Impact: Security vulnerability if deployed as-is

2. **ML Models**: Currently uses heuristic algorithms. For production:
   - Train actual ML models (Isolation Forest, XGBoost)
   - Replace heuristic in `ml_service/training/model_loader.py`
   - Validate model performance on test data

3. **Blockchain Integration**: Currently simulated. For production:
   - Implement real transaction submission to blockchain
   - Add transaction confirmation waiting
   - Implement retry logic for failed transactions
   - Add blockchain state reconciliation

4. **Error Handling**: Some endpoints return generic 500 errors. Should:
   - Add structured error responses
   - Implement error tracking (Sentry, etc.)
   - Add retry logic for transient failures

5. **Monitoring**: No APM or alerting. Should add:
   - Application performance monitoring
   - Error rate alerting
   - ML model performance tracking
   - Security event alerting

6. **Database**: No connection pooling or read replicas. Should:
   - Configure PgBouncer or similar
   - Add read replicas for analytics queries
   - Implement database backup strategy

7. **Caching**: Redis is configured but not used. Should:
   - Cache market data
   - Cache user positions
   - Cache leaderboard data

8. **Testing**: Limited test coverage. Should add:
   - Unit tests for all services
   - Integration tests for API endpoints
   - E2E tests for critical flows
   - Load testing

## Development Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 15+
- Redis 7+ (optional, for Celery)
- Docker and Docker Compose (recommended)

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Docker Development

```bash
# Start all services
cd infrastructure
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Access Django shell
docker-compose exec web python manage.py shell
```

## Key Configuration

### Environment Variables

- `SECRET_KEY`: Django secret key (required)
- `DEBUG`: Enable debug mode (False in production)
- `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Database connection
- `CELERY_BROKER_URL`: Redis URL for Celery (optional)
- `WEB3_PROVIDER_HTTP`: Blockchain RPC endpoint
- `CONTRACT_ADDRESS`: Deployed smart contract address

### Django Settings

- `INSTALLED_APPS`: All Django apps and third-party packages
- `MIDDLEWARE`: Request processing pipeline
- `REST_FRAMEWORK`: API configuration (pagination, throttling, authentication)
- `CORS_ALLOWED_ORIGINS`: Allowed frontend origins

## API Documentation

- Swagger UI: `http://localhost:8000/swagger/`
- ReDoc: `http://localhost:8000/redoc/`
- GraphQL Playground: `http://localhost:8000/graphql/`

## Testing

Run the master integration test suite:

```bash
python tests/master_integration_suite.py
```

This verifies:
- Database connectivity
- API endpoints
- Security features
- ML model inference

See `TESTING_GUIDE.md` in project root for detailed testing procedures.

## Related Documentation

- `backend_api/api/README.md` - API applications breakdown
- `backend_api/core/README.md` - Core utilities
- `ml_service/README.md` - ML models and risk assessment
- `security_engine/README.md` - Security and RBAC
- `database_layer/docs/README.md` - Database schema
