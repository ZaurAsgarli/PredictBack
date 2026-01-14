# API Applications

Django applications that provide REST API endpoints for the prediction market platform. Each app is responsible for a specific domain of functionality.

## Purpose

The API layer handles HTTP requests, validates input, orchestrates business logic, and returns serialized responses. It does not contain database models (those are in each app's `models.py`) or ML logic (calls `ml_service`).

## Responsibilities

- HTTP request/response handling
- Input validation via serializers
- Business logic orchestration
- Database queries via ORM
- Response serialization

**Does NOT own**:
- Database schema (models are in each app, but schema is shared)
- ML model inference (calls `ml_service`)
- Security enforcement (uses Django permissions and `security_engine`)
- Blockchain interaction (uses `indexer` service)

## Application Breakdown

### `users/` - User Management

**Purpose**: User accounts, authentication, and profiles.

**Endpoints**:
- `POST /api/users/signup/` - User registration
- `POST /api/users/login/` - User login (JWT token)
- `GET /api/users/me/` - Current user profile
- `GET /api/users/{id}/` - User details

**Models**: `User` (custom user model with roles, wallet_address, points)

**Key Files**:
- `views.py`: `SignUpView`, login views
- `models.py`: `User` model with `Role` enum
- `serializers.py`: User serialization

**Interfaces**:
- Calls: Django auth system, JWT token generation
- Called by: Frontend, other API apps (for user lookups)

### `markets/` - Market Management

**Purpose**: Prediction markets (events) creation, listing, and resolution.

**Endpoints**:
- `GET /api/markets/` - List markets (with filtering)
- `GET /api/markets/{id}/` - Market details
- `POST /api/markets/create/` - Create new market
- `POST /api/markets/{id}/trade/` - Place trade on market

**Models**: `Market`, `MarketCategory`, `KnowledgeTag`, `Resolution`

**Key Files**:
- `views.py`: `MarketViewSet`, market creation logic
- `models.py`: Market models
- `services.py`: Market business logic (pricing, AMM)
- `polymarket_service.py`: External market integration (if used)

**Interfaces**:
- Calls: `trades` app (for trade execution), `liquidity` app (for liquidity pools)
- Called by: Frontend, `trades` app (for market validation)

### `trades/` - Trade Execution

**Purpose**: Execute trades (predictions), manage positions, integrate ML risk assessment.

**Endpoints**:
- `POST /api/trades/` - Create trade (with ML risk check)
- `GET /api/trades/` - List trades (with filtering)
- `GET /api/users/me/trades/` - User's trades

**Models**: `Trade`

**Key Files**:
- `views.py`: `TradeViewSet.create()` - Main trade execution flow with ML integration
- `models.py`: `Trade` model
- `services.py`: `TradeExecutionService` - Trade execution logic
- `tasks.py`: Celery tasks (if async processing needed)

**Execution Flow**:
1. Validate input (amount > 0, market exists, market active)
2. ML risk assessment (calls `ml_service`)
3. Circuit breaker check (score > 0.85 → reject)
4. Auto-ban check (score > 0.90 → block user)
5. Execute trade (AMM pricing, position update)
6. Store trade in database

**Interfaces**:
- Calls: `ml_service` (risk assessment), `markets` app (market validation), `positions` app (position updates)
- Called by: Frontend

### `positions/` - Position Management

**Purpose**: User positions per market (YES/NO shares, P&L).

**Endpoints**:
- `GET /api/positions/` - List positions
- `GET /api/positions/{id}/` - Position details

**Models**: `Position`

**Key Files**:
- `views.py`: `PositionViewSet`
- `models.py`: `Position` model
- `services.py`: Position calculation logic

**Interfaces**:
- Called by: `trades` app (updates positions on trade execution)
- Calls: `markets` app (for market data)

### `liquidity/` - Liquidity Management

**Purpose**: Liquidity pool management, liquidity provision events.

**Endpoints**:
- `GET /api/liquidity/` - List liquidity events
- `POST /api/liquidity/add/` - Add liquidity
- `POST /api/liquidity/remove/` - Remove liquidity

**Models**: `LiquidityEvent`, `LiquidityPool`

**Key Files**:
- `views.py`: Liquidity management views
- `models.py`: Liquidity models
- `services.py`: Liquidity calculation logic

**Interfaces**:
- Called by: `markets` app (for liquidity pool updates)
- Calls: `markets` app (for market data)

### `analytics/` - Analytics and Leaderboards

**Purpose**: User rankings, market statistics, leaderboards.

**Endpoints**:
- `GET /api/analytics/global/` - Global leaderboard
- `GET /api/analytics/weekly/` - Weekly leaderboard
- `GET /api/analytics/monthly/` - Monthly leaderboard

**Models**: None (queries other apps' models)

**Key Files**:
- `views.py`: Leaderboard calculation views
- Aggregates data from `users`, `trades`, `markets` apps

**Interfaces**:
- Calls: `users`, `trades`, `markets` apps (for data aggregation)
- Called by: Frontend

### `disputes/` - Dispute Resolution

**Purpose**: Market resolution disputes, bond management.

**Endpoints**:
- `GET /api/disputes/` - List disputes
- `POST /api/disputes/create/` - Create dispute
- `POST /api/disputes/{id}/resolve/` - Resolve dispute

**Models**: `Dispute`, `DisputeBond`

**Key Files**:
- `views.py`: Dispute management views
- `models.py`: Dispute models

**Interfaces**:
- Called by: Frontend, `markets` app (for market resolution)

### `indexer/` - Blockchain Event Indexer

**Purpose**: Sync blockchain events to database, provide JSON-RPC interface.

**Endpoints**:
- `POST /api/indexer/rpc/` - JSON-RPC 2.0 endpoint
- `GET /api/indexer/status/` - Indexer status

**Models**: `OnchainTransaction`, `OnchainEventLog`

**Key Files**:
- `views.py`: JSON-RPC server, status endpoint
- `models.py`: Indexer models
- `services/processor.py`: `EventProcessor` - Maps blockchain events to Django models
- `management/commands/listen_events.py`: Background service that polls blockchain

**Execution Flow**:
1. `listen_events` command polls blockchain for new events
2. Events passed to `EventProcessor.process_event()`
3. Processor maps event to Django model (Market, Trade, LiquidityEvent, User)
4. Event stored in `OnchainEventLog` for audit trail
5. Database models updated/created

**Interfaces**:
- Calls: Web3.py (blockchain interaction), `markets`, `trades`, `liquidity`, `users` apps (for model updates)
- Called by: Docker service (runs as background process)

### `ml_api/` - ML API Endpoints

**Purpose**: Expose ML model predictions via REST API.

**Endpoints**:
- `POST /api/ml/risk/predict/` - Trade risk prediction (Model 1)
- `GET /api/ml/token-behavior/market/{id}/` - Token behavior forecast (Model 3)
- `GET /api/ml/manipulation/market/{id}/` - Manipulation analysis (Model 4)
- `GET /api/ml/health/` - Platform health status (Model 5)

**Models**: None (uses `ml_service.training.models`)

**Key Files**:
- `views.py`: ML prediction endpoints
- Calls `ml_service` for inference

**Interfaces**:
- Calls: `ml_service` (model inference)
- Called by: Frontend (admin dashboard), `trades` app (for risk assessment)

### `admin/` - Admin Dashboard Endpoints

**Purpose**: Admin dashboard data (security logs, ML insights, statistics).

**Endpoints**:
- `GET /api/admin/ml-insights/` - ML model metrics
- `GET /api/admin/deployments/` - Deployment logs
- `GET /api/admin/logs/` - Security logs (via `security_engine`)

**Key Files**:
- `views.py`: `MLInsightsView`, `DeploymentLogsView`, `StatsView`, `SecurityLogsView`

**Interfaces**:
- Calls: `security_engine`, `ml_service` (for data aggregation)
- Called by: Frontend (admin dashboard)

**Security Note**: Currently uses `AllowAny` - must be changed to `IsAdminUser` in production.

### `webhooks/` - Webhook Handlers

**Purpose**: Handle external webhooks (blockchain events, third-party integrations).

**Endpoints**:
- `POST /api/webhook/onchain/` - Blockchain event webhook
- `POST /webhooks/onchain/` - Alternative webhook endpoint

**Key Files**:
- `onchain_webhook.py`: Webhook handler for blockchain events

**Interfaces**:
- Calls: `indexer` service (for event processing)
- Called by: External services (blockchain nodes, third-party APIs)

## Execution Flow

### Trade Creation Flow

```
1. POST /api/trades/
   ├─ TradeViewSet.create() receives request
   ├─ Validate user (IsAuthenticated)
   ├─ Validate input (serializer)
   ├─ Validate market (exists, active)
   │
2. ML Risk Assessment
   ├─ Call ml_service.training.model_loader.predict_trade_risk()
   ├─ Check circuit breaker (score > 0.85)
   ├─ Check auto-ban (score > 0.90)
   │
3. Trade Execution
   ├─ Call TradeExecutionService.execute_trade()
   ├─ Calculate position (AMM pricing)
   ├─ Update/Create Position
   ├─ Create Trade record
   │
4. Response
   └─ Return serialized Trade object
```

### Market Creation Flow

```
1. POST /api/markets/create/
   ├─ MarketViewSet or create view receives request
   ├─ Validate user (IsAuthenticated)
   ├─ Validate input (serializer)
   │
2. Market Creation
   ├─ Create Market record
   ├─ Initialize liquidity pool (if applicable)
   ├─ Link knowledge tags
   │
3. Response
   └─ Return serialized Market object
```

## Interfaces

### Between Apps

- `trades` → `markets`: Market validation
- `trades` → `positions`: Position updates
- `trades` → `ml_service`: Risk assessment
- `indexer` → `markets`, `trades`, `liquidity`, `users`: Model updates from blockchain
- `analytics` → `users`, `trades`, `markets`: Data aggregation

### External

- Frontend: All apps expose REST endpoints
- Blockchain: `indexer` app polls blockchain
- ML Service: `trades` and `ml_api` apps call ML service

## Security / Constraints

### Authentication

- Most endpoints require `IsAuthenticated` (JWT token)
- Admin endpoints currently use `AllowAny` (must be changed to `IsAdminUser`)

### Authorization

- Role-based checks are not enforced in views (roles exist but not checked)
- User blocking is enforced by ML risk assessment, not by permission checks

### Input Validation

- All endpoints use Django REST Framework serializers
- Amount validation: `amount > 0` (enforced in views)
- Market status validation: Market must be `active` for trades

### Trust Boundaries

- API apps trust each other (no inter-app authentication)
- API apps trust `ml_service` (no validation of ML responses)
- API apps trust database (no validation of model data)

## Related Documentation

- `backend_api/README.md`: Backend architecture
- `ml_service/README.md`: ML service details
- `security_engine/README.md`: Security and RBAC
- Individual app `models.py`: Database schema
