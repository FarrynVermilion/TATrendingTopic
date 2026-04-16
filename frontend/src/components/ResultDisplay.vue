<script setup lang="ts">
import { ref, computed } from 'vue'

interface WordFactor {
  j: number
  numerator: number
  denominator: number
  formula: string
  result: number
}

interface WordDetail {
  word: string
  count_in_doc: number
  n_z_w: number
  factors: WordFactor[]
}

interface ClusterDetail {
  cluster: number
  m_z: number
  n_z: number
  p_cluster: number
  p_cluster_formula: string
  p_words: number
  p_words_formula: string
  p_total_raw: number
  p_normalized: number
  word_details: WordDetail[]
}

interface SampleCalc {
  doc_index: number
  doc_words: string[]
  prev_cluster: number
  new_cluster: number
  transferred: boolean
  probabilities: number[]
  chosen_cluster_prob: number
  cluster_details: ClusterDetail[]
}

interface ClusterStat {
  cluster_id: number
  m_z: number
  n_z: number
  top_words: { word: string; count: number }[]
}

interface IterationLog {
  phase: string
  iteration?: number
  description?: string
  params?: Record<string, number>
  assignments?: number[]
  total_transfers?: number
  total_documents?: number
  converged?: boolean
  cluster_stats: ClusterStat[]
  sample_calculations?: SampleCalc[]
}

interface Topic {
  topic_id: number
  topic_label: number
  doc_count: number
  top_words: string[]
  word_scores: Record<string, number>
}

interface Document {
  doc_index: number
  original_text: string
  preprocessed: string
  topic_id: number
}

interface GsdmmResults {
  message: string
  num_topics_found: number
  num_documents: number
  topics: Topic[]
  documents: Document[]
  iteration_logs: IterationLog[]
  topics_csv_url: string
  documents_csv_url: string
}

const props = defineProps<{
  results: GsdmmResults
}>()

const emit = defineEmits<{
  (e: 'reset'): void
}>()

const activeTab = ref('steps') // 'steps' | 'topics' | 'documents'
const selectedTopicFilter = ref<number | null>(null)
const expandedStep = ref<number | null>(0) // which step accordion is open
const expandedCalc = ref<number | null>(null) // which sample calc is expanded

const filteredDocuments = computed(() => {
  if (selectedTopicFilter.value === null) {
    return props.results.documents
  }
  return props.results.documents.filter(
    (doc) => doc.topic_id === selectedTopicFilter.value
  )
})

const filterByTopic = (topicLabel: number) => {
  selectedTopicFilter.value = topicLabel
  activeTab.value = 'documents'
}

const clearFilter = () => {
  selectedTopicFilter.value = null
}

const maxDocCount = computed(() => {
  if (!props.results.topics.length) return 1
  return Math.max(...props.results.topics.map((t) => t.doc_count))
})

const toggleStep = (index: number) => {
  expandedStep.value = expandedStep.value === index ? null : index
  expandedCalc.value = null
}

const toggleCalc = (index: number) => {
  expandedCalc.value = expandedCalc.value === index ? null : index
}

const formatScientific = (value: number): string => {
  if (value === 0) return '0'
  if (Math.abs(value) < 0.0001 || Math.abs(value) > 9999) {
    return value.toExponential(4)
  }
  return value.toFixed(6)
}
</script>

