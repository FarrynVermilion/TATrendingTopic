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
import math

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
    """

    def __init__(self, K=15, alpha=0.1, beta=0.1, n_iters=30):
        self.K = K
        self.alpha = alpha
        self.beta = beta
        self.n_iters = n_iters

        # Corpus-level statistics
        self.number_docs = 0
        self.vocab_size = 0

        # Per-cluster statistics
        self.cluster_doc_count = [0] * K
        self.cluster_word_count = [0] * K
        self.cluster_word_distribution = [{} for _ in range(K)]

        # Step-by-step logs
        self.iteration_logs = []

    def calculate_coherence(self, docs, top_words, epsilon=1e-12):
        """
        Calculate UMass Coherence Score for a topic.
        Higher (less negative) is better.
        """
        coherence = 0.0
        # Build document-word mapping for fast lookup
        doc_sets = [set(doc) for doc in docs]
        
        for i in range(1, len(top_words)):
            w_i = top_words[i]
            # Count docs containing w_i
            d_wi = sum(1 for d in doc_sets if w_i in d)
            if d_wi == 0: continue
            
            for j in range(0, i):
                w_j = top_words[j]
                # Count docs containing both w_i and w_j
                d_wi_wj = sum(1 for d in doc_sets if w_i in d and w_j in d)
                
                coherence += math.log((d_wi_wj + epsilon) / d_wi)
        
        return round(coherence, 4)

    @staticmethod
    def _build_vocab(docs):
        vocab = set()
        for doc in docs:
            vocab.update(doc)
        return vocab

    def _get_cluster_snapshot(self, top_n=5):
        snapshot = []
        for k in range(self.K):
            top_words = sorted(
                self.cluster_word_distribution[k].items(),
                key=lambda x: x[1], reverse=True
            )[:top_n]
            snapshot.append({
                'cluster_id': k,
                'm_z': self.cluster_doc_count[k],
                'n_z': self.cluster_word_count[k],
                'top_words': [{'word': w, 'count': c} for w, c in top_words],
            })
        return snapshot

    def _initialize(self, docs):
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
        p = np.zeros(self.K)
        details = []
        doc_word_counts = Counter(doc)

        for k in range(self.K):
            m_z = self.cluster_doc_count[k]
            p_cluster = (m_z + self.alpha) / (self.number_docs - 1 + self.K * self.alpha)

            p_words = 1.0
            n_z = self.cluster_word_count[k]
            
            for word, count in doc_word_counts.items():
                n_z_w = self.cluster_word_distribution[k].get(word, 0)
                for j in range(count):
                    p_words *= (n_z_w + self.beta + j) / (n_z + self.vocab_size * self.beta + j)

            p_total = p_cluster * p_words
            p[k] = p_total

        total = p.sum()
        p_normalized = p / total if total > 0 else np.ones(self.K) / self.K
        return p_normalized, None

    def _remove_doc_from_cluster(self, doc, cluster):
        self.cluster_doc_count[cluster] -= 1
        for word in doc:
            self.cluster_word_count[cluster] -= 1
            self.cluster_word_distribution[cluster][word] -= 1
            if self.cluster_word_distribution[cluster][word] == 0:
                del self.cluster_word_distribution[cluster][word]

    def _add_doc_to_cluster(self, doc, cluster):
        self.cluster_doc_count[cluster] += 1
        for word in doc:
            self.cluster_word_count[cluster] += 1
            self.cluster_word_distribution[cluster][word] = \
                self.cluster_word_distribution[cluster].get(word, 0) + 1

    def fit(self, docs, sample_size=5):
        cluster_assignments = self._initialize(docs)
        for iteration in range(self.n_iters):
            total_transfers = 0
            for i, doc in enumerate(docs):
                prev_cluster = cluster_assignments[i]
                self._remove_doc_from_cluster(doc, prev_cluster)
                probabilities, _ = self._score_detailed(doc)
                new_cluster = int(np.argmax(np.random.multinomial(1, probabilities)))
                cluster_assignments[i] = new_cluster
                self._add_doc_to_cluster(doc, new_cluster)
                if new_cluster != prev_cluster:
                    total_transfers += 1
            if total_transfers == 0:
                break
        return cluster_assignments

    def get_topics(self, docs, top_n=10):
        topics = []
        for k in range(self.K):
            if self.cluster_doc_count[k] == 0:
                continue

            sorted_words = sorted(
                self.cluster_word_distribution[k].items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]

            top_words_list = [w for w, _ in sorted_words]
            coherence_score = self.calculate_coherence(docs, top_words_list)

            topics.append({
                'topic_id': k,
                'doc_count': self.cluster_doc_count[k],
                'top_words': top_words_list,
                'coherence_score': coherence_score
            })

        topics.sort(key=lambda x: x['doc_count'], reverse=True)
        for i, topic in enumerate(topics):
            topic['topic_label'] = i + 1
        return topics


def process_csv_gsdmm(file_obj, text_column, K=15, n_iters=20):
    df_raw = pd.read_csv(file_obj)
    dataset = [preprocess_tweet(str(text)) for text in df_raw[text_column] if not pd.isna(text)]
    dataset = [d for d in dataset if d]

    mgp = MovieGroupProcess(K=K, alpha=0.1, beta=0.1, n_iters=n_iters)
    assignments = mgp.fit(dataset)
    topics = mgp.get_topics(dataset, top_n=10)
    
    return topics, assignments
