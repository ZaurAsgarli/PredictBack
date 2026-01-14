# ML Service

Machine learning service for trade risk assessment, token behavior forecasting, and market manipulation detection. This module provides heuristic-based risk scoring and supports trained ML models when available.

## Purpose

The ML service evaluates trade risk before execution, predicts token price movements, and detects market manipulation patterns. It is called by the trade execution flow to enforce circuit breakers and auto-ban high-risk users.

## Responsibilities

- Feature engineering from trade data
- Risk score calculation (heuristic-based, with fallback to trained models if available)
- Token behavior prediction (Model 3)
- Market manipulation detection (Model 4)
- Platform health monitoring (Model 5)
- Prediction storage to database and file logs

**Does NOT own**:
- API endpoints (exposed via `backend_api/api/ml_api/`)
- Trade execution logic (called by `backend_api/api/trades/`)
- Database models (defined in `ml_service.training.models`)

## Model Types

### Model 1: Trade Risk Prediction

**Type**: Heuristic Algorithm (with optional Isolation Forest fallback)

**Current Implementation**: Deterministic heuristic, not a trained ML model.

**Formula**:
```
Risk Score = (failed_logins * 0.2) + (trade_velocity_factor * 0.3) + (stake_factor * 0.5) + age_penalty

Where:
- failed_logins: Count of failed login attempts (default: 0)
- trade_velocity_factor: 1.0 if time_since_last_trade < 10 seconds, else 100 / (time_diff + 1), capped at 1.0
- stake_factor: 1.0 if stake_ratio > 3.0, else stake_ratio / 3.0
  (stake_ratio = amount_staked / (user_avg_stake + 1.0))
- age_penalty: 0.5 if wallet_age_days < 1, else 0.0
```

**Risk Level Thresholds**:
- `score > 0.85`: HIGH risk → Trade REJECTED
- `score > 0.90`: CRITICAL risk → Trade REJECTED + User AUTO-BANNED
- `score > 0.5`: MEDIUM risk → Trade allowed, logged
- `score <= 0.5`: LOW risk → Trade allowed

**Threshold Rationale**:
- 0.85: Circuit breaker threshold. Trades above this are likely anomalous (high velocity, large stake relative to history, or new account).
- 0.90: Auto-ban threshold. Indicates severe risk (combination of multiple risk factors).

**Location**: `ml_service/training/model_loader.py:predict_trade_risk()`

**Trained Model Fallback**: If `isolation_forest.pkl` exists, the heuristic is bypassed and the trained model is used. Currently, the heuristic is always used.

### Model 3: Token Behavior Forecasting

**Type**: XGBoost Classifier (if model file exists, otherwise not used)

**Purpose**: Predict token price movement direction (UP/DOWN/FLAT) for a given market.

**Features**: Market-specific features loaded from `model3_token_xgb_features.pkl`. Features are not documented in code and must match training data.

**Output**:
- `predicted_label`: "UP", "DOWN", or "FLAT"
- `proba`: Probability distribution over labels
- `risk_score`: Confidence score (0.0 to 1.0), calculated as `2 * (max_prob - 0.5)` if max_prob >= 0.5, else 0.0

**Location**: `ml_service/training/model_loader.py:predict_token_behavior()`

**Status**: Model files may not exist. Function raises `TokenBehaviorModelError` if files are missing.

### Model 4: Market Manipulation Detection

**Type**: Graph Analytics + Classification (heuristic-based)

**Purpose**: Detect coordinated attacks, pump & dump schemes, and wash trading.

**Methodology**:
1. Build wallet-to-wallet transaction graph
2. Detect cliques (coordinated wallet clusters)
3. Analyze patterns (pump & dump, wash trading)
4. Calculate manipulation score (0-1)

**Location**: `ml_service/training/notebooks/model_4_manipulation.py`

**Status**: Implemented in notebooks, not integrated into API endpoints.

### Model 5: Platform Health Early Warning System (MHEWS)

**Type**: Meta-Model (Aggregation)

**Purpose**: Aggregate signals from Models 1-4 to assess overall platform health.

**Input**: Outputs from Models 1-4 (anomaly rates, exposure, token behavior, manipulation rates)

**Output**:
- `platform_stress_level`: Overall stress (0-1)
- `systemic_risk_index`: Systemic risk (0-1)
- `health_status`: "HEALTHY", "STABLE", "ELEVATED", "WARNING", "CRITICAL"
- `alert_level`: "LOW", "MEDIUM", "HIGH", "CRITICAL"

**Location**: `ml_service/training/notebooks/model_5_mhews.py`

**Status**: Implemented in notebooks, partially integrated via `ml_service/training/services/mhews_service.py`.

## Feature Sources

### Model 1 Features

**Input Columns** (required):
- `user_id`: User identifier
- `created_at`: Trade timestamp (ISO format string or datetime)
- `amount_staked`: Trade amount (float)

**Engineered Features** (output of `build_features()`):
- `amount_staked`: Original stake amount
- `time_since_last_trade`: Seconds since user's previous trade (0.0 for first trade)
- `hour_of_day`: Hour of day (0-23)
- `user_total_trades`: Total trade count for user (from input DataFrame)
- `user_avg_stake`: Average stake amount for user (from input DataFrame)

**Additional Features** (injected by trade view):
- `failed_logins`: Count of failed login attempts (default: 0, not currently fetched)
- `wallet_age_days`: Account age in days (default: 100, not currently calculated from user.date_joined)

**Location**: `ml_service/training/features.py:build_features()`

### Model 3 Features

**Source**: Loaded from `model3_token_xgb_features.pkl` at runtime. Feature list is not hardcoded.

**Validation**: Function validates that input DataFrame has all required features before prediction.

## Training vs Inference Separation

