"""
preprocessing.py — N-Gram Extraction & Mention Edge List Builder

Extracts two parallel data streams from the raw tweet dataset:
  1. N-Gram term list with TF-IDF scores (from cleaned text)
  2. Directed edge list of @mention relationships (from raw text)

This module bridges the gap between the scraper output and the two
analysis dimensions (Burst Kleinberg + Link Anomaly).
"""

import re
import math
import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
from typing import List, Dict, Tuple, Optional


# ─── N-Gram Extraction ──────────────────────────────────────────────────────

def extract_ngrams(texts: List[str], n_range: Tuple[int, int] = (1, 2),
                   min_df: int = 3, max_df_ratio: float = 0.85) -> pd.DataFrame:
    """
    Extract N-grams from cleaned text with TF-IDF scoring.

    Args:
        texts:        List of cleaned tweet texts (already stemmed/stopword-removed)
        n_range:      Tuple of (min_n, max_n) for N-gram sizes
        min_df:       Minimum document frequency to keep a term
        max_df_ratio: Maximum document frequency ratio (filter too-common terms)

    Returns:
        DataFrame with columns: [term, frequency, n, df, tf_idf]
    """
    N = len(texts)
    if N == 0:
        return pd.DataFrame(columns=['term', 'frequency', 'n', 'df', 'tf_idf'])

    # Tokenize and generate N-grams
    global_freq = Counter()
    doc_freq = Counter()

    for text in texts:
        if not isinstance(text, str) or not text.strip():
            continue

        tokens = text.split()
        doc_ngrams = set()

        for n in range(n_range[0], n_range[1] + 1):
            for i in range(len(tokens) - n + 1):
                ngram = ' '.join(tokens[i:i + n])
                global_freq[ngram] += 1
                doc_ngrams.add(ngram)

        for ngram in doc_ngrams:
            doc_freq[ngram] += 1

    # Compute TF-IDF and filter
    total_terms = sum(global_freq.values())
    max_df = int(N * max_df_ratio)

    records = []
    for term, freq in global_freq.items():
        df = doc_freq[term]

        if df < min_df or df > max_df:
            continue

        tf = freq / total_terms
        idf = math.log2(N / df) if df > 0 else 0
        tf_idf = tf * idf

        n_size = len(term.split())
        records.append({
            'term': term,
            'frequency': freq,
            'n': n_size,
            'df': df,
            'tf': round(tf, 8),
            'idf': round(idf, 4),
            'tf_idf': round(tf_idf, 6),
        })

    df_result = pd.DataFrame(records)
    if not df_result.empty:
        df_result = df_result.sort_values('tf_idf', ascending=False).reset_index(drop=True)
        df_result.insert(0, 'id', range(1, len(df_result) + 1))

    return df_result, total_terms


# ─── Edge List (Mention Graph) Extraction ────────────────────────────────────

MENTION_REGEX = re.compile(r'@(\w+)')


def extract_edge_list(df: pd.DataFrame,
                      text_col: str = 'text',
                      handle_col: str = 'handle',
                      time_col: str = 'datetime',
                      tweet_id_col: str = 'tweet_id') -> pd.DataFrame:
    """
    Build a directed edge list from @mention patterns in raw tweet text.

    Each row represents: source_user --mentions--> target_user

    IMPORTANT: Must use RAW text (before cleaning), because the cleaner
    removes @mentions via regex.

    Args:
        df:           Raw tweet DataFrame
        text_col:     Column containing raw tweet text
        handle_col:   Column containing the tweet author's handle
        time_col:     Column containing tweet timestamp
        tweet_id_col: Column containing tweet ID

    Returns:
        DataFrame with columns: [id, source_user, target_mention, weight, tweet_id, timestamp]
    """
    edges = []
    edge_counter = Counter()

    for _, row in df.iterrows():
        raw_text = str(row.get(text_col, ''))
        source = str(row.get(handle_col, '')).lower()
        timestamp = str(row.get(time_col, ''))
        tweet_id = str(row.get(tweet_id_col, ''))

        if not source or not raw_text:
            continue

        mentions = MENTION_REGEX.findall(raw_text)
        for target in mentions:
            target = target.lower()
            if target == source:
                continue  # Skip self-mentions

            edge_key = (source, target)
            edge_counter[edge_key] += 1

            edges.append({
                'source_user': source,
                'target_mention': target,
                'weight': edge_counter[edge_key],
                'tweet_id': tweet_id,
                'timestamp': timestamp,
            })

    df_edges = pd.DataFrame(edges)
    if not df_edges.empty:
        df_edges.insert(0, 'id', range(1, len(df_edges) + 1))
    else:
        df_edges = pd.DataFrame(
            columns=['id', 'source_user', 'target_mention', 'weight', 'tweet_id', 'timestamp']
        )

    return df_edges


