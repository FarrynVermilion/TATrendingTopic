<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  (e: 'file-selected', file: File): void
}>()

const isDragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const handleFile = (file: File) => {
  if (file && file.name.endsWith('.csv')) {
    emit('file-selected', file)
  } else {
    alert('Please upload a valid CSV file.')
  }
}

const onDrop = (e: DragEvent) => {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) handleFile(file)
}

const onFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    handleFile(target.files[0])
  }
}

const triggerFileInput = () => {
  fileInput.value?.click()
}
</script>

<template>
  <div class="flex flex-col items-center justify-center p-8">
    <div 
      class="w-full max-w-xl p-12 mt-4 border-2 border-dashed rounded-3xl transition-all duration-300 flex flex-col items-center justify-center cursor-pointer group"
      :class="isDragging ? 'border-indigo-500 bg-indigo-50 shadow-inner' : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50'"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="triggerFileInput"
    >
      <input 
        type="file" 
        accept=".csv" 
        class="hidden" 
        ref="fileInput"
        @change="onFileChange"
      />
      
      <div class="p-4 bg-white rounded-full shadow-sm text-indigo-500 group-hover:scale-110 transition-transform duration-300 mb-6">
        <svg class="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
        </svg>
      </div>

      <h3 class="text-xl font-bold text-slate-700 mb-2">Upload your CSV</h3>
      <p class="text-slate-500 text-center text-sm px-4">
        Drag and drop your file here, or click to browse. Only .csv files are supported.
      </p>
    </div>
  </div>
</template>
