"""
trend_validator.py — Dual-Gate Trending Topic Classification

The core thesis contribution: merges text-dimension burst analysis
(Kleinberg) with social-dimension link anomaly detection to produce
a validated, categorized trending topic classification.

Decision Matrix:
  ┌──────────────────┬──────────────────┬──────────────────┐
  │                  │  Normal Network  │ Anomalous Network│
  ├──────────────────┼──────────────────┼──────────────────┤
  │ Burst Detected   │ 🟢 ORGANIC      │ 🔴 ANOMALOUS     │
  │ (Kleinberg ≥ 1)  │                  │                  │
  ├──────────────────┼──────────────────┼──────────────────┤
  │ No Burst         │ ⚪ UNVERIFIED    │ 🟡 SUSPICIOUS    │
  │ (Kleinberg = 0)  │                  │                  │
  └──────────────────┴──────────────────┴──────────────────┘
"""

import pandas as pd
from typing import List, Dict, Optional
from collections import defaultdict


def classify_trend(term: str,
                   burst_level: int,
                   anomaly_score: float,
                   theta: float = 0.5) -> str:
    """
    Dual-gate trending topic validation.

    Args:
        term:          The candidate term
        burst_level:   Highest Kleinberg state (0 = no burst, 1+ = burst)
        anomaly_score: Link anomaly score (0 = normal, 1 = anomalous)
        theta:         Anomaly threshold (tunable hyperparameter)

    Returns:
        Status string: 'organic' | 'anomalous' | 'suspicious' | 'unverified'
    """
    has_burst = burst_level >= 1
    is_anomalous = anomaly_score > theta

    if has_burst and not is_anomalous:
        return 'organic'
    elif has_burst and is_anomalous:
        return 'anomalous'
    elif not has_burst and is_anomalous:
        return 'suspicious'
    else:
        return 'unverified'


def _infer_category(term: str) -> str:
    """
    Simple keyword-based category inference for geopolitical terms.
    This can be replaced with a more sophisticated classifier later.
    """
    categories = {
        'military': ['perang', 'militer', 'rudal', 'serangan', 'bom', 'nuklir',
                      'tank', 'pesawat', 'tentara', 'pasukan', 'senjata', 'invasi'],
        'diplomacy': ['negosiasi', 'perjanjian', 'damai', 'diplomasi', 'embargo',
                       'sanksi', 'resolusi', 'pbb', 'konferensi', 'bilateral'],
        'politics': ['presiden', 'pemerintah', 'kebijakan', 'partai', 'pemilu',
                      'demonstrasi', 'protes', 'referendum', 'oposisi'],
        'economy': ['minyak', 'ekonomi', 'pasar', 'saham', 'inflasi', 'harga',
                     'ekspor', 'impor', 'investasi'],
        'humanitarian': ['pengungsi', 'korban', 'sipil', 'kemanusiaan', 'evakuasi',
                          'bantuan', 'krisis'],
    }

    term_lower = term.lower()
    for category, keywords in categories.items():
        for kw in keywords:
            if kw in term_lower:
                return category

    return 'general'


def build_trend_summary(burst_periods: List[Dict],
                         burst_anomaly_scores: List[Dict],
                         edge_df: pd.DataFrame,
                         anomaly_threshold: float = 0.5) -> List[Dict]:
    """
    Build the executive summary: ranked list of trending topics with
    dual-validated classification.

    This function cross-references burst periods with their corresponding
    anomaly scores to produce the final classification matrix.

    Args:
        burst_periods:        List of burst period dicts from Kleinberg
        burst_anomaly_scores: List of per-burst anomaly score dicts
        edge_df:              Full edge list DataFrame (for mention counts)
        anomaly_threshold:    Score threshold for anomaly flagging

    Returns:
        List of trend dicts matching the TrendResult TypeScript interface:
        [{
            rank, term, category, status, burst_level,
            anomaly_score, mention_count, burst_start, burst_end
        }]
    """
    # Group bursts by term — take the strongest burst for each term
    term_bursts = defaultdict(list)
    for burst in burst_periods:
        term_bursts[burst['term']].append(burst)

    # Build anomaly score lookup: (term, start) → score
    anomaly_lookup = {}
    for score_entry in burst_anomaly_scores:
        key = (score_entry['term'], score_entry['start'])
        anomaly_lookup[key] = score_entry

    # Count mentions per term from the edge list
    mention_counts = defaultdict(int)
    if not edge_df.empty:
        for _, row in edge_df.iterrows():
            # A mention is any edge in the network during the analysis period
            mention_counts[row.get('source_user', '')] += 1
            mention_counts[row.get('target_mention', '')] += 1

    # Build trend results
    trends = []
    for term, bursts in term_bursts.items():
        # Take the burst with the highest level
        best_burst = max(bursts, key=lambda b: b.get('burst_level', 0))
        burst_level = best_burst.get('burst_level', 0)
        burst_start = best_burst.get('start', '')
        burst_end = best_burst.get('end', '')

        # Find the matching anomaly score
        lookup_key = (term, burst_start)
        anomaly_data = anomaly_lookup.get(lookup_key, {})
        anomaly_score = anomaly_data.get('anomaly_score', 0.0)

        # Classify using the dual-gate
        status = classify_trend(term, burst_level, anomaly_score, anomaly_threshold)

        # Count term mentions in the edge data
        # (proxy: count edges during the burst window)
        burst_edge_count = anomaly_data.get('edge_count', 0)

        trends.append({
            'term': term,
            'category': _infer_category(term),
            'status': status,
            'burst_level': burst_level,
            'anomaly_score': round(anomaly_score, 4),
            'mention_count': burst_edge_count,
            'burst_start': burst_start,
            'burst_end': burst_end,
            'intensity': best_burst.get('intensity', 0.0),
        })

    # Rank: organic first, then by burst level, then by intensity
    status_priority = {'organic': 0, 'anomalous': 1, 'suspicious': 2, 'unverified': 3}
    trends.sort(key=lambda t: (
        status_priority.get(t['status'], 9),
        -t['burst_level'],
        -t['intensity'],
    ))

    # Assign ranks
    for i, trend in enumerate(trends):
        trend['rank'] = i + 1

    return trends


