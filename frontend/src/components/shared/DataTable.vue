<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  columns: { key: string; label: string; sortable?: boolean; align?: 'left' | 'center' | 'right'; width?: string }[]
  rows: Record<string, any>[]
  totalCount: number
  currentPage: number
  totalPages: number
  isLoading?: boolean
  emptyMessage?: string
  title?: string
}>()

const emit = defineEmits<{
  'page-change': [page: number]
}>()

const sortKey = ref<string | null>(null)
const sortDir = ref<'asc' | 'desc'>('asc')

function toggleSort(key: string) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}

const sortedRows = computed(() => {
  if (!sortKey.value) return props.rows
  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  return [...props.rows].sort((a, b) => {
    const va = a[key]
    const vb = b[key]
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir
    return String(va).localeCompare(String(vb)) * dir
  })
})

const pageRange = computed(() => {
  const total = props.totalPages
  const current = props.currentPage
  const delta = 2
  const range: number[] = []
  for (let i = Math.max(1, current - delta); i <= Math.min(total, current + delta); i++) {
    range.push(i)
  }
  return range
})

const showStart = computed(() => (props.currentPage - 1) * 20 + 1)
const showEnd = computed(() => Math.min(props.currentPage * 20, props.totalCount))
</script>

<template>
  <div class="card overflow-hidden !p-0">
    <!-- Header -->
    <div v-if="title" class="px-5 pt-5 pb-3 flex items-center justify-between">
      <h3 class="text-sm font-bold text-text uppercase tracking-wider">{{ title }}</h3>
      <span class="text-xs text-text-muted font-mono">{{ totalCount.toLocaleString() }} records</span>
    </div>

    <!-- Table -->
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-y border-border bg-surface-alt/50">
            <th
              v-for="col in columns"
              :key="col.key"
              class="px-4 py-3 font-semibold text-xs uppercase tracking-wider text-text-muted whitespace-nowrap select-none"
              :class="{
                'text-left': col.align !== 'center' && col.align !== 'right',
                'text-center': col.align === 'center',
                'text-right': col.align === 'right',
                'cursor-pointer hover:text-text': col.sortable,
              }"
              :style="col.width ? { width: col.width } : {}"
              @click="col.sortable && toggleSort(col.key)"
            >
              <div class="inline-flex items-center gap-1">
                {{ col.label }}
                <template v-if="col.sortable && sortKey === col.key">
                  <svg v-if="sortDir === 'asc'" class="w-3 h-3 text-primary" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
                  </svg>
                  <svg v-else class="w-3 h-3 text-primary" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </template>
              </div>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border/50">
          <!-- Loading skeleton -->
          <template v-if="isLoading">
            <tr v-for="i in 5" :key="'skel-' + i">
              <td v-for="col in columns" :key="col.key" class="px-4 py-3">
                <div class="skeleton h-4 w-full max-w-[120px]" />
              </td>
            </tr>
          </template>

          <!-- Data rows -->
          <template v-else-if="sortedRows.length > 0">
            <tr
              v-for="(row, idx) in sortedRows"
              :key="idx"
              class="hover:bg-primary/3 transition-colors"
            >
              <td
                v-for="col in columns"
                :key="col.key"
                class="px-4 py-3 whitespace-nowrap"
                :class="{
                  'text-left': col.align !== 'center' && col.align !== 'right',
                  'text-center': col.align === 'center',
                  'text-right': col.align === 'right',
                  'font-mono text-xs': typeof row[col.key] === 'number',
                }"
              >
                <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                  {{ row[col.key] }}
                </slot>
              </td>
            </tr>
          </template>

          <!-- Empty state -->
          <tr v-else>
            <td :colspan="columns.length" class="px-4 py-12 text-center text-text-muted">
              <svg class="w-10 h-10 mx-auto mb-3 text-border" fill="none" viewBox="0 0 24 24" stroke-width="1" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
              </svg>
              {{ emptyMessage || 'No data available' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="px-5 py-3 flex items-center justify-between border-t border-border bg-surface-alt/30">
      <p class="text-xs text-text-muted">
        Showing <span class="font-semibold text-text">{{ showStart }}-{{ showEnd }}</span> of <span class="font-semibold text-text">{{ totalCount.toLocaleString() }}</span>
      </p>
      <div class="flex items-center gap-1">
        <button
          class="px-2 py-1 rounded-lg text-xs font-medium text-text-muted hover:bg-surface-alt transition-colors disabled:opacity-30"
          :disabled="currentPage <= 1"
          @click="emit('page-change', currentPage - 1)"
        >
          ‹ Prev
        </button>
        <button
          v-for="p in pageRange"
          :key="p"
          class="w-8 h-8 rounded-lg text-xs font-medium transition-all duration-200"
          :class="p === currentPage ? 'bg-primary text-white shadow-sm' : 'text-text-muted hover:bg-surface-alt'"
          @click="emit('page-change', p)"
        >
          {{ p }}
        </button>
        <button
          class="px-2 py-1 rounded-lg text-xs font-medium text-text-muted hover:bg-surface-alt transition-colors disabled:opacity-30"
          :disabled="currentPage >= totalPages"
          @click="emit('page-change', currentPage + 1)"
        >
          Next ›
        </button>
      </div>
    </div>
  </div>
</template>
