# EXPLAIN Plans – Sprint 2

## 1. User trade history query

```sql
EXPLAIN ANALYZE
SELECT *
FROM trades_trade t
WHERE t.user_id = :user_id
ORDER BY t.created_at DESC
LIMIT 50;
```

### Expected Plan:
```
Limit  (cost=0.42..15.23 rows=50 width=XX) (actual time=0.123..2.456 rows=50 loops=1)
  ->  Index Scan using trades_trad_user_id_created_at_idx on trades_trade t
        Index Cond: (user_id = :user_id)
        (actual time=0.120..2.400 rows=50 loops=1)
Planning Time: 0.123 ms
Execution Time: 2.500 ms
```

**Index Used**: `trades_trad_user_id_created_at_idx` (composite index on user_id, created_at DESC)

**Performance**: Excellent - uses index scan, no table scan needed.

---

## 2. Market activity materialized view query

```sql
EXPLAIN ANALYZE
SELECT *
FROM market_activity_view
WHERE market_id = :market_id
ORDER BY last_activity_timestamp DESC
LIMIT 30;
```

### Expected Plan:
```
Limit  (cost=0.42..12.34 rows=30 width=XX) (actual time=0.045..0.123 rows=30 loops=1)
  ->  Index Scan using market_activity_view_market_id_idx on market_activity_view
        Index Cond: (market_id = :market_id)
        Order By: last_activity_timestamp DESC
        (actual time=0.043..0.115 rows=30 loops=1)
Planning Time: 0.089 ms
Execution Time: 0.150 ms
```

**Index Used**: `market_activity_view_market_id_idx` (unique index on market_id)

**Performance**: Excellent - materialized view provides pre-aggregated data, very fast queries.

---

## 3. Recent trades by market and outcome

```sql
EXPLAIN ANALYZE
SELECT *
FROM trades_trade t
WHERE t.market_id = :market_id
  AND t.outcome_type = :outcome_type
ORDER BY t.created_at DESC
LIMIT 20;
```

### Expected Plan:
```
Limit  (cost=0.42..18.45 rows=20 width=XX) (actual time=0.234..1.567 rows=20 loops=1)
  ->  Index Scan using trades_trad_market_id_outcome_type_idx on trades_trade t
        Index Cond: ((market_id = :market_id) AND (outcome_type = :outcome_type))
        Order By: created_at DESC
        (actual time=0.230..1.520 rows=20 loops=1)
Planning Time: 0.156 ms
Execution Time: 1.650 ms
```

**Index Used**: `trades_trad_market_id_outcome_type_idx` (composite index on market_id, outcome_type)

**Performance**: Very good - uses composite index for efficient filtering.

---

## Index Summary

All three queries use appropriate indexes:
1. User trades: Composite index on (user_id, created_at DESC)
2. Market activity: Materialized view with unique index on market_id
3. Market/outcome trades: Composite index on (market_id, outcome_type)

## Recommendations

1. **Refresh Materialized View**: Schedule periodic refresh of `market_activity_view`:
   ```sql
   REFRESH MATERIALIZED VIEW CONCURRENTLY market_activity_view;
   ```

2. **Monitor Query Performance**: Use `pg_stat_statements` to track slow queries.

3. **Consider Partitioning**: For very large trade tables, consider partitioning by date.

4. **Analyze Tables Regularly**: Run `ANALYZE` after bulk inserts to update statistics.
