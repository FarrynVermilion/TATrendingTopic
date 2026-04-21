"""
GSDMM (Gibbs Sampling Dirichlet Multinomial Mixture) implementation.

This algorithm is specifically designed for short-text topic modeling (e.g., tweets).
It uses the "Movie Group Process" analogy where documents cluster around topics
based on two principles:
  1. Documents prefer topics with more existing documents (popularity)
  2. Documents prefer topics whose word distribution matches their own (coherence)

Reference:
  Yin, J. & Wang, J. (2014). "A Dirichlet Multinomial Mixture Model-based Approach
  for Short Text Clustering." In Proceedings of KDD '14.

This implementation records detailed step-by-step calculations for academic use.
"""

import numpy as np
import pandas as pd
from collections import Counter
from copy import deepcopy

def preprocess_tweet(tweet):
    """
    Assume the tweet is already pre-cleaned and tokenized by the offline script.
    Simply splits the string by whitespace to get the list of tokens.
    """
    if not isinstance(tweet, str):
        return []
    
    # Split by whitespace and filter out empty strings
    tokens = [t for t in tweet.split() if t]
    return tokens



class MovieGroupProcess:
    """
    GSDMM topic model for short texts.

    Parameters
    ----------
    K : int
        Maximum number of topics (clusters). The algorithm may use fewer
        if it determines some clusters are empty.
    alpha : float
        Dirichlet prior for document-topic distribution. Controls how
        strongly documents are attracted to popular clusters. Lower values
        lead to fewer, larger clusters.
    beta : float
        Dirichlet prior for topic-word distribution. Controls smoothing
        of word probabilities within clusters. Lower values lead to more
        distinct word distributions per topic.
    n_iters : int
        Number of Gibbs sampling iterations to run.
    """

    def __init__(self, K=15, alpha=0.1, beta=0.1, n_iters=30):
        self.K = K
        self.alpha = alpha
        self.beta = beta
        self.n_iters = n_iters

        # Corpus-level statistics (populated during fitting)
        self.number_docs = 0
        self.vocab_size = 0

        # Per-cluster statistics
        self.cluster_doc_count = [0] * K       # m_z: number of docs in cluster z
        self.cluster_word_count = [0] * K      # n_z: total words in cluster z
        self.cluster_word_distribution = [{} for _ in range(K)]  # n_z_w: word counts per cluster

        # Step-by-step logs for skripsi display
        self.iteration_logs = []

    @staticmethod
    def _build_vocab(docs):
        """Build vocabulary set from list of tokenized documents."""
        vocab = set()
        for doc in docs:
            vocab.update(doc)
        return vocab

    def _get_cluster_snapshot(self, top_n=5):
        """
        Take a snapshot of current cluster statistics.
        Used for recording state at each step.
        """
        snapshot = []
        for k in range(self.K):
            top_words = sorted(
                self.cluster_word_distribution[k].items(),
                key=lambda x: x[1], reverse=True
            )[:top_n]
            snapshot.append({
                'cluster_id': k,
                'm_z': self.cluster_doc_count[k],      # doc count
                'n_z': self.cluster_word_count[k],      # total word count
                'top_words': [{'word': w, 'count': c} for w, c in top_words],
            })
        return snapshot

    def _initialize(self, docs):
        """
        Phase 1: Random initialization.
        Assign each document to a random cluster and update statistics.
        """
        self.number_docs = len(docs)
        self.vocab_size = len(self._build_vocab(docs))

        cluster_assignments = []
        for doc in docs:
            z = np.random.randint(0, self.K)
            cluster_assignments.append(z)

            self.cluster_doc_count[z] += 1
            for word in doc:
                self.cluster_word_count[z] += 1
                self.cluster_word_distribution[z][word] = \
                    self.cluster_word_distribution[z].get(word, 0) + 1

        return cluster_assignments

    def _score_detailed(self, doc):
        """
        Calculate the probability with full calculation details.

        For each cluster k, computes:
          p(z=k|d) ∝ p(z=k) × p(words_in_d | z=k)

        Where:
          p(z=k) = (m_z + α) / (D - 1 + K × α)
          p(words|z=k) = ∏ over words w with count c_w in doc:
              ∏ j=0..c_w-1: (n_{z,w} + β + j) / (n_z + V×β + j)

        Returns
        -------
        probabilities : np.ndarray
            Normalized probabilities.
        details : list[dict]
            Per-cluster calculation breakdown.
        """
        p = np.zeros(self.K)
        details = []
        doc_word_counts = Counter(doc)

        for k in range(self.K):
            # Component 1: p(z=k) — Cluster popularity
            m_z = self.cluster_doc_count[k]
            p_cluster_num = m_z + self.alpha
            p_cluster_den = self.number_docs - 1 + self.K * self.alpha
            p_cluster = p_cluster_num / p_cluster_den

            # Component 2: p(words|z=k) — Word likelihood
            p_words = 1.0
            word_calc_steps = []
            n_z = self.cluster_word_count[k]
            p_words_factors = []  # collect each factor string for the formula display

            for word, count in doc_word_counts.items():
                n_z_w = self.cluster_word_distribution[k].get(word, 0)
                word_factors = []
                for j in range(count):
                    numerator = n_z_w + self.beta + j
                    denominator = n_z + self.vocab_size * self.beta + j
                    factor = numerator / denominator
                    p_words *= factor
                    word_factors.append({
                        'j': j,
                        'numerator': round(numerator, 4),
                        'denominator': round(denominator, 4),
                        'formula': f"({n_z_w}+{self.beta}+{j})/({n_z}+{self.vocab_size}×{self.beta}+{j})",
                        'result': round(factor, 8),
                    })
                    p_words_factors.append(f"({n_z_w}+{self.beta}+{j})/({n_z}+{self.vocab_size}×{self.beta}+{j})")

                word_calc_steps.append({
                    'word': word,
                    'count_in_doc': count,
                    'n_z_w': n_z_w,
                    'factors': word_factors,
                })

            p_total = p_cluster * p_words
            p[k] = p_total

            details.append({
                'cluster': k,
                'm_z': m_z,
                'n_z': n_z,
                'p_cluster': round(p_cluster, 8),
                'p_cluster_formula': f"({m_z} + {self.alpha}) / ({self.number_docs - 1} + {self.K} × {self.alpha})",
                'p_words': float(f"{p_words:.8e}"),
                'p_words_formula': " × ".join(p_words_factors) if p_words_factors else "1",
                'p_total_raw': float(f"{p_total:.8e}"),
                'word_details': word_calc_steps,
            })

        # Normalize
        total = p.sum()
        if total > 0:
            p_normalized = p / total
        else:
            p_normalized = np.ones(self.K) / self.K

        # Add normalized probabilities to details
        for k in range(self.K):
            details[k]['p_normalized'] = round(float(p_normalized[k]), 8)

        return p_normalized, details

    def _remove_doc_from_cluster(self, doc, cluster):
        """Remove a document's contribution from its current cluster."""
        self.cluster_doc_count[cluster] -= 1
        for word in doc:
            self.cluster_word_count[cluster] -= 1
            self.cluster_word_distribution[cluster][word] -= 1
            if self.cluster_word_distribution[cluster][word] == 0:
                del self.cluster_word_distribution[cluster][word]

    def _add_doc_to_cluster(self, doc, cluster):
        """Add a document's contribution to a cluster."""
        self.cluster_doc_count[cluster] += 1
        for word in doc:
            self.cluster_word_count[cluster] += 1
            self.cluster_word_distribution[cluster][word] = \
                self.cluster_word_distribution[cluster].get(word, 0) + 1

    def fit(self, docs, sample_size=5):
        """
        Fit the GSDMM model with detailed step logging.

        Parameters
        ----------
        docs : list[list[str]]
            List of tokenized documents.
        sample_size : int
            Number of sample documents to log detailed calculations for
            per iteration (to keep response size manageable).

        Returns
        -------
        cluster_assignments : list[int]
            Final cluster assignment for each document.
        """
        cluster_assignments = self._initialize(docs)
        self.iteration_logs = []

        # Log initial state
        initial_log = {
            'phase': 'initialization',
            'description': 'Random assignment of each document to a cluster',
            'params': {
                'K': self.K,
                'alpha': self.alpha,
                'beta': self.beta,
                'D': self.number_docs,
                'V': self.vocab_size,
                'n_iters': self.n_iters,
            },
            'assignments': list(cluster_assignments),
            'cluster_stats': self._get_cluster_snapshot(),
        }
        self.iteration_logs.append(initial_log)

        for iteration in range(self.n_iters):
            total_transfers = 0
            sample_calculations = []

            for i, doc in enumerate(docs):
                prev_cluster = cluster_assignments[i]

                # Step a: Remove doc from current cluster
                self._remove_doc_from_cluster(doc, prev_cluster)

                # Step b: Score all clusters (with details for sample docs)
                is_sample = i < sample_size
                if is_sample:
                    probabilities, calc_details = self._score_detailed(doc)
                else:
                    probabilities, _ = self._score_detailed(doc)
                    calc_details = None

                # Step c: Sample new cluster
                new_cluster = int(np.argmax(np.random.multinomial(1, probabilities)))

                # Step d: Add doc to new cluster
                cluster_assignments[i] = new_cluster
                self._add_doc_to_cluster(doc, new_cluster)

                if new_cluster != prev_cluster:
                    total_transfers += 1

                # Record sample document calculations
                if is_sample:
                    sample_calculations.append({
                        'doc_index': i + 1,
                        'doc_words': list(doc),
                        'prev_cluster': prev_cluster,
                        'new_cluster': new_cluster,
                        'transferred': new_cluster != prev_cluster,
                        'probabilities': [round(float(p), 8) for p in probabilities],
                        'chosen_cluster_prob': round(float(probabilities[new_cluster]), 8),
                        'cluster_details': calc_details,
                    })

            # Log this iteration
            iter_log = {
                'phase': 'iteration',
                'iteration': iteration + 1,
                'total_transfers': total_transfers,
                'total_documents': len(docs),
                'converged': total_transfers == 0,
                'cluster_stats': self._get_cluster_snapshot(),
                'sample_calculations': sample_calculations,
            }
            self.iteration_logs.append(iter_log)

            # Early stopping if converged
            if total_transfers == 0:
                break

        return cluster_assignments

    def get_topics(self, top_n=10):
        """
        Extract the top N words for each non-empty cluster.
        """
        topics = []
        for k in range(self.K):
            if self.cluster_doc_count[k] == 0:
                continue

            sorted_words = sorted(
                self.cluster_word_distribution[k].items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]

            total_words_in_cluster = self.cluster_word_count[k]
            topics.append({
                'topic_id': k,
                'doc_count': self.cluster_doc_count[k],
                'top_words': [w for w, _ in sorted_words],
                'word_scores': {
                    w: round(c / total_words_in_cluster, 4) if total_words_in_cluster > 0 else 0
                    for w, c in sorted_words
                }
            })

        topics.sort(key=lambda x: x['doc_count'], reverse=True)

        for i, topic in enumerate(topics):
            topic['topic_label'] = i + 1

        return topics


