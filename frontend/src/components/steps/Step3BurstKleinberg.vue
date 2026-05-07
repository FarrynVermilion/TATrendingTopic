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
            ? 'rgba(239, 68, 68, 0.85)' // Extreme Red
            : 'rgba(245, 158, 11, 0.65)', // Extreme Amber
          borderWidth: 2,
          borderColor: b.burst_level >= 2
            ? 'rgba(239, 68, 68, 1)'
            : 'rgba(245, 158, 11, 0.9)',
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
      lineStyle: { 
        width: 4, 
        color: '#6366f1',
        shadowBlur: 10,
        shadowColor: 'rgba(255, 255, 255, 1)',
        shadowOffsetX: 0,
        shadowOffsetY: 0
      },
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
    <div class="flex flex-col gap-6 float-up">
      <!-- Main Header Card -->
      <div class="card !p-0 overflow-hidden bg-gradient-to-br from-white to-surface-alt border border-border/50">
        <div class="grid grid-cols-1 lg:grid-cols-12">
          <!-- Left: Title Section -->
          <div class="lg:col-span-4 p-6 border-b lg:border-b-0 lg:border-r border-border/50 bg-primary/[0.02]">
            <div class="space-y-1">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75Z" />
                  </svg>
                </div>
                <h2 class="text-2xl font-bold text-text tracking-tight">Burst Analysis</h2>
              </div>
              <p class="text-sm text-text-muted">Modified Kleinberg State-Based Intensity Modeling</p>
            </div>
          </div>

          <!-- Middle: Config/Context -->
          <div class="lg:col-span-3 p-6 grid grid-cols-2 gap-4 items-center border-b lg:border-b-0 lg:border-r border-border/50">
            <div class="space-y-1">
              <p class="text-[9px] font-black uppercase tracking-widest text-primary/60 leading-none">Scaling ($s$)</p>
              <p class="text-lg font-bold text-text tabular-nums">{{ store.analysisConfig.kleinberg_s || '2.0' }}</p>
            </div>
            <div class="space-y-1">
              <p class="text-[9px] font-black uppercase tracking-widest text-primary/60 leading-none">Transition ($\gamma$)</p>
              <p class="text-lg font-bold text-text tabular-nums">{{ store.analysisConfig.kleinberg_gamma || '1.0' }}</p>
            </div>
          </div>

          <!-- Right: Detailed Methodology -->
          <div class="lg:col-span-5 p-6 bg-accent/[0.03]">
            <div class="space-y-3">
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-black uppercase tracking-widest text-accent">Methodology: Viterbi Minimization</span>
                <div class="h-px flex-1 bg-accent/20"></div>
              </div>
              <div class="grid grid-cols-3 gap-3">
                <div class="space-y-1">
                  <p class="text-[9px] font-bold text-text uppercase">1. Emission</p>
                  <p class="font-mono text-[9px] font-bold text-primary">$-\ln P(c|q)$</p>
                  <p class="text-[8px] text-text-muted leading-tight"><strong class="text-text">e.g.</strong> Data fits 20/hr (State 1) better than 10/hr (State 0).</p>
                </div>
                <div class="space-y-1 border-x border-border/50 px-3">
                  <p class="text-[9px] font-bold text-text uppercase">2. Transition</p>
                  <p class="font-mono text-[9px] font-bold text-primary">$\tau(i,j)$</p>
                  <p class="text-[8px] text-text-muted leading-tight"><strong class="text-text">e.g.</strong> Penalty to switch. Prevents jitter from minor spikes.</p>
                </div>
                <div class="space-y-1">
                  <p class="text-[9px] font-bold text-text uppercase">3. Intensity</p>
                  <p class="font-mono text-[9px] font-bold text-primary">$W_{rel}$</p>
                  <p class="text-[8px] text-text-muted leading-tight"><strong class="text-text">e.g.</strong> 250 excess tweets / 500 max = 50% score.</p>
                </div>
              </div>
              <div class="mt-2 pt-2 border-t border-accent/10">
                <p class="text-[8px] italic text-text-muted">
                  <strong class="text-accent not-italic">Logic:</strong> Viterbi selects the path where (Emission + Transition) cost is minimal.
                </p>
              </div>
            </div>
          </div>
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

    <!-- Legend & Methodology Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 float-up" style="animation-delay: 0.25s;">
      <!-- Legend -->
      <div class="lg:col-span-4 card !py-3 !px-5 flex flex-col justify-center gap-4">
        <span class="text-xs font-semibold text-text-muted uppercase tracking-wider">Visual Legend</span>
        <div class="space-y-3">
          <div class="flex items-center gap-3">
            <div class="w-5 h-4 rounded-sm shadow-sm" style="background: rgba(245, 158, 11, 0.65); border: 1px solid rgba(245, 158, 11, 1);" />
            <span class="text-[10px] font-black text-amber-700 uppercase tracking-tighter">Low Burst (State 1)</span>
          </div>
          <div class="flex items-center gap-3">
            <div class="w-5 h-4 rounded-sm shadow-sm" style="background: rgba(239, 68, 68, 0.85); border: 1px solid rgba(239, 68, 68, 1);" />
            <span class="text-[10px] font-black text-red-700 uppercase tracking-tighter">High Burst (State 2+)</span>
          </div>
        </div>
      </div>

      <!-- Mathematical Logic -->
      <div class="lg:col-span-8 card !p-5 border-l-4 border-l-primary bg-primary/[0.02]">
        <div class="flex items-start gap-4">
          <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 15.75V18m-3-3V1.5m-3 3V18m3-3h.008v.008H12v-.008Zm0-6h.008v.008H12V9Zm0-6h.008v.008H12V3Zm-3 3h.008v.008H9V6Zm0 6h.008v.008H9v-.008Zm0 6h.008v.008H9V18Zm6-3h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008V9Z" />
            </svg>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
            <div class="space-y-1">
              <p class="text-[10px] font-black uppercase tracking-widest text-primary">State Rate ($\lambda_q$)</p>
              <p class="font-mono text-[11px] font-bold text-text bg-white/60 p-2 rounded">
                $\lambda_q = \lambda_0 \times s^q$
              </p>
              <p class="text-[9px] text-text-muted leading-tight">Frequency scaling based on factor $s$.</p>
            </div>
            <div class="space-y-1">
              <p class="text-[10px] font-black uppercase tracking-widest text-primary">Transition Cost</p>
              <p class="font-mono text-[11px] font-bold text-text bg-white/60 p-2 rounded">
                $\tau(i, j) = (j-i) \gamma \ln n$
              </p>
              <p class="text-[9px] text-text-muted leading-tight">Penalizes state changes to filter noise.</p>
            </div>
            <div class="space-y-1">
              <p class="text-[10px] font-black uppercase tracking-widest text-primary">Intensity ($W$)</p>
              <p class="font-mono text-[11px] font-bold text-text bg-white/60 p-2 rounded">
                $W = \sum (C_t - \lambda_0)$
              </p>
              <p class="text-[9px] text-text-muted leading-tight">Excess frequency over baseline rate.</p>
            </div>
          </div>
        </div>

        <!-- Concrete Example -->
        <div class="mt-4 pt-4 border-t border-primary/10">
          <p class="text-[10px] font-bold text-primary uppercase tracking-wider mb-2">Practical Example:</p>
          <p class="text-[11px] text-text-muted leading-relaxed">
            If the <span class="text-text font-semibold">Base Rate ($\lambda_0$)</span> is <span class="text-primary font-bold">10 tweets/hr</span> 
            and <span class="text-text font-semibold">Scaling ($s$)</span> is <span class="text-primary font-bold">2.0</span>:
            <br/>
            • <span class="text-amber-600 font-bold">State 1 (Low)</span> triggers when frequency exceeds <span class="text-text font-bold">20/hr</span> ($10 \times 2^1$).
            <br/>
            • <span class="text-red-600 font-bold">State 2 (High)</span> triggers when frequency exceeds <span class="text-text font-bold">40/hr</span> ($10 \times 2^2$).
            <br/>
            <span class="inline-block mt-2 font-semibold text-text">Intensity Example:</span>
            If the strongest burst in your dataset has <span class="text-primary font-bold">500 excess tweets</span> ($W_{max} = 500$) and the current burst has <span class="text-primary font-bold">250 excess tweets</span> ($W = 250$), its <span class="text-accent font-bold">Intensity is 50%</span>.
          </p>
        </div>
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
                <span class="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-tighter"
                  :class="bp.burst_level >= 2 ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-amber-100 text-amber-700 border border-amber-200'">
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
