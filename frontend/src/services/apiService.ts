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

const httpClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  headers: {
    'X-Api-Key': import.meta.env.VITE_API_KEY || 'default_secret_key',
  },
})

// ─── Step 1: Dataset Overview ───────────────────────────────────────────────

export async function getDatasetOverview(): Promise<DatasetMeta> {
  const { data } = await httpClient.get<DatasetMeta>('/dataset/overview/')
  return data
}

export async function uploadDatasets(file: File): Promise<{ message: string; overview: DatasetMeta }> {
  const formData = new FormData()
  formData.append('file', file)

  // Use a fresh call to ensure no global headers interfere with the boundary
  const { data } = await axios.post(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/dataset/upload/`, formData, {
    headers: {
      'X-Api-Key': import.meta.env.VITE_API_KEY || 'my_super_secret_api_key_123',
      'Content-Type': 'multipart/form-data' 
    },
    transformRequest: (data, headers) => {
      if (headers) delete headers['Content-Type']
      return data
    }
  })
  return data
}

export async function startPipeline(config: any = {}): Promise<{ pipeline_id: string; status: string }> {
  const { data } = await httpClient.post('/pipeline/start/', config)
  return data
}

export async function getPipelineStatus(): Promise<{ status: string; pipeline_id: string }> {
  const { data } = await httpClient.get('/pipeline/status/')
  return data
}

// ─── Step 2: Preprocessing ──────────────────────────────────────────────────

export async function getNgrams(page: number = 1): Promise<PaginatedResponse<NGram>> {
  const { data } = await httpClient.get<PaginatedResponse<NGram>>('/preprocessing/ngrams/', {
    params: { page },
  })
  return data
}

export async function getEdges(page: number = 1): Promise<PaginatedResponse<Edge>> {
  const { data } = await httpClient.get<PaginatedResponse<Edge>>('/preprocessing/edges/', {
    params: { page },
  })
  return data
}

// ─── Step 3: Burst Kleinberg ────────────────────────────────────────────────

export async function getBurstAnalysis(term?: string): Promise<BurstAnalysis> {
  const { data } = await httpClient.get<BurstAnalysis>('/burst/analysis/', {
    params: term ? { term } : {},
  })
  return data
}

// ─── Step 4: Link Anomaly ───────────────────────────────────────────────────

export async function getNetworkData(): Promise<NetworkData> {
  const { data } = await httpClient.get<NetworkData>('/link-anomaly/network/')
  return data
}

// ─── Step 5: Executive Summary ──────────────────────────────────────────────

export async function getTrendSummary(): Promise<{ trends: TrendResult[] }> {
  const { data } = await httpClient.get<{ trends: TrendResult[] }>('/summary/trends/')
  return data
}

// ─── Legacy Support ────────────────────────────────────────────────────────

export async function getCsvHeaders(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await httpClient.post('/get-headers/', formData)
  return response.data
}

export async function processGsdmm(file: File, textColumn: string, numTopics: number = 15) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('text_column', textColumn)
  formData.append('num_topics', numTopics.toString())
  const response = await httpClient.post('/process-gsdmm/', formData)
  return response.data
}
