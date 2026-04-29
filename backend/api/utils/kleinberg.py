"""
kleinberg.py — Modified Term-Level Burst Detection (Kleinberg 2002)

Implements the Kleinberg burst detection algorithm adapted for term-level
analysis of tweet time-series data. Instead of detecting bursts in overall
document volume, this module detects bursts in individual term frequencies.

Reference:
  Kleinberg, J. (2002). "Bursty and Hierarchical Structure in Streams."
  In Proceedings of the 8th ACM SIGKDD.

The "modification" is the term-level application: for each candidate term,
we construct a per-hour frequency time-series, then run the Kleinberg
automaton to identify contiguous burst intervals.
"""

import math
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BurstInterval:
    """A detected burst period for a specific term."""
    term: str
    start: str         # Bin label (datetime string)
    end: str           # Bin label (datetime string)
    burst_level: int   # Kleinberg state (1+ = burst, higher = stronger)
    intensity: float   # Normalized intensity score [0, 1]
    weight: float      # Raw cost/significance of this burst


class KleinbergBurstDetector:
    """
    Kleinberg's infinite-state automaton for burst detection.

    The algorithm models a stream of events as transitions between
    discrete states, where higher states correspond to higher event
    rates (bursts). The optimal state sequence is found via dynamic
    programming (Viterbi algorithm).

    Parameters:
        s:     Scaling factor between burst states (default: 2.0)
               Higher s requires stronger evidence for bursts.
        gamma: Transition cost coefficient (default: 1.0)
               Higher gamma penalizes state transitions more heavily,
               producing fewer, more significant bursts.
    """

    def __init__(self, s: float = 2.0, gamma: float = 1.0):
        self.s = s
        self.gamma = gamma

    def detect(self, counts: List[int], labels: List[str],
               max_states: int = 5) -> List[dict]:
        """
        Run burst detection on a single term's time-series.

        Args:
            counts:     List of event counts per time bin
            labels:     List of bin labels (e.g., datetime strings)
            max_states: Maximum number of burst states to consider

        Returns:
            List of dicts with keys: {start, end, burst_level, weight}
        """
        n = len(counts)
        if n == 0:
            return []

        total_events = sum(counts)
        if total_events == 0:
            return []

        # Base rate: expected events per interval
        base_rate = total_events / n

        if base_rate < 0.1:
            # Too sparse — can't meaningfully detect bursts
            return []

        # Rate for each state: λ_q = base_rate * s^q
        rates = [base_rate * (self.s ** q) for q in range(max_states)]

        # Transition cost: τ(i, j) = (j - i) * gamma * ln(n)  if j > i
        ln_n = math.log(max(n, 2))

        def transition_cost(from_state: int, to_state: int) -> float:
            if to_state <= from_state:
                return 0.0
            return (to_state - from_state) * self.gamma * ln_n

        # Emission cost: -log P(count | state)
        # Using Poisson model: P(k; λ) = (λ^k * e^-λ) / k!
        def emission_cost(count: int, state: int) -> float:
            lam = rates[state]
            if lam <= 0:
                return float('inf')
            # -log Poisson(count; lam)
            # = lam - count * ln(lam) + ln(count!)
            log_factorial = sum(math.log(i) for i in range(1, count + 1))
            return lam - count * math.log(lam) + log_factorial

        # ─── Viterbi Algorithm ───────────────────────────────────────

        # dp[t][q] = minimum total cost to be in state q at time t
        dp = np.full((n, max_states), float('inf'))
        backptr = np.zeros((n, max_states), dtype=int)

        # Initialize t=0
        for q in range(max_states):
            dp[0][q] = transition_cost(0, q) + emission_cost(counts[0], q)

        # Fill forward
        for t in range(1, n):
            for q in range(max_states):
                emit = emission_cost(counts[t], q)
                best_cost = float('inf')
                best_prev = 0

                for prev_q in range(max_states):
                    cost = dp[t - 1][prev_q] + transition_cost(prev_q, q) + emit
                    if cost < best_cost:
                        best_cost = cost
                        best_prev = prev_q

                dp[t][q] = best_cost
                backptr[t][q] = best_prev

        # Backtrack: find optimal state sequence
        states = [0] * n
        states[-1] = int(np.argmin(dp[-1]))

        for t in range(n - 2, -1, -1):
            states[t] = backptr[t + 1][states[t + 1]]

        # ─── Extract Burst Intervals ─────────────────────────────────

        bursts = []
        i = 0
        while i < n:
            if states[i] >= 1:
                level = states[i]
                start_idx = i
                # Extend while in the same or higher burst state
                while i < n and states[i] >= 1:
                    level = max(level, states[i])
                    i += 1
                end_idx = i - 1

                # Weight: sum of counts during burst - expected baseline count
                burst_count = sum(counts[start_idx:end_idx + 1])
                expected_count = base_rate * (end_idx - start_idx + 1)
                weight = burst_count - expected_count

                bursts.append({
                    'start': labels[start_idx],
                    'end': labels[end_idx],
                    'burst_level': level,
                    'weight': round(weight, 2),
                })
            else:
                i += 1

        return bursts

    def detect_for_term(self, term: str, series: List[Tuple[str, int]]) -> List[BurstInterval]:
        """
        Convenience wrapper: run detection on a (label, count) series for a named term.

        Args:
            term:   The term being analyzed
            series: List of (bin_label, count) tuples

        Returns:
            List of BurstInterval objects
        """
        if not series:
            return []

        labels = [s[0] for s in series]
        counts = [s[1] for s in series]

        raw_bursts = self.detect(counts, labels)

        if not raw_bursts:
            return []

        # Normalize intensities relative to the strongest burst
        max_weight = max(b['weight'] for b in raw_bursts) if raw_bursts else 1.0
        max_weight = max(max_weight, 1.0)

        return [
            BurstInterval(
                term=term,
                start=b['start'],
                end=b['end'],
                burst_level=b['burst_level'],
                intensity=round(min(b['weight'] / max_weight, 1.0), 4),
                weight=b['weight'],
            )
            for b in raw_bursts
        ]


