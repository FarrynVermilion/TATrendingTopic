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

      <!-- Footer: Pipeline Status -->
      <div class="p-6 border-t border-white/10 bg-black/20">
        <div class="flex items-center justify-between mb-3">
          <span class="text-[10px] font-bold uppercase tracking-widest text-white/90">System Status</span>
          <div v-if="store.pipelineStatus === 'running'" class="flex gap-1">
            <span class="w-1 h-3 bg-accent animate-[bounce_1s_infinite_0ms] rounded-full shadow-[0_0_8px_var(--color-accent)]"></span>
            <span class="w-1 h-3 bg-accent animate-[bounce_1s_infinite_200ms] rounded-full shadow-[0_0_8px_var(--color-accent)]"></span>
            <span class="w-1 h-3 bg-accent animate-[bounce_1s_infinite_400ms] rounded-full shadow-[0_0_8px_var(--color-accent)]"></span>
          </div>
        </div>
        
        <div 
          class="flex items-center gap-3 p-3 rounded-xl transition-all duration-500"
          :class="[
            store.pipelineStatus === 'running' ? 'bg-accent/20 border border-accent/40' : 
            store.pipelineStatus === 'completed' ? 'bg-success/20 border border-success/40' : 
            'bg-white/5 border border-white/20'
          ]"
        >
          <div 
            class="w-3 h-3 rounded-full shadow-[0_0_12px_rgba(0,0,0,0.5)]" 
            :class="[
              store.pipelineStatus === 'running' ? 'bg-accent animate-pulse shadow-accent/60' : 
              store.pipelineStatus === 'completed' ? 'bg-success shadow-success/60' : 
              'bg-white/40'
            ]" 
          />
          <div class="flex flex-col">
            <span 
              class="text-[13px] font-black capitalize leading-none tracking-tight"
              :class="store.pipelineStatus === 'running' ? 'text-accent' : store.pipelineStatus === 'completed' ? 'text-success' : 'text-white'"
            >
              {{ store.pipelineStatus === 'running' ? 'Analyzing Data' : store.pipelineStatus === 'completed' ? 'Analysis Ready' : 'System Idle' }}
            </span>
            <span class="text-[11px] text-white/70 mt-1.5 font-bold tracking-tight">Modified Kleinberg × Link Anomaly</span>
          </div>
        </div>
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
