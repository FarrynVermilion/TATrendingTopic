<script setup lang="ts">
import { useAnalysisStore } from '@/stores/analysisStore'
import StatusBadge from '@/components/shared/StatusBadge.vue'

const store = useAnalysisStore()
</script>

<template>
  <div class="space-y-8">
    <div class="float-up">
      <div class="flex items-center gap-3 mb-2">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0 1 18 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3 1.5 1.5 3-3.75" />
          </svg>
        </div>
        <div>
          <h2 class="text-2xl font-bold text-text">Executive Summary</h2>
          <p class="text-sm text-text-muted">Validated trending topics with dual-algorithm classification</p>
        </div>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 float-up">
      <div class="card !p-4 text-center">
        <p class="stat-value gradient-text">{{ store.trendResults.length }}</p>
        <p class="text-xs text-text-muted mt-1">Total Trends</p>
      </div>
      <div class="card !p-4 text-center">
        <p class="stat-value text-success">{{ store.trendResults.filter(t => t.status === 'organic').length }}</p>
        <p class="text-xs text-text-muted mt-1">🟢 Organic</p>
      </div>
      <div class="card !p-4 text-center">
        <p class="stat-value text-danger">{{ store.trendResults.filter(t => t.status === 'anomalous').length }}</p>
        <p class="text-xs text-text-muted mt-1">🔴 Anomalous</p>
      </div>
      <div class="card !p-4 text-center">
        <p class="stat-value text-warning">{{ store.trendResults.filter(t => t.status === 'suspicious').length }}</p>
        <p class="text-xs text-text-muted mt-1">🟡 Suspicious</p>
      </div>
    </div>

    <!-- Results Table -->
    <div class="card float-up !p-0 overflow-hidden" style="animation-delay: 0.15s;">
      <div class="px-5 pt-5 pb-3">
        <h3 class="text-sm font-bold text-text uppercase tracking-wider">Trending Topic Classification</h3>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-y border-border bg-surface-alt/50">
              <th class="px-4 py-2 text-center text-xs font-semibold text-text-muted uppercase w-12">#</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-text-muted uppercase">Term</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-text-muted uppercase">Category</th>
              <th class="px-4 py-2 text-center text-xs font-semibold text-text-muted uppercase">Status</th>
              <th class="px-4 py-2 text-center text-xs font-semibold text-text-muted uppercase">Burst</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-text-muted uppercase">Anomaly</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-text-muted uppercase">Mentions</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-text-muted uppercase">Period</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/50">
            <tr v-for="t in store.trendResults" :key="t.rank" class="hover:bg-primary/3 transition-colors">
              <td class="px-4 py-3 text-center font-bold text-text-muted">{{ t.rank }}</td>
              <td class="px-4 py-3 font-semibold text-text">{{ t.term }}</td>
              <td class="px-4 py-3 text-xs text-text-muted">{{ t.category }}</td>
              <td class="px-4 py-3 text-center">
                <StatusBadge :status="t.status" size="sm" />
              </td>
              <td class="px-4 py-3 text-center">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold"
                  :class="t.burst_level >= 2 ? 'bg-danger/10 text-danger' : 'bg-warning/10 text-warning'">
                  L{{ t.burst_level }}
                </span>
              </td>
              <td class="px-4 py-3 text-right font-mono text-xs">{{ (t.anomaly_score * 100).toFixed(1) }}%</td>
              <td class="px-4 py-3 text-right font-mono text-xs">{{ t.mention_count.toLocaleString() }}</td>
              <td class="px-4 py-3 font-mono text-[11px] text-text-muted whitespace-nowrap">
                {{ t.burst_start }} → {{ t.burst_end }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Reset Button -->
    <div class="flex justify-center pt-4 float-up" style="animation-delay: 0.3s;">
      <button class="btn-secondary" @click="store.resetPipeline()">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
        </svg>
        Run New Analysis
      </button>
    </div>
  </div>
</template>