# ─── Full Pipeline Orchestrator ──────────────────────────────────────────────

def run_full_pipeline(df_raw: pd.DataFrame,
                      df_cleaned: pd.DataFrame,
                      top_n_terms: int = 50,
                      bin_hours: int = 1,
                      kleinberg_s: float = 2.0,
                      kleinberg_gamma: float = 1.0,
                      anomaly_threshold: float = 0.5) -> Dict:
    """
    Execute the complete 5-step analysis pipeline.

    This is the master orchestrator that chains:
      1. Preprocessing (N-grams + Edge List)
      2. Kleinberg Burst Detection
      3. Link Anomaly Detection
      4. Trend Validation & Classification

    Args:
        df_raw:              Raw scraped tweets DataFrame
        df_cleaned:          Cleaned tweets DataFrame
        top_n_terms:         Number of top TF-IDF terms to analyze
        bin_hours:           Time bin width for burst detection
        kleinberg_s:         Scaling factor for Kleinberg
        kleinberg_gamma:     Transition cost for Kleinberg
        anomaly_threshold:   Score threshold for anomaly classification

    Returns:
        Dict with all pipeline results for the frontend to consume
    """
    from .preprocessing import (
        compute_dataset_overview,
        extract_ngrams,
        extract_edge_list,
        build_term_time_series,
    )
    from .kleinberg import run_burst_detection
    from .link_anomaly import run_link_anomaly_analysis

    # ─── Step 1: Dataset Overview ────────────────────────────────────
    overview = compute_dataset_overview(df_raw, df_cleaned)

    # ─── Step 2: Preprocessing ───────────────────────────────────────
    if 'cleaned_text' not in df_cleaned.columns and 'text' in df_cleaned.columns:
        df_cleaned['cleaned_text'] = df_cleaned['text']
        
    cleaned_texts = df_cleaned['cleaned_text'].dropna().astype(str).tolist()
    ngrams, total_tokens = extract_ngrams(cleaned_texts, n_range=(1, 2), min_df=5)
    edge_list = extract_edge_list(df_raw)

    # ─── Step 3: Burst Detection ─────────────────────────────────────
    time_series_data = build_term_time_series(
        df_cleaned, text_col='cleaned_text', time_col='datetime',
        top_n_terms=top_n_terms, bin_hours=bin_hours,
    )

    burst_result = run_burst_detection(
        time_series_data['term_series'],
        time_series_data['bins'],
        s=kleinberg_s,
        gamma=kleinberg_gamma,
    )

    # ─── Step 4: Link Anomaly Detection ──────────────────────────────
    anomaly_result = run_link_anomaly_analysis(
        edge_list,
        burst_result['burst_periods'],
        anomaly_threshold=anomaly_threshold,
    )

    # ─── Step 5: Trend Validation ────────────────────────────────────
    trend_summary = build_trend_summary(
        burst_result['burst_periods'],
        anomaly_result['burst_anomaly_scores'],
        edge_list,
        anomaly_threshold=anomaly_threshold,
    )

    return {
        'overview': overview,
        'ngrams': {
            'count': len(ngrams),
            'total_tokens': total_tokens,
            'results': ngrams.to_dict('records') if not ngrams.empty else [],
        },
        'edge_list': {
            'count': len(edge_list),
            'results': edge_list.head(100).to_dict('records') if not edge_list.empty else [],
        },
        'burst_analysis': burst_result,
        'network': anomaly_result['network'],
        'trends': trend_summary,
    }
