<script setup lang="ts">
import { useAnalysisStore } from '@/stores/analysisStore'
import { useStepper } from '@/composables/useStepper'
import Step1DatasetOverview from '@/components/steps/Step1DatasetOverview.vue'
import Step2Preprocessing from '@/components/steps/Step2Preprocessing.vue'
import Step3BurstKleinberg from '@/components/steps/Step3BurstKleinberg.vue'
import Step4LinkAnomaly from '@/components/steps/Step4LinkAnomaly.vue'
import Step5Summary from '@/components/steps/Step5Summary.vue'
import LoadingOverlay from '@/components/shared/LoadingOverlay.vue'

const store = useAnalysisStore()
const { currentStep, canGoNext, canGoPrev, handleNext, handlePrev, isLoading } = useStepper()
</script>

<template>
  <div class="space-y-8">
    <!-- Error Banner -->
    <Transition name="slide">
      <div
        v-if="store.pipelineError"
        class="card !py-3 !px-5 border-l-4 border-l-danger flex items-center justify-between"
      >
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-danger shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
          </svg>
          <span class="text-sm text-danger font-medium">{{ store.pipelineError }}</span>
        </div>
        <button class="text-danger/50 hover:text-danger" @click="store.pipelineError = null">&times;</button>
      </div>
    </Transition>

    <!-- Step Content (Stacked) -->
    <div class="flex flex-col gap-16 pb-12">
      <!-- Step 1 is always visible -->
      <div id="step-1" class="scroll-mt-24">
        <Step1DatasetOverview />
      </div>

      <Transition name="fade">
        <div v-if="currentStep >= 2" id="step-2" class="scroll-mt-24 relative before:absolute before:inset-0 before:bg-white/40 before:-z-10 dark:before:bg-black/20 p-8 rounded-3xl border border-border/60 shadow-sm">
          <Step2Preprocessing />
        </div>
      </Transition>

      <Transition name="fade">
        <div v-if="currentStep >= 3" id="step-3" class="scroll-mt-24 relative before:absolute before:inset-0 before:bg-white/40 before:-z-10 dark:before:bg-black/20 p-8 rounded-3xl border border-border/60 shadow-sm">
          <Step3BurstKleinberg />
        </div>
      </Transition>

      <Transition name="fade">
        <div v-if="currentStep >= 4" id="step-4" class="scroll-mt-24 relative before:absolute before:inset-0 before:bg-white/40 before:-z-10 dark:before:bg-black/20 p-8 rounded-3xl border border-border/60 shadow-sm">
          <Step4LinkAnomaly />
        </div>
      </Transition>

      <Transition name="fade">
        <div v-if="currentStep >= 5" id="step-5" class="scroll-mt-24 relative before:absolute before:inset-0 before:bg-white/40 before:-z-10 dark:before:bg-black/20 p-8 rounded-3xl border border-border/60 shadow-sm">
          <Step5Summary />
        </div>
      </Transition>
    </div>

    <!-- Bottom Navigation -->
    <div
      class="flex items-center justify-between pt-4 border-t border-border"
    >
      <button
        v-if="canGoPrev"
        class="btn-secondary"
        @click="handlePrev()"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Previous Step
      </button>
      <div v-else />

      <button
        v-if="canGoNext && currentStep < 5"
        class="btn-primary"
        :disabled="isLoading"
        @click="handleNext()"
      >
        Next Step
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
        </svg>
      </button>
    </div>

    <!-- Loading overlay for step transitions -->
    <LoadingOverlay v-if="isLoading" message="Processing..." overlay />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
