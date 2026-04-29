import axios from 'axios'
import type {
  DatasetMeta,
  NGram,
  Edge,
  PaginatedResponse,
  BurstAnalysis,
  NetworkData,
  TrendResult,
} from '@/types/analysis'

// ─── Axios Instance ─────────────────────────────────────────────────────────

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  headers: {
    'X-Api-Key': import.meta.env.VITE_API_KEY || 'default_secret_key',
    'Content-Type': 'application/json',
  },
})

// ─── Step 1: Dataset Overview ───────────────────────────────────────────────

export async function getDatasetOverview(): Promise<DatasetMeta> {
  const { data } = await api.get<DatasetMeta>('/dataset/overview/')
  return data
}

export async function startPipeline(): Promise<{ pipeline_id: string; status: string }> {
  const { data } = await api.post('/pipeline/start/')
  return data
}

// ─── Step 2: Preprocessing ──────────────────────────────────────────────────

export async function getNgrams(page: number = 1): Promise<PaginatedResponse<NGram>> {
  const { data } = await api.get<PaginatedResponse<NGram>>('/preprocessing/ngrams/', {
    params: { page },
  })
  return data
}

export async function getEdges(page: number = 1): Promise<PaginatedResponse<Edge>> {
  const { data } = await api.get<PaginatedResponse<Edge>>('/preprocessing/edges/', {
    params: { page },
  })
  return data
}

// ─── Step 3: Burst Kleinberg ────────────────────────────────────────────────

export async function getBurstAnalysis(term?: string): Promise<BurstAnalysis> {
  const { data } = await api.get<BurstAnalysis>('/burst/analysis/', {
    params: term ? { term } : {},
  })
  return data
}

// ─── Step 4: Link Anomaly ───────────────────────────────────────────────────

export async function getNetworkData(): Promise<NetworkData> {
  const { data } = await api.get<NetworkData>('/link-anomaly/network/')
  return data
}

// ─── Step 5: Executive Summary ──────────────────────────────────────────────

export async function getTrendSummary(): Promise<{ trends: TrendResult[] }> {
  const { data } = await api.get<{ trends: TrendResult[] }>('/summary/trends/')
  return data
}

// ─── Legacy: GSDMM endpoints (preserved for backward compatibility) ─────────

export async function getCsvHeaders(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/get-headers/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export async function processGsdmm(file: File, textColumn: string, numTopics: number = 15) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('text_column', textColumn)
  formData.append('num_topics', numTopics.toString())
  const response = await api.post('/process-gsdmm/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}
