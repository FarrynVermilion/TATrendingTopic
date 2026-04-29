<script setup lang="ts">
import { useStepper } from '@/composables/useStepper'

const { steps, progress } = useStepper()
</script>

<template>
  <div class="px-4 pb-3">
    <!-- Progress bar -->
    <div class="h-1 bg-border rounded-full overflow-hidden">
      <div
        class="h-full rounded-full transition-all duration-500 ease-out"
        style="background: linear-gradient(90deg, var(--color-primary), var(--color-accent))"
        :style="{ width: `${progress}%` }"
      />
    </div>
    <!-- Step dots -->
    <div class="flex justify-between mt-2">
      <div
        v-for="step in steps"
        :key="step.id"
        class="flex flex-col items-center gap-0.5"
      >
        <div
          class="w-2 h-2 rounded-full transition-all duration-300"
          :class="{
            'bg-primary scale-125': step.isActive,
            'bg-success': step.isCompleted,
            'bg-border': !step.isActive && !step.isCompleted,
          }"
        />
        <span class="text-[9px] font-medium" :class="step.isActive ? 'text-primary' : 'text-text-muted'">
          {{ step.id }}
        </span>
      </div>
    </div>
  </div>
</template>
