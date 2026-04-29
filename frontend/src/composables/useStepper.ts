import { computed } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import type { StepId } from '@/types/analysis'

/**
 * Composable for stepper navigation logic.
 * Encapsulates step transitions, validation, and keyboard navigation.
 */
export function useStepper() {
  const store = useAnalysisStore()

  const progress = computed(() => ((store.currentStep - 1) / 4) * 100)

  const currentStepDef = computed(
    () => store.steps.find((s) => s.id === store.currentStep)!,
  )

  function isStepAccessible(step: StepId): boolean {
    return step <= store.currentStep
  }

  function navigateToStep(step: StepId) {
    if (isStepAccessible(step)) {
      store.goToStep(step)
    }
  }

  async function handleNext() {
    if (!store.canGoNext) return

    const next = (store.currentStep + 1) as StepId

    // Trigger data fetching for the next step
    switch (next) {
      case 3:
        await store.fetchBurstAnalysis()
        break
      case 4:
        await store.fetchNetworkData()
        break
      case 5:
        await store.fetchTrendSummary()
        break
    }

    store.nextStep()
  }

  function handlePrev() {
    store.prevStep()
  }

  return {
    currentStep: computed(() => store.currentStep),
    steps: computed(() => store.steps),
    progress,
    currentStepDef,
    canGoNext: computed(() => store.canGoNext),
    canGoPrev: computed(() => store.canGoPrev),
    isLoading: computed(() => store.isLoading),
    isStepAccessible,
    navigateToStep,
    handleNext,
    handlePrev,
  }
}
