<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  subtitle?: string
  icon?: string
  trend?: 'up' | 'down' | 'neutral'
  color?: 'primary' | 'accent' | 'success' | 'danger' | 'warning'
}>()

const iconPaths: Record<string, string> = {
  'document': 'M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z',
  'users': 'M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z',
  'clock': 'M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  'bolt': 'm3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z',
  'chart': 'M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6',
  'hashtag': 'M5.25 8.25h15m-16.5 7.5h15m-1.8-13.5-3.9 19.5m-2.1-19.5-3.9 19.5',
}

const colorMap: Record<string, string> = {
  primary: 'from-primary/15 to-primary/5 text-primary',
  accent: 'from-accent/15 to-accent/5 text-accent',
  success: 'from-success/15 to-success/5 text-success',
  danger: 'from-danger/15 to-danger/5 text-danger',
  warning: 'from-warning/15 to-warning/5 text-warning',
}
</script>

<template>
  <div class="card group float-up">
    <div class="flex items-start justify-between">
      <div class="min-w-0 flex-1">
        <p class="text-xs font-medium text-text-muted uppercase tracking-wider mb-2">{{ label }}</p>
        <p class="stat-value gradient-text">{{ typeof value === 'number' ? value.toLocaleString() : value }}</p>
        <p v-if="subtitle" class="text-sm text-text-muted mt-1">{{ subtitle }}</p>
      </div>
      <div
        v-if="icon"
        class="w-12 h-12 shrink-0 rounded-xl bg-gradient-to-br flex items-center justify-center"
        :class="colorMap[color ?? 'primary']"
      >
        <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" :d="iconPaths[icon] || ''" />
        </svg>
      </div>
    </div>

    <!-- Trend indicator -->
    <div v-if="trend" class="flex items-center gap-1 mt-3">
      <svg v-if="trend === 'up'" class="w-4 h-4 text-success" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" />
      </svg>
      <svg v-else-if="trend === 'down'" class="w-4 h-4 text-danger" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6 9 12.75l4.286-4.286a11.948 11.948 0 0 1 4.306 6.43l.776 2.898m0 0 3.182-5.511m-3.182 5.51-5.511-3.181" />
      </svg>
    </div>
  </div>
</template>
