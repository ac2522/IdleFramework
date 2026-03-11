import type { Node, Edge } from '@xyflow/react'

// -- Node data types for each of 16 node types --

interface NodeDataBase {
  label: string
  nodeType: string
  tags: string[]
  activation_mode: string
  pull_mode: string
  cooldown_time: number | null
  [key: string]: unknown
}

export interface ResourceNodeData extends NodeDataBase {
  nodeType: 'resource'
  name: string
  initial_value: number
}

export interface GeneratorNodeData extends NodeDataBase {
  nodeType: 'generator'
  name: string
  base_production: number
  cost_base: number
  cost_growth_rate: number
  cycle_time: number
}

export interface NestedGeneratorNodeData extends NodeDataBase {
  nodeType: 'nested_generator'
  name: string
  target_generator: string
  production_rate: number
  cost_base: number
  cost_growth_rate: number
}

export interface UpgradeNodeData extends NodeDataBase {
  nodeType: 'upgrade'
  name: string
  upgrade_type: 'multiplicative' | 'additive' | 'percentage'
  magnitude: number
  cost: number
  target: string
  stacking_group: string
  duration: number | null
}

export interface PrestigeLayerNodeData extends NodeDataBase {
  nodeType: 'prestige_layer'
  name: string
  formula_expr: string
  layer_index: number
  reset_scope: string[]
  persistence_scope: string[]
  bonus_type: 'multiplicative' | 'additive' | 'percentage'
}

export interface SacrificeNodeData extends NodeDataBase {
  nodeType: 'sacrifice'
  name: string
  formula_expr: string
  reset_scope: string[]
  bonus_type: 'multiplicative' | 'additive' | 'percentage'
}

export interface AchievementNodeData extends NodeDataBase {
  nodeType: 'achievement'
  name: string
  condition_type: string
  targets: Array<{ node_id: string; property: string; threshold: number }>
  logic: string
  bonus: Record<string, unknown> | null
  permanent: boolean
}

export interface ManagerNodeData extends NodeDataBase {
  nodeType: 'manager'
  name: string
  target: string
  automation_type: 'collect' | 'buy' | 'activate'
}

export interface ConverterNodeData extends NodeDataBase {
  nodeType: 'converter'
  name: string
  inputs: Array<{ resource: string; amount: number }>
  outputs: Array<{ resource: string; amount: number }>
  rate: number
}

export interface ProbabilityNodeData extends NodeDataBase {
  nodeType: 'probability'
  name: string
  expected_value: number
  variance: number
  crit_chance: number
  crit_multiplier: number
}

export interface EndConditionNodeData extends NodeDataBase {
  nodeType: 'end_condition'
  name: string
  condition_type: string
  targets: Array<{ node_id: string; property: string; threshold: number }>
  logic: string
}

export interface UnlockGateNodeData extends NodeDataBase {
  nodeType: 'unlock_gate'
  name: string
  condition_type: string
  targets: Array<{ node_id: string; property: string; threshold: number }>
  prerequisites: string[]
  logic: string
  permanent: boolean
}

export interface ChoiceGroupNodeData extends NodeDataBase {
  nodeType: 'choice_group'
  name: string
  options: string[]
  max_selections: number
  respeccable: boolean
  respec_cost: number | null
}

export interface RegisterNodeData extends NodeDataBase {
  nodeType: 'register'
  name: string
  formula_expr: string
  input_labels: Array<Record<string, string>>
}

export interface GateNodeData extends NodeDataBase {
  nodeType: 'gate'
  name: string
  mode: 'deterministic' | 'probabilistic'
  weights: number[] | null
  probabilities: number[] | null
}

export interface QueueNodeData extends NodeDataBase {
  nodeType: 'queue'
  name: string
  delay: number
  capacity: number | null
}

export type EditorNodeData =
  | ResourceNodeData
  | GeneratorNodeData
  | NestedGeneratorNodeData
  | UpgradeNodeData
  | PrestigeLayerNodeData
  | SacrificeNodeData
  | AchievementNodeData
  | ManagerNodeData
  | ConverterNodeData
  | ProbabilityNodeData
  | EndConditionNodeData
  | UnlockGateNodeData
  | ChoiceGroupNodeData
  | RegisterNodeData
  | GateNodeData
  | QueueNodeData

export type EditorNode = Node<EditorNodeData>
export type EditorEdge = Edge<{ edgeType: string; rate?: number; formula?: string; condition?: string }>

// -- Edge type constants --

export const RESOURCE_EDGE_TYPES = ['resource_flow', 'consumption', 'production_target'] as const
export const STATE_EDGE_TYPES = ['state_modifier', 'activator', 'trigger', 'unlock_dependency', 'upgrade_target'] as const
export const ALL_EDGE_TYPES = [...RESOURCE_EDGE_TYPES, ...STATE_EDGE_TYPES] as const

// -- Node color map --

