<script setup lang="ts">
import { useStepper } from '@/composables/useStepper'

const { steps, currentStep, isStepAccessible, navigateToStep } = useStepper()

/**
 * SVG icon paths keyed by step icon name.
 * Using inline SVG to avoid a heavy icon library dependency.
 */
const iconPaths: Record<string, string> = {
  'database': 'M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125',
  'funnel': 'M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z',
  'chart-bar': 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z',
  'globe-alt': 'M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5a17.92 17.92 0 0 1-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418',
  'clipboard-document-check': 'M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0 1 18 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3 1.5 1.5 3-3.75',
}
</script>

<template>
  <nav class="px-3">
    <ol class="space-y-1">
      <li v-for="step in steps" :key="step.id">
        <button
          :id="`stepper-step-${step.id}`"
          class="w-full flex items-start gap-3 p-3 rounded-xl text-left transition-all duration-200 group"
          :class="{
            'bg-white/10 shadow-sm shadow-white/5': step.isActive,
            'hover:bg-white/5 cursor-pointer': isStepAccessible(step.id) && !step.isActive,
            'opacity-40 cursor-not-allowed': step.isLocked,
          }"
          :disabled="step.isLocked"
          @click="navigateToStep(step.id)"
        >
          <!-- Step Indicator Circle -->
          <div
            class="w-8 h-8 shrink-0 rounded-lg flex items-center justify-center transition-all duration-300 mt-0.5"
            :class="{
              'bg-gradient-to-br from-primary to-accent shadow-md shadow-primary/30': step.isActive,
              'bg-success/20 text-success': step.isCompleted,
              'bg-white/10 text-sidebar-muted': !step.isActive && !step.isCompleted,
            }"
          >
            <!-- Checkmark for completed -->
            <svg v-if="step.isCompleted" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
            </svg>
            <!-- Icon for active/locked -->
            <svg v-else class="w-4 h-4" :class="step.isActive ? 'text-white' : ''" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" :d="iconPaths[step.icon] || ''" />
            </svg>
          </div>

          <!-- Step Label -->
          <div class="min-w-0">
            <p
              class="text-sm font-semibold leading-tight truncate"
              :class="step.isActive ? 'text-white' : step.isCompleted ? 'text-sidebar-text' : 'text-sidebar-muted'"
            >
              {{ step.title }}
            </p>
            <p class="text-xs mt-0.5 truncate" :class="step.isActive ? 'text-white/60' : 'text-sidebar-muted/60'">
              {{ step.subtitle }}
            </p>
          </div>
        </button>
      </li>
    </ol>
  </nav>
</template>
