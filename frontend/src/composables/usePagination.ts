import { ref, computed } from 'vue'

/**
 * Composable for client-side pagination logic.
 * Reusable across DataTable instances in Step 2 and Step 5.
 */
export function usePagination<T>(options: {
  fetchFn: (page: number) => Promise<void>
  totalCount: () => number
  pageSize?: number
}) {
  const currentPage = ref(1)
  const pageSize = options.pageSize ?? 20
  const isPageLoading = ref(false)

  const totalPages = computed(() =>
    Math.max(1, Math.ceil(options.totalCount() / pageSize)),
  )

  const hasPrev = computed(() => currentPage.value > 1)
  const hasNext = computed(() => currentPage.value < totalPages.value)

  const pageRange = computed(() => {
    const total = totalPages.value
    const current = currentPage.value
    const delta = 2
    const range: number[] = []

    for (
      let i = Math.max(1, current - delta);
      i <= Math.min(total, current + delta);
      i++
    ) {
      range.push(i)
    }
    return range
  })

  async function goToPage(page: number) {
    if (page < 1 || page > totalPages.value || page === currentPage.value) return
    isPageLoading.value = true
    currentPage.value = page
    try {
      await options.fetchFn(page)
    } finally {
      isPageLoading.value = false
    }
  }

  async function nextPage() {
    if (hasNext.value) await goToPage(currentPage.value + 1)
  }

  async function prevPage() {
    if (hasPrev.value) await goToPage(currentPage.value - 1)
  }

  return {
    currentPage,
    totalPages,
    hasPrev,
    hasNext,
    pageRange,
    isPageLoading,
    goToPage,
    nextPage,
    prevPage,
  }
}
