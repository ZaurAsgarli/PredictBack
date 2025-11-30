# ML Models - PredictHub Data Science

Machine learning models for risk analysis, manipulation detection, and platform health monitoring.

---

## 🤖 Models Overview

### Model 1: Trade Risk Detection (Suspicious Trades)

**Type**: Anomaly Detection (Isolation Forest)

**Purpose**: Detects suspicious or anomalous trading patterns.

**Input Features:**
- `amount_staked`: Trade amount
- `time_since_last_trade`: Time since user's last trade
- `hour_of_day`: Hour when trade was placed
- `user_total_trades`: User's total trade count
- `user_avg_stake`: User's average stake amount

**Output:**
- `score`: Anomaly score (-1.0 to 1.0)
- `label`: Prediction (1 = normal, -1 = anomaly)
- `risk_level`: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`

**Storage**: Saved to `ml_traderiskprediction` table

**API Endpoint**: `POST /api/ml/risk/predict/`

---

### Model 4: Market Manipulation Detection

**Type**: Graph Analytics + Classification

**Purpose**: Detects coordinated attacks, pump & dump schemes, and wash trading.

**Methodology:**
1. **Graph Construction**: Builds wallet-to-wallet transaction graph
2. **Clique Detection**: Identifies coordinated wallet clusters
3. **Pattern Analysis**: Detects pump & dump and wash trading patterns
4. **Scoring**: Calculates manipulation score (0-1)

**Input:**
- Trade data (user_id, market_id, amount, timestamp)
- Time window for coordination detection

**Output:**
- `manipulation_score`: Overall manipulation score (0-1)
- `is_manipulation_suspected`: Boolean flag
- `pump_dump_score`: Pump & dump score
- `wash_trading_score`: Wash trading score
- `clique_id`: Detected clique ID
- `risk_level`: Risk classification

**Storage**: Saved to `ml_marketmanipulationscore` table

**API Endpoints**:
- `GET /api/ml/manipulation/market/{id}/` - Market analysis
- `GET /api/ml/manipulation/user/{id}/` - User risk

---

### Model 5: Platform Health Early Warning System (MHEWS)

**Type**: Meta-Model (Aggregation)

**Purpose**: Aggregates signals from Models 1-4 to assess overall platform health.

**Input:**
- Outputs from Model 1 (anomaly rates)
- Outputs from Model 2 (position exposure)
- Outputs from Model 3 (token behavior)
- Outputs from Model 4 (manipulation rates)

**Output:**
- `platform_stress_level`: Overall stress (0-1)
- `systemic_risk_index`: Systemic risk (0-1)
- `health_status`: `HEALTHY`, `STABLE`, `ELEVATED`, `WARNING`, `CRITICAL`
- `alert_level`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `alert_messages`: Human-readable alerts

**Storage**: Saved to `ml_platformhealthmetric` table

**API Endpoints**:
- `GET /api/ml/health/` - Current health status
- `GET /api/ml/health/dashboard/` - Dashboard data

---

## 📥 Input Features

### Feature Engineering (`ml/features.py`)

The `build_features()` function transforms raw trade data into model-ready features:

```python
def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build features for Model 1 (Trade Risk).
    
    Input columns:
    - user_id
    - created_at
    - amount_staked
    
    Output columns:
    - amount_staked
    - time_since_last_trade
    - hour_of_day
    - user_total_trades
    - user_avg_stake
    """
```

**Usage:**
```python
from ml.features import build_features
import pandas as pd

df = pd.DataFrame([{
    'user_id': 1,
    'created_at': '2024-01-01T12:00:00Z',
    'amount_staked': 100.0
}])

features = build_features(df)
```

---

## 📤 Output Destination

### Database Storage

All model predictions are saved to the database:

#### Trade Risk Predictions (`ml_traderiskprediction`)

```python
from ml.services.db_storage_service import save_trade_risk_prediction

save_trade_risk_prediction(
    user_id=1,
    trade_id=123,
    market_id=5,
    score=0.75,
    label=1,
    risk_level='LOW',
    features={'amount_staked': 100.0}
)
```

#### Manipulation Scores (`ml_marketmanipulationscore`)

```python
from ml.services.db_storage_service import save_manipulation_score

save_manipulation_score(
    market_id=5,
    user_id=1,
    manipulation_score=0.85,
    is_manipulation_suspected=True,
    risk_level='HIGH',
    pump_dump_score=0.9,
    wash_trading_score=0.7
)
```

#### Platform Health Metrics (`ml_platformhealthmetric`)

```python
from ml.services.db_storage_service import save_platform_health_metric

save_platform_health_metric(
    platform_stress_level=0.65,
    systemic_risk_index=0.55,
    health_status='ELEVATED',
    alert_level='MEDIUM',
    model1_stress_score=0.6,
    model2_stress_score=0.5,
    model3_stress_score=0.7,
    model4_stress_score=0.8
)
```

### Audit Log (`ml_modelpredictionaudit`)

All predictions are also logged to the audit table for compliance:

```sql
SELECT 
    model_name,
    COUNT(*) as prediction_count,
    MAX(created_at) as latest_prediction
FROM ml_modelpredictionaudit
GROUP BY model_name;
```

---

## 🔄 Model Integration Flow

### Model 1 Flow

```
API Request → predict_trade_risk_view()
    ↓
build_features() → Feature engineering
    ↓
predict_trade_risk() → Model prediction
    ↓
save_trade_risk_prediction() → Database storage
    ↓
Response → Return score & risk_level
```

### Model 4 Flow

```
API Request → get_market_manipulation_analysis()
    ↓
Query trades from database
    ↓
detect_market_manipulation() → Graph analysis
    ↓
save_manipulation_score() → Database storage
    ↓
Response → Return manipulation analysis
```

### Model 5 Flow

```
API Request → get_platform_health_status()
    ↓
Aggregate signals from Models 1-4
    ↓
calculate_market_health() → Meta-model
    ↓
save_platform_health_metric() → Database storage
    ↓
Response → Return health status
```

---

## 🧪 Testing & Verification

### Verify ML DB Integration

```bash
# Run verification command
python manage.py verify_ml_db_integration --test-all

# Test individual models
python manage.py verify_ml_db_integration --test-model1
python manage.py verify_ml_db_integration --test-model4
python manage.py verify_ml_db_integration --test-model5
```

### Query Predictions

```python
from ml.models import TradeRiskPrediction, MarketManipulationScore, PlatformHealthMetric

# Get recent high-risk trades
high_risk = TradeRiskPrediction.objects.filter(
    risk_level__in=['HIGH', 'CRITICAL']
).order_by('-created_at')[:10]

# Get markets with manipulation
suspected = MarketManipulationScore.objects.filter(
    is_manipulation_suspected=True
)

# Get latest health status
latest_health = PlatformHealthMetric.objects.latest('created_at')
print(f"Status: {latest_health.health_status}, Stress: {latest_health.platform_stress_level:.2%}")
```

---

## 📊 Model Files

### Core Model Files

- `model_loader.py` - Loads trained models (Isolation Forest)
- `model_4_manipulation.py` - Manipulation detection logic
- `model_5_mhews.py` - Platform health calculation
- `features.py` - Feature engineering
- `exposure.py` - Position exposure calculations

### Service Files

- `services/db_storage_service.py` - Database storage functions
- `services/exposure_service.py` - Model 2 (exposure) service
- `services/manipulation_service.py` - Model 4 service
- `services/mhews_service.py` - Model 5 service

### Trained Models

- `models/isolation_forest.pkl` - Trained Model 1
- `models/feature_scaler.pkl` - Feature scaler

---

## 🔧 Configuration

### Model Paths

Models are loaded from:
```python
MODEL_DIR = Path(__file__).parent / "models"
ISOLATION_FOREST_PATH = MODEL_DIR / "isolation_forest.pkl"
SCALER_PATH = MODEL_DIR / "feature_scaler.pkl"
```

### Model Versions

Each prediction stores a model version:
```python
model_version = 'v1.0'  # Default
```

Update version when retraining models.

---

## 📈 Usage Examples

### Predict Trade Risk (API)

```bash
curl -X POST http://localhost:8000/api/ml/risk/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "amount_staked": 150.0,
    "created_at": "2024-01-01T12:00:00Z"
  }'
```

**Response:**
```json
{
  "score": 0.75,
  "label": 1,
  "risk_level": "LOW"
}
```

### Get Platform Health (API)

```bash
curl http://localhost:8000/api/ml/health/
```

**Response:**
```json
{
  "platform_stress_level": 0.35,
  "systemic_risk_index": 0.25,
  "health_status": "HEALTHY",
  "alert_level": "LOW"
}
```

### Get Manipulation Analysis (API)

```bash
curl http://localhost:8000/api/ml/manipulation/market/5/
```

**Response:**
```json
{
  "market_id": 5,
  "manipulation_score": 0.85,
  "is_manipulation_suspected": true,
  "risk_level": "HIGH",
  "pump_dump_score": 0.9,
  "wash_trading_score": 0.7
}
```

---

## 🔍 Monitoring

### Check Prediction Statistics

```python
from ml.services.db_storage_service import get_prediction_statistics

stats = get_prediction_statistics(model_name='model1', days=7)
print(f"Total: {stats['total_predictions']}")
print(f"Success Rate: {stats['success_rate']:.2%}")
```

### Query Recent Predictions

```sql
-- Recent high-risk predictions
SELECT 
    user_id,
    score,
    risk_level,
    created_at
FROM ml_traderiskprediction
WHERE risk_level IN ('HIGH', 'CRITICAL')
ORDER BY created_at DESC
LIMIT 10;

-- Platform health history
SELECT 
    health_status,
    alert_level,
    platform_stress_level,
    created_at
FROM ml_platformhealthmetric
ORDER BY created_at DESC
LIMIT 20;
```

---

## 📚 Related Documentation

- **Backend**: See `../README.md`
- **Database**: See `../db_docs/README.md`
- **API**: See `../ml_api/views.py`
- **Testing**: See `../../TESTING_GUIDE.md`

---

## 🚀 Quick Commands

```bash
# Verify integration
python manage.py verify_ml_db_integration --test-all

# Test Model 1
python manage.py verify_ml_db_integration --test-model1

# Query predictions (Django shell)
python manage.py shell
>>> from ml.models import TradeRiskPrediction
>>> TradeRiskPrediction.objects.count()
```

