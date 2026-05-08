<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import type { NetworkNode, NetworkEdge } from '@/types/analysis'

const store = useAnalysisStore()
const networkContainer = ref<HTMLDivElement | null>(null)
let networkInstance: Network | null = null

function buildNetwork(nodes: NetworkNode[], edges: NetworkEdge[]) {
  if (!networkContainer.value) return

  const visNodes = new DataSet(
    nodes.map((n) => ({
      id: n.id,
      label: n.label,
      size: Math.max(8, Math.min(40, n.degree * 2)),
      color: {
        background: n.group === 'anomalous' ? '#ef4444'
          : n.group === 'hub' ? '#f59e0b'
          : '#6366f1',
        border: n.group === 'anomalous' ? '#dc2626'
          : n.group === 'hub' ? '#d97706'
          : '#4f46e5',
        highlight: { background: '#22d3ee', border: '#06b6d4' },
      },
      font: {
        size: n.degree > 10 ? 12 : 9,
        color: '#334155',
        face: 'Inter, sans-serif',
      },
      borderWidth: n.group === 'anomalous' ? 3 : 1,
      shadow: n.group === 'anomalous',
      title: `@${n.label}\nDegree: ${n.degree}\nAnomaly: ${(n.anomaly_score * 100).toFixed(1)}%`,
    })),
  )

  const visEdges = new DataSet(
    edges.map((e) => ({
      id: e.id,
      from: e.from,
      to: e.to,
      width: Math.max(1, Math.min(5, e.weight)),
      color: {
        color: e.is_anomalous ? '#ef4444' : '#cbd5e1',
        highlight: '#22d3ee',
        opacity: e.is_anomalous ? 0.8 : 0.3,
      },
      dashes: e.is_anomalous,
      arrows: { to: { enabled: true, scaleFactor: 0.5 } },
    })),
  )

  const options = {
    physics: {
      solver: 'barnesHut',
      barnesHut: {
        gravitationalConstant: -3000,
        centralGravity: 0.3,
        springLength: 120,
        springConstant: 0.04,
        damping: 0.09,
      },
      stabilization: { iterations: 200 },
    },
    interaction: {
      hover: true,
      tooltipDelay: 150,
      zoomView: true,
      dragView: true,
    },
    layout: { improvedLayout: true },
  }

  networkInstance = new Network(networkContainer.value, { nodes: visNodes, edges: visEdges }, options)
}

watch(
  () => store.networkData,
  (data) => {
    if (data.nodes.length > 0) {
      buildNetwork(data.nodes, data.edges)
    }
  },
  { deep: true },
)

onMounted(() => {
  if (store.networkData.nodes.length > 0) {
    buildNetwork(store.networkData.nodes, store.networkData.edges)
  }
})

onBeforeUnmount(() => {
  networkInstance?.destroy()
})
</script>

<template>
  <div class="space-y-8">
    <!-- Configuration Panel -->
    <div class="card float-up border border-danger/20 bg-gradient-to-br from-danger/5 to-transparent">
      <div class="flex items-center gap-2 mb-4">
        <svg class="w-5 h-5 text-danger" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <h3 class="text-sm font-bold text-text uppercase tracking-wider">Link Anomaly Settings</h3>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-text-muted uppercase">Anomaly Threshold θ</label>
          <input v-model.number="store.analysisConfig.anomaly_threshold" type="number" step="0.05" min="0.1" max="0.9" class="w-full bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-danger/20 outline-none" />
        </div>
      </div>
      <div class="mt-4 flex justify-end">
        <button class="btn-primary glow-pulse" :disabled="store.isLoading" @click="store.runLinkAnomaly()">
          Run Link Anomaly
        </button>
      </div>
    </div>

    <div v-show="store.networkData.nodes.length > 0" class="flex flex-col gap-6 float-up" style="animation-delay: 0.1s;">
      <div class="card !p-6 float-up bg-gradient-to-br from-white to-surface-alt border border-border/50">
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-8">
        <!-- Title & Subtitle -->
        <div class="space-y-1">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-danger/10 flex items-center justify-center text-danger">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-text tracking-tight">Link Anomaly Detection</h2>
          </div>
          <p class="text-sm text-text-muted pl-13">Mention-based network graph with anomaly highlighting</p>
        </div>

        <!-- Formula Panel -->
        <div class="px-5 py-3 rounded-xl bg-danger/5 border border-danger/10 flex items-center gap-6">
          <div class="space-y-1">
            <p class="text-[10px] font-black uppercase tracking-widest text-danger">Anomaly Score (Z-Score)</p>
            <div class="font-mono text-[11px] font-bold text-text py-1 leading-tight">
              Score = (Deg<sub class="text-[8px]">obs</sub> - E[Deg]) / <span class="text-danger">σ</span><sub class="text-[8px]">Deg</sub>
            </div>
            <p class="text-[9px] text-text-muted italic">Detecting statistically improbable connection densities</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Network Graph Container -->
    <div class="card float-up !p-2 relative" style="animation-delay: 0.1s;">
      <div ref="networkContainer" class="w-full rounded-xl bg-white/50" style="height: 520px;" />
      <!-- Legend overlay -->
      <div class="absolute top-4 right-4 card !p-3 !rounded-xl space-y-2">
        <p class="text-[10px] font-bold text-text-muted uppercase tracking-wider">Legend</p>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-[#6366f1]" />
          <span class="text-[11px] text-text-muted">Normal Node</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-[#ef4444] shadow-sm shadow-red-500/50" />
          <span class="text-[11px] text-text-muted">Anomalous Node</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-[#f59e0b]" />
          <span class="text-[11px] text-text-muted">Hub Node</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-6 h-0 border-t-2 border-dashed border-[#ef4444]" />
          <span class="text-[11px] text-text-muted">Anomalous Edge</span>
        </div>
      </div>
    </div>

    <!-- Anomaly Clusters -->
    <div v-if="store.networkData.anomalies.length > 0" class="space-y-4">
      <h3 class="text-sm font-bold text-text uppercase tracking-wider">Detected Anomaly Clusters</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          v-for="a in store.networkData.anomalies"
          :key="a.cluster_id"
          class="card float-up !p-4 border-l-4"
          :class="a.type === 'bot_network' || a.type === 'astroturfing' ? 'border-l-danger' : 'border-l-warning'"
        >
          <div class="flex items-start justify-between mb-2">
            <span class="text-xs font-bold uppercase tracking-wider" :class="a.type === 'bot_network' || a.type === 'astroturfing' ? 'text-danger' : 'text-warning'">
              {{ a.type.replace('_', ' ') }}
            </span>
            <span class="font-mono text-xs text-text-muted">{{ (a.confidence * 100).toFixed(0) }}% conf.</span>
          </div>
          <p class="text-sm text-text-muted mb-2">{{ a.description }}</p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="node in a.nodes.slice(0, 8)"
              :key="node"
              class="px-2 py-0.5 rounded-full bg-surface-alt text-[10px] font-mono text-text-muted border border-border"
            >
              @{{ node }}
            </span>
            <span v-if="a.nodes.length > 8" class="px-2 py-0.5 text-[10px] text-text-muted">
              +{{ a.nodes.length - 8 }} more
            </span>
          </div>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>
