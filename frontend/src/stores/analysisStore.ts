import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  DatasetMeta,
  NGram,
  Edge,
  PaginatedResponse,
  BurstAnalysis,
  NetworkData,
  TrendResult,
  PipelineStatus,
  StepId,
  StepDefinition,
  AnalysisConfig,
} from '@/types/analysis'
import * as apiService from '@/services/apiService'

export const useAnalysisStore = defineStore('analysis', () => {
  // ─── Pipeline Control ───────────────────────────────────────────────

  const currentStep = ref<StepId>(1)
  const pipelineStatus = ref<PipelineStatus>('idle')
  const pipelineError = ref<string | null>(null)
  const isLoading = ref(false)

  // ─── Step 1: Dataset Overview ─────────────────────────────────────

  const datasetMeta = ref<DatasetMeta | null>(null)

  // ─── Step 2: Preprocessing ────────────────────────────────────────

  const ngrams = ref<PaginatedResponse<NGram>>({
    results: [], count: 0, next: null, previous: null,
  })
  const edgeList = ref<PaginatedResponse<Edge>>({
    results: [], count: 0, next: null, previous: null,
  })

  // ─── Step 3: Burst Kleinberg ──────────────────────────────────────

  const burstAnalysis = ref<BurstAnalysis>({
    term_frequencies: [],
    burst_periods: [],
    available_terms: [],
  })
  const selectedBurstTerm = ref<string | null>(null)

  // ─── Step 4: Link Anomaly ─────────────────────────────────────────

  const networkData = ref<NetworkData>({
    nodes: [], edges: [], anomalies: [],
  })

  // ─── Global Configuration ─────────────────────────────────────────

  const analysisConfig = ref<AnalysisConfig>({
    kleinberg_s: 2.0,
    kleinberg_gamma: 1.0,
    anomaly_threshold: 0.8,
    min_ngram_freq: 5,
  })

  // ─── Step 5: Summary ──────────────────────────────────────────────

  const trendResults = ref<TrendResult[]>([])

  // ─── Step Definitions ─────────────────────────────────────────────

  const steps = computed<StepDefinition[]>(() => [
    {
      id: 1, title: 'Dataset Overview', subtitle: 'Corpus constraints & metadata',
      icon: 'database', isCompleted: currentStep.value > 1,
      isActive: currentStep.value === 1, isLocked: false,
    },
    {
      id: 2, title: 'Pre-processing', subtitle: 'N-Gram extraction & Edge List',
      icon: 'funnel', isCompleted: currentStep.value > 2,
      isActive: currentStep.value === 2, isLocked: currentStep.value < 2,
    },
    {
      id: 3, title: 'Burst Detection', subtitle: 'Modified Kleinberg analysis',
      icon: 'chart-bar', isCompleted: currentStep.value > 3,
      isActive: currentStep.value === 3, isLocked: currentStep.value < 3,
    },
    {
      id: 4, title: 'Link Anomaly', subtitle: 'Mention-based network analysis',
      icon: 'globe-alt', isCompleted: currentStep.value > 4,
      isActive: currentStep.value === 4, isLocked: currentStep.value < 4,
    },
    {
      id: 5, title: 'Executive Summary', subtitle: 'Validated trending topics',
      icon: 'clipboard-document-check', isCompleted: false,
      isActive: currentStep.value === 5, isLocked: currentStep.value < 5,
    },
  ])

  const canGoNext = computed(() => currentStep.value < 5 && !isLoading.value)
  const canGoPrev = computed(() => currentStep.value > 1 && !isLoading.value)

  // ─── Actions ──────────────────────────────────────────────────────

  async function fetchDatasetOverview() {
    isLoading.value = true
    pipelineError.value = null
    try {
      const { overview } = await apiService.getDatasetOverview()
      datasetMeta.value = overview
    } catch (err: any) {
      // If no dataset is loaded (404), we don't treat it as an error
      // so that the UI can show the Upload panel.
      if (err.response?.status === 404) {
        datasetMeta.value = null
      } else {
        pipelineError.value = err.response?.data?.error || err.message
      }
    } finally {
      isLoading.value = false
    }
  }

  async function uploadDatasets(file: File) {
    isLoading.value = true
    pipelineError.value = null
    try {
      const { overview } = await apiService.uploadDatasets(file)
      datasetMeta.value = overview
    } catch (err: any) {
      pipelineError.value = err.response?.data?.error || err.message
    } finally {
      isLoading.value = false
    }
  }

  async function startPipeline(config: any = {}) {
    isLoading.value = true
    pipelineStatus.value = 'running'
    pipelineError.value = null
    try {
      console.log('--- ANALYSIS PIPELINE v2.0 ---')
      console.log('Starting pipeline...', { apiService })
      if (typeof apiService.getPipelineStatus !== 'function') {
        throw new Error('Critical: apiService.getPipelineStatus is not a function! Check imports.')
      }
      await apiService.startPipeline(config)
      
      // Poll for completion
      let finished = false
      while (!finished) {
        try {
          const { status } = await apiService.getPipelineStatus()
          console.log('Poll status:', status)
          pipelineStatus.value = status as PipelineStatus
          
          if (status === 'completed') {
            finished = true
          } else if (status === 'error') {
            throw new Error('Pipeline failed on server')
          } else {
            await new Promise(resolve => setTimeout(resolve, 2000))
          }
        } catch (pollErr: any) {
          console.error('POLLING ERROR:', pollErr)
          pipelineError.value = pollErr.message
          pipelineStatus.value = 'error'
          throw pollErr
        }
      }

      currentStep.value = 2
      // Automatically fetch step 2 data
      await Promise.all([
        fetchNgrams(1),
        fetchEdges(1),
      ])
    } catch (err: any) {
      pipelineStatus.value = 'error'
      pipelineError.value = err.response?.data?.error || err.message
    } finally {
      isLoading.value = false
    }
  }

  async function fetchNgrams(page: number = 1) {
    try {
      const data = await apiService.getNgrams(page)
      ngrams.value = data
    } catch (err: any) {
      pipelineError.value = err.response?.data?.error || err.message
    }
  }

  async function fetchEdges(page: number = 1) {
    try {
      const data = await apiService.getEdges(page)
      edgeList.value = data
    } catch (err: any) {
      pipelineError.value = err.response?.data?.error || err.message
    }
  }

  async function fetchBurstAnalysis(term?: string) {
    isLoading.value = true
    pipelineError.value = null
    try {
      const data = await apiService.getBurstAnalysis(term)
      burstAnalysis.value = data
      if (term) selectedBurstTerm.value = term
      else if (data.available_terms.length > 0) {
        selectedBurstTerm.value = data.available_terms[0]
      }
    } catch (err: any) {
      pipelineError.value = err.response?.data?.error || err.message
    } finally {
      isLoading.value = false
    }
  }

  async function fetchNetworkData() {
    isLoading.value = true
    pipelineError.value = null
    try {
      const data = await apiService.getNetworkData()
      networkData.value = data
    } catch (err: any) {
      pipelineError.value = err.response?.data?.error || err.message
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTrendSummary() {
    isLoading.value = true
    pipelineError.value = null
    try {
      const { trends } = await apiService.getTrendSummary()
      trendResults.value = trends
      pipelineStatus.value = 'completed'
    } catch (err: any) {
      pipelineError.value = err.response?.data?.error || err.message
    } finally {
      isLoading.value = false
    }
  }

  function goToStep(step: StepId) {
    if (step <= currentStep.value || step === currentStep.value + 1) {
      currentStep.value = step
    }
  }

  function nextStep() {
    if (canGoNext.value) currentStep.value = (currentStep.value + 1) as StepId
  }

  function prevStep() {
    if (canGoPrev.value) currentStep.value = (currentStep.value - 1) as StepId
  }

  function resetPipeline() {
    currentStep.value = 1
    pipelineStatus.value = 'idle'
    pipelineError.value = null
    isLoading.value = false
    datasetMeta.value = null
    ngrams.value = { results: [], count: 0, next: null, previous: null }
    edgeList.value = { results: [], count: 0, next: null, previous: null }
    burstAnalysis.value = { term_frequencies: [], burst_periods: [], available_terms: [] }
    selectedBurstTerm.value = null
    networkData.value = { nodes: [], edges: [], anomalies: [] }
    trendResults.value = []
  }

  return {
    // State
    currentStep,
    pipelineStatus,
    pipelineError,
    isLoading,
    datasetMeta,
    ngrams,
    edgeList,
    burstAnalysis,
    selectedBurstTerm,
    networkData,
    trendResults,
    analysisConfig,
    steps,
    canGoNext,
    canGoPrev,

    // Actions
    fetchDatasetOverview,
    uploadDatasets,
    startPipeline,
    fetchNgrams,
    fetchEdges,
    fetchBurstAnalysis,
    fetchNetworkData,
    fetchTrendSummary,
    goToStep,
    nextStep,
    prevStep,
    resetPipeline,
  }
})
