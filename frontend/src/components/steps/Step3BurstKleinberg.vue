<script setup lang="ts">
import { computed, watch } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent,
  DataZoomComponent, MarkAreaComponent, LegendComponent,
} from 'echarts/components'

use([
  CanvasRenderer, LineChart, TitleComponent, TooltipComponent,
  GridComponent, DataZoomComponent, MarkAreaComponent, LegendComponent,
])

const store = useAnalysisStore()

watch(() => store.selectedBurstTerm, (term) => {
  if (term) store.fetchBurstAnalysis(term)
})

const chartOption = computed(() => {
  const freq = store.burstAnalysis.term_frequencies
  const bursts = store.burstAnalysis.burst_periods
  const term = store.selectedBurstTerm || 'All Terms'

  const markAreaData = bursts
    .filter(b => !store.selectedBurstTerm || b.term === store.selectedBurstTerm)
    .map(b => ([
      {
        xAxis: b.start,
        itemStyle: {
          color: b.burst_level >= 2
            ? 'rgba(220, 60, 60, 0.12)'
            : 'rgba(250, 180, 50, 0.10)',
        },
      },
      { xAxis: b.end },
    ]))

  return {
    backgroundColor: 'transparent',
    title: {
      text: `Term Frequency — "${term}"`,
      textStyle: { fontSize: 14, fontWeight: 700, color: '#1a1a2e' },
      left: 16, top: 16,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e2e8f0',
      textStyle: { fontSize: 12, color: '#334155' },
    },
    legend: { show: false },
    grid: { left: 60, right: 30, top: 70, bottom: 80 },
    xAxis: {
      type: 'category',
      data: freq.map(p => p.date),
      axisLabel: { fontSize: 10, color: '#94a3b8', rotate: 30 },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
    },
    yAxis: {
      type: 'value',
      name: 'Frequency',
      nameTextStyle: { fontSize: 11, color: '#94a3b8' },
      axisLabel: { fontSize: 10, color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 24, bottom: 10 },
    ],
    series: [{
      name: 'Frequency',
      type: 'line',
      data: freq.map(p => p.frequency),
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 2.5, color: '#6366f1' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(99, 102, 241, 0.15)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0.01)' },
          ],
        },
      },
      itemStyle: { color: '#6366f1' },
      markArea: { silent: true, data: markAreaData },
    }],
  }
})
</script>

<template>
  <div class="space-y-8">
    <div class="float-up">
      <div class="flex items-center gap-3 mb-2">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75Z" />
          </svg>
        </div>
        <div>
          <h2 class="text-2xl font-bold text-text">Burst Detection (Kleinberg)</h2>
          <p class="text-sm text-text-muted">Term frequency over time with highlighted burst periods</p>
        </div>
      </div>
    </div>

    <!-- Term Selector -->
    <div class="card float-up !py-3 !px-5">
      <div class="flex items-center gap-4 flex-wrap">
        <label class="text-xs font-semibold text-text-muted uppercase tracking-wider shrink-0">Select Term:</label>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="term in store.burstAnalysis.available_terms"
            :key="term"
            class="px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200"
            :class="store.selectedBurstTerm === term
              ? 'bg-primary text-white shadow-sm shadow-primary/30'
              : 'bg-surface-alt text-text-muted border border-border hover:bg-white hover:shadow-sm'"
            @click="store.selectedBurstTerm = term"
          >
            {{ term }}
          </button>
        </div>
      </div>
    </div>

    <!-- ECharts Line Chart -->
    <div class="card float-up !p-4" style="animation-delay: 0.15s;">
      <VChart
        :option="chartOption"
        :autoresize="true"
        style="width: 100%; height: 420px;"
      />
    </div>

    <!-- Legend -->
    <div class="card float-up !py-3 !px-5 flex items-center gap-6" style="animation-delay: 0.25s;">
      <span class="text-xs font-semibold text-text-muted uppercase tracking-wider">Legend:</span>
      <div class="flex items-center gap-2">
        <div class="w-4 h-3 rounded-sm" style="background: rgba(250, 180, 50, 0.25);" />
        <span class="text-xs text-text-muted">Low Burst (State 1)</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-4 h-3 rounded-sm" style="background: rgba(220, 60, 60, 0.25);" />
        <span class="text-xs text-text-muted">High Burst (State 2+)</span>
      </div>
    </div>

    <!-- Burst Periods Table -->
    <div class="card float-up !p-0 overflow-hidden" style="animation-delay: 0.35s;">
      <div class="px-5 pt-4 pb-2">
        <h3 class="text-sm font-bold text-text uppercase tracking-wider">Detected Burst Periods</h3>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-y border-border bg-surface-alt/50">
              <th class="px-4 py-2 text-left text-xs font-semibold text-text-muted uppercase">Term</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-text-muted uppercase">Start</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-text-muted uppercase">End</th>
              <th class="px-4 py-2 text-center text-xs font-semibold text-text-muted uppercase">Level</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-text-muted uppercase">Intensity</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/50">
            <tr v-for="(bp, i) in store.burstAnalysis.burst_periods" :key="i" class="hover:bg-primary/3">
              <td class="px-4 py-2 font-mono text-xs font-semibold text-primary">{{ bp.term }}</td>
              <td class="px-4 py-2 font-mono text-xs text-text-muted">{{ bp.start }}</td>
              <td class="px-4 py-2 font-mono text-xs text-text-muted">{{ bp.end }}</td>
              <td class="px-4 py-2 text-center">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold"
                  :class="bp.burst_level >= 2 ? 'bg-danger/10 text-danger' : 'bg-warning/10 text-warning'">
                  State {{ bp.burst_level }}
                </span>
              </td>
              <td class="px-4 py-2 text-right font-mono text-xs">{{ (bp.intensity * 100).toFixed(1) }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