def process_csv_gsdmm(file_obj, text_column, K=15, n_iters=20):
    """
    Process a CSV file and run GSDMM topic modeling.
    Note: This function now expects the 'text_column' to already be pre-cleaned 
    (tokenized words separated by spaces).

    Returns
    -------
    topics : list[dict]
        Topic summaries with top words.
    documents : list[dict]
        Each document with its topic assignment.
    iteration_logs : list[dict]
        Step-by-step calculation logs for each iteration.
    """
    df_raw = pd.read_csv(file_obj)

    if text_column not in df_raw.columns:
        raise ValueError(f"Column '{text_column}' not found in CSV.")

    # Preprocess all documents
    dataset = []
    original_texts = []
    original_indices = []

    for i, text in enumerate(df_raw[text_column]):
        if pd.isna(text):
            continue
        tokens = preprocess_tweet(str(text))
        if tokens:
            dataset.append(tokens)
            original_texts.append(str(text))
            original_indices.append(i)

    if not dataset:
        raise ValueError("No valid text data found after preprocessing.")

    # Run GSDMM
    mgp = MovieGroupProcess(K=K, alpha=0.1, beta=0.1, n_iters=n_iters)
    assignments = mgp.fit(dataset, sample_size=5)

    # Extract topics
    topics = mgp.get_topics(top_n=10)

    # Build a mapping from raw cluster_id to sequential topic_label
    cluster_to_label = {t['topic_id']: t['topic_label'] for t in topics}

    # Build document results
    documents = []
    for i, (tokens, assignment) in enumerate(zip(dataset, assignments)):
        documents.append({
            'doc_index': original_indices[i] + 1,
            'original_text': original_texts[i],
            'preprocessed': ', '.join(tokens),
            'topic_id': cluster_to_label.get(assignment, -1),
        })

    return topics, documents, mgp.iteration_logs
