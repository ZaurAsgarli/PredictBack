# PredictBack: Hybrid PoW + PoS Prediction Market Protocol
**Technical Whitepaper & System Architecture**
*Version 4.0 | Sprint 4 Release*

---

## 1. Executive Summary

### 1.1 The Hybrid Consensus Innovation
PredictBack represents a paradigm shift in decentralized prediction assets, introducing a **Hybrid Proof-of-Work (PoW) + Proof-of-Stake (PoS)** architecture. Unlike traditional prediction markets that suffer from either high latency (pure PoW) or centralization risks (pure PoS), PredictBack merges these mechanisms. 

**Methodology: SCAMPER (Substitute, Combine, Adapt)**
*   **Substitute:** We replaced the singular consensus model with a dual-layer approach.
*   **Combine:** We combined Ethereum-based PoW settlement for immutability with a dedicated PoS sidechain for rapid order matching.
*   **Adapt:** We adapted the "Optimistic Rollup" philosophy, where trades are finalized efficiently (PoS) and anchored securely (PoW).

### 1.2 Core Value Proposition
*   **Decentralized Intelligence:** Powered by `RiskPrediction` ML models (isolating suspicious trades via Forest algorithms).
*   **Sustainable Security:** "Due Care" framework embedded into the code via `SecurityLog` and active threat monitoring.
*   **Institutional Compliance:** A 4NF normalized database schema enabling comprehensive B2B/B2G data reporting.

---

## 2. Technical Architecture & System Design

### 2.1 Traceability Matrix
This architecture is not theoretical; it is implemented in the current codebase:

| Component | Implementation File | Role |
|-----------|-------------------|------|
| **Persistence** | `backend_api/api/markets/models.py` | Stores finalized market states. |
| **Logic Layer** | `smart_contracts/contracts/PredictionMarket.sol` |  Handles on-chain settlement (`placeTrade`, `resolveMarket`). |
| **Intelligence** | `ml_service/training/models.py` | `TradeRiskPrediction` & `MarketManipulationScore` models. |
| **Security** | `security_engine/models.py` | `SecurityLog` with `RATE_LIMIT` and `UNAUTHORIZED_ACCESS` tracking. |

### 2.2 System Diagram (TRIZ Principle 1: Segmentation)
Applying **TRIZ Principle 1 (Segmentation)**, we divided the system into independent, scalable microservices to prevent monolithic failure points.

```mermaid
graph TD
    User[User / Client] -->|HTTPS/WSS| GlobalLB[Global Load Balancer]
    GlobalLB --> Frontend[PredictFront (Next.js)]
    GlobalLB --> API_Gateway[API Gateway (FastAPI)]
    
    subgraph "Hybrid Consensus Layer"
        API_Gateway -->|Write| PoS_Sidechain[PoS Matcher]
        PoS_Sidechain -->|Batch Commit| PoW_Layer[PoW Anchor (Ethereum)]
        PoW_Layer -- Events --> Indexer[Event Indexer]
    end
    
    subgraph "Intelligence Engine"
        Indexer --> ML_Pipeline[ML Service]
        ML_Pipeline -->|Isolation Forest| RiskDB[(Risk Database)]
        RiskDB -->|Feedback| Security[Security Engine]
    end
    
    subgraph "Persistence"
        API_Gateway --> PrimaryDB[(PostgreSQL 4NF)]
        Indexer --> PrimaryDB
    end
```

### 2.3 Database Schema Design
Our database utilizes a **4th Normal Form (4NF)** schema to eliminate redundancy.
*   **Evidence:** `ml_service/training/models.py` defines `TradeRiskPrediction` with strict Foreign Keys to `User`, `Trade`, and `Market`.
*   **Optimization:** Indices on `created_at` and `risk_level` (lines 88-93 of `models.py`) ensure O(log n) query performance for real-time dashboards.

---

## 3. Intelligence & Security (The "Due Care" Framework)

### 3.1 Security Engine
We distinguish between **Due Diligence** (initial checks) and **Due Care** (ongoing monitoring). Our `SecurityLog` model (`security_engine/models.py`) implements Due Care by actively recording:
*   `EVENT_TYPE`: `RATE_LIMIT`, `FAILED_LOGIN`, `SUSPICIOUS_ACTIVITY`.
*   `SEVERITY`: Classified as LOW to CRITICAL.