### Training

**Location**: `ml_service/training/notebooks/`

**Notebooks**:
- `model3_token_behaviour_forcasting.ipynb`: Train Model 3
- `model_4_trainer.py`: Train Model 4
- `model_5_trainer.py`: Train Model 5

**Output**: Trained model files (`.pkl`) saved to `ml_service/training/models/`

### Inference

**Location**: `ml_service/training/model_loader.py`

**Functions**:
- `predict_trade_risk()`: Model 1 inference (heuristic)
- `predict_token_behavior()`: Model 3 inference (XGBoost, if model exists)

**Called by**: `backend_api/api/trades/views.py` (trade execution) and `backend_api/api/ml_api/views.py` (ML API endpoints)

**Storage**: Predictions stored via `ml_service/training/services/db_storage_service.py`

## Risk Scoring Logic

### Model 1 Risk Score

**Calculation**: See formula above.

**Interpretation**:
- Higher score = higher risk
- Score components are weighted: stake_factor (50%) > velocity_factor (30%) > failed_logins (20%)
- New accounts (< 1 day) get +0.5 penalty

**False Positive Risks**:
- Legitimate high-frequency traders may trigger velocity_factor
- Large legitimate trades may trigger stake_factor
- New users may be penalized by age_penalty

**Mitigation**: Thresholds (0.85, 0.90) are set high to reduce false positives. Manual review recommended for blocked trades.

### Model 3 Risk Score

**Calculation**: `2 * (max_prob - 0.5)` if max_prob >= 0.5, else 0.0

**Interpretation**:
- High confidence in UP or DOWN → high risk_score (close to 1.0)
- High confidence in FLAT → lower risk_score
- Low confidence overall → low risk_score (0.0)

**False Positive Risks**: Not applicable (predictive, not blocking).

## Known Limitations

### Model 1 (Heuristic)

1. **No Historical Context**: Current implementation passes only the current trade to `build_features()`, resulting in `time_since_last_trade = 0.0` for first trade. Overridden to 3600 seconds in trade view.

2. **Missing User Data**: `failed_logins` and `wallet_age_days` are not fetched from database. Defaults are used (0 and 100).

3. **No Trained Model**: Isolation Forest model file may not exist. Heuristic is always used.

4. **Single Trade Context**: Feature engineering requires trade history, but only current trade is passed. User statistics (total_trades, avg_stake) are calculated from single-row DataFrame, resulting in values of 1 and the current stake amount.

### Model 3

1. **Model File Dependency**: Function fails if model files are missing. No fallback.

2. **Feature Mismatch**: Features must exactly match training data. No validation of feature meaning or distribution shift.

3. **No Retraining Pipeline**: Model must be manually retrained and deployed.

### Model 4 and 5

1. **Not Integrated**: Implemented in notebooks but not called by API endpoints.

2. **Graph Construction**: Requires full trade history. May be slow for large markets.

## Execution Flow

### Trade Risk Assessment (Model 1)

```
1. Trade request arrives at TradeViewSet.create()
2. Extract trade data (user_id, amount_staked, created_at)
3. Call build_features() with single-row DataFrame
4. Override time_since_last_trade to 3600 (safe default)
5. Call predict_trade_risk(features)
6. Check circuit breaker (score > 0.85)
   - If true: Reject trade, log to DualLogger
   - If score > 0.90: Auto-ban user
7. If passed: Continue trade execution
8. Store prediction to database via DualLogger (after trade_id available)
```

**Location**: `backend_api/api/trades/views.py:98-188`

### Token Behavior Prediction (Model 3)

```
1. API request to /api/ml/token-behavior/market/{id}/
2. Load model and features from disk (cached after first load)
3. Build features DataFrame from market trade history
4. Call predict_token_behavior(features_df)
5. Return predictions with probabilities and risk scores
```

**Location**: `backend_api/api/ml_api/views.py` (if implemented)

## Interfaces

### Called By

- `backend_api/api/trades/views.py`: Trade execution flow
- `backend_api/api/ml_api/views.py`: ML API endpoints

### Calls

- `ml_service.training.models`: Database models for prediction storage
- `backend_api.core.utils.ml_logger.DualLogger`: Dual logging (file + database)

### Database Models

- `ml_service.training.models.TradeRiskPrediction`: Model 1 predictions
- `ml_service.training.models.MarketManipulationScore`: Model 4 predictions (if used)
- `ml_service.training.models.PlatformHealthMetric`: Model 5 predictions (if used)

## Security / Constraints

### Trust Boundaries

- ML service is called by backend API. No direct external access.
- Predictions are logged but not used for user-facing decisions (except circuit breaker).

### Assumptions

- Feature data is valid (no validation in `build_features()` beyond column presence)
- Model files (if present) are compatible with current code version
- Database is available for prediction storage

### Limits

- Heuristic risk score is capped at 1.0
- Model 3 requires exact feature match (no feature drift handling)
- No model versioning or A/B testing

### Fail-Safe Behavior

- If ML service fails during trade execution, trade is allowed (fail-open) but error is logged.
- If Model 3 model files are missing, API endpoint returns error (no fallback).

## File Structure

```
ml_service/
├── training/
│   ├── model_loader.py          # Model 1 & 3 inference
│   ├── features.py              # Feature engineering
│   ├── models/                  # Trained model files (.pkl)
│   ├── services/                # Service layer (DB storage, etc.)
│   ├── notebooks/               # Training notebooks
│   └── models.py                # Django models for predictions
├── data/                        # Training datasets
└── tests/                       # Unit tests
```

## Related Documentation

- `backend_api/README.md`: Backend architecture
- `backend_api/api/trades/views.py`: Trade execution with ML integration
- `ml_service/training/README.md`: Training procedures (if exists)
