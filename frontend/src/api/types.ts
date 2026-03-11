export interface ResourceState {
  current_value: number
  production_rate: number
}

export interface GeneratorState {
  owned: number
  cost_next: number
  production_per_sec: number
}

export interface UpgradeState {
  purchased: boolean
  cost: number
  affordable: boolean
}

export interface PrestigeState {
  available_currency: number
  formula_preview: string
}

export interface AchievementState {
  id: string
  name: string
  unlocked: boolean
}

export interface SessionState {
  session_id: string
  game_id: string
  elapsed_time: number
  resources: Record<string, ResourceState>
  generators: Record<string, GeneratorState>
  upgrades: Record<string, UpgradeState>
  prestige: PrestigeState | null
  achievements: AchievementState[]
}

export interface GameSummary {
  id: string
  name: string
  node_count: number
  edge_count: number
  bundled: boolean
}

export interface PurchaseStep {
  time: number
  node_id: string
  cost: number
  count: number
}

export interface TimelineEntry {
  time: number
  production_rate: number
}

export interface AutoOptimizeResponse {
  purchases: PurchaseStep[]
  timeline: TimelineEntry[]
  final_production: number
  final_balance: number
}

export interface AnalysisResult {
  game_name: string
  simulation_time: number
  dead_upgrades: Array<{ upgrade_id: string; reason: string; cost?: number }>
  progression_walls: Array<{ reason: string; severity?: string }>
  dominant_strategy: { dominant_gen: string | null; ratio: number; productions: Record<string, number> } | null
  sensitivity: Array<{ perturbation_pct: number; final_production: number; final_balance: number }>
  optimizer_result: {
    purchases: PurchaseStep[]
    timeline: TimelineEntry[]
    final_production: number
    final_balance: number
    final_time: number
  } | null
}

export interface CompareResult {
  baseline: { final_production: number }
  variants: Record<string, { final_production: number; ratio_vs_baseline: number }>
}

export interface ApiError {
  error: string
  detail: string
  status: number
}

export type OptimizerType = 'greedy' | 'beam' | 'mcts' | 'bnb'