# ─── Pipeline Entry Point ───────────────────────────────────────────────────

def run_burst_detection(term_series: Dict[str, List[Tuple[str, int]]],
                        bins: List[str],
                        s: float = 2.0,
                        gamma: float = 1.0,
                        selected_term: Optional[str] = None) -> Dict:
    """
    Run burst detection across multiple terms (or a single selected term).

    Args:
        term_series:   Dict mapping term -> [(bin_label, count), ...]
        bins:          Full list of bin labels
        s:             Kleinberg scaling factor
        gamma:         Kleinberg transition cost
        selected_term: If set, only analyze this term

    Returns:
        Dict matching the BurstAnalysis TypeScript interface:
        {
            'term_frequencies': [{'date': ..., 'frequency': ..., 'term': ...}],
            'burst_periods':    [{'term': ..., 'start': ..., 'end': ..., 'burst_level': ..., 'intensity': ...}],
            'available_terms':  [...]
        }
    """
    detector = KleinbergBurstDetector(s=s, gamma=gamma)

    available_terms = list(term_series.keys())

    if selected_term and selected_term in term_series:
        terms_to_analyze = [selected_term]
    else:
        terms_to_analyze = available_terms

    # Build frequency output
    frequencies = []
    for term in terms_to_analyze:
        for label, count in term_series.get(term, []):
            frequencies.append({
                'date': label,
                'frequency': count,
                'term': term,
            })

    # Run burst detection
    all_bursts = []
    for term in terms_to_analyze:
        series = term_series.get(term, [])
        bursts = detector.detect_for_term(term, series)
        for b in bursts:
            all_bursts.append({
                'term': b.term,
                'start': b.start,
                'end': b.end,
                'burst_level': b.burst_level,
                'intensity': b.intensity,
            })

    return {
        'term_frequencies': frequencies,
        'burst_periods': all_bursts,
        'available_terms': available_terms,
    }
