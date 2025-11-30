Normalization Notes (4NF+)
==========================

users_user uses 1 row per user without repeating groups.

markets_market uses markets_marketcategory for categories instead of repeating columns.

trades_trade stores 1 trade per row (user + market + outcome + stake).

positions_position stores 1 position per row (avoid multi-outcome columns).

liquidity_liquidityevent, disputes_dispute, markets_pricehistory, markets_resolution each store their own facts.

indexer_onchaintransaction stores blockchain transactions.

indexer_onchaineventlog stores blockchain events, using (tx_hash, log_index) unique pairs to avoid multivalued attributes.

No table mixes multiple independent multivalued attributes.

All important relationships use foreign keys.

This ensures no update/delete anomalies and meets 4NF normalization standards.


