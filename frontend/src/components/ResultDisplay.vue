<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  results: any
}>()

const emit = defineEmits<{
  (e: 'reset'): void
}>()

const activeTab = ref('words') // 'words' | 'sentences'
</script>

<template>
  <div class="animate-in fade-in slide-in-from-bottom-4 duration-500">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-slate-800">Analysis Results</h2>
      <button 
        @click="emit('reset')"
        class="text-sm px-4 py-2 text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg font-medium transition-colors"
      >
        Start New Analysis
      </button>
    </div>

    <!-- Tabs -->
    <div class="flex space-x-1 p-1 bg-slate-100/50 rounded-xl mb-6 shadow-inner">
      <button 
        @click="activeTab = 'words'"
        :class="activeTab === 'words' ? 'bg-white shadow text-indigo-700' : 'text-slate-500 hover:text-slate-700'"
        class="flex-1 py-2.5 text-sm font-medium rounded-lg transition-all"
      >
        Word Weights (Top 20)
      </button>
      <button 
        @click="activeTab = 'sentences'"
        :class="activeTab === 'sentences' ? 'bg-white shadow text-indigo-700' : 'text-slate-500 hover:text-slate-700'"
        class="flex-1 py-2.5 text-sm font-medium rounded-lg transition-all"
      >
        Sentence Weights (Top 20)
      </button>
    </div>

    <!-- Actions (Downloads) -->
    <div class="flex justify-end gap-3 mb-4">
      <a 
        v-if="results.word_weights_url && activeTab === 'words'" 
        :href="results.word_weights_url" 
        download 
        class="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg text-sm font-medium transition-colors border border-emerald-200"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
        </svg>
        Download CSV
      </a>
      <a 
        v-if="results.sentence_weights_url && activeTab === 'sentences'" 
        :href="results.sentence_weights_url" 
        download 
        class="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg text-sm font-medium transition-colors border border-emerald-200"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
        </svg>
        Download CSV
      </a>
    </div>

    <!-- Words Table -->
    <div v-show="activeTab === 'words'" class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm text-left text-slate-500">
          <thead class="text-xs text-slate-700 uppercase bg-slate-50 border-b border-slate-200">
            <tr>
              <th scope="col" class="px-6 py-4">Kata Unik</th>
              <th scope="col" class="px-6 py-4">Total</th>
              <th scope="col" class="px-6 py-4">Jml Tweet</th>
              <th scope="col" class="px-6 py-4">TF</th>
              <th scope="col" class="px-6 py-4">IDF</th>
              <th scope="col" class="px-6 py-4 text-right">Bobot</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="word in results.top_words" :key="word['Kata Unik']" class="bg-white border-b hover:bg-slate-50 transition-colors">
              <td class="px-6 py-4 font-medium text-slate-900 whitespace-nowrap">{{ word['Kata Unik'] }}</td>
              <td class="px-6 py-4">{{ word['Seluruh Kemunculan'] }}</td>
              <td class="px-6 py-4">{{ word['Jml Tweet Mengandung Kata'] }}</td>
              <td class="px-6 py-4">{{ Number(word['Term Frequency (TF)']).toFixed(4) }}</td>
              <td class="px-6 py-4">{{ Number(word['IDF']).toFixed(4) }}</td>
              <td class="px-6 py-4 text-right font-semibold text-indigo-600">{{ Number(word['Bobot Kata']).toFixed(4) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Sentences Table -->
    <div v-show="activeTab === 'sentences'" class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm text-left text-slate-500">
          <thead class="text-xs text-slate-700 uppercase bg-slate-50 border-b border-slate-200">
            <tr>
              <th scope="col" class="px-6 py-4 w-12">No</th>
              <th scope="col" class="px-6 py-4">Kalimat (Preprocessing)</th>
              <th scope="col" class="px-6 py-4 w-24">Panjang</th>
              <th scope="col" class="px-6 py-4 w-24 text-right">Bobot</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sentence in results.top_sentences" :key="sentence['No Urut']" class="bg-white border-b hover:bg-slate-50 transition-colors">
              <td class="px-6 py-4 font-medium text-slate-900">{{ sentence['No Urut'] }}</td>
              <td class="px-6 py-4 italic text-slate-600 max-w-md truncate" :title="sentence['Hasil Kalimat']">{{ sentence['Hasil Kalimat'] }}</td>
              <td class="px-6 py-4">{{ sentence['Panjang Kalimat'] }}</td>
              <td class="px-6 py-4 text-right font-semibold text-indigo-600">{{ Number(sentence['Bobot Kalimat']).toFixed(4) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>
