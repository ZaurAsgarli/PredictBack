CREATE MATERIALIZED VIEW IF NOT EXISTS market_activity_summary AS
SELECT
    m.id AS market_id,
    m.title,
    m.status,
    date_trunc('day', t.created_at) AS day,
    COUNT(*) AS trades_count,
    SUM(t.amount_staked) AS total_volume,
    COUNT(DISTINCT t.user_id) AS unique_traders
FROM trades_trade t
JOIN markets_market m ON t.market_id = m.id
GROUP BY m.id, m.title, m.status, date_trunc('day', t.created_at);


