"""
link_anomaly.py — Mention-Based Link Anomaly Detection

Detects anomalous mention patterns in the social graph within specific
time windows. Inspired by Sato et al. (2012) "Detecting Anomalous Link
Patterns in Evolving Networks", adapted with practical proxy features
for tweet mention networks.

The core idea: organic trending topics produce diverse, reciprocal mention
patterns, while astroturfing/bot campaigns produce low-entropy, coordinated,
one-directional mention floods targeting specific accounts.

Features computed per time window:
  1. Degree Entropy        — diversity of mention targets
  2. Temporal Clustering   — how tightly packed mentions are in time
  3. Source/Target Ratio   — balance between unique sources and targets
  4. Reciprocity           — fraction of bidirectional mention pairs
  5. Hub Concentration     — fraction of edges going to top-K targets
"""

import math
import numpy as np
import pandas as pd
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple


# ─── Feature Extractors ─────────────────────────────────────────────────────

def _degree_entropy(edges: pd.DataFrame) -> float:
    """
    Compute the normalized Shannon entropy of out-degree distribution.

    High entropy = diverse mention targets (normal).
    Low entropy = concentrated mentions to few targets (suspicious).

    Returns:
        Normalized entropy in [0, 1], where 1 = maximum diversity.
    """
    if edges.empty:
        return 1.0

    target_counts = edges['target_mention'].value_counts()
    total = target_counts.sum()

    if total == 0 or len(target_counts) <= 1:
        return 0.0

    probs = target_counts / total
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    max_entropy = math.log2(len(target_counts))

    return entropy / max_entropy if max_entropy > 0 else 0.0


def _temporal_clustering_score(edges: pd.DataFrame, time_col: str = 'timestamp') -> float:
    """
    Measure how temporally clustered the mentions are.

    Organic mentions spread over time. Coordinated campaigns produce
    tight temporal clusters (many mentions within short windows).

    Returns:
        Score in [0, 1], where 1 = extremely clustered (suspicious).
    """
    if edges.empty or len(edges) < 3:
        return 0.0

    timestamps = pd.to_datetime(edges[time_col], errors='coerce').dropna()
    if len(timestamps) < 3:
        return 0.0

    timestamps = timestamps.sort_values()
    deltas = timestamps.diff().dropna().dt.total_seconds()

    if deltas.empty:
        return 0.0

    # Use coefficient of variation of inter-arrival times
    # Low CV = very regular/clustered → suspicious
    # High CV = variable/organic → normal
    mean_delta = deltas.mean()
    std_delta = deltas.std()

    if mean_delta == 0:
        return 1.0  # All at the same time → maximum clustering

    cv = std_delta / mean_delta if mean_delta > 0 else 0

    # Invert: low CV means high clustering score
    # Sigmoid-like normalization: score = 1 / (1 + cv)
    clustering = 1.0 / (1.0 + cv)

    # Also check: what fraction of edges fall within a 5-minute window?
    # (A stronger signal of coordination)
    total_span = (timestamps.max() - timestamps.min()).total_seconds()
    if total_span > 0:
        # Count max edges in any 300s window
        ts_arr = timestamps.values.astype(np.int64) // 10**9
        max_in_window = 0
        for i in range(len(ts_arr)):
            window_end = ts_arr[i] + 300
            count = np.sum((ts_arr >= ts_arr[i]) & (ts_arr <= window_end))
            max_in_window = max(max_in_window, count)

        burst_ratio = max_in_window / len(ts_arr)
    else:
        burst_ratio = 1.0

    return min((clustering * 0.5 + burst_ratio * 0.5), 1.0)


def _source_target_ratio(edges: pd.DataFrame) -> float:
    """
    Ratio of unique sources to unique targets.

    Normal networks: ratio ≈ 0.3-0.7 (many users mention many users).
    Bot campaigns: ratio >> 1 or << 0.1 (many accounts → few targets).

    Returns:
        Imbalance score in [0, 1], where 1 = extreme imbalance.
    """
    if edges.empty:
        return 0.0

    n_sources = edges['source_user'].nunique()
    n_targets = edges['target_mention'].nunique()

    if n_targets == 0:
        return 1.0

    ratio = n_sources / n_targets

    # Score: distance from the "normal" ratio of ~0.5
    # Map via: |ratio - balanced| / max_deviation
    if ratio > 1:
        # Many sources → few targets (classic astroturf)
        imbalance = min((ratio - 1) / 10.0, 1.0)
    else:
        # More targets than sources (less common, but still unusual)
        imbalance = min((1.0 / ratio - 1) / 10.0, 1.0) if ratio > 0 else 1.0

    return imbalance


