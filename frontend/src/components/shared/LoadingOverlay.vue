<script setup lang="ts">
defineProps<{
  message?: string
  overlay?: boolean
}>()
</script>

<template>
  <div
    class="flex flex-col items-center justify-center gap-4 py-16"
    :class="overlay ? 'absolute inset-0 bg-white/70 backdrop-blur-sm z-20 rounded-2xl' : ''"
  >
    <!-- Animated spinner -->
    <div class="relative w-12 h-12">
      <div class="absolute inset-0 rounded-full border-2 border-border" />
      <div class="absolute inset-0 rounded-full border-2 border-transparent border-t-primary animate-spin" />
      <div class="absolute inset-1.5 rounded-full border-2 border-transparent border-b-accent animate-spin" style="animation-direction: reverse; animation-duration: 0.8s;" />
    </div>
    <p v-if="message" class="text-sm font-medium text-text-muted animate-pulse">{{ message }}</p>
  </div>
</template>
