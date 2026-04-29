<script setup lang="ts">
import StepperNav from '@/components/layout/StepperNav.vue'
import StepperProgress from '@/components/layout/StepperProgress.vue'
import { useAnalysisStore } from '@/stores/analysisStore'

const store = useAnalysisStore()
</script>

<template>
  <div class="flex min-h-screen">
    <!-- Sidebar: Desktop Stepper Navigation -->
    <aside class="hidden lg:flex flex-col w-72 xl:w-80 glass-dark shrink-0 sticky top-0 h-screen">
      <!-- Brand Header -->
      <div class="p-6 pb-4 border-b border-white/10">
        <div class="flex items-center gap-3 mb-1">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
          </div>
          <div>
            <h1 class="text-base font-bold text-white leading-tight">The Examiner</h1>
            <p class="text-xs text-sidebar-muted">Trending Topic Analyzer</p>
          </div>
        </div>
      </div>

      <!-- Step List -->
      <div class="flex-1 overflow-y-auto py-4">
        <StepperNav />
      </div>

      <!-- Footer -->
      <div class="p-4 border-t border-white/10">
        <div class="flex items-center gap-2 text-xs text-sidebar-muted">
          <div class="w-2 h-2 rounded-full" :class="store.pipelineStatus === 'running' ? 'bg-accent animate-pulse' : store.pipelineStatus === 'completed' ? 'bg-success' : 'bg-sidebar-muted'" />
          <span class="capitalize">{{ store.pipelineStatus }}</span>
        </div>
        <p class="text-[11px] text-sidebar-muted/50 mt-1">Modified Burst Kleinberg × Link Anomaly</p>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 min-w-0">
      <!-- Mobile Header + Progress -->
      <div class="lg:hidden sticky top-0 z-30 bg-surface/80 backdrop-blur-xl border-b border-border">
        <div class="px-4 py-3 flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
          </div>
          <span class="font-bold text-sm gradient-text">The Examiner</span>
        </div>
        <StepperProgress />
      </div>

      <!-- Page Content -->
      <div class="p-6 lg:p-10 max-w-7xl mx-auto">
        <slot />
      </div>
    </main>
  </div>
</template>