def _reciprocity_ratio(edges: pd.DataFrame) -> float:
    """
    Fraction of mention pairs that are reciprocal (A→B and B→A both exist).

    Organic conversations have some reciprocity.
    Bot campaigns are almost entirely one-directional.

    Returns:
        Reciprocity in [0, 1], where 1 = fully reciprocal (normal).
    """
    if edges.empty:
        return 0.0

    pairs = set()
    reverse_pairs = set()

    for _, row in edges.iterrows():
        pair = (row['source_user'], row['target_mention'])
        reverse = (row['target_mention'], row['source_user'])

        pairs.add(pair)
        if reverse in pairs:
            reverse_pairs.add(pair)
            reverse_pairs.add(reverse)

    if len(pairs) == 0:
        return 0.0

    return len(reverse_pairs) / len(pairs)


def _hub_concentration(edges: pd.DataFrame, top_k: int = 3) -> float:
    """
    Fraction of total edges directed at the top-K mentioned accounts.

    High concentration = a few accounts receive most mentions (suspicious).

    Returns:
        Score in [0, 1], where 1 = all edges go to top-K accounts.
    """
    if edges.empty:
        return 0.0

    target_counts = edges['target_mention'].value_counts()
    total = target_counts.sum()

    if total == 0:
        return 0.0

    top_count = target_counts.head(top_k).sum()
    return top_count / total


# ─── Anomaly Score Aggregation ───────────────────────────────────────────────

def compute_anomaly_score(edges: pd.DataFrame,
                          weights: Optional[Dict[str, float]] = None) -> Dict:
    """
    Compute the aggregate anomaly score for a set of edges.

    Args:
        edges:   DataFrame of edges in a specific time window
        weights: Feature weights (default: equal weights)

    Returns:
        Dict with: {
            'anomaly_score': float,
            'features': {feature_name: value},
            'edge_count': int,
            'unique_sources': int,
            'unique_targets': int,
        }
    """
    if weights is None:
        weights = {
            'degree_entropy': 0.25,
            'temporal_clustering': 0.20,
            'source_target_imbalance': 0.20,
            'reciprocity': 0.15,
            'hub_concentration': 0.20,
        }

    if edges.empty or len(edges) < 5:
        return {
            'anomaly_score': 0.0,
            'features': {},
            'edge_count': 0,
            'unique_sources': 0,
            'unique_targets': 0,
        }

    features = {
        'degree_entropy': round(1.0 - _degree_entropy(edges), 4),
        'temporal_clustering': round(_temporal_clustering_score(edges), 4),
        'source_target_imbalance': round(_source_target_ratio(edges), 4),
        'reciprocity': round(1.0 - _reciprocity_ratio(edges), 4),
        'hub_concentration': round(_hub_concentration(edges), 4),
    }

    score = sum(features[k] * weights.get(k, 0) for k in features)
    score = min(max(score, 0.0), 1.0)

    return {
        'anomaly_score': round(score, 4),
        'features': features,
        'edge_count': len(edges),
        'unique_sources': int(edges['source_user'].nunique()),
        'unique_targets': int(edges['target_mention'].nunique()),
    }


# ─── Network Graph Construction ─────────────────────────────────────────────

