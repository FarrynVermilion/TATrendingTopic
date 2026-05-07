<script setup lang="ts">
import { ref } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import DataTable from '@/components/shared/DataTable.vue'

const store = useAnalysisStore()
const ngramPage = ref(1)
const edgePage = ref(1)

async function onNgramPageChange(page: number) {
  ngramPage.value = page
  await store.fetchNgrams(page)
}

async function onEdgePageChange(page: number) {
  edgePage.value = page
  await store.fetchEdges(page)
}

const ngramCols = [
  { key: 'term', label: 'Term', sortable: true },
  { key: 'frequency', label: 'Count', sortable: true, align: 'right' as const },
  { key: 'tf_idf', label: 'Score', sortable: true, align: 'right' as const },
]

const edgeCols = [
  { key: 'source_user', label: 'Source', sortable: true },
  { key: 'target_mention', label: 'Target', sortable: true },
  { key: 'weight', label: 'Weight', sortable: true, align: 'right' as const },
  { key: 'timestamp', label: 'Time', align: 'right' as const },
]
</script>

<template>
  <div class="space-y-8">
    <div class="flex flex-col gap-6 float-up">
      <!-- Main Stats Card -->
      <div class="card !p-0 overflow-hidden bg-gradient-to-br from-white to-surface-alt border border-border/50">
        <div class="grid grid-cols-1 lg:grid-cols-12">
          <!-- Left: Title Section -->
          <div class="lg:col-span-4 p-6 border-b lg:border-b-0 lg:border-r border-border/50 bg-primary/[0.02]">
            <div class="space-y-1">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z" />
                  </svg>
                </div>
                <h2 class="text-2xl font-bold text-text tracking-tight">Pre-processing Insights</h2>
              </div>
              <p class="text-sm text-text-muted">N-Gram extraction & network synthesis</p>
            </div>
          </div>

          <!-- Middle: Metrics Grid -->
          <div class="lg:col-span-5 p-6 grid grid-cols-3 gap-6 items-center">
            <div class="space-y-1">
              <p class="text-[9px] font-black uppercase tracking-widest text-primary/60 leading-none">Total Tweets</p>
              <p class="text-lg font-bold text-text tabular-nums">{{ store.datasetMeta?.total_tweets?.toLocaleString() || '0' }}</p>
            </div>
            <div class="space-y-1">
              <p class="text-[9px] font-black uppercase tracking-widest text-primary/60 leading-none">Unique Authors</p>
              <p class="text-lg font-bold text-text tabular-nums">{{ store.datasetMeta?.unique_users?.toLocaleString() || '0' }}</p>
            </div>
            <div class="space-y-1">
              <p class="text-[9px] font-black uppercase tracking-widest text-primary/60 leading-none">Total Tokens</p>
              <p class="text-lg font-bold text-text tabular-nums">{{ store.ngrams.total_tokens?.toLocaleString() || '0' }}</p>
            </div>
          </div>

          <!-- Right: Formula Section -->
          <div class="lg:col-span-3 p-6 bg-accent/[0.03] flex items-center border-t lg:border-t-0 lg:border-l border-border/50">
            <div class="space-y-2 w-full">
              <p class="text-[9px] font-black uppercase tracking-widest text-accent leading-none">TF-IDF Methodology</p>
              <div class="font-mono text-[11px] font-bold text-text bg-white/50 p-2 rounded border border-accent/10 text-center">
                Score = <span class="text-text-muted opacity-60">(Count/Tokens)</span> × log₂(N/DF)
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <DataTable
        title="N-Gram Terms"
        :columns="ngramCols"
        :rows="store.ngrams.results"
        :total-count="store.ngrams.count"
        :current-page="ngramPage"
        :total-pages="Math.max(1, Math.ceil(store.ngrams.count / 20))"
        :is-loading="store.isLoading"
        empty-message="No N-Grams extracted yet"
        @page-change="onNgramPageChange"
      >
        <template #cell-term="{ value }">
          <span class="font-mono text-xs font-semibold text-primary">{{ value }}</span>
        </template>
        <template #cell-tf_idf="{ value }">
          <span class="font-mono text-xs font-bold text-accent">{{ Number(value).toFixed(4) }}</span>
        </template>
      </DataTable>

      <DataTable
        title="Edge List (Mentions)"
        :columns="edgeCols"
        :rows="store.edgeList.results"
        :total-count="store.edgeList.count"
        :current-page="edgePage"
        :total-pages="Math.max(1, Math.ceil(store.edgeList.count / 20))"
        :is-loading="store.isLoading"
        empty-message="No edges generated yet"
        @page-change="onEdgePageChange"
      >
        <template #cell-source_user="{ value }">
          <span class="text-xs font-semibold">@{{ value }}</span>
        </template>
        <template #cell-target_mention="{ value }">
          <span class="text-xs text-accent font-semibold">@{{ value }}</span>
        </template>
      </DataTable>
    </div>
  </div>
</template>