export const NODE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  resource:         { bg: 'bg-blue-50 dark:bg-blue-950',    border: 'border-blue-400',   text: 'text-blue-800 dark:text-blue-200' },
  generator:        { bg: 'bg-green-50 dark:bg-green-950',  border: 'border-green-400',  text: 'text-green-800 dark:text-green-200' },
  nested_generator: { bg: 'bg-green-50 dark:bg-green-950',  border: 'border-green-600',  text: 'text-green-800 dark:text-green-200' },
  upgrade:          { bg: 'bg-orange-50 dark:bg-orange-950', border: 'border-orange-400', text: 'text-orange-800 dark:text-orange-200' },
  manager:          { bg: 'bg-orange-50 dark:bg-orange-950', border: 'border-orange-600', text: 'text-orange-800 dark:text-orange-200' },
  prestige_layer:   { bg: 'bg-purple-50 dark:bg-purple-950', border: 'border-purple-400', text: 'text-purple-800 dark:text-purple-200' },
  sacrifice:        { bg: 'bg-purple-50 dark:bg-purple-950', border: 'border-purple-600', text: 'text-purple-800 dark:text-purple-200' },
  achievement:      { bg: 'bg-yellow-50 dark:bg-yellow-950', border: 'border-yellow-400', text: 'text-yellow-800 dark:text-yellow-200' },
  end_condition:    { bg: 'bg-yellow-50 dark:bg-yellow-950', border: 'border-yellow-600', text: 'text-yellow-800 dark:text-yellow-200' },
  unlock_gate:      { bg: 'bg-teal-50 dark:bg-teal-950',   border: 'border-teal-400',   text: 'text-teal-800 dark:text-teal-200' },
  gate:             { bg: 'bg-teal-50 dark:bg-teal-950',   border: 'border-teal-600',   text: 'text-teal-800 dark:text-teal-200' },
  choice_group:     { bg: 'bg-teal-50 dark:bg-teal-950',   border: 'border-teal-500',   text: 'text-teal-800 dark:text-teal-200' },
  probability:      { bg: 'bg-pink-50 dark:bg-pink-950',   border: 'border-pink-400',   text: 'text-pink-800 dark:text-pink-200' },
  register:         { bg: 'bg-slate-50 dark:bg-slate-900', border: 'border-slate-400',  text: 'text-slate-800 dark:text-slate-200' },
  queue:            { bg: 'bg-slate-50 dark:bg-slate-900', border: 'border-slate-600',  text: 'text-slate-800 dark:text-slate-200' },
  converter:        { bg: 'bg-amber-50 dark:bg-amber-950', border: 'border-amber-400',  text: 'text-amber-800 dark:text-amber-200' },
}

// -- Default data factories for each node type --

export function nextNodeId(): string {
  return `node_${crypto.randomUUID().slice(0, 8)}`
}

export function defaultNodeData(nodeType: string, id: string): EditorNodeData {
  const base = { label: '', tags: [] as string[], activation_mode: 'automatic', pull_mode: 'pull_any', cooldown_time: null }

  switch (nodeType) {
    case 'resource':
      return { ...base, nodeType: 'resource', name: id, initial_value: 0 }
    case 'generator':
      return { ...base, nodeType: 'generator', name: id, base_production: 1, cost_base: 10, cost_growth_rate: 1.07, cycle_time: 1 }
    case 'nested_generator':
      return { ...base, nodeType: 'nested_generator', name: id, target_generator: '', production_rate: 1, cost_base: 100, cost_growth_rate: 1.15 }
    case 'upgrade':
      return { ...base, nodeType: 'upgrade', name: id, upgrade_type: 'multiplicative', magnitude: 2, cost: 100, target: '', stacking_group: '', duration: null }
    case 'prestige_layer':
      return { ...base, nodeType: 'prestige_layer', name: id, formula_expr: 'floor(balance / 1e6)', layer_index: 0, reset_scope: [], persistence_scope: [], bonus_type: 'multiplicative' }
    case 'sacrifice':
      return { ...base, nodeType: 'sacrifice', name: id, formula_expr: 'floor(balance / 1e6)', reset_scope: [], bonus_type: 'multiplicative' }
    case 'achievement':
      return { ...base, nodeType: 'achievement', name: id, condition_type: 'single_threshold', targets: [], logic: 'and', bonus: null, permanent: true }
    case 'manager':
      return { ...base, nodeType: 'manager', name: id, target: '', automation_type: 'collect' }
    case 'converter':
      return { ...base, nodeType: 'converter', name: id, inputs: [], outputs: [], rate: 1 }
    case 'probability':
      return { ...base, nodeType: 'probability', name: id, expected_value: 1, variance: 0, crit_chance: 0, crit_multiplier: 1 }
    case 'end_condition':
      return { ...base, nodeType: 'end_condition', name: id, condition_type: 'single_threshold', targets: [], logic: 'and' }
    case 'unlock_gate':
      return { ...base, nodeType: 'unlock_gate', name: id, condition_type: 'single_threshold', targets: [], prerequisites: [], logic: 'and', permanent: true }
    case 'choice_group':
      return { ...base, nodeType: 'choice_group', name: id, options: [], max_selections: 1, respeccable: false, respec_cost: null }
    case 'register':
      return { ...base, nodeType: 'register', name: id, formula_expr: '0', input_labels: [] }
    case 'gate':
      return { ...base, nodeType: 'gate', name: id, mode: 'deterministic', weights: null, probabilities: null }
    case 'queue':
      return { ...base, nodeType: 'queue', name: id, delay: 1, capacity: null }
    default:
      return { ...base, nodeType: 'resource', name: id, initial_value: 0 }
  }
}
