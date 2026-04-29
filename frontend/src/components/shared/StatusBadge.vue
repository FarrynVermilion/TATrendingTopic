<script setup lang="ts">
import type { TrendStatus } from '@/types/analysis'

const props = defineProps<{
  status: TrendStatus
  size?: 'sm' | 'md'
}>()

const config: Record<TrendStatus, { emoji: string; label: string; classes: string }> = {
  organic: {
    emoji: '🟢',
    label: 'Organic',
    classes: 'bg-success-light text-success border-success/20',
  },
  anomalous: {
    emoji: '🔴',
    label: 'Anomalous',
    classes: 'bg-danger-light text-danger border-danger/20',
  },
  suspicious: {
    emoji: '🟡',
    label: 'Suspicious',
    classes: 'bg-warning-light text-warning border-warning/20',
  },
  unverified: {
    emoji: '⚪',
    label: 'Unverified',
    classes: 'bg-surface-alt text-text-muted border-border',
  },
}
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full border font-semibold"
    :class="[
      config[props.status].classes,
      size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs',
    ]"
  >
    <span>{{ config[props.status].emoji }}</span>
    <span>{{ config[props.status].label }}</span>
  </span>
</template>
