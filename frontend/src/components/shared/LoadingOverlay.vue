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
    <div class="relative w-28 h-28 mb-6">
      <!-- Deep Glow Layers -->
      <div class="absolute -inset-4 bg-primary/20 rounded-full blur-2xl animate-pulse" />
      <div class="absolute -inset-2 bg-accent/10 rounded-full blur-xl animate-pulse" style="animation-delay: 500ms" />
      
      <!-- Glass Ring Base -->
      <div class="absolute inset-0 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm shadow-inner" />
      
      <!-- Primary Orbit -->
      <div class="absolute inset-0 rounded-full border-t-2 border-l-2 border-primary animate-spin" style="animation-duration: 2s" />
      
      <!-- Accent Orbit (Reverse) -->
      <div class="absolute inset-3 rounded-full border-b-2 border-r-2 border-accent animate-spin" style="animation-direction: reverse; animation-duration: 1.5s" />
      
      <!-- Inner Pulse Core -->
      <div class="absolute inset-[30%] rounded-full bg-gradient-to-br from-primary via-accent to-primary bg-[length:200%_200%] animate-[gradient_3s_ease_infinite] shadow-[0_0_20px_rgba(var(--color-primary),0.5)]">
        <div class="absolute inset-0 rounded-full bg-white/20 animate-ping opacity-20" />
      </div>
      
      <!-- Floating Particles (CSS Only) -->
      <div class="absolute inset-0 animate-[spin_10s_linear_infinite]">
        <div class="absolute top-0 left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-primary rounded-full blur-[1px] shadow-[0_0_8px_var(--color-primary)]" />
      </div>
    </div>

    <div class="text-center space-y-4 max-w-xs">
      <div class="space-y-2">
        <h3 v-if="message" class="text-xl font-bold text-text tracking-tight">
          {{ message }}
        </h3>
        <div class="flex items-center justify-center gap-2">
          <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 0ms" />
          <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 200ms" />
          <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 400ms" />
        </div>
      </div>
      
      <p class="inline-block text-[10px] font-bold uppercase tracking-[0.2em] text-primary/60 px-4 py-1.5 border border-primary/20 rounded-full bg-primary/5">
        Computational Engine Active
      </p>
    </div>
  </div>
</template>
