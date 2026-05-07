<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import StatCard from '@/components/shared/StatCard.vue'
import LoadingOverlay from '@/components/shared/LoadingOverlay.vue'

const store = useAnalysisStore()

const datasetFile = ref<File | undefined>(undefined)

const config = ref({
  top_n_terms: 50,
  bin_hours: 1,
  kleinberg_s: 2.0,
  kleinberg_gamma: 1.0,
  anomaly_threshold: 0.5,
})

const fileInput = ref<HTMLInputElement | null>(null)

function handleStartPipeline() {
  store.startPipeline(config.value)
}

function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    datasetFile.value = file
  }
}

async function handleUpload() {
  if (datasetFile.value) {
    await store.uploadDatasets(datasetFile.value)
  }
}

function handleChangeDataset() {
  store.datasetMeta = null
  datasetFile.value = undefined
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

onMounted(() => {
  if (!store.datasetMeta) {
    store.fetchDatasetOverview()
  }
})
</script>

<template>
  <div class="space-y-8">
    <!-- Step Header -->
    <div class="float-up">
      <div class="flex items-center gap-3 mb-2">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
          </svg>
        </div>
        <div>
          <h2 class="text-2xl font-bold text-text">Dataset Overview</h2>
          <p class="text-sm text-text-muted">Corpus constraints and initial metadata before analysis</p>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="store.pipelineError" class="card border-l-4 border-l-danger float-up">
      <div class="flex items-center gap-3">
        <svg class="w-5 h-5 text-danger" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
        </svg>
        <p class="text-sm text-danger font-medium">{{ store.pipelineError }}</p>
      </div>
      <button class="btn-secondary mt-3 text-xs" @click="store.fetchDatasetOverview()">Retry</button>
    </div>

    <!-- Loading State -->
    <LoadingOverlay 
      v-else-if="store.isLoading" 
      :message="store.pipelineStatus === 'running' ? 'Running analysis algorithms...' : 'Uploading and preparing dataset...'" 
    />

    <!-- Upload Section -->
    <div v-else-if="!store.datasetMeta" class="float-up space-y-6">
      <div class="card bg-gradient-to-br from-primary/5 to-accent/5 border-primary/20">
        <h3 class="text-lg font-bold text-text mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75v-2.25m-18 0A2.25 2.25 0 0 1 5.25 15h13.5A2.25 2.25 0 0 1 21 16.5m-18 0V6a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 6v10.5m-18 0h18M9 10.5l3 3m0 0 3-3m-3 3V3.75" />
          </svg>
          Upload New Dataset
        </h3>
        
        <div class="space-y-6">
          <!-- Dataset File -->
          <div class="space-y-2">
            <label class="text-xs font-bold text-text-muted uppercase tracking-wider">Dataset (.csv)</label>
            <div class="relative group">
              <input 
                type="file" 
                accept=".csv" 
                ref="fileInput"
                class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                @change="handleFileUpload"
              />
              <div 
                class="border-2 border-dashed rounded-xl p-8 text-center transition-all bg-surface/50"
                :class="datasetFile ? 'border-success' : 'border-border group-hover:border-primary/50'"
              >
                <div 
                  class="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3 transition-all duration-300"
                  :class="datasetFile ? 'bg-success/20 text-success scale-110' : 'bg-primary/10 text-primary group-hover:scale-110'"
                >
                  <svg v-if="!datasetFile" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                  </svg>
                  <svg v-else class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                </div>
                <div class="text-sm font-medium text-text truncate">
                  {{ datasetFile ? datasetFile.name : 'Select dataset.csv' }}
                </div>
                <div class="text-[10px] text-text-muted mt-2 max-w-xs mx-auto">
                  Must contain: <strong class="text-text">text</strong>, 
                  <strong class="text-text">cleaned_text</strong>, 
                  <strong class="text-text">handle</strong>, and 
                  <strong class="text-text">datetime</strong>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-6 flex justify-center">
          <button 
            class="btn-primary px-8"
            :disabled="!datasetFile || store.isLoading"
            @click="handleUpload"
          >
            Upload & Analyze
          </button>
        </div>
      </div>
    </div>

    <!-- Active Dataset View -->
    <div v-else class="space-y-8">
      <!-- Dataset Overview (if exists) -->
      <div class="flex justify-between items-center float-up">
        <h3 class="text-sm font-bold text-text uppercase tracking-wider">Active Dataset Statistics</h3>
        <button class="text-xs text-primary hover:underline font-medium" @click="handleChangeDataset">
          Change Dataset
        </button>
      </div>

      <!-- KPI Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Total Tweets"
          :value="store.datasetMeta.total_tweets"
          subtitle="Scraped corpus size"
          icon="document"
          color="primary"
        />
        <StatCard
          label="Peak Rate"
          :value="`${store.datasetMeta.rate_limit}/hr`"
          subtitle="Max hourly density"
          icon="clock"
          color="primary"
        />
        <StatCard
          label="Unique Users"
          :value="store.datasetMeta.unique_users"
          subtitle="Distinct authors"
          icon="users"
          color="accent"
        />
        <StatCard
          label="Avg Tweets/Hour"
          :value="store.datasetMeta.avg_tweets_per_hour"
          subtitle="Collection throughput"
          icon="bolt"
          color="success"
        />
      </div>

      <!-- Dataset Info Card -->
      <div class="card float-up" style="animation-delay: 0.1s;">
        <h3 class="text-sm font-bold text-text uppercase tracking-wider mb-4">Collection Parameters</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Date Range -->
          <div class="space-y-3">
            <div class="flex items-center gap-2 text-xs font-semibold text-text-muted uppercase tracking-wider">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
              </svg>
              Date Range
            </div>
            <div class="flex items-center gap-3">
              <span class="px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-sm font-mono font-semibold">
                {{ store.datasetMeta.date_range.start }}
              </span>
              <svg class="w-4 h-4 text-text-muted shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
              <span class="px-3 py-1.5 rounded-lg bg-accent/10 text-accent text-sm font-mono font-semibold">
                {{ store.datasetMeta.date_range.end }}
              </span>
            </div>
          </div>

          <!-- Keyword Distribution -->
          <div class="space-y-3">
            <div class="flex items-center gap-2 text-xs font-semibold text-text-muted uppercase tracking-wider">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 8.25h15m-16.5 7.5h15m-1.8-13.5-3.9 19.5m-2.1-19.5-3.9 19.5" />
              </svg>
              Keyword Distribution
            </div>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="(count, keyword) in store.datasetMeta.keyword_distribution"
                :key="String(keyword)"
                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-alt border border-border text-xs font-medium"
              >
                <span class="text-text">{{ keyword }}</span>
                <span class="font-mono text-text-muted text-[10px] bg-border/50 rounded px-1.5 py-0.5">{{ count }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Pipeline Configuration Panel -->
      <div class="card float-up" style="animation-delay: 0.2s;">
        <div class="flex items-center gap-2 mb-4">
          <svg class="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12a7.5 7.5 0 0 0 15 0m-15 0a7.5 7.5 0 1 1 15 0m-15 0H3m16.5 0H21m-1.5 0H12m-8.457 3.077 1.41-.513m14.095-5.128 1.41-.513M5.106 17.785l1.15-.964m11.49-9.642 1.149-.964M7.501 19.795l.75-1.3m7.5-12.99.75-1.3m2.786 14.128-1.41-.514M5.106 6.215l1.15.964m11.49 9.642 1.149.964M10.501 19.795l-.75-1.3m7.5-12.99-.75-1.3" />
          </svg>
          <h3 class="text-sm font-bold text-text uppercase tracking-wider">Pipeline Configuration</h3>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <!-- Top N Terms -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-bold text-text-muted uppercase">Top N Terms</label>
            <input
              v-model.number="config.top_n_terms"
              type="number"
              min="5"
              max="200"
              class="w-full bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-primary/20 outline-none transition-all"
            />
          </div>

          <!-- Bin Hours -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-bold text-text-muted uppercase">Bin Hours</label>
            <input
              v-model.number="config.bin_hours"
              type="number"
              min="1"
              max="24"
              class="w-full bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-primary/20 outline-none transition-all"
            />
          </div>

          <!-- Kleinberg S -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-bold text-text-muted uppercase">Kleinberg S</label>
            <input
              v-model.number="config.kleinberg_s"
              type="number"
              step="0.1"
              min="1.1"
              class="w-full bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-primary/20 outline-none transition-all"
            />
          </div>

          <!-- Kleinberg Gamma -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-bold text-text-muted uppercase">Gamma</label>
            <input
              v-model.number="config.kleinberg_gamma"
              type="number"
              step="0.1"
              min="0.1"
              class="w-full bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-primary/20 outline-none transition-all"
            />
          </div>

          <!-- Anomaly Threshold -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-bold text-text-muted uppercase">Threshold θ</label>
            <input
              v-model.number="config.anomaly_threshold"
              type="number"
              step="0.05"
              min="0.1"
              max="0.9"
              class="w-full bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-primary/20 outline-none transition-all"
            />
          </div>
        </div>
      </div>

      <!-- Methodology Note -->
      <div class="card float-up border-l-4 border-l-primary" style="animation-delay: 0.3s;">
        <div class="flex gap-3">
          <svg class="w-5 h-5 text-primary shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
          </svg>
          <div>
            <h4 class="text-sm font-bold text-text mb-1">Methodology</h4>
            <p class="text-sm text-text-muted leading-relaxed">
              This pipeline applies a <strong class="text-text">Modified Term-Level Burst Kleinberg</strong> algorithm 
              to detect temporal bursts in term frequencies, followed by <strong class="text-text">Mention-Based Link Anomaly Detection</strong> 
              to validate trends against network manipulation (bot networks, astroturfing). The combination produces 
              a dual-validated trending topic classification.
            </p>
          </div>
        </div>
      </div>

      <!-- Start Button -->
      <div class="flex justify-end">
        <button
          id="btn-start-pipeline"
          class="btn-primary text-base glow-pulse"
          :disabled="store.isLoading"
          @click="handleStartPipeline"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
          </svg>
          Start Analysis Pipeline
        </button>
      </div>
    </div>
  </div>
</template>
