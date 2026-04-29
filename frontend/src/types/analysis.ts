/**
 * TypeScript interfaces for the Trending Topic Analysis Pipeline.
 * "Detection of Geopolitical Trending Topics Using Modified Term-Level
 *  Burst Kleinberg and Mention-Based Link Anomaly"
 */

// ─── Step 1: Dataset Overview ───────────────────────────────────────────────

export interface DatasetMeta {
  total_tweets: number
  rate_limit: number
  date_range: { start: string; end: string }
  keyword_distribution: Record<string, number>
  unique_users: number
  avg_tweets_per_hour: number
}

// ─── Step 2: Preprocessing ──────────────────────────────────────────────────

export interface NGram {
  id: number
  term: string
  frequency: number
  n: number              // 1 for unigram, 2 for bigram, etc.
  df: number             // document frequency
  tf_idf: number
}

export interface Edge {
  id: number
  source_user: string
  target_mention: string
  weight: number
  tweet_id: string
  timestamp: string
}

export interface PaginatedResponse<T> {
  results: T[]
  count: number
  next: string | null
  previous: string | null
}

// ─── Step 3: Burst Kleinberg ────────────────────────────────────────────────

export interface TimeSeriesPoint {
  date: string
  frequency: number
  term: string
}

export interface BurstPeriod {
  term: string
  start: string
  end: string
  burst_level: number    // Kleinberg state (0 = baseline, 1+ = burst)
  intensity: number      // normalized score 0..1
}

export interface BurstAnalysis {
  term_frequencies: TimeSeriesPoint[]
  burst_periods: BurstPeriod[]
  available_terms: string[]
}

// ─── Step 4: Link Anomaly ───────────────────────────────────────────────────

export interface NetworkNode {
  id: string
  label: string
  group: string          // 'normal' | 'anomalous' | 'hub'
  degree: number
  anomaly_score: number
  size?: number
}

export interface NetworkEdge {
  id: string
  from: string
  to: string
  weight: number
  is_anomalous: boolean
}

export interface AnomalyResult {
  cluster_id: string
  type: 'bot_network' | 'astroturfing' | 'organic' | 'coordinated'
  confidence: number
  nodes: string[]
  description: string
}

export interface NetworkData {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
  anomalies: AnomalyResult[]
}

// ─── Step 5: Executive Summary ──────────────────────────────────────────────

export type TrendStatus = 'organic' | 'anomalous' | 'suspicious' | 'unverified'

export interface TrendResult {
  rank: number
  term: string
  category: string
  burst_level: number
  burst_start: string
  burst_end: string
  anomaly_score: number
  status: TrendStatus
  supporting_evidence: string
  mention_count: number
  unique_users: number
}

// ─── Pipeline Control ───────────────────────────────────────────────────────

export type PipelineStatus = 'idle' | 'running' | 'completed' | 'error'

export type StepId = 1 | 2 | 3 | 4 | 5

export interface StepDefinition {
  id: StepId
  title: string
  subtitle: string
  icon: string
  isCompleted: boolean
  isActive: boolean
  isLocked: boolean
}
