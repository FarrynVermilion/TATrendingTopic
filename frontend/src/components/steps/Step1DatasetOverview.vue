<script setup lang="ts">
import { onMounted } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import StatCard from '@/components/shared/StatCard.vue'
import LoadingOverlay from '@/components/shared/LoadingOverlay.vue'

const store = useAnalysisStore()

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

    <!-- Loading State -->
    <LoadingOverlay v-if="store.isLoading" message="Loading dataset metadata..." />

    <template v-else-if="store.datasetMeta">
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
          label="Rate Limit"
          :value="`${store.datasetMeta.rate_limit}/hr`"
          subtitle="Fixed API constraint"
          icon="clock"
          color="warning"
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
      <div class="card float-up" style="animation-delay: 0.15s;">
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
          @click="store.startPipeline()"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
          </svg>
          Start Analysis Pipeline
        </button>
      </div>
    </template>

    <!-- Error State -->
    <div v-else-if="store.pipelineError" class="card border-l-4 border-l-danger">
      <p class="text-sm text-danger font-medium">{{ store.pipelineError }}</p>
      <button class="btn-secondary mt-3 text-xs" @click="store.fetchDatasetOverview()">Retry</button>
    </div>
  </div>
</template>
