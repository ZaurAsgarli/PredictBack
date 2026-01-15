# PredictBack Protocol — Backend (Port 8000)

## Purpose: the engine room

The backend is the canonical authority for PredictBack Protocol. It provides a consistent, auditable execution environment for markets and trades, and it is the enforcement point for authorization, data integrity, and operational policy.

At a business level, the backend enables:

- **Fast, reliable execution**: predictable trade validation and state transitions.
- **Integrity guarantees**: consistent rules enforced centrally (RBAC, market invariants, dispute actions).
- **Security posture**: a measurable, reviewable audit trail of anomalous behavior and admin interventions.

## Data model architecture (core relationships)

The backend is organized around a small set of domain primitives:

- **Markets (oracles and outcome resolution)**: define questions, timelines, and resolution status.
- **Trades (execution events)**: represent user intents accepted and recorded by the engine.
- **Positions (stateful exposure)**: summarize user exposure per market as a function of executed trades.

This separation supports both transactional correctness (trades as events) and efficient queries (positions as derived state).

## AI security layer (real-time risk posture)

The AI security layer exists to reduce manipulation and abuse in high-velocity environments:

- **Heuristic and model-assisted scoring**: produces risk signals from user behavior and trade patterns.
- **Threshold-driven responses**: signals can trigger flags, rate-limit emphasis, or admin review workflows.
- **Human-in-the-loop governance**: the admin dashboard consumes these signals to enable explicit intervention.

The key principle is that AI does not replace governance; it improves detection and prioritization.

## Web3 simulation and on-chain fidelity

The protocol is designed for on-chain verifiability while maintaining the usability and throughput of a Web2 execution engine.

For local development and controlled demos, the system may generate and record simulated on-chain artifacts:

- **Gas fee estimates**
- **Transaction hashes (TxHashes)**
- **Blockchain-style event logs**

These artifacts exist to preserve the mental model of settlement without requiring full on-chain dependencies during development.

## Scalability posture (large dataset operations)

The backend is expected to handle growth beyond casual volumes:

- **Optimized PostgreSQL queries** for large tables (trades, positions, logs).
- **Pagination-first API surfaces** to prevent unbounded payloads.
- **Pre-aggregation patterns** where necessary for analytics workloads.

In operational terms, the goal is to sustain correctness and responsiveness at 5,000+ records and beyond, without compromising auditability.

## Where to go next

- **API surface map**: `backend_api/api/README.md`
- **Core configuration and operational utilities**: `backend_api/core/README.md`
- **Security engine**: `security_engine/README.md`
- **ML service**: `ml_service/README.md`