<template>
  <div class="animate-in fade-in slide-in-from-bottom-4 duration-500">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-2xl font-bold text-slate-800">Topic Analysis Results</h2>
        <p class="text-sm text-slate-500 mt-1">
          Found <span class="font-semibold text-indigo-600">{{ results.num_topics_found }}</span> topics
          across <span class="font-semibold text-indigo-600">{{ results.num_documents }}</span> documents
        </p>
      </div>
      <button 
        @click="emit('reset')"
        class="text-sm px-4 py-2 text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg font-medium transition-colors"
      >
        Start New Analysis
      </button>
    </div>

    <!-- Tabs -->
    <div class="flex space-x-1 p-1 bg-slate-100/50 rounded-xl mb-6 shadow-inner">
      <button 
        @click="activeTab = 'steps'"
        :class="activeTab === 'steps' ? 'bg-white shadow text-indigo-700' : 'text-slate-500 hover:text-slate-700'"
        class="flex-1 py-2.5 text-sm font-medium rounded-lg transition-all"
      >
        📊 Calculation Steps
      </button>
      <button 
        @click="activeTab = 'topics'"
        :class="activeTab === 'topics' ? 'bg-white shadow text-indigo-700' : 'text-slate-500 hover:text-slate-700'"
        class="flex-1 py-2.5 text-sm font-medium rounded-lg transition-all"
      >
        Topics Overview
      </button>
      <button 
        @click="activeTab = 'documents'"
        :class="activeTab === 'documents' ? 'bg-white shadow text-indigo-700' : 'text-slate-500 hover:text-slate-700'"
        class="flex-1 py-2.5 text-sm font-medium rounded-lg transition-all"
      >
        Document Clusters
      </button>
    </div>

    <!-- Downloads -->
    <div class="flex justify-end gap-3 mb-4">
      <a 
        v-if="results.topics_csv_url && activeTab === 'topics'" 
        :href="results.topics_csv_url" 
        download 
        class="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg text-sm font-medium transition-colors border border-emerald-200"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
        Download Topics CSV
      </a>
      <a 
        v-if="results.documents_csv_url && activeTab === 'documents'" 
        :href="results.documents_csv_url" 
        download 
        class="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg text-sm font-medium transition-colors border border-emerald-200"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
        Download Documents CSV
      </a>
    </div>

    <!-- ==================== CALCULATION STEPS TAB ==================== -->
    <div v-show="activeTab === 'steps'" class="space-y-3">

      <!-- ===== GSDMM Formula Reference Panel ===== -->
      <div class="bg-gradient-to-br from-indigo-50 to-slate-50 rounded-xl border border-indigo-200 p-5 mb-2">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-lg">📐</span>
          <h3 class="text-sm font-bold text-indigo-800">GSDMM Formula Reference</h3>
        </div>

        <p class="text-xs text-slate-600 mb-4 leading-relaxed">
          GSDMM (<i>Gibbs Sampling Dirichlet Multinomial Mixture</i>) is a short-text topic model 
          based on the <b>Movie Group Process</b> analogy (Yin &amp; Wang, 2014). Each document is 
          assigned to exactly <b>one</b> topic. The algorithm iteratively reassigns documents to the 
          topic with the highest posterior probability.
        </p>

        <!-- Main Formula -->
        <div class="bg-white rounded-lg border border-indigo-100 px-4 py-3 mb-3">
          <p class="text-xs font-semibold text-slate-700 mb-2">Posterior probability of document <i>d</i> belonging to cluster <i>z</i>:</p>
          <p class="text-sm font-mono text-center text-indigo-900 py-1">
            p(z | d) &nbsp;∝&nbsp; p(z) &nbsp;×&nbsp; p(w<sub>d</sub> | z)
          </p>
        </div>

        <!-- Sub-formulas in two columns -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <!-- p(z) formula -->
          <div class="bg-white rounded-lg border border-slate-200 px-4 py-3">
            <p class="text-xs font-semibold text-slate-700 mb-1.5">① Cluster Popularity — p(z):</p>
            <p class="text-sm font-mono text-center text-slate-800 py-1">
              p(z) = (m<sub>z</sub> + α) / (D − 1 + K × α)
            </p>
            <p class="text-xs text-slate-500 mt-2 leading-relaxed">
              Documents prefer clusters that already contain many documents. 
              A cluster with more members (m<sub>z</sub>) gets a higher probability.
            </p>
          </div>

          <!-- p(w|z) formula -->
          <div class="bg-white rounded-lg border border-slate-200 px-4 py-3">
            <p class="text-xs font-semibold text-slate-700 mb-1.5">② Word Likelihood — p(w<sub>d</sub> | z):</p>
            <p class="text-sm font-mono text-center text-slate-800 py-1">
              p(w|z) = ∏<sub>w∈d</sub> ∏<sub>j=0</sub><sup>c<sub>w</sub>−1</sup> 
              (n<sub>z,w</sub> + β + j) / (n<sub>z</sub> + V×β + j)
            </p>
            <p class="text-xs text-slate-500 mt-2 leading-relaxed">
              Documents prefer clusters whose word distribution matches their own words. 
              A cluster that already contains the same words gets a higher probability.
            </p>
          </div>
        </div>

        <!-- Variable definitions -->
        <div class="bg-white rounded-lg border border-slate-200 px-4 py-3">
          <p class="text-xs font-semibold text-slate-700 mb-2">Variable Definitions:</p>
          <div class="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1 text-xs text-slate-600">
            <span><b class="font-mono">D</b> = Total number of documents</span>
            <span><b class="font-mono">K</b> = Max number of clusters (topics)</span>
            <span><b class="font-mono">V</b> = Vocabulary size (unique words)</span>
            <span><b class="font-mono">m<sub>z</sub></b> = Number of docs in cluster z</span>
            <span><b class="font-mono">n<sub>z</sub></b> = Total words in cluster z</span>
            <span><b class="font-mono">n<sub>z,w</sub></b> = Count of word w in cluster z</span>
            <span><b class="font-mono">c<sub>w</sub></b> = Count of word w in document</span>
            <span><b class="font-mono">α</b> = Dirichlet prior (doc-topic)</span>
            <span><b class="font-mono">β</b> = Dirichlet prior (topic-word)</span>
          </div>
        </div>

        <!-- Algorithm steps -->
        <div class="mt-3 bg-white rounded-lg border border-slate-200 px-4 py-3">
          <p class="text-xs font-semibold text-slate-700 mb-2">Algorithm Steps:</p>
          <ol class="text-xs text-slate-600 space-y-1 list-decimal list-inside">
            <li><b>Initialization:</b> Randomly assign each document to one of K clusters.</li>
            <li><b>For each iteration:</b> For each document d:
              <ol class="ml-4 mt-0.5 space-y-0.5 list-[lower-alpha] list-inside text-slate-500">
                <li>Remove d from its current cluster (update m<sub>z</sub>, n<sub>z</sub>, n<sub>z,w</sub>).</li>
                <li>Calculate p(z|d) for all K clusters using the formulas above.</li>
                <li>Assign d to the cluster with the highest probability (sample from multinomial).</li>
                <li>Update cluster statistics with the new assignment.</li>
              </ol>
            </li>
            <li><b>Convergence:</b> Stop when no documents transfer between clusters, or max iterations reached.</li>
          </ol>
        </div>
      </div>

      <div 
        v-for="(log, logIndex) in results.iteration_logs" 
        :key="logIndex"
        class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden"
      >
        <!-- Step Header (Accordion toggle) -->
        <button
          @click="toggleStep(logIndex)"
          class="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-slate-50 transition-colors"
        >
          <div class="flex items-center gap-3">
            <!-- Phase badge -->
            <span 
              v-if="log.phase === 'initialization'"
              class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-amber-100 text-amber-700 text-xs font-bold"
            >0</span>
            <span 
              v-else
              class="inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold"
              :class="log.converged ? 'bg-emerald-100 text-emerald-700' : 'bg-indigo-100 text-indigo-700'"
            >{{ log.iteration }}</span>
            
            <div>
              <h3 class="text-sm font-semibold text-slate-800">
                <template v-if="log.phase === 'initialization'">
                  Initialization — Random Assignment
                </template>
                <template v-else>
                  Iteration {{ log.iteration }}
                  <span v-if="log.converged" class="ml-2 text-emerald-600 text-xs font-normal">(Converged ✓)</span>
                </template>
              </h3>
              <p class="text-xs text-slate-500 mt-0.5">
                <template v-if="log.phase === 'initialization'">
                  D={{ log.params?.D }}, V={{ log.params?.V }}, K={{ log.params?.K }}, α={{ log.params?.alpha }}, β={{ log.params?.beta }}
                </template>
                <template v-else>
                  {{ log.total_transfers }} transfers out of {{ log.total_documents }} documents
                </template>
              </p>
            </div>
          </div>
          <svg 
            class="w-5 h-5 text-slate-400 transition-transform duration-200" 
            :class="expandedStep === logIndex ? 'rotate-180' : ''"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
          </svg>
        </button>

        <!-- Step Detail Content -->
        <div v-show="expandedStep === logIndex" class="border-t border-slate-100 px-5 py-4 space-y-4">
          
          <!-- Explanation text for Initialization -->
          <div v-if="log.phase === 'initialization'" class="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
            <p class="text-xs text-amber-800 leading-relaxed">
              <b>Step 0 — Initialization:</b> Each document is randomly assigned to one of 
              <b>K = {{ log.params?.K }}</b> clusters. This creates the initial state of the cluster statistics:
              <b>m<sub>z</sub></b> (number of documents per cluster) and <b>n<sub>z</sub></b> (total word count per cluster).
              The corpus has <b>D = {{ log.params?.D }}</b> documents and <b>V = {{ log.params?.V }}</b> unique words.
              Dirichlet priors: <b>α = {{ log.params?.alpha }}</b>, <b>β = {{ log.params?.beta }}</b>.
            </p>
          </div>

          <!-- Explanation text for Iterations -->
          <div v-if="log.phase === 'iteration'" class="border rounded-lg px-4 py-3" :class="log.converged ? 'bg-emerald-50 border-emerald-200' : 'bg-blue-50 border-blue-200'">
            <p class="text-xs leading-relaxed" :class="log.converged ? 'text-emerald-800' : 'text-blue-800'">
              <b>Iteration {{ log.iteration }}:</b>
              Each of the {{ log.total_documents }} documents was evaluated. For each document,
              it was temporarily removed from its cluster, then the probability p(z|d) was calculated for all clusters.
              The document was reassigned to the cluster with the highest probability.
              <b>{{ log.total_transfers }} document(s)</b> moved to a different cluster in this iteration.
              <span v-if="log.converged">
                <br/><b>✓ Converged:</b> No documents changed clusters — the algorithm has reached a stable state and stops.
              </span>
              <span v-else-if="log.total_transfers && log.total_transfers > 0">
                The algorithm continues to the next iteration because documents are still moving.
              </span>
            </p>
          </div>
          
          <!-- Cluster Statistics Table -->
          <div>
            <h4 class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Cluster Statistics (m<sub>z</sub>, n<sub>z</sub>)
            </h4>
            <div class="overflow-x-auto">
              <table class="w-full text-xs text-left text-slate-600 border border-slate-200 rounded-lg">
                <thead class="bg-slate-50 text-slate-700">
                  <tr>
                    <th class="px-3 py-2 font-semibold">Cluster (z)</th>
                    <th class="px-3 py-2 font-semibold">m<sub>z</sub> (docs)</th>
                    <th class="px-3 py-2 font-semibold">n<sub>z</sub> (words)</th>
                    <th class="px-3 py-2 font-semibold">Top Words</th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="cs in log.cluster_stats" 
                    :key="cs.cluster_id"
                    class="border-t border-slate-100 hover:bg-slate-50"
                    :class="cs.m_z === 0 ? 'opacity-40' : ''"
                  >
                    <td class="px-3 py-2 font-medium">{{ cs.cluster_id }}</td>
                    <td class="px-3 py-2">{{ cs.m_z }}</td>
                    <td class="px-3 py-2">{{ cs.n_z }}</td>
                    <td class="px-3 py-2">
                      <span v-if="cs.top_words.length">
                        <span v-for="(tw, twi) in cs.top_words" :key="tw.word">
                          {{ tw.word }}<span class="text-slate-400">({{ tw.count }})</span><span v-if="twi < cs.top_words.length - 1">, </span>
                        </span>
                      </span>
                      <span v-else class="text-slate-400 italic">empty</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Initialization: show first N assignments -->
          <div v-if="log.phase === 'initialization' && log.assignments">
            <h4 class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Initial Random Assignments (first 20)
            </h4>
            <div class="flex flex-wrap gap-1.5">
              <span 
                v-for="(a, ai) in log.assignments.slice(0, 20)" 
                :key="ai"
                class="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-slate-100 text-slate-700"
              >
                d<sub>{{ ai + 1 }}</sub> → z<sub>{{ a }}</sub>
              </span>
              <span v-if="log.assignments.length > 20" class="text-xs text-slate-400 self-center">
                ... ({{ log.assignments.length - 20 }} more)
              </span>
            </div>
          </div>

          <!-- Iteration: Sample Document Calculations -->
          <div v-if="log.sample_calculations && log.sample_calculations.length">
            <h4 class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
              Sample Document Calculations
            </h4>
            <p class="text-xs text-slate-500 mb-3 leading-relaxed">
              Below shows the detailed probability calculation for sample documents. For each document,
              the algorithm computes <span class="font-mono">p(z|d) = p(z) × p(w<sub>d</sub>|z)</span> 
              for every cluster, then normalizes to get the final probabilities. 
              The cluster with the highest normalized probability is chosen.
            </p>
            
            <div class="space-y-2">
              <div 
                v-for="(calc, calcIndex) in log.sample_calculations" 
                :key="calc.doc_index"
                class="border border-slate-200 rounded-lg overflow-hidden"
              >
                <!-- Sample doc header -->
                <button
                  @click="toggleCalc(logIndex * 100 + calcIndex)"
                  class="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-50 transition-colors text-xs"
                >
                  <div class="flex items-center gap-3">
                    <span class="font-semibold text-slate-700">Doc #{{ calc.doc_index }}</span>
                    <span class="text-slate-400">
                      Words: [{{ calc.doc_words.slice(0, 5).join(', ') }}<span v-if="calc.doc_words.length > 5">...</span>]
                    </span>
                    <span 
                      class="px-2 py-0.5 rounded font-medium"
                      :class="calc.transferred ? 'bg-orange-100 text-orange-700' : 'bg-emerald-100 text-emerald-700'"
                    >
                      z={{ calc.prev_cluster }} → z={{ calc.new_cluster }}
                      {{ calc.transferred ? '(moved)' : '(stayed)' }}
                    </span>
                  </div>
                  <svg 
                    class="w-4 h-4 text-slate-400 transition-transform duration-200" 
                    :class="expandedCalc === (logIndex * 100 + calcIndex) ? 'rotate-180' : ''"
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                  </svg>
                </button>

                <!-- Detailed probability calculations -->
                <div 
                  v-show="expandedCalc === (logIndex * 100 + calcIndex)" 
                  class="border-t border-slate-100 px-4 py-3 bg-slate-50/50"
                >
                  <!-- Formula reminder callout -->
                  <div class="bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-2 mb-3">
                    <p class="text-xs text-indigo-700 leading-relaxed">
                      <b>Calculation for Doc #{{ calc.doc_index }}:</b> 
                      Words in this document = [<span class="font-mono">{{ calc.doc_words.join(', ') }}</span>].
                      For each cluster z, we compute:
                      <span class="font-mono">p(z) = (m<sub>z</sub> + α) / (D−1 + K×α)</span>, then
                      <span class="font-mono">p(w|z) = ∏(n<sub>z,w</sub> + β + j) / (n<sub>z</sub> + V×β + j)</span>, 
                      and multiply them to get the unnormalized score. Finally, we normalize across all clusters.
                    </p>
                  </div>

                  <!-- Probability summary bar -->
                  <div class="mb-3">
                    <p class="text-xs text-slate-500 mb-1 font-medium">Normalized Probabilities per Cluster:</p>
                    <div class="flex flex-wrap gap-1.5">
                      <span 
                        v-for="(cd, ci) in calc.cluster_details" 
                        :key="ci"
                        class="px-2 py-1 rounded text-xs font-mono"
                        :class="ci === calc.new_cluster ? 'bg-indigo-200 text-indigo-900 font-bold' : 'bg-slate-100 text-slate-600'"
                      >
                        p(z={{ cd.cluster }}) = {{ cd.p_normalized.toFixed(6) }}
                      </span>
                    </div>
                  </div>

                  <!-- Detailed per-cluster calculation table -->
                  <div class="overflow-x-auto">
                    <table class="w-full text-xs text-left border border-slate-200 rounded">
                      <thead class="bg-slate-100 text-slate-700">
                        <tr>
                          <th class="px-2 py-1.5 font-semibold">z</th>
                          <th class="px-2 py-1.5 font-semibold">m<sub>z</sub></th>
                          <th class="px-2 py-1.5 font-semibold">n<sub>z</sub></th>
                          <th class="px-2 py-1.5 font-semibold">p(z) formula</th>
                          <th class="px-2 py-1.5 font-semibold">p(z)</th>
                          <th class="px-2 py-1.5 font-semibold">p(w|z)</th>
                          <th class="px-2 py-1.5 font-semibold">p(z)×p(w|z)</th>
                          <th class="px-2 py-1.5 font-semibold">Normalized</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr 
                          v-for="cd in calc.cluster_details" 
                          :key="cd.cluster"
                          class="border-t border-slate-100"
                          :class="cd.cluster === calc.new_cluster ? 'bg-indigo-50 font-medium' : ''"
                        >
                          <td class="px-2 py-1.5">{{ cd.cluster }}</td>
                          <td class="px-2 py-1.5">{{ cd.m_z }}</td>
                          <td class="px-2 py-1.5">{{ cd.n_z }}</td>
                          <td class="px-2 py-1.5 font-mono text-slate-500">{{ cd.p_cluster_formula }}</td>
                          <td class="px-2 py-1.5 font-mono">{{ cd.p_cluster.toFixed(6) }}</td>
                          <td class="px-2 py-1.5 font-mono">{{ formatScientific(cd.p_words) }}</td>
                          <td class="px-2 py-1.5 font-mono">{{ formatScientific(cd.p_total_raw) }}</td>
                          <td class="px-2 py-1.5 font-mono font-bold" :class="cd.cluster === calc.new_cluster ? 'text-indigo-700' : ''">
                            {{ cd.p_normalized.toFixed(6) }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <!-- ===== DETAILED FORMULA WITH NUMBERS for chosen cluster ===== -->
                  <div class="mt-3 bg-white border border-indigo-200 rounded-lg p-4 space-y-3">
                    <p class="text-xs font-semibold text-indigo-800">
                      📝 Full Calculation for Chosen Cluster z={{ calc.new_cluster }}
                    </p>

                    <!-- Step 1: p(z) with actual numbers -->
                    <div class="bg-slate-50 rounded-lg px-3 py-2">
                      <p class="text-xs font-semibold text-slate-700 mb-1">Step 1: Cluster Popularity — p(z={{ calc.new_cluster }})</p>
                      <p class="text-xs font-mono text-slate-700">
                        p(z) = (m<sub>z</sub> + α) / (D − 1 + K × α)
                      </p>
                      <p class="text-xs font-mono text-indigo-700 mt-1">
                        p(z={{ calc.new_cluster }}) = {{ calc.cluster_details[calc.new_cluster]?.p_cluster_formula }}
                        = <b>{{ calc.cluster_details[calc.new_cluster]?.p_cluster.toFixed(6) }}</b>
                      </p>
                    </div>

                    <!-- Step 2: p(w|z) with actual numbers per word -->
                    <div class="bg-slate-50 rounded-lg px-3 py-2">
                      <p class="text-xs font-semibold text-slate-700 mb-1">Step 2: Word Likelihood — p(w|z={{ calc.new_cluster }})</p>
                      <p class="text-xs text-slate-500 mb-2">
                        For each word <i>w</i> in the document, compute 
                        (n<sub>z,w</sub> + β + j) / (n<sub>z</sub> + V×β + j) and multiply all factors together.
                      </p>

                      <!-- Per-word factor table -->
                      <div 
                        v-for="wd in calc.cluster_details[calc.new_cluster]?.word_details || []"
                        :key="wd.word"
                        class="mb-2"
                      >
                        <p class="text-xs font-medium text-slate-600 mb-1">
                          Word "<span class="text-indigo-700">{{ wd.word }}</span>" — 
                          appears {{ wd.count_in_doc }}× in doc, 
                          n<sub>z,w</sub> = {{ wd.n_z_w }} in cluster
                        </p>
                        <table class="w-full text-xs border border-slate-200 rounded">
                          <thead class="bg-slate-100">
                            <tr>
                              <th class="px-2 py-1 text-left">j</th>
                              <th class="px-2 py-1 text-left">Formula</th>
                              <th class="px-2 py-1 text-left">Numerator</th>
                              <th class="px-2 py-1 text-left">Denominator</th>
                              <th class="px-2 py-1 text-left">Result</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="f in wd.factors" :key="f.j" class="border-t border-slate-100">
                              <td class="px-2 py-1">{{ f.j }}</td>
                              <td class="px-2 py-1 font-mono text-slate-500">{{ f.formula }}</td>
                              <td class="px-2 py-1 font-mono">{{ f.numerator }}</td>
                              <td class="px-2 py-1 font-mono">{{ f.denominator }}</td>
                              <td class="px-2 py-1 font-mono font-medium text-indigo-700">{{ f.result.toFixed(8) }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>

                      <!-- p(w|z) result -->
                      <p class="text-xs font-mono text-slate-700 mt-2">
                        p(w|z={{ calc.new_cluster }}) = <span class="text-slate-400">{{ calc.cluster_details[calc.new_cluster]?.p_words_formula }}</span>
                      </p>
                      <p class="text-xs font-mono text-indigo-700">
                        p(w|z={{ calc.new_cluster }}) = <b>{{ formatScientific(calc.cluster_details[calc.new_cluster]?.p_words || 0) }}</b>
                      </p>
                    </div>

                    <!-- Step 3: Final result -->
                    <div class="bg-indigo-50 rounded-lg px-3 py-2 border border-indigo-100">
                      <p class="text-xs font-semibold text-slate-700 mb-1">Step 3: Combined Score</p>
                      <p class="text-xs font-mono text-slate-700">
                        p(z={{ calc.new_cluster }}|d) ∝ p(z) × p(w|z)
                        = {{ calc.cluster_details[calc.new_cluster]?.p_cluster.toFixed(6) }}
                        × {{ formatScientific(calc.cluster_details[calc.new_cluster]?.p_words || 0) }}
                        = <b class="text-indigo-700">{{ formatScientific(calc.cluster_details[calc.new_cluster]?.p_total_raw || 0) }}</b>
                      </p>
                      <p class="text-xs font-mono text-indigo-800 mt-1">
                        After normalization: <b>p(z={{ calc.new_cluster }}|d) = {{ calc.cluster_details[calc.new_cluster]?.p_normalized.toFixed(6) }}</b>
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- ==================== TOPICS OVERVIEW TAB ==================== -->
    <div v-show="activeTab === 'topics'" class="space-y-4">
      <div 
        v-for="topic in results.topics" 
        :key="topic.topic_label"
        class="bg-white rounded-xl shadow-sm border border-slate-200 p-5 hover:shadow-md transition-shadow"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3">
            <span class="inline-flex items-center justify-center w-9 h-9 rounded-full bg-indigo-100 text-indigo-700 text-sm font-bold">
              {{ topic.topic_label }}
            </span>
            <div>
              <h3 class="text-sm font-semibold text-slate-800">Topic {{ topic.topic_label }}</h3>
              <p class="text-xs text-slate-500">{{ topic.doc_count }} documents</p>
            </div>
          </div>
          <button
            @click="filterByTopic(topic.topic_label)"
            class="text-xs px-3 py-1.5 text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg font-medium transition-colors"
          >
            View Docs →
          </button>
        </div>

        <div class="w-full bg-slate-100 rounded-full h-2 mb-3">
          <div 
            class="bg-gradient-to-r from-indigo-500 to-cyan-400 h-2 rounded-full transition-all duration-500"
            :style="{ width: (topic.doc_count / maxDocCount * 100) + '%' }"
          ></div>
        </div>

        <div class="flex flex-wrap gap-2">
          <span 
            v-for="word in topic.top_words" 
            :key="word"
            class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
          >
            {{ word }}
            <span v-if="topic.word_scores[word]" class="ml-1 text-slate-400">
              {{ (topic.word_scores[word] * 100).toFixed(1) }}%
            </span>
          </span>
        </div>
      </div>
    </div>

    <!-- ==================== DOCUMENT CLUSTERS TAB ==================== -->
    <div v-show="activeTab === 'documents'">
      <div v-if="selectedTopicFilter !== null" class="mb-4 flex items-center gap-2 text-sm">
        <span class="text-slate-500">Filtered by:</span>
        <span class="inline-flex items-center gap-1.5 px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full font-medium">
          Topic {{ selectedTopicFilter }}
          <button @click="clearFilter" class="hover:text-indigo-900 focus:outline-none">&times;</button>
        </span>
        <span class="text-slate-400">({{ filteredDocuments.length }} documents)</span>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm text-left text-slate-500">
            <thead class="text-xs text-slate-700 uppercase bg-slate-50 border-b border-slate-200">
              <tr>
                <th scope="col" class="px-4 py-4 w-14">#</th>
                <th scope="col" class="px-4 py-4 w-20">Topic</th>
                <th scope="col" class="px-4 py-4">Original Text</th>
                <th scope="col" class="px-4 py-4">Preprocessed</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="doc in filteredDocuments" 
                :key="doc.doc_index" 
                class="bg-white border-b hover:bg-slate-50 transition-colors"
              >
                <td class="px-4 py-3 font-medium text-slate-900">{{ doc.doc_index }}</td>
                <td class="px-4 py-3">
                  <span class="inline-flex items-center justify-center w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold">
                    {{ doc.topic_id }}
                  </span>
                </td>
                <td class="px-4 py-3 text-slate-600 max-w-xs truncate" :title="doc.original_text">
                  {{ doc.original_text }}
                </td>
                <td class="px-4 py-3 italic text-slate-400 max-w-xs truncate" :title="doc.preprocessed">
                  {{ doc.preprocessed }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!filteredDocuments.length" class="p-8 text-center text-slate-400">
          No documents to display.
        </div>
      </div>
    </div>

  </div>
</template>
