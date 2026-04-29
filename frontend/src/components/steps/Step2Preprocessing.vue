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
  { key: 'frequency', label: 'Freq', sortable: true, align: 'right' as const },
  { key: 'n', label: 'N', align: 'center' as const },
  { key: 'tf_idf', label: 'TF-IDF', sortable: true, align: 'right' as const },
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
    <div class="float-up">
      <div class="flex items-center gap-3 mb-2">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z" />
          </svg>
        </div>
        <div>
          <h2 class="text-2xl font-bold text-text">Data Pre-processing</h2>
          <p class="text-sm text-text-muted">N-Gram extraction & mention Edge List</p>
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
          <span class="font-mono text-xs">{{ Number(value).toFixed(4) }}</span>
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