# ─── Time-Binned Term Frequencies ────────────────────────────────────────────

def build_term_time_series(df: pd.DataFrame,
                           text_col: str = 'cleaned_text',
                           time_col: str = 'datetime',
                           top_n_terms: int = 100,
                           bin_hours: int = 1) -> Dict:
    """
    Construct per-term time-binned frequency series for Burst Detection.

    Args:
        df:           DataFrame with cleaned text and timestamps
        text_col:     Column with cleaned (stemmed) text
        time_col:     Column with timestamps
        top_n_terms:  Number of top TF-IDF terms to track
        bin_hours:    Width of each time bin in hours

    Returns:
        Dict with:
          'term_series': {term: [(bin_label, count), ...]}
          'bins':        List of bin labels (datetime strings)
          'available_terms': List of term names
    """
    # Parse timestamps
    df = df.copy()
    df['_ts'] = pd.to_datetime(df[time_col], errors='coerce')
    df = df.dropna(subset=['_ts'])

    if df.empty:
        return {'term_series': {}, 'bins': [], 'available_terms': []}

    # Determine the top-N terms by TF-IDF
    all_texts = df[text_col].dropna().astype(str).tolist()
    ngram_df, _ = extract_ngrams(all_texts, n_range=(1, 1), min_df=5)

    if ngram_df.empty:
        return {'term_series': {}, 'bins': [], 'available_terms': []}

    top_terms = ngram_df.head(top_n_terms)['term'].tolist()

    # Create time bins
    min_ts = df['_ts'].min()
    max_ts = df['_ts'].max()
    freq_str = f'{bin_hours}h'
    bins = pd.date_range(start=min_ts.floor(freq_str), end=max_ts.ceil(freq_str), freq=freq_str)
    bin_labels = [b.strftime('%Y-%m-%d %H:%M') for b in bins[:-1]]

    df['_bin'] = pd.cut(df['_ts'], bins=bins, labels=bin_labels, include_lowest=True)

    # Count per-term per-bin
    term_series = {}
    for term in top_terms:
        mask = df[text_col].astype(str).str.contains(
            r'(?:^|\s)' + re.escape(term) + r'(?:\s|$)', regex=True, na=False
        )
        term_df = df[mask]
        counts = term_df.groupby('_bin', observed=True).size()
        series = [(label, int(counts.get(label, 0))) for label in bin_labels]
        term_series[term] = series

    return {
        'term_series': term_series,
        'bins': bin_labels,
        'available_terms': top_terms,
    }


# ─── Dataset Overview Statistics ─────────────────────────────────────────────

def compute_dataset_overview(df_raw: pd.DataFrame, df_cleaned: pd.DataFrame) -> Dict:
    """
    Compute the Step 1 overview statistics.

    Args:
        df_raw:     Raw scraped DataFrame
        df_cleaned: Cleaned DataFrame

    Returns:
        Dict matching the DatasetMeta TypeScript interface
    """
    # Defensive check for required columns
    required = ['datetime', 'keyword', 'handle']
    missing = [c for c in required if c not in df_raw.columns]
    if missing:
        raise KeyError(f"Dataset is missing required columns: {', '.join(missing)}")

    timestamps = pd.to_datetime(df_raw['datetime'], errors='coerce').dropna()

    # Extract clean keyword (strip since_time/until_time suffixes)
    keywords = df_raw['keyword'].astype(str).str.split(r'\s+since_time', regex=True).str[0]
    keyword_dist = {str(k): int(v) for k, v in keywords.value_counts().head(20).items()}

    # Compute stats
    if len(timestamps) >= 2:
        total_hours = (timestamps.max() - timestamps.min()).total_seconds() / 3600
        avg_per_hour = round(len(timestamps) / max(total_hours, 1), 1)
        
        # Calculate peak hourly rate using a 60-minute rolling window
        # (This avoids the "calendar hour split" issue)
        ts_series = pd.Series(1, index=timestamps).sort_index()
        rolling_counts = ts_series.rolling('1h').count()
        peak_rate = int(rolling_counts.max()) if not rolling_counts.empty else 0
    else:
        avg_per_hour = 0
        peak_rate = len(df_raw)

    preview_data = df_raw.head(5).fillna('').to_dict(orient='records')
    available_columns = df_raw.columns.tolist()

    return {
        'total_tweets': len(df_raw),
        'rate_limit': peak_rate,
        'date_range': {
            'start': timestamps.min().strftime('%Y-%m-%d') if len(timestamps) > 0 else '',
            'end': timestamps.max().strftime('%Y-%m-%d') if len(timestamps) > 0 else '',
        },
        'keyword_distribution': keyword_dist,
        'unique_users': int(df_raw['handle'].nunique()),
        'avg_tweets_per_hour': avg_per_hour,
        'available_columns': available_columns,
        'preview_data': preview_data,
    }
