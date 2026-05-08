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
  { key: 'frequency', label: 'Frequency', sortable: true, align: 'right' as const },
  { key: 'df', label: 'DF', sortable: true, align: 'right' as const },
  { key: 'tf_idf', label: 'TF IDF', sortable: true, align: 'right' as const },
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
    <!-- Configuration Panel -->
    <div class="card float-up border border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
      <div class="flex items-center gap-2 mb-4">
        <svg class="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 1 1 0-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 0 1-1.44-4.282m3.102.069a18.03 18.03 0 0 1-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 0 1 8.835 2.535M10.34 6.66a23.847 23.847 0 0 0 8.835-2.535m0 0A23.74 23.74 0 0 0 18.795 3m.38 1.125a23.91 23.91 0 0 1 1.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 0 0 1.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 0 1 0 3.46" />
        </svg>
        <h3 class="text-sm font-bold text-text uppercase tracking-wider">Preprocessing Settings</h3>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-text-muted uppercase">Text Column (Raw)</label>
          <input v-model="store.analysisConfig.text_column" type="text" class="w-full bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 outline-none" />
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-text-muted uppercase">Cleaned Text Column</label>
          <input v-model="store.analysisConfig.cleaned_text_column" type="text" class="w-full bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 outline-none" />
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-text-muted uppercase">Time Column</label>
          <input v-model="store.analysisConfig.time_column" type="text" class="w-full bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 outline-none" />
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-text-muted uppercase">Handle Column</label>
          <input v-model="store.analysisConfig.handle_column" type="text" class="w-full bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 outline-none" />
        </div>
      </div>

      <!-- Dataset Preview -->
      <div class="mt-6 border-t border-border/50 pt-4" v-if="store.datasetMeta?.available_columns?.length">
        <h4 class="text-xs font-bold text-text-muted uppercase tracking-wider mb-3">Dataset Preview (Top 5 rows)</h4>
        <div class="overflow-x-auto rounded-lg border border-border">
          <table class="w-full text-xs text-left">
            <thead class="bg-surface-alt border-b border-border">
              <tr>
                <th v-for="col in store.datasetMeta.available_columns" :key="col" class="px-3 py-2 font-semibold text-text-muted whitespace-nowrap">
                  {{ col }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border/50 bg-white/50">
              <tr v-for="(row, i) in store.datasetMeta.preview_data" :key="i" class="hover:bg-surface-alt/50 transition-colors">
                <td v-for="col in store.datasetMeta.available_columns" :key="col" class="px-3 py-2 whitespace-nowrap max-w-[200px] truncate" :title="String(row[col])">
                  {{ row[col] }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="mt-4 flex justify-end">
        <button class="btn-primary glow-pulse" :disabled="store.isLoading" @click="store.runPreprocessing()">
          Run Preprocessing
        </button>
      </div>
    </div>

    <div v-if="store.ngrams.count > 0" class="flex flex-col gap-6 float-up" style="animation-delay: 0.1s;">
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
              <div class="text-[10px] text-text-muted leading-tight space-y-1 mt-1">
                <p><strong>N:</strong> Total number of tweets</p>
                <p><strong>DF:</strong> Document Frequency (number of tweets containing the term)</p>
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
        <template #cell-df="{ value }">
          <span class="text-xs text-text-muted tabular-nums">{{ value }}</span>
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
  </div>
</template>
