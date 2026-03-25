<script setup lang="ts">
import { ref } from 'vue'
import FileUpload from './components/FileUpload.vue'
import ColumnSelector from './components/ColumnSelector.vue'
import ResultDisplay from './components/ResultDisplay.vue'
import { getCsvHeaders, processTfidf } from './services/api'

// State
const step = ref(1)
const selectedFile = ref<File | null>(null)
const csvHeaders = ref<string[]>([])
const selectedColumn = ref('')
const isLoading = ref(false)
const results = ref<any>(null)
const errorMsg = ref('')

const handleFileSelected = async (file: File) => {
  errorMsg.value = ''
  isLoading.value = true
  selectedFile.value = file
  
  try {
    const data = await getCsvHeaders(file)
    csvHeaders.value = data.headers
    step.value = 2 // Move to column selection
  } catch (err: any) {
    errorMsg.value = err.response?.data?.error || err.message || 'Failed to get CSV headers'
    selectedFile.value = null
  } finally {
    isLoading.value = false
  }
}

const handleColumnSelected = async (column: string) => {
  errorMsg.value = ''
  selectedColumn.value = column
  isLoading.value = true
  
  try {
    const data = await processTfidf(selectedFile.value!, column)
    results.value = data
    step.value = 3 // Move to results
  } catch (err: any) {
    errorMsg.value = err.response?.data?.error || err.message || 'Failed to process TF-IDF'
  } finally {
    isLoading.value = false
  }
}

const resetFlow = () => {
  step.value = 1
  selectedFile.value = null
  csvHeaders.value = []
  selectedColumn.value = ''
  results.value = null
  errorMsg.value = ''
}
</script>

<template>
  <main class="min-h-screen py-10 px-4 sm:px-6 lg:px-8 font-sans">
    <div class="max-w-4xl mx-auto">
      
      <!-- Header -->
      <div class="text-center mb-12">
        <h1 class="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-cyan-500 mb-2">
          TF-IDF Analyzer
        </h1>
        <p class="text-slate-500 text-lg">Upload your dataset to extract key words and calculate sentence weights dynamically.</p>
      </div>

      <!-- Error Alert -->
      <div v-if="errorMsg" class="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 shadow-sm flex items-center justify-between">
        <span>{{ errorMsg }}</span>
        <button @click="errorMsg = ''" class="text-red-500 hover:text-red-800 focus:outline-none">&times;</button>
      </div>

      <!-- Main Content Area -->
      <div class="glass rounded-3xl p-8 relative overflow-hidden">
        
        <!-- Loading Overlay -->
        <div v-if="isLoading" class="absolute inset-0 bg-white/70 backdrop-blur-sm z-10 flex flex-col items-center justify-center">
          <svg class="animate-spin h-10 w-10 text-indigo-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span class="text-indigo-800 font-medium">Processing your data. This might take a moment...</span>
        </div>

        <!-- Step 1: Upload (Transition with fade) -->
        <Transition name="fade" mode="out-in">
          <FileUpload 
            v-if="step === 1" 
            @file-selected="handleFileSelected" 
          />
          
          <!-- Step 2: Configure Column -->
          <ColumnSelector 
            v-else-if="step === 2" 
            :headers="csvHeaders"
            :filename="selectedFile?.name"
            @column-selected="handleColumnSelected"
            @back="step = 1"
          />
          
          <!-- Step 3: Results Display -->
          <ResultDisplay 
            v-else-if="step === 3" 
            :results="results"
            @reset="resetFlow"
          />
        </Transition>

      </div>
    </div>
  </main>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
