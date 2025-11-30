"""
Model 4: Market Manipulation Pattern Classifier

This module detects coordinated attacks, "pump & dump" schemes, and liquidity wash cycles
using graph analytics and pattern recognition.

Key Features:
- Graph-based analysis of wallet-to-wallet transaction patterns
- Clique detection for coordinated trading groups
- Timing-based manipulation scoring
- Pump & dump pattern recognition
- Wash trading detection

Author: Prediction Hub ML Team
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import warnings

import numpy as np
import pandas as pd
import networkx as nx
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')


# ============================================================================
# GRAPH CONSTRUCTION & ANALYSIS
# ============================================================================

def build_transaction_graph(
    df_trades: pd.DataFrame,
    time_window_minutes: int = 60,
    min_transaction_value: float = 0.0,
) -> nx.Graph:
    """
    Build a weighted graph from trade transactions.
    
    Nodes represent users (wallets), edges represent coordinated trading activity.
    Edge weights indicate the strength of coordination (based on timing and market overlap).
    
    Args:
        df_trades: DataFrame with columns:
            - user_id: User/wallet identifier
            - market_id: Market identifier
            - created_at: Timestamp of trade
            - amount_staked: Transaction value
            - trade_type: 'buy' or 'sell'
            - outcome_type: 'YES' or 'NO'
        time_window_minutes: Maximum time difference (minutes) for considering trades as coordinated
        min_transaction_value: Minimum transaction value to include in graph
        
    Returns:
        NetworkX Graph with:
            - Nodes: user_id
            - Edges: (user1, user2) with weight = coordination_score
            - Node attributes: user_id, total_volume, num_trades
    """
    df = df_trades.copy()
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    # Filter by minimum transaction value
    if min_transaction_value > 0:
        df = df[df['amount_staked'] >= min_transaction_value].copy()
    
    # Sort by timestamp
    df = df.sort_values('created_at').reset_index(drop=True)
    
    G = nx.Graph()
    
    # Add all users as nodes with attributes
    for user_id in df['user_id'].unique():
        user_trades = df[df['user_id'] == user_id]
        G.add_node(
            user_id,
            total_volume=float(user_trades['amount_staked'].sum()),
            num_trades=len(user_trades),
            markets=list(user_trades['market_id'].unique())
        )
    
    # Build edges based on coordinated trading
    # Two users are connected if they trade in the same market within time_window
    user_pairs = {}
    
    for market_id in df['market_id'].unique():
        market_trades = df[df['market_id'] == market_id].copy()
        market_trades = market_trades.sort_values('created_at')
        
        for i, trade1 in market_trades.iterrows():
            user1 = trade1['user_id']
            time1 = trade1['created_at']
            
            # Find trades within time window
            window_end = time1 + timedelta(minutes=time_window_minutes)
            subsequent_trades = market_trades[
                (market_trades['created_at'] > time1) & 
                (market_trades['created_at'] <= window_end)
            ]
            
            for j, trade2 in subsequent_trades.iterrows():
                user2 = trade2['user_id']
                
                if user1 == user2:
                    continue
                
                # Calculate coordination score
                time_diff = (trade2['created_at'] - time1).total_seconds() / 60.0  # minutes
                time_score = np.exp(-time_diff / (time_window_minutes / 2))  # Exponential decay
                
                # Direction alignment score (both buying or both selling = higher coordination)
                direction_score = 1.0 if trade1['trade_type'] == trade2['trade_type'] else 0.5
                
                # Outcome alignment score (same outcome = higher coordination)
                outcome_score = 1.0 if trade1['outcome_type'] == trade2['outcome_type'] else 0.3
                
                # Volume similarity score
                vol1 = float(trade1['amount_staked'])
                vol2 = float(trade2['amount_staked'])
                vol_ratio = min(vol1, vol2) / max(vol1, vol2) if max(vol1, vol2) > 0 else 0
                volume_score = vol_ratio
                
                # Combined coordination score
                coordination_score = time_score * direction_score * outcome_score * volume_score
                
                # Update edge weight (sum if edge already exists)
                pair_key = tuple(sorted([user1, user2]))
                if pair_key not in user_pairs:
                    user_pairs[pair_key] = 0.0
                user_pairs[pair_key] += coordination_score
    
    # Add edges to graph
    for (user1, user2), weight in user_pairs.items():
        if weight > 0.1:  # Threshold to avoid noise
            if G.has_edge(user1, user2):
                G[user1][user2]['weight'] += weight
            else:
                G.add_edge(user1, user2, weight=weight, coordination_count=1)
    
    return G


def detect_cliques(
    G: nx.Graph,
    min_clique_size: int = 3,
    min_edge_weight: float = 0.3,
) -> List[List[int]]:
    """
    Detect cliques (fully connected subgraphs) in the transaction graph.
    
    Cliques represent groups of users who all trade together, indicating potential coordination.
    
    Args:
        G: NetworkX graph from build_transaction_graph
        min_clique_size: Minimum number of users in a clique
        min_edge_weight: Minimum edge weight to consider for clique detection
        
    Returns:
        List of cliques, where each clique is a list of user_ids
    """
    # Filter graph to only include edges above threshold
    G_filtered = G.copy()
    edges_to_remove = [
        (u, v) for u, v, d in G_filtered.edges(data=True)
        if d.get('weight', 0) < min_edge_weight
    ]
    G_filtered.remove_edges_from(edges_to_remove)
    
    # Find all maximal cliques
    cliques = list(nx.find_cliques(G_filtered))
    
    # Filter by minimum size
    cliques = [clique for clique in cliques if len(clique) >= min_clique_size]
    
    return cliques


def calculate_clique_manipulation_score(
    clique: List[int],
    G: nx.Graph,
    df_trades: pd.DataFrame,
) -> float:
    """
    Calculate manipulation score for a detected clique.
    
    Higher scores indicate stronger evidence of coordinated manipulation.
    
    Args:
        clique: List of user_ids in the clique
        G: Transaction graph
        df_trades: Original trade DataFrame
        market_id: Specific market to analyze (optional)
        
    Returns:
        Manipulation score between 0 and 1
    """
    if len(clique) < 2:
        return 0.0
    
    clique_trades = df_trades[df_trades['user_id'].isin(clique)].copy()
    
    if len(clique_trades) == 0:
        return 0.0
    
    scores = []
    
    # 1. Edge weight score (average coordination strength)
    edge_weights = []
    for i, user1 in enumerate(clique):
        for user2 in clique[i+1:]:
            if G.has_edge(user1, user2):
                edge_weights.append(G[user1][user2].get('weight', 0))
    if edge_weights:
        scores.append(np.mean(edge_weights))
    
    # 2. Market concentration score (trading in same markets)
    markets_per_user = clique_trades.groupby('user_id')['market_id'].nunique()
    if len(markets_per_user) > 0:
        # Lower market diversity = higher manipulation risk
        avg_markets = markets_per_user.mean()
        total_markets = clique_trades['market_id'].nunique()
        concentration = 1.0 - (avg_markets / max(total_markets, 1))
        scores.append(concentration)
    
    # 3. Timing synchronization score
    clique_trades['created_at'] = pd.to_datetime(clique_trades['created_at'])
    clique_trades = clique_trades.sort_values('created_at')
    
    time_diffs = []
    for market_id in clique_trades['market_id'].unique():
        market_trades = clique_trades[clique_trades['market_id'] == market_id]
        if len(market_trades) > 1:
            market_trades = market_trades.sort_values('created_at')
            time_diffs.extend(market_trades['created_at'].diff().dt.total_seconds().dropna().tolist())
    
    if time_diffs:
        # Lower time differences = higher synchronization
        avg_time_diff = np.mean(time_diffs)
        sync_score = 1.0 / (1.0 + avg_time_diff / 3600)  # Normalize by hour
        scores.append(min(sync_score, 1.0))
    
    # 4. Volume concentration score
    total_volume = clique_trades['amount_staked'].sum()
    if total_volume > 0:
        # Higher volume concentration = higher manipulation risk
        volume_score = min(total_volume / 10000.0, 1.0)  # Normalize
        scores.append(volume_score)
    
    # Combine scores (weighted average)
    if scores:
        return np.mean(scores)
    return 0.0


# ============================================================================
# PUMP & DUMP DETECTION
# ============================================================================

def detect_pump_and_dump(
    df_trades: pd.DataFrame,
    market_id: int,
    time_window_hours: int = 24,
) -> Dict[str, float]:
    """
    Detect pump & dump patterns in a specific market.
    
    Pattern: Rapid buying (pump) followed by selling (dump) within short time window.
    
    Args:
        df_trades: Trade DataFrame
        market_id: Market to analyze
        time_window_hours: Time window to look for pump & dump cycle
        
    Returns:
        Dictionary with:
            - pump_dump_score: 0-1 score indicating likelihood
            - pump_volume: Total buy volume in pump phase
            - dump_volume: Total sell volume in dump phase
            - cycle_duration_hours: Duration of cycle
    """
    market_trades = df_trades[df_trades['market_id'] == market_id].copy()
    market_trades['created_at'] = pd.to_datetime(market_trades['created_at'])
    market_trades = market_trades.sort_values('created_at')
    
    if len(market_trades) < 10:  # Need minimum trades
        return {
            'pump_dump_score': 0.0,
            'pump_volume': 0.0,
            'dump_volume': 0.0,
            'cycle_duration_hours': 0.0,
        }
    
    # Identify pump phase (rapid buying)
    buy_trades = market_trades[market_trades['trade_type'] == 'buy'].copy()
    sell_trades = market_trades[market_trades['trade_type'] == 'sell'].copy()
    
    if len(buy_trades) == 0 or len(sell_trades) == 0:
        return {
            'pump_dump_score': 0.0,
            'pump_volume': float(buy_trades['amount_staked'].sum()) if len(buy_trades) > 0 else 0.0,
            'dump_volume': float(sell_trades['amount_staked'].sum()) if len(sell_trades) > 0 else 0.0,
            'cycle_duration_hours': 0.0,
        }
    
    # Find rapid buying period
    buy_trades['rolling_volume'] = buy_trades['amount_staked'].rolling(window=5, min_periods=1).sum()
    buy_trades['rolling_count'] = buy_trades['amount_staked'].rolling(window=5, min_periods=1).count()
    
    # Pump phase: high volume buying in short time
    pump_threshold = buy_trades['rolling_volume'].quantile(0.75)
    pump_trades = buy_trades[buy_trades['rolling_volume'] >= pump_threshold]
    
    if len(pump_trades) == 0:
        return {
            'pump_dump_score': 0.0,
            'pump_volume': 0.0,
            'dump_volume': 0.0,
            'cycle_duration_hours': 0.0,
        }
    
    pump_start = pump_trades['created_at'].min()
    pump_end = pump_trades['created_at'].max()
    pump_volume = float(pump_trades['amount_staked'].sum())
    
    # Find dump phase (selling after pump)
    dump_window_end = pump_end + timedelta(hours=time_window_hours)
    dump_trades = sell_trades[
        (sell_trades['created_at'] >= pump_end) &
        (sell_trades['created_at'] <= dump_window_end)
    ]
    
    dump_volume = float(dump_trades['amount_staked'].sum()) if len(dump_trades) > 0 else 0.0
    
    # Calculate pump & dump score
    if pump_volume > 0:
        volume_ratio = dump_volume / pump_volume
        time_ratio = (dump_window_end - pump_start).total_seconds() / (time_window_hours * 3600)
        
        # Higher score if: high dump/pump ratio, short time window
        pump_dump_score = volume_ratio * (1.0 - min(time_ratio, 1.0))
        pump_dump_score = min(pump_dump_score, 1.0)
    else:
        pump_dump_score = 0.0
    
    cycle_duration = (dump_window_end - pump_start).total_seconds() / 3600.0 if dump_volume > 0 else 0.0
    
    return {
        'pump_dump_score': pump_dump_score,
        'pump_volume': pump_volume,
        'dump_volume': dump_volume,
        'cycle_duration_hours': cycle_duration,
    }


# ============================================================================
# WASH TRADING DETECTION
# ============================================================================

def detect_wash_trading(
    df_trades: pd.DataFrame,
    market_id: int,
    time_window_hours: int = 1,
) -> Dict[str, float]:
    """
    Detect wash trading patterns (circular trading to create false volume).
    
    Pattern: Same users buying and selling to each other in circular patterns.
    
    Args:
        df_trades: Trade DataFrame
        market_id: Market to analyze
        time_window_hours: Time window for circular pattern detection
        
    Returns:
        Dictionary with wash_trading_score and related metrics
    """
    market_trades = df_trades[df_trades['market_id'] == market_id].copy()
    market_trades['created_at'] = pd.to_datetime(market_trades['created_at'])
    market_trades = market_trades.sort_values('created_at')
    
    if len(market_trades) < 5:
        return {'wash_trading_score': 0.0, 'circular_patterns': 0}
    
    # Build directed graph for this market
    G_directed = nx.DiGraph()
    
    for _, trade in market_trades.iterrows():
        user_id = trade['user_id']
        trade_type = trade['trade_type']
        amount = float(trade['amount_staked'])
        timestamp = trade['created_at']
        
        G_directed.add_node(user_id)
        
        # Look for opposite trades within time window
        if trade_type == 'buy':
            # Find sells from other users
            window_end = timestamp + timedelta(hours=time_window_hours)
            opposite_trades = market_trades[
                (market_trades['trade_type'] == 'sell') &
                (market_trades['user_id'] != user_id) &
                (market_trades['created_at'] >= timestamp) &
                (market_trades['created_at'] <= window_end)
            ]
            
            for _, opp_trade in opposite_trades.iterrows():
                seller_id = opp_trade['user_id']
                if not G_directed.has_edge(user_id, seller_id):
                    G_directed.add_edge(user_id, seller_id, weight=0, count=0)
                G_directed[user_id][seller_id]['weight'] += amount
                G_directed[user_id][seller_id]['count'] += 1
    
    # Detect circular patterns (cycles in directed graph)
    try:
        cycles = list(nx.simple_cycles(G_directed))
        circular_patterns = len(cycles)
        
        # Calculate wash trading score
        if circular_patterns > 0:
            # Score based on number of cycles and their weights
            cycle_weights = []
            for cycle in cycles:
                cycle_weight = 0
                for i in range(len(cycle)):
                    u = cycle[i]
                    v = cycle[(i + 1) % len(cycle)]
                    if G_directed.has_edge(u, v):
                        cycle_weight += G_directed[u][v].get('weight', 0)
                cycle_weights.append(cycle_weight)
            
            avg_cycle_weight = np.mean(cycle_weights) if cycle_weights else 0
            wash_trading_score = min(circular_patterns * 0.2 + avg_cycle_weight / 1000.0, 1.0)
        else:
            wash_trading_score = 0.0
    except:
        wash_trading_score = 0.0
        circular_patterns = 0
    
    return {
        'wash_trading_score': wash_trading_score,
        'circular_patterns': circular_patterns,
    }


# ============================================================================
# MAIN MANIPULATION DETECTION FUNCTION
# ============================================================================

def detect_market_manipulation(
    df_trades: pd.DataFrame,
    market_id: Optional[int] = None,
    time_window_minutes: int = 60,
    min_clique_size: int = 3,
) -> pd.DataFrame:
    """
    Main function to detect market manipulation patterns.
    
    Combines clique detection, pump & dump, and wash trading analysis.
    
    Args:
        df_trades: DataFrame with columns: user_id, market_id, created_at, amount_staked,
                   trade_type, outcome_type
        market_id: Specific market to analyze (None = analyze all markets)
        time_window_minutes: Time window for coordination detection
        min_clique_size: Minimum clique size for detection
        
    Returns:
        DataFrame with manipulation scores per market/user combination:
            - market_id
            - user_id (if user-specific)
            - manipulation_score: 0-1 score
            - is_manipulation_suspected: Boolean flag
            - clique_id: ID of detected clique (if applicable)
            - pump_dump_score: Pump & dump score
            - wash_trading_score: Wash trading score
            - risk_level: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    """
    df = df_trades.copy()
    
    # Filter by market if specified
    if market_id is not None:
        df = df[df['market_id'] == market_id].copy()
    
    if len(df) == 0:
        return pd.DataFrame(columns=[
            'market_id', 'manipulation_score', 'is_manipulation_suspected',
            'clique_id', 'pump_dump_score', 'wash_trading_score', 'risk_level'
        ])
    
    results = []
    
    # Analyze each market
    for mkt_id in df['market_id'].unique():
        market_trades = df[df['market_id'] == mkt_id].copy()
        
        # 1. Build transaction graph
        G = build_transaction_graph(market_trades, time_window_minutes=time_window_minutes)
        
        # 2. Detect cliques
        cliques = detect_cliques(G, min_clique_size=min_clique_size)
        
        # 3. Calculate clique manipulation scores
        clique_scores = {}
        for idx, clique in enumerate(cliques):
            score = calculate_clique_manipulation_score(clique, G, market_trades)
            clique_scores[idx] = {
                'clique': clique,
                'score': score,
            }
        
        # 4. Pump & dump detection
        pump_dump_result = detect_pump_and_dump(market_trades, mkt_id)
        pump_dump_score = pump_dump_result['pump_dump_score']
        
        # 5. Wash trading detection
        wash_result = detect_wash_trading(market_trades, mkt_id)
        wash_score = wash_result['wash_trading_score']
        
        # 6. Combine scores
        max_clique_score = max([cs['score'] for cs in clique_scores.values()]) if clique_scores else 0.0
        
        # Weighted combination
        manipulation_score = (
            0.4 * max_clique_score +
            0.35 * pump_dump_score +
            0.25 * wash_score
        )
        
        # Determine risk level
        if manipulation_score >= 0.8:
            risk_level = 'CRITICAL'
        elif manipulation_score >= 0.6:
            risk_level = 'HIGH'
        elif manipulation_score >= 0.4:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        # Get clique ID for users in cliques
        user_clique_map = {}
        for clique_id, clique_data in clique_scores.items():
            for user_id in clique_data['clique']:
                user_clique_map[user_id] = clique_id
        
        # Create results for each user in the market
        market_users = market_trades['user_id'].unique()
        for user_id in market_users:
            user_clique_id = user_clique_map.get(user_id, None)
            
            # User-specific manipulation score (higher if in clique)
            user_manipulation_score = manipulation_score
            if user_clique_id is not None:
                user_manipulation_score = max(
                    user_manipulation_score,
                    clique_scores[user_clique_id]['score']
                )
            
            results.append({
                'market_id': mkt_id,
                'user_id': user_id,
                'manipulation_score': user_manipulation_score,
                'is_manipulation_suspected': user_manipulation_score >= 0.5,
                'clique_id': user_clique_id,
                'pump_dump_score': pump_dump_score,
                'wash_trading_score': wash_score,
                'risk_level': risk_level,
            })
    
    result_df = pd.DataFrame(results)
    
    # If no results, return empty DataFrame with correct columns
    if len(result_df) == 0:
        return pd.DataFrame(columns=[
            'market_id', 'user_id', 'manipulation_score', 'is_manipulation_suspected',
            'clique_id', 'pump_dump_score', 'wash_trading_score', 'risk_level'
        ])
    
    return result_df


# ============================================================================
# SYNTHETIC DATA GENERATOR (for testing)
# ============================================================================

def generate_synthetic_manipulation_data(
    n_users: int = 50,
    n_markets: int = 5,
    n_normal_trades: int = 200,
    n_manipulation_trades: int = 50,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic trade data with embedded manipulation patterns.
    
    Useful for testing and validation.
    
    Args:
        n_users: Number of unique users
        n_markets: Number of markets
        n_normal_trades: Number of normal trades
        n_manipulation_trades: Number of manipulation trades
        seed: Random seed
        
    Returns:
        DataFrame with synthetic trade data
    """
    np.random.seed(seed)
    
    trades = []
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    
    # Generate normal trades
    for i in range(n_normal_trades):
        trade_time = base_time + timedelta(
            hours=np.random.randint(0, 720),
            minutes=np.random.randint(0, 60)
        )
        trades.append({
            'user_id': np.random.randint(1, n_users + 1),
            'market_id': np.random.randint(1, n_markets + 1),
            'created_at': trade_time,
            'amount_staked': np.random.uniform(10, 1000),
            'trade_type': np.random.choice(['buy', 'sell']),
            'outcome_type': np.random.choice(['YES', 'NO']),
        })
    
    # Generate manipulation trades (coordinated clique)
    manipulation_clique = list(range(1, 6))  # Users 1-5 form a clique
    manipulation_market = 1
    
    for i in range(n_manipulation_trades):
        # Coordinated timing (within 10 minutes of each other)
        base_manip_time = base_time + timedelta(
            hours=np.random.randint(100, 200),
            minutes=np.random.randint(0, 60)
        )
        trade_time = base_manip_time + timedelta(
            minutes=np.random.randint(0, 10)
        )
        
        trades.append({
            'user_id': np.random.choice(manipulation_clique),
            'market_id': manipulation_market,
            'created_at': trade_time,
            'amount_staked': np.random.uniform(500, 2000),  # Higher volumes
            'trade_type': 'buy' if i < n_manipulation_trades * 0.6 else 'sell',
            'outcome_type': 'YES',
        })
    
    df = pd.DataFrame(trades)
    df = df.sort_values('created_at').reset_index(drop=True)
    
    return df


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Generate synthetic data
    print("Generating synthetic trade data...")
    df_trades = generate_synthetic_manipulation_data()
    print(f"Generated {len(df_trades)} trades")
    
    # Detect manipulation
    print("\nDetecting market manipulation patterns...")
    results = detect_market_manipulation(df_trades)
    
    print(f"\nDetected {results['is_manipulation_suspected'].sum()} suspicious cases")
    print("\nTop manipulation scores:")
    print(results.nlargest(10, 'manipulation_score')[['market_id', 'user_id', 'manipulation_score', 'risk_level']])
    
    print("\nRisk level distribution:")
    print(results['risk_level'].value_counts())