def build_network_graph(edge_df: pd.DataFrame,
                        anomaly_results: List[Dict],
                        anomaly_threshold: float = 0.5,
                        max_nodes: int = 200) -> Dict:
    """
    Build the network graph data structure for vis-network visualization.

    Args:
        edge_df:           Full edge list DataFrame
        anomaly_results:   List of anomaly analysis results per burst window
        anomaly_threshold: Score above which nodes/edges are marked anomalous
        max_nodes:         Maximum nodes to include (for performance)

    Returns:
        Dict matching the NetworkData TypeScript interface:
        {
            'nodes': [{id, label, degree, anomaly_score, group}],
            'edges': [{id, from, to, weight, is_anomalous}],
            'anomalies': [{cluster_id, type, nodes, confidence, description}]
        }
    """
    if edge_df.empty:
        return {'nodes': [], 'edges': [], 'anomalies': []}

    # Aggregate edges: count unique interactions per pair
    edge_agg = edge_df.groupby(['source_user', 'target_mention']).agg(
        weight=('weight', 'max'),
    ).reset_index()

    # Compute node degrees
    out_degree = edge_agg.groupby('source_user')['weight'].sum()
    in_degree = edge_agg.groupby('target_mention')['weight'].sum()

    all_users = set(out_degree.index) | set(in_degree.index)
    degree_map = {}
    for user in all_users:
        degree_map[user] = int(out_degree.get(user, 0)) + int(in_degree.get(user, 0))

    # Select top nodes by degree
    top_users = sorted(degree_map.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
    top_user_set = set(u for u, _ in top_users)

    # Identify anomalous nodes from burst window analyses
    anomalous_users = set()
    for result in anomaly_results:
        if result.get('anomaly_score', 0) > anomaly_threshold:
            # Mark top sources in anomalous windows
            window_edges = result.get('_edges', pd.DataFrame())
            if not window_edges.empty:
                top_sources = window_edges['source_user'].value_counts().head(10).index.tolist()
                anomalous_users.update(top_sources)

    # Identify hub nodes (top 5 by in-degree)
    top_hubs = set(in_degree.nlargest(5).index)

    # Build nodes
    nodes = []
    for user, degree in top_users:
        if user in anomalous_users:
            group = 'anomalous'
            anomaly_score = 0.8
        elif user in top_hubs:
            group = 'hub'
            anomaly_score = 0.2
        else:
            group = 'normal'
            anomaly_score = 0.0

        nodes.append({
            'id': user,
            'label': user,
            'degree': degree,
            'anomaly_score': anomaly_score,
            'group': group,
        })

    # Build edges (only between included nodes)
    edges = []
    for idx, row in edge_agg.iterrows():
        src = row['source_user']
        tgt = row['target_mention']
        if src in top_user_set and tgt in top_user_set:
            is_anomalous = src in anomalous_users or tgt in anomalous_users
            edges.append({
                'id': f"e-{idx}",
                'from': src,
                'to': tgt,
                'weight': int(row['weight']),
                'is_anomalous': is_anomalous,
            })

    # Build anomaly clusters
    anomalies = []
    cluster_id = 0
    for result in anomaly_results:
        if result.get('anomaly_score', 0) > anomaly_threshold:
            cluster_id += 1
            score = result['anomaly_score']
            features = result.get('features', {})

            # Determine type based on dominant feature
            if features.get('hub_concentration', 0) > 0.6:
                atype = 'astroturfing'
                desc = f"High hub concentration ({features['hub_concentration']:.0%}) — many accounts mentioning the same target."
            elif features.get('temporal_clustering', 0) > 0.5:
                atype = 'bot_network'
                desc = f"Tight temporal clustering ({features['temporal_clustering']:.0%}) — coordinated posting within short window."
            elif features.get('degree_entropy', 0) > 0.5:
                atype = 'coordinated'
                desc = f"Low mention diversity ({features['degree_entropy']:.0%}) — repetitive mention pattern."
            else:
                atype = 'suspicious'
                desc = f"Multiple weak anomaly signals (composite score: {score:.0%})."

            window_edges = result.get('_edges', pd.DataFrame())
            cluster_nodes = []
            if not window_edges.empty:
                cluster_nodes = window_edges['source_user'].value_counts().head(15).index.tolist()

            anomalies.append({
                'cluster_id': cluster_id,
                'type': atype,
                'nodes': cluster_nodes,
                'confidence': round(score, 2),
                'description': desc,
            })

    return {
        'nodes': nodes,
        'edges': edges,
        'anomalies': anomalies,
    }


# ─── Pipeline Entry Point ───────────────────────────────────────────────────

def run_link_anomaly_analysis(edge_df: pd.DataFrame,
                               burst_periods: List[Dict],
                               anomaly_threshold: float = 0.5) -> Dict:
    """
    Run link anomaly detection for each burst period, then build network graph.

    For each burst period detected by Kleinberg, we window the edge list to
    that exact time range and compute the anomaly score. This is the critical
    "windowed social validation" strategy.

    Args:
        edge_df:            Full edge list DataFrame (from preprocessing)
        burst_periods:      List of burst dicts with {term, start, end, ...}
        anomaly_threshold:  Score above which activity is flagged

    Returns:
        Dict with:
        {
            'network': {nodes, edges, anomalies},
            'burst_anomaly_scores': [{term, start, end, anomaly_score, features}],
        }
    """
    if edge_df.empty:
        return {
            'network': {'nodes': [], 'edges': [], 'anomalies': []},
            'burst_anomaly_scores': [],
        }

    # Parse timestamps in edge list
    edge_df = edge_df.copy()
    edge_df['_ts'] = pd.to_datetime(edge_df['timestamp'], errors='coerce')

    burst_scores = []
    anomaly_results_with_edges = []

    for burst in burst_periods:
        start_ts = pd.to_datetime(burst['start'], errors='coerce')
        end_ts = pd.to_datetime(burst['end'], errors='coerce')

        if pd.isna(start_ts) or pd.isna(end_ts):
            continue

        # Window the edge list to this burst period
        mask = (edge_df['_ts'] >= start_ts) & (edge_df['_ts'] <= end_ts)
        windowed_edges = edge_df[mask]

        result = compute_anomaly_score(windowed_edges)
        result['_edges'] = windowed_edges  # Keep for network graph building

        burst_scores.append({
            'term': burst.get('term', ''),
            'start': burst['start'],
            'end': burst['end'],
            'burst_level': burst.get('burst_level', 1),
            'anomaly_score': result['anomaly_score'],
            'features': result['features'],
            'edge_count': result['edge_count'],
        })

        anomaly_results_with_edges.append(result)

    # Build the vis-network graph
    network = build_network_graph(
        edge_df, anomaly_results_with_edges, anomaly_threshold
    )

    return {
        'network': network,
        'burst_anomaly_scores': burst_scores,
    }
