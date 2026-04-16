<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  headers: string[]
  filename?: string
}>()

const emit = defineEmits<{
  (e: 'column-selected', payload: { column: string; numTopics: number }): void
  (e: 'back'): void
}>()

const selected = ref(props.headers[0] || '')
const numTopics = ref(15)

const proceed = () => {
  if (selected.value) {
    emit('column-selected', {
      column: selected.value,
      numTopics: numTopics.value
    })
  }
}
</script>

<template>
  <div class="flex flex-col items-center p-8 animate-in fade-in zoom-in duration-300">
    
    <div class="mb-8 text-center">
      <div class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-700 rounded-full text-sm font-medium mb-6">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
        </svg>
        {{ filename }}
      </div>
      <h2 class="text-2xl font-bold text-slate-800">Configure Analysis</h2>
      <p class="text-slate-500 mt-2">Select a text column and set topic parameters.</p>
    </div>

    <div class="w-full max-w-md space-y-6">
      
      <!-- Text Column Selector -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">Text Column</label>
        <div class="relative">
          <select 
            v-model="selected"
            class="block w-full pl-4 pr-10 py-3 text-base border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-xl appearance-none bg-white shadow-sm transition-shadow hover:shadow-md"
          >
            <option disabled value="">Please select one</option>
            <option v-for="header in headers" :key="header" :value="header">
              {{ header }}
            </option>
          </select>
          <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-slate-500">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
            </svg>
          </div>
        </div>
      </div>

      <!-- Number of Topics Input -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">Number of Topics (K)</label>
        <div class="flex items-center gap-4">
          <input 
            v-model.number="numTopics"
            type="number"
            min="2"
            max="50"
            class="block w-full pl-4 pr-4 py-3 text-base border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-xl bg-white shadow-sm transition-shadow hover:shadow-md"
          />
        </div>
        <p class="mt-1.5 text-xs text-slate-400">
          Maximum number of topics to discover (2–50). The algorithm may find fewer if clusters are empty.
        </p>
      </div>

      <div class="flex gap-4 w-full pt-4">
        <button 
          @click="emit('back')"
          class="flex-1 px-4 py-3 border border-slate-300 shadow-sm text-sm font-medium rounded-xl text-slate-700 bg-white hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
        >
          Cancel
        </button>
        <button 
          @click="proceed"
          :disabled="!selected"
          class="flex-1 px-4 py-3 border border-transparent shadow-sm text-sm font-medium rounded-xl text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:-translate-y-0.5"
        >
          Run Topic Modeling
        </button>
      </div>
      
    </div>
  </div>
</template>