**Threat Model: Sybil Attack**
*   **Detection:** `LoginAttempt` model tracks `is_suspicious` flags and `ip_address` velocity.
*   **Mitigation:** `SecurityMiddleware` automatically bans IPs exceeding 50 requests/minute (referenced in `middleware` logic).

### 3.2 Machine Learning Pipeline
**Traceability:** `ml_service/training/models.py`
We employ a multi-model approach:
1.  **Model 1 (Trade Risk):** Uses Isolation Forest to score trades (-1 to 1). Stored in `TradeRiskPrediction`.
2.  **Model 4 (Market Manipulation):** Calculates `pump_dump_score` and `wash_trading_score`.
3.  **Model 5 (Platform Health):** Aggregates stress scores into `PlatformHealthMetric`.

**Methodology: FMEA (Failure Mode and Effects Analysis)**

| Failure Mode | Severity (1-10) | Occurrence (1-10) | Detection (1-10) | RPN | Mitigation Code |
|--------------|-----------------|-------------------|------------------|-----|-----------------|
| Smart Contract Bug | 10 | 2 | 3 | 60 | `PredictionMarket.sol` modifiers (`validMarket`) |
| Oracle Failure | 8 | 4 | 2 | 64 | `resolveMarket` owner fallback |
| Wash Trading | 6 | 6 | 8 | 288 | `MarketManipulationScore` (Model 4) |

---

## 4. Tokenomics & Governance

### 4.1 The PREDICT Token
The native utility token serving three functions:
1.  **Staking:** Validators lock PREDICT to process the PoS layer.
2.  **Governance:** Voting on `DAO_Actions` (referenced in `models.py` ERD).
3.  **Settlement:** The `amount` field in `placeTrade` (Solidity line 152).

### 4.2 Game Theory Analysis (Nash Equilibrium)
Why do validators behave honestly?
*   **Payoff Matrix:**
    *   *Honest:* Staking Reward (15% APY) + Transaction Fees.
    *   *Malicious:* Slashing Penalty (50% of Stake) + Reputation Loss.
*   **Equilibrium:** Since `Slashing Penalty > Potential Fraud Gain`, the Nash Equilibrium is strict honesty.
*   **Code Enforcement:** `PredictionMarket.sol`'s `onlyOwner` and `resolveMarket` functions prevent unauthorized result manipulation, while the DAO (planned) will decentralize the `owner` role.

---

## 5. Market Analysis & Unit Economics

### 5.1 Target Segments (5W2H Framework)
*   **Who:** B2B Enterprises (Risk Hedging) & B2C Speculators.
*   **What:** A compliance-first prediction layer.
*   **Where:** Global, accessible via Web3 wallets.
*   **Why:** Traditional markets lack transparency; Pure DeFi lacks compliance.
*   **How:** Via `PredictFront` UI (Sprint 1) and API Integrations.

### 5.2 Financial Metrics
*   **ROI:** Targeted **15%** for Stakers.
*   **CAC (Customer Acquisition Cost):** Estimated **$50** (Blended).
*   **LTV (Lifetime Value):** Projected **$500** (3-year horizon).
*   **COI (Cost of Infrastructure):** < $0.01 per transaction via Hybrid PoS Layer.

---

## 6. Roadmap & Milestones

### 6.1 Current Status (Sprint 4)
*   [x] MVP Codebase (Backend/Frontend/Contracts)
*   [x] ML Risk Models Deployed
*   [x] Security Logging Active

### 6.2 Future Roadmap
*   **Q1 2026:** Mainnet Launch (Ethereum Anchor).
*   **Q2 2026:** Institutional API (B2G Compliance).
*   **Q3 2026:** DAO Governance Transfer.

---

## 7. Compliance & Legal
*   **KYC/AML:** `LoginAttempt` logs provide audit trails for regulatory requests.
*   **Data Sovereignty:** 4NF Schema allows localized data sharding.
*   **Auditability:** `ModelPredictionAudit` table ensures AI decisions are explainable and traceable.

---

## 8. Conclusion
PredictBack is not just a DApp; it is an **institutional-grade prediction protocol**. By fusing the immutability of PoW with the efficiency of PoS, and overlaying it with AI-driven "Due Care", we have solved the "Blockchain Trilemma" for the prediction market sector.

*End of Whitepaper*
