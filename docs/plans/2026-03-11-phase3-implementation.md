# Phase 3: React Flow Node Editor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Visual game designer using React Flow where users drag-and-drop all 16 node types, connect edges, edit properties, and see live analysis feedback.

**Architecture:** New `/editor` route with three-panel layout (palette, canvas, properties). React Flow v12 canvas with 16 custom node components + 2 custom edge types. Graph ↔ GameDefinition conversion layer with dagre auto-layout. Live analysis via debounced REST polling to existing `POST /analysis/run`.

**Tech Stack:** @xyflow/react v12, @dagrejs/dagre, React 19, TypeScript 5, Tailwind CSS 4, Vitest (frontend tests)

---

## Reference Files

Before starting, read these files to understand existing patterns:

- **Node model:** `src/idleframework/model/nodes.py` — All 16 node types with fields
- **Edge model:** `src/idleframework/model/edges.py` — Edge type with 8 edge_type variants
- **Game model:** `src/idleframework/model/game.py` — GameDefinition with validation
- **Frontend patterns:** `frontend/src/components/game/GeneratorCard.tsx` — Tailwind component style
- **API client:** `frontend/src/api/client.ts` — apiFetch pattern
- **Types:** `frontend/src/api/types.ts` — TypeScript interface patterns
- **Nav:** `frontend/src/components/layout/Nav.tsx` — Navigation pattern
- **App router:** `frontend/src/App.tsx` — Route registration
- **Fixture:** `tests/fixtures/minicap.json` — Example game JSON

---

### Task 1: React Flow Setup + Canvas Shell

**Files:**
- Modify: `frontend/package.json` (add @xyflow/react, @dagrejs/dagre)
- Create: `frontend/src/pages/EditorPage.tsx`
- Modify: `frontend/src/App.tsx` (add /editor route)
- Modify: `frontend/src/components/layout/Nav.tsx` (add Editor link)

**Step 1: Install dependencies**

```bash
cd frontend && npm install @xyflow/react @dagrejs/dagre && npm install -D @types/dagre
```

**Step 2: Create EditorPage with empty React Flow canvas**

Create `frontend/src/pages/EditorPage.tsx`:

```tsx
import { useCallback, useState } from 'react'
import {
  ReactFlow,
  ReactFlowProvider,
  Controls,
  MiniMap,
  Background,
  addEdge,
  useNodesState,
  useEdgesState,
  type OnConnect,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

function EditorCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  const onConnect: OnConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  )

  return (
    <div className="flex h-[calc(100vh-57px)]">
      {/* Palette placeholder */}
      <aside className="w-56 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 overflow-y-auto">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
          Node Palette
        </h3>
        <p className="text-xs text-gray-400">Drag nodes here...</p>
      </aside>

      {/* Canvas */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
        >
          <Controls />
          <MiniMap />
          <Background />
        </ReactFlow>
      </div>

      {/* Properties placeholder */}
      <aside className="w-72 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 overflow-y-auto">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
          Properties
        </h3>
        <p className="text-xs text-gray-400">Select a node to edit...</p>
      </aside>
    </div>
  )
}

export default function EditorPage() {
  return (
    <ReactFlowProvider>
      <EditorCanvas />
    </ReactFlowProvider>
  )
}
```

**Step 3: Add route and nav link**

In `frontend/src/App.tsx`, add:
```tsx
import EditorPage from './pages/EditorPage'
// In Routes, add:
<Route path="/editor" element={<EditorPage />} />
```

In `frontend/src/components/layout/Nav.tsx`, add an Editor NavLink after Analyze:
```tsx
<NavLink to="/editor" className={linkClass}>Editor</NavLink>
```

**Step 4: Verify it compiles and renders**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: React Flow canvas shell with three-panel editor layout"
```

---

### Task 2: Editor Type Definitions

**Files:**
- Create: `frontend/src/editor/types.ts`

These types bridge between React Flow's node/edge model and our GameDefinition model.

**Step 1: Create editor type definitions**

Create `frontend/src/editor/types.ts`:

```tsx
import type { Node, Edge } from '@xyflow/react'

// -- Node data types for each of 16 node types --

interface NodeDataBase {
  label: string
  nodeType: string
  tags: string[]
  activation_mode: string
  pull_mode: string
  cooldown_time: number | null
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

let _nodeCounter = 0
export function nextNodeId(): string {
  return `node_${++_nodeCounter}`
}

export function resetNodeCounter(max = 0): void {
  _nodeCounter = max
}

export function defaultNodeData(nodeType: string, id: string): EditorNodeData {
  const base = { label: '', tags: [], activation_mode: 'automatic', pull_mode: 'pull_any', cooldown_time: null }

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
```

**Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/editor/
git commit -m "feat: editor type definitions for all 16 node types"
```

---

### Task 3: Custom Node Components (all 16)

**Files:**
- Create: `frontend/src/editor/nodes/BaseNode.tsx`
- Create: `frontend/src/editor/nodes/ResourceNode.tsx`
- Create: `frontend/src/editor/nodes/GeneratorNode.tsx`
- Create: `frontend/src/editor/nodes/NestedGeneratorNode.tsx`
- Create: `frontend/src/editor/nodes/UpgradeNode.tsx`
- Create: `frontend/src/editor/nodes/PrestigeLayerNode.tsx`
- Create: `frontend/src/editor/nodes/SacrificeNode.tsx`
- Create: `frontend/src/editor/nodes/AchievementNode.tsx`
- Create: `frontend/src/editor/nodes/ManagerNode.tsx`
- Create: `frontend/src/editor/nodes/ConverterNode.tsx`
- Create: `frontend/src/editor/nodes/ProbabilityNode.tsx`
- Create: `frontend/src/editor/nodes/EndConditionNode.tsx`
- Create: `frontend/src/editor/nodes/UnlockGateNode.tsx`
- Create: `frontend/src/editor/nodes/ChoiceGroupNode.tsx`
- Create: `frontend/src/editor/nodes/RegisterNode.tsx`
- Create: `frontend/src/editor/nodes/GateNode.tsx`
- Create: `frontend/src/editor/nodes/QueueNode.tsx`
- Create: `frontend/src/editor/nodes/index.ts`

**Step 1: Create shared BaseNode wrapper**

Create `frontend/src/editor/nodes/BaseNode.tsx`:

```tsx
import { Handle, Position } from '@xyflow/react'
import { NODE_COLORS } from '../types'

interface BaseNodeProps {
  nodeType: string
  name: string
  selected?: boolean
  children?: React.ReactNode
}

export default function BaseNode({ nodeType, name, selected, children }: BaseNodeProps) {
  const colors = NODE_COLORS[nodeType] ?? NODE_COLORS.resource

  return (
    <div
      className={`${colors.bg} border-2 ${colors.border} rounded-lg p-3 min-w-48 shadow-sm ${
        selected ? 'ring-2 ring-blue-500' : ''
      }`}
    >
      <Handle type="target" position={Position.Left} className="!w-3 !h-3" />
      <div className={`text-xs font-medium uppercase tracking-wide mb-1 opacity-60 ${colors.text}`}>
        {nodeType.replace(/_/g, ' ')}
      </div>
      <div className={`font-semibold ${colors.text}`}>{name || '(unnamed)'}</div>
      {children && <div className={`text-sm mt-1 opacity-75 ${colors.text}`}>{children}</div>}
      <Handle type="source" position={Position.Right} className="!w-3 !h-3" />
    </div>
  )
}
```

**Step 2: Create all 16 node components**

Each follows the same pattern: receives `NodeProps<EditorNode>`, renders `BaseNode` with type-specific summary fields. Here are all 16:

Create `frontend/src/editor/nodes/ResourceNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function ResourceNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'resource') return null
  return (
    <BaseNode nodeType="resource" name={data.name} selected={selected}>
      <div>Initial: {data.initial_value}</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/GeneratorNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function GeneratorNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'generator') return null
  return (
    <BaseNode nodeType="generator" name={data.name} selected={selected}>
      <div>{data.base_production}/cycle ({data.cycle_time}s)</div>
      <div>Cost: {data.cost_base} x {data.cost_growth_rate}^n</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/NestedGeneratorNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function NestedGeneratorNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'nested_generator') return null
  return (
    <BaseNode nodeType="nested_generator" name={data.name} selected={selected}>
      <div>Target: {data.target_generator || '(none)'}</div>
      <div>Rate: {data.production_rate}/s</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/UpgradeNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function UpgradeNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'upgrade') return null
  return (
    <BaseNode nodeType="upgrade" name={data.name} selected={selected}>
      <div>{data.upgrade_type} x{data.magnitude}</div>
      <div>Cost: {data.cost} | Target: {data.target || '(none)'}</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/PrestigeLayerNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function PrestigeLayerNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'prestige_layer') return null
  return (
    <BaseNode nodeType="prestige_layer" name={data.name} selected={selected}>
      <div>Layer {data.layer_index}</div>
      <div className="font-mono text-xs truncate">{data.formula_expr}</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/SacrificeNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function SacrificeNodeComponent({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'sacrifice') return null
  return (
    <BaseNode nodeType="sacrifice" name={data.name} selected={selected}>
      <div className="font-mono text-xs truncate">{data.formula_expr}</div>
      <div>{data.bonus_type}</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/AchievementNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function AchievementNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'achievement') return null
  return (
    <BaseNode nodeType="achievement" name={data.name} selected={selected}>
      <div>{data.condition_type} ({data.targets.length} targets)</div>
      <div>{data.permanent ? 'Permanent' : 'Temporary'}</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/ManagerNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function ManagerNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'manager') return null
  return (
    <BaseNode nodeType="manager" name={data.name} selected={selected}>
      <div>{data.automation_type} | Target: {data.target || '(none)'}</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/ConverterNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function ConverterNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'converter') return null
  return (
    <BaseNode nodeType="converter" name={data.name} selected={selected}>
      <div>{data.inputs.length} in → {data.outputs.length} out</div>
      <div>Rate: {data.rate}/s</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/ProbabilityNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function ProbabilityNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'probability') return null
  return (
    <BaseNode nodeType="probability" name={data.name} selected={selected}>
      <div>EV: {data.expected_value}</div>
      {data.crit_chance > 0 && <div>Crit: {(data.crit_chance * 100).toFixed(0)}% x{data.crit_multiplier}</div>}
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/EndConditionNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function EndConditionNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'end_condition') return null
  return (
    <BaseNode nodeType="end_condition" name={data.name} selected={selected}>
      <div>{data.condition_type} ({data.targets.length} targets)</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/UnlockGateNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function UnlockGateNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'unlock_gate') return null
  return (
    <BaseNode nodeType="unlock_gate" name={data.name} selected={selected}>
      <div>{data.condition_type} ({data.targets.length} targets)</div>
      <div>{data.prerequisites.length} prerequisites</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/ChoiceGroupNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function ChoiceGroupNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'choice_group') return null
  return (
    <BaseNode nodeType="choice_group" name={data.name} selected={selected}>
      <div>{data.options.length} options (max {data.max_selections})</div>
      {data.respeccable && <div>Respeccable</div>}
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/RegisterNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function RegisterNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'register') return null
  return (
    <BaseNode nodeType="register" name={data.name} selected={selected}>
      <div className="font-mono text-xs truncate">{data.formula_expr}</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/GateNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function GateNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'gate') return null
  return (
    <BaseNode nodeType="gate" name={data.name} selected={selected}>
      <div>{data.mode}</div>
    </BaseNode>
  )
}
```

Create `frontend/src/editor/nodes/QueueNode.tsx`:
```tsx
import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function QueueNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'queue') return null
  return (
    <BaseNode nodeType="queue" name={data.name} selected={selected}>
      <div>Delay: {data.delay}s</div>
      {data.capacity != null && <div>Capacity: {data.capacity}</div>}
    </BaseNode>
  )
}
```

**Step 3: Create nodeTypes registry**

Create `frontend/src/editor/nodes/index.ts`:

```tsx
import type { NodeTypes } from '@xyflow/react'
import ResourceNode from './ResourceNode'
import GeneratorNode from './GeneratorNode'
import NestedGeneratorNode from './NestedGeneratorNode'
import UpgradeNode from './UpgradeNode'
import PrestigeLayerNode from './PrestigeLayerNode'
import SacrificeNodeComponent from './SacrificeNode'
import AchievementNode from './AchievementNode'
import ManagerNode from './ManagerNode'
import ConverterNode from './ConverterNode'
import ProbabilityNode from './ProbabilityNode'
import EndConditionNode from './EndConditionNode'
import UnlockGateNode from './UnlockGateNode'
import ChoiceGroupNode from './ChoiceGroupNode'
import RegisterNode from './RegisterNode'
import GateNode from './GateNode'
import QueueNode from './QueueNode'

export const editorNodeTypes: NodeTypes = {
  resource: ResourceNode,
  generator: GeneratorNode,
  nested_generator: NestedGeneratorNode,
  upgrade: UpgradeNode,
  prestige_layer: PrestigeLayerNode,
  sacrifice: SacrificeNodeComponent,
  achievement: AchievementNode,
  manager: ManagerNode,
  converter: ConverterNode,
  probability: ProbabilityNode,
  end_condition: EndConditionNode,
  unlock_gate: UnlockGateNode,
  choice_group: ChoiceGroupNode,
  register: RegisterNode,
  gate: GateNode,
  queue: QueueNode,
}
```

**Step 4: Wire nodeTypes into EditorPage**

In `frontend/src/pages/EditorPage.tsx`, import and pass `editorNodeTypes`:
```tsx
import { editorNodeTypes } from '../editor/nodes'
// In <ReactFlow>:
<ReactFlow nodeTypes={editorNodeTypes} ... />
```

**Step 5: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 6: Commit**

```bash
git add frontend/src/editor/
git commit -m "feat: custom node components for all 16 node types"
```

---

### Task 4: Custom Edge Types (resource vs state)

**Files:**
- Create: `frontend/src/editor/edges/ResourceEdge.tsx`
- Create: `frontend/src/editor/edges/StateEdge.tsx`
- Create: `frontend/src/editor/edges/index.ts`
- Modify: `frontend/src/pages/EditorPage.tsx` (register edge types)

**Step 1: Create resource edge (solid)**

Create `frontend/src/editor/edges/ResourceEdge.tsx`:

```tsx
import { BaseEdge, getBezierPath, EdgeLabelRenderer, type EdgeProps } from '@xyflow/react'

export default function ResourceEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, id, label } = props
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  })

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={{ stroke: '#3b82f6', strokeWidth: 2 }} />
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="bg-white dark:bg-gray-800 text-xs px-1.5 py-0.5 rounded border border-blue-300 dark:border-blue-600 text-blue-700 dark:text-blue-300 nopan"
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}
```

**Step 2: Create state edge (dashed)**

Create `frontend/src/editor/edges/StateEdge.tsx`:

```tsx
import { BaseEdge, getBezierPath, EdgeLabelRenderer, type EdgeProps } from '@xyflow/react'

export default function StateEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, id, label } = props
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  })

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={{ stroke: '#a855f7', strokeWidth: 2, strokeDasharray: '6 3' }} />
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="bg-white dark:bg-gray-800 text-xs px-1.5 py-0.5 rounded border border-purple-300 dark:border-purple-600 text-purple-700 dark:text-purple-300 nopan"
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}
```

**Step 3: Create edge types index**

Create `frontend/src/editor/edges/index.ts`:

```tsx
import type { EdgeTypes } from '@xyflow/react'
import ResourceEdge from './ResourceEdge'
import StateEdge from './StateEdge'

export const editorEdgeTypes: EdgeTypes = {
  resource: ResourceEdge,
  state: StateEdge,
}
```

**Step 4: Wire into EditorPage**

In `frontend/src/pages/EditorPage.tsx`, import and pass:
```tsx
import { editorEdgeTypes } from '../editor/edges'
// In <ReactFlow>:
<ReactFlow edgeTypes={editorEdgeTypes} ... />
```

**Step 5: Verify and commit**

Run: `cd frontend && npx tsc --noEmit`

```bash
git add frontend/src/editor/edges/ frontend/src/pages/EditorPage.tsx
git commit -m "feat: custom edge types — solid resource, dashed state"
```

---

### Task 5: Node Palette with Drag-and-Drop

**Files:**
- Create: `frontend/src/editor/NodePalette.tsx`
- Modify: `frontend/src/pages/EditorPage.tsx` (replace palette placeholder, add DnD handlers)

**Step 1: Create NodePalette component**

Create `frontend/src/editor/NodePalette.tsx`:

```tsx
import { NODE_COLORS } from './types'

interface PaletteCategory {
  label: string
  types: Array<{ type: string; name: string; description: string }>
}

const CATEGORIES: PaletteCategory[] = [
  {
    label: 'Resources',
    types: [
      { type: 'resource', name: 'Resource', description: 'Stores a value (e.g. gold, mana)' },
    ],
  },
  {
    label: 'Producers',
    types: [
      { type: 'generator', name: 'Generator', description: 'Produces resources over time' },
      { type: 'nested_generator', name: 'Nested Gen', description: 'Generates other generators' },
      { type: 'converter', name: 'Converter', description: 'Converts inputs to outputs' },
    ],
  },
  {
    label: 'Modifiers',
    types: [
      { type: 'upgrade', name: 'Upgrade', description: 'Boosts production or efficiency' },
      { type: 'manager', name: 'Manager', description: 'Automates actions' },
    ],
  },
  {
    label: 'Meta',
    types: [
      { type: 'prestige_layer', name: 'Prestige', description: 'Reset layer for prestige currency' },
      { type: 'sacrifice', name: 'Sacrifice', description: 'Sacrifice resources for bonuses' },
      { type: 'achievement', name: 'Achievement', description: 'Unlocked by conditions' },
      { type: 'end_condition', name: 'End Condition', description: 'Win/lose condition' },
    ],
  },
  {
    label: 'Control',
    types: [
      { type: 'unlock_gate', name: 'Unlock Gate', description: 'Gates content behind conditions' },
      { type: 'gate', name: 'Gate', description: 'Routes flow deterministically or randomly' },
      { type: 'choice_group', name: 'Choice Group', description: 'Player picks from options' },
      { type: 'probability', name: 'Probability', description: 'Random outcomes with EV' },
    ],
  },
  {
    label: 'Advanced',
    types: [
      { type: 'register', name: 'Register', description: 'Computed value from formula' },
      { type: 'queue', name: 'Queue', description: 'Delays resource flow' },
    ],
  },
]

function onDragStart(event: React.DragEvent, nodeType: string) {
  event.dataTransfer.setData('application/reactflow', nodeType)
  event.dataTransfer.effectAllowed = 'move'
}

export default function NodePalette() {
  return (
    <aside className="w-56 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3 overflow-y-auto">
      <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
        Node Palette
      </h3>
      {CATEGORIES.map((cat) => (
        <div key={cat.label} className="mb-4">
          <h4 className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase mb-1.5">{cat.label}</h4>
          <div className="flex flex-col gap-1.5">
            {cat.types.map(({ type, name, description }) => {
              const colors = NODE_COLORS[type] ?? NODE_COLORS.resource
              return (
                <div
                  key={type}
                  draggable
                  onDragStart={(e) => onDragStart(e, type)}
                  className={`${colors.bg} border ${colors.border} rounded-md px-2.5 py-1.5 cursor-grab active:cursor-grabbing`}
                  title={description}
                >
                  <div className={`text-sm font-medium ${colors.text}`}>{name}</div>
                  <div className="text-xs opacity-60 truncate">{description}</div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </aside>
  )
}
```

**Step 2: Add DnD handlers to EditorPage**

Update `frontend/src/pages/EditorPage.tsx` to handle drops. Replace the palette placeholder `<aside>` with `<NodePalette />` and add `onDrop`/`onDragOver` to `<ReactFlow>`:

```tsx
import { useReactFlow } from '@xyflow/react'
import NodePalette from '../editor/NodePalette'
import { defaultNodeData, nextNodeId } from '../editor/types'

// Inside EditorCanvas:
const { screenToFlowPosition } = useReactFlow()

const onDragOver = useCallback((event: React.DragEvent) => {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}, [])

const onDrop = useCallback(
  (event: React.DragEvent) => {
    event.preventDefault()
    const nodeType = event.dataTransfer.getData('application/reactflow')
    if (!nodeType) return

    const position = screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    })
    const id = nextNodeId()
    const newNode: Node = {
      id,
      type: nodeType,
      position,
      data: defaultNodeData(nodeType, id),
    }
    setNodes((nds) => [...nds, newNode])
  },
  [screenToFlowPosition, setNodes],
)

// In JSX, replace palette <aside> with:
<NodePalette />

// Add to <ReactFlow>:
onDrop={onDrop}
onDragOver={onDragOver}
```

**Step 3: Verify and commit**

Run: `cd frontend && npx tsc --noEmit`

```bash
git add frontend/src/editor/NodePalette.tsx frontend/src/pages/EditorPage.tsx
git commit -m "feat: node palette with drag-and-drop for all 16 types"
```

---

### Task 6: Graph ↔ GameDefinition Conversion

**Files:**
- Create: `frontend/src/editor/conversion.ts`

These are the core pure functions that convert between React Flow graph state and GameDefinition JSON. They must handle all 16 node types and all 8 edge types.

**Step 1: Create conversion functions**

Create `frontend/src/editor/conversion.ts`:

```tsx
import dagre from '@dagrejs/dagre'
import type { Node, Edge } from '@xyflow/react'
import {
  type EditorNodeData,
  type EditorNode,
  RESOURCE_EDGE_TYPES,
  resetNodeCounter,
} from './types'

// -- Game JSON types (matching Python GameDefinition) --

interface GameNode {
  id: string
  type: string
  [key: string]: unknown
}

interface GameEdge {
  id: string
  source: string
  target: string
  edge_type: string
  rate?: number | null
  formula?: string | null
  condition?: string | null
}

export interface GameDefinitionJSON {
  schema_version: string
  name: string
  description?: string
  nodes: GameNode[]
  edges: GameEdge[]
  stacking_groups: Record<string, string>
  time_unit?: string
}

// -- graphToGame: React Flow → GameDefinition JSON --

export function graphToGame(
  nodes: Node[],
  edges: Edge[],
  metadata: { name: string; description?: string; stacking_groups: Record<string, string> },
): GameDefinitionJSON {
  const gameNodes: GameNode[] = nodes.map((n) => {
    const data = n.data as EditorNodeData
    const { label: _label, nodeType, tags, activation_mode, pull_mode, cooldown_time, ...rest } = data
    return {
      id: n.id,
      type: nodeType,
      tags,
      activation_mode,
      pull_mode,
      ...(cooldown_time != null ? { cooldown_time } : {}),
      ...rest,
    }
  })

  const gameEdges: GameEdge[] = edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    edge_type: (e.data as Record<string, unknown>)?.edgeType as string ?? 'resource_flow',
    ...((e.data as Record<string, unknown>)?.rate != null ? { rate: (e.data as Record<string, unknown>).rate as number } : {}),
    ...((e.data as Record<string, unknown>)?.formula ? { formula: (e.data as Record<string, unknown>).formula as string } : {}),
    ...((e.data as Record<string, unknown>)?.condition ? { condition: (e.data as Record<string, unknown>).condition as string } : {}),
  }))

  return {
    schema_version: '1.0',
    name: metadata.name,
    ...(metadata.description ? { description: metadata.description } : {}),
    stacking_groups: metadata.stacking_groups,
    nodes: gameNodes,
    edges: gameEdges,
  }
}

// -- gameToGraph: GameDefinition JSON → React Flow nodes/edges with dagre layout --

export function gameToGraph(game: GameDefinitionJSON): { nodes: EditorNode[]; edges: Edge[] } {
  // Find max numeric suffix in node IDs to set counter
  let maxId = 0
  for (const n of game.nodes) {
    const match = n.id.match(/_(\d+)$/)
    if (match) maxId = Math.max(maxId, parseInt(match[1], 10))
  }
  resetNodeCounter(maxId)

  // Convert nodes
  const rfNodes: EditorNode[] = game.nodes.map((n) => {
    const { id, type, ...rest } = n
    return {
      id,
      type: type as string,
      position: { x: 0, y: 0 }, // will be set by dagre
      data: {
        label: (rest.name as string) ?? id,
        nodeType: type as string,
        tags: (rest.tags as string[]) ?? [],
        activation_mode: (rest.activation_mode as string) ?? 'automatic',
        pull_mode: (rest.pull_mode as string) ?? 'pull_any',
        cooldown_time: (rest.cooldown_time as number | null) ?? null,
        ...rest,
      } as EditorNodeData,
    }
  })

  // Convert edges
  const rfEdges: Edge[] = game.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: RESOURCE_EDGE_TYPES.includes(e.edge_type as typeof RESOURCE_EDGE_TYPES[number]) ? 'resource' : 'state',
    label: e.edge_type.replace(/_/g, ' '),
    data: {
      edgeType: e.edge_type,
      rate: e.rate ?? undefined,
      formula: e.formula ?? undefined,
      condition: e.condition ?? undefined,
    },
  }))

  // Apply dagre layout
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', nodesep: 60, ranksep: 120 })

  for (const node of rfNodes) {
    g.setNode(node.id, { width: 200, height: 80 })
  }
  for (const edge of rfEdges) {
    g.setEdge(edge.source, edge.target)
  }

  dagre.layout(g)

  for (const node of rfNodes) {
    const pos = g.node(node.id)
    if (pos) {
      node.position = { x: pos.x - 100, y: pos.y - 40 }
    }
  }

  return { nodes: rfNodes, edges: rfEdges }
}
```

**Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/editor/conversion.ts
git commit -m "feat: graph ↔ GameDefinition conversion with dagre auto-layout"
```

---

### Task 7: Property Panel

**Files:**
- Create: `frontend/src/editor/PropertyPanel.tsx`
- Create: `frontend/src/editor/FormulaField.tsx`
- Modify: `frontend/src/pages/EditorPage.tsx` (wire property panel)

**Step 1: Create FormulaField (textarea with live validation preview)**

Create `frontend/src/editor/FormulaField.tsx`:

```tsx
import { useState, useEffect, useRef } from 'react'

interface FormulaFieldProps {
  value: string
  onChange: (value: string) => void
  label: string
}

export default function FormulaField({ value, onChange, label }: FormulaFieldProps) {
  const [localValue, setLocalValue] = useState(value)
  const [validationMsg, setValidationMsg] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    setLocalValue(value)
  }, [value])

  const handleChange = (newValue: string) => {
    setLocalValue(newValue)

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      // Basic client-side validation: check balanced parens, no empty
      const trimmed = newValue.trim()
      if (!trimmed) {
        setValidationMsg('Formula cannot be empty')
      } else {
        const opens = (trimmed.match(/\(/g) || []).length
        const closes = (trimmed.match(/\)/g) || []).length
        if (opens !== closes) {
          setValidationMsg(`Unbalanced parentheses (${opens} open, ${closes} close)`)
        } else {
          setValidationMsg(null)
        }
      }
      onChange(newValue)
    }, 300)
  }

  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{label}</label>
      <textarea
        value={localValue}
        onChange={(e) => handleChange(e.target.value)}
        rows={2}
        className={`w-full font-mono text-sm rounded-md border px-2 py-1.5 bg-white dark:bg-gray-900 ${
          validationMsg
            ? 'border-red-400 dark:border-red-500'
            : 'border-gray-300 dark:border-gray-600'
        }`}
      />
      {validationMsg ? (
        <p className="text-xs text-red-500 mt-0.5">{validationMsg}</p>
      ) : (
        localValue.trim() && <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">Valid syntax</p>
      )}
    </div>
  )
}
```

**Step 2: Create PropertyPanel**

Create `frontend/src/editor/PropertyPanel.tsx`:

```tsx
import { useCallback } from 'react'
import type { Node } from '@xyflow/react'
import type { EditorNodeData } from './types'
import FormulaField from './FormulaField'

interface PropertyPanelProps {
  selectedNode: Node | null
  onUpdateNode: (nodeId: string, data: Partial<EditorNodeData>) => void
}

export default function PropertyPanel({ selectedNode, onUpdateNode }: PropertyPanelProps) {
  if (!selectedNode) {
    return (
      <aside className="w-72 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 overflow-y-auto">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
          Properties
        </h3>
        <p className="text-xs text-gray-400">Select a node to edit...</p>
      </aside>
    )
  }

  const data = selectedNode.data as EditorNodeData
  const nodeId = selectedNode.id

  const update = useCallback(
    (field: string, value: unknown) => {
      onUpdateNode(nodeId, { [field]: value } as Partial<EditorNodeData>)
    },
    [nodeId, onUpdateNode],
  )

  return (
    <aside className="w-72 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 overflow-y-auto">
      <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
        Properties — {data.nodeType.replace(/_/g, ' ')}
      </h3>

      <div className="flex flex-col gap-3">
        {/* Common: ID (read-only) and Name */}
        <Field label="ID" value={nodeId} readOnly />
        <Field label="Name" value={(data as Record<string, unknown>).name as string ?? ''} onChange={(v) => update('name', v)} />
        <TagsField tags={data.tags} onChange={(v) => update('tags', v)} />

        {/* Type-specific fields */}
        {data.nodeType === 'resource' && (
          <NumberField label="Initial Value" value={data.initial_value} onChange={(v) => update('initial_value', v)} />
        )}

        {data.nodeType === 'generator' && (
          <>
            <NumberField label="Base Production" value={data.base_production} onChange={(v) => update('base_production', v)} />
            <NumberField label="Cost Base" value={data.cost_base} onChange={(v) => update('cost_base', v)} />
            <NumberField label="Cost Growth Rate" value={data.cost_growth_rate} onChange={(v) => update('cost_growth_rate', v)} step={0.01} />
            <NumberField label="Cycle Time (s)" value={data.cycle_time} onChange={(v) => update('cycle_time', v)} step={0.1} />
          </>
        )}

        {data.nodeType === 'nested_generator' && (
          <>
            <Field label="Target Generator" value={data.target_generator} onChange={(v) => update('target_generator', v)} />
            <NumberField label="Production Rate" value={data.production_rate} onChange={(v) => update('production_rate', v)} />
            <NumberField label="Cost Base" value={data.cost_base} onChange={(v) => update('cost_base', v)} />
            <NumberField label="Cost Growth Rate" value={data.cost_growth_rate} onChange={(v) => update('cost_growth_rate', v)} step={0.01} />
          </>
        )}

        {data.nodeType === 'upgrade' && (
          <>
            <SelectField label="Upgrade Type" value={data.upgrade_type} options={['multiplicative', 'additive', 'percentage']} onChange={(v) => update('upgrade_type', v)} />
            <NumberField label="Magnitude" value={data.magnitude} onChange={(v) => update('magnitude', v)} step={0.1} />
            <NumberField label="Cost" value={data.cost} onChange={(v) => update('cost', v)} />
            <Field label="Target" value={data.target} onChange={(v) => update('target', v)} />
            <Field label="Stacking Group" value={data.stacking_group} onChange={(v) => update('stacking_group', v)} />
          </>
        )}

        {data.nodeType === 'prestige_layer' && (
          <>
            <FormulaField label="Formula" value={data.formula_expr} onChange={(v) => update('formula_expr', v)} />
            <NumberField label="Layer Index" value={data.layer_index} onChange={(v) => update('layer_index', v)} />
            <SelectField label="Bonus Type" value={data.bonus_type} options={['multiplicative', 'additive', 'percentage']} onChange={(v) => update('bonus_type', v)} />
          </>
        )}

        {data.nodeType === 'sacrifice' && (
          <>
            <FormulaField label="Formula" value={data.formula_expr} onChange={(v) => update('formula_expr', v)} />
            <SelectField label="Bonus Type" value={data.bonus_type} options={['multiplicative', 'additive', 'percentage']} onChange={(v) => update('bonus_type', v)} />
          </>
        )}

        {data.nodeType === 'achievement' && (
          <>
            <SelectField label="Condition Type" value={data.condition_type} options={['single_threshold', 'multi_threshold', 'collection', 'compound']} onChange={(v) => update('condition_type', v)} />
            <CheckboxField label="Permanent" value={data.permanent} onChange={(v) => update('permanent', v)} />
          </>
        )}

        {data.nodeType === 'manager' && (
          <>
            <Field label="Target" value={data.target} onChange={(v) => update('target', v)} />
            <SelectField label="Automation Type" value={data.automation_type} options={['collect', 'buy', 'activate']} onChange={(v) => update('automation_type', v)} />
          </>
        )}

        {data.nodeType === 'converter' && (
          <NumberField label="Rate" value={data.rate} onChange={(v) => update('rate', v)} step={0.1} />
        )}

        {data.nodeType === 'probability' && (
          <>
            <NumberField label="Expected Value" value={data.expected_value} onChange={(v) => update('expected_value', v)} />
            <NumberField label="Variance" value={data.variance} onChange={(v) => update('variance', v)} />
            <NumberField label="Crit Chance" value={data.crit_chance} onChange={(v) => update('crit_chance', v)} step={0.01} />
            <NumberField label="Crit Multiplier" value={data.crit_multiplier} onChange={(v) => update('crit_multiplier', v)} />
          </>
        )}

        {data.nodeType === 'end_condition' && (
          <SelectField label="Condition Type" value={data.condition_type} options={['single_threshold', 'multi_threshold', 'collection', 'compound']} onChange={(v) => update('condition_type', v)} />
        )}

        {data.nodeType === 'unlock_gate' && (
          <>
            <SelectField label="Condition Type" value={data.condition_type} options={['single_threshold', 'multi_threshold', 'collection', 'compound']} onChange={(v) => update('condition_type', v)} />
            <CheckboxField label="Permanent" value={data.permanent} onChange={(v) => update('permanent', v)} />
          </>
        )}

        {data.nodeType === 'choice_group' && (
          <>
            <NumberField label="Max Selections" value={data.max_selections} onChange={(v) => update('max_selections', v)} />
            <CheckboxField label="Respeccable" value={data.respeccable} onChange={(v) => update('respeccable', v)} />
          </>
        )}

        {data.nodeType === 'register' && (
          <FormulaField label="Formula" value={data.formula_expr} onChange={(v) => update('formula_expr', v)} />
        )}

        {data.nodeType === 'gate' && (
          <SelectField label="Mode" value={data.mode} options={['deterministic', 'probabilistic']} onChange={(v) => update('mode', v)} />
        )}

        {data.nodeType === 'queue' && (
          <>
            <NumberField label="Delay (s)" value={data.delay} onChange={(v) => update('delay', v)} step={0.1} />
            <NumberField label="Capacity" value={data.capacity ?? 0} onChange={(v) => update('capacity', v || null)} />
          </>
        )}
      </div>
    </aside>
  )
}

// -- Reusable field components --

function Field({ label, value, onChange, readOnly }: { label: string; value: string; onChange?: (v: string) => void; readOnly?: boolean }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{label}</label>
      <input
        type="text"
        value={value}
        onChange={onChange ? (e) => onChange(e.target.value) : undefined}
        readOnly={readOnly}
        className={`w-full text-sm rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1.5 bg-white dark:bg-gray-900 ${readOnly ? 'opacity-60' : ''}`}
      />
    </div>
  )
}

function NumberField({ label, value, onChange, step }: { label: string; value: number; onChange: (v: number) => void; step?: number }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{label}</label>
      <input
        type="number"
        value={value}
        step={step ?? 1}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="w-full text-sm rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1.5 bg-white dark:bg-gray-900"
      />
    </div>
  )
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full text-sm rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1.5 bg-white dark:bg-gray-900"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    </div>
  )
}

function CheckboxField({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
      <input type="checkbox" checked={value} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  )
}

function TagsField({ tags, onChange }: { tags: string[]; onChange: (tags: string[]) => void }) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && e.currentTarget.value.trim()) {
      e.preventDefault()
      const newTag = e.currentTarget.value.trim()
      if (!tags.includes(newTag)) {
        onChange([...tags, newTag])
      }
      e.currentTarget.value = ''
    }
  }

  const removeTag = (tag: string) => {
    onChange(tags.filter((t) => t !== tag))
  }

  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Tags</label>
      <div className="flex flex-wrap gap-1 mb-1">
        {tags.map((tag) => (
          <span key={tag} className="inline-flex items-center gap-1 bg-gray-200 dark:bg-gray-700 text-xs rounded px-2 py-0.5">
            {tag}
            <button onClick={() => removeTag(tag)} className="text-gray-500 hover:text-red-500">&times;</button>
          </span>
        ))}
      </div>
      <input
        type="text"
        placeholder="Type + Enter"
        onKeyDown={handleKeyDown}
        className="w-full text-sm rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1.5 bg-white dark:bg-gray-900"
      />
    </div>
  )
}
```

**Step 3: Wire PropertyPanel into EditorPage**

In `frontend/src/pages/EditorPage.tsx`:

```tsx
import PropertyPanel from '../editor/PropertyPanel'

// Inside EditorCanvas, add state tracking for selected node:
const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null

const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
  setSelectedNodeId(node.id)
}, [])

const onPaneClick = useCallback(() => {
  setSelectedNodeId(null)
}, [])

const onUpdateNode = useCallback((nodeId: string, updates: Partial<EditorNodeData>) => {
  setNodes((nds) =>
    nds.map((n) =>
      n.id === nodeId ? { ...n, data: { ...n.data, ...updates } } : n,
    ),
  )
}, [setNodes])

// Add to <ReactFlow>:
onNodeClick={onNodeClick}
onPaneClick={onPaneClick}

// Replace properties <aside> with:
<PropertyPanel selectedNode={selectedNode} onUpdateNode={onUpdateNode} />
```

**Step 4: Verify and commit**

Run: `cd frontend && npx tsc --noEmit`

```bash
git add frontend/src/editor/PropertyPanel.tsx frontend/src/editor/FormulaField.tsx frontend/src/pages/EditorPage.tsx
git commit -m "feat: property panel with type-specific fields and formula validation"
```

---

### Task 8: Import/Export (Save, Load, Download)

**Files:**
- Create: `frontend/src/editor/EditorToolbar.tsx`
- Modify: `frontend/src/pages/EditorPage.tsx` (wire toolbar)

**Step 1: Create EditorToolbar**

Create `frontend/src/editor/EditorToolbar.tsx`:

```tsx
import { useState } from 'react'
import type { Node, Edge } from '@xyflow/react'
import { graphToGame, gameToGraph, type GameDefinitionJSON } from './conversion'
import type { EditorNode } from './types'
import { listGames, getGame, createGame } from '../api/games'

interface EditorToolbarProps {
  nodes: Node[]
  edges: Edge[]
  gameName: string
  onSetGameName: (name: string) => void
  onLoadGraph: (nodes: EditorNode[], edges: Edge[]) => void
}

export default function EditorToolbar({ nodes, edges, gameName, onSetGameName, onLoadGraph }: EditorToolbarProps) {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const handleSave = async () => {
    if (!gameName.trim()) {
      setMessage('Please enter a game name')
      return
    }
    setLoading(true)
    setMessage(null)
    try {
      const game = graphToGame(nodes, edges, { name: gameName, stacking_groups: {} })
      await createGame(game as unknown as Record<string, unknown>)
      setMessage('Saved!')
    } catch (e) {
      setMessage(`Save failed: ${e instanceof Error ? e.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleLoad = async () => {
    setLoading(true)
    setMessage(null)
    try {
      const { games } = await listGames()
      if (games.length === 0) {
        setMessage('No games found')
        setLoading(false)
        return
      }
      // Show simple selection (first game for now, could be a dropdown)
      const gameId = games[0].id
      const gameData = await getGame(gameId) as unknown as GameDefinitionJSON
      const { nodes: newNodes, edges: newEdges } = gameToGraph(gameData)
      onLoadGraph(newNodes, newEdges)
      onSetGameName(gameData.name)
      setMessage(`Loaded: ${gameData.name}`)
    } catch (e) {
      setMessage(`Load failed: ${e instanceof Error ? e.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleLoadFromSelect = async (gameId: string) => {
    setLoading(true)
    setMessage(null)
    try {
      const gameData = await getGame(gameId) as unknown as GameDefinitionJSON
      const { nodes: newNodes, edges: newEdges } = gameToGraph(gameData)
      onLoadGraph(newNodes, newEdges)
      onSetGameName(gameData.name)
      setMessage(`Loaded: ${gameData.name}`)
    } catch (e) {
      setMessage(`Load failed: ${e instanceof Error ? e.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    const game = graphToGame(nodes, edges, { name: gameName || 'untitled', stacking_groups: {} })
    const blob = new Blob([JSON.stringify(game, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${gameName || 'game'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleUploadFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const game = JSON.parse(reader.result as string) as GameDefinitionJSON
        const { nodes: newNodes, edges: newEdges } = gameToGraph(game)
        onLoadGraph(newNodes, newEdges)
        onSetGameName(game.name)
        setMessage(`Loaded: ${game.name}`)
      } catch (err) {
        setMessage(`Invalid JSON: ${err instanceof Error ? err.message : 'Unknown error'}`)
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
      <input
        type="text"
        value={gameName}
        onChange={(e) => onSetGameName(e.target.value)}
        placeholder="Game name..."
        className="text-sm rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 bg-white dark:bg-gray-800 w-48"
      />

      <LoadGameDropdown onSelect={handleLoadFromSelect} />

      <button onClick={handleSave} disabled={loading} className="px-3 py-1 text-sm font-medium rounded-md bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50">
        Save
      </button>
      <button onClick={handleDownload} className="px-3 py-1 text-sm font-medium rounded-md bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200">
        Download JSON
      </button>
      <label className="px-3 py-1 text-sm font-medium rounded-md bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 cursor-pointer">
        Upload JSON
        <input type="file" accept=".json" onChange={handleUploadFile} className="hidden" />
      </label>

      {message && (
        <span className={`text-xs ml-2 ${message.startsWith('Save failed') || message.startsWith('Load failed') || message.startsWith('Invalid') ? 'text-red-500' : 'text-green-600 dark:text-green-400'}`}>
          {message}
        </span>
      )}
    </div>
  )
}

function LoadGameDropdown({ onSelect }: { onSelect: (gameId: string) => void }) {
  const [games, setGames] = useState<Array<{ id: string; name: string }>>([])
  const [open, setOpen] = useState(false)

  const handleOpen = async () => {
    if (!open) {
      try {
        const { games: g } = await listGames()
        setGames(g)
      } catch {
        setGames([])
      }
    }
    setOpen(!open)
  }

  return (
    <div className="relative">
      <button onClick={handleOpen} className="px-3 py-1 text-sm font-medium rounded-md bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200">
        Load
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-50 min-w-48">
          {games.length === 0 ? (
            <div className="px-3 py-2 text-xs text-gray-400">No games found</div>
          ) : (
            games.map((g) => (
              <button
                key={g.id}
                onClick={() => { onSelect(g.id); setOpen(false) }}
                className="block w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                {g.name}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
```

**Step 2: Wire into EditorPage**

In `frontend/src/pages/EditorPage.tsx`, add above the three-panel layout:

```tsx
import EditorToolbar from '../editor/EditorToolbar'

// Add state:
const [gameName, setGameName] = useState('Untitled Game')

const onLoadGraph = useCallback((newNodes: EditorNode[], newEdges: Edge[]) => {
  setNodes(newNodes)
  setEdges(newEdges)
}, [setNodes, setEdges])

// In JSX, add before the flex div:
<EditorToolbar
  nodes={nodes}
  edges={edges}
  gameName={gameName}
  onSetGameName={setGameName}
  onLoadGraph={onLoadGraph}
/>
```

**Step 3: Verify and commit**

Run: `cd frontend && npx tsc --noEmit`

```bash
git add frontend/src/editor/EditorToolbar.tsx frontend/src/pages/EditorPage.tsx
git commit -m "feat: editor toolbar with save, load, download, upload"
```

---

### Task 9: Live Analysis Panel

**Files:**
- Create: `frontend/src/editor/LiveAnalysisPanel.tsx`
- Modify: `frontend/src/pages/EditorPage.tsx` (wire analysis)

**Step 1: Create LiveAnalysisPanel**

Create `frontend/src/editor/LiveAnalysisPanel.tsx`:

```tsx
import { useEffect, useRef, useState } from 'react'
import type { Node, Edge } from '@xyflow/react'
import { graphToGame } from './conversion'
import { runAnalysis } from '../api/analysis'
import type { AnalysisResult } from '../api/types'

interface LiveAnalysisPanelProps {
  nodes: Node[]
  edges: Edge[]
  gameName: string
}

export default function LiveAnalysisPanel({ nodes, edges, gameName }: LiveAnalysisPanelProps) {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const versionRef = useRef(0)

  useEffect(() => {
    // Skip if no nodes
    if (nodes.length === 0) {
      setResult(null)
      setError(null)
      return
    }

    if (debounceRef.current) clearTimeout(debounceRef.current)

    debounceRef.current = setTimeout(async () => {
      const version = ++versionRef.current
      setLoading(true)
      setError(null)
      try {
        // Save game first, then run analysis
        const game = graphToGame(nodes, edges, { name: gameName || 'untitled', stacking_groups: {} })
        const { createGame } = await import('../api/games')
        const { id } = await createGame(game as unknown as Record<string, unknown>)
        if (version !== versionRef.current) return // stale
        const analysisResult = await runAnalysis({ game_id: id, simulation_time: 60 })
        if (version !== versionRef.current) return
        setResult(analysisResult)
      } catch (e) {
        if (version !== versionRef.current) return
        setError(e instanceof Error ? e.message : 'Analysis failed')
        setResult(null)
      } finally {
        if (version === versionRef.current) setLoading(false)
      }
    }, 1000) // 1s debounce for analysis (heavier than validation)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [nodes, edges, gameName])

  const hasWarnings = result && (result.dead_upgrades.length > 0 || result.progression_walls.length > 0)
  const statusColor = error ? 'text-red-500' : hasWarnings ? 'text-amber-500' : 'text-green-500'
  const statusIcon = error ? 'X' : hasWarnings ? '!' : '\u2713'

  return (
    <div className="mt-4 border-t border-gray-200 dark:border-gray-700 pt-3">
      <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-2">
        Live Analysis
        <span className={`text-lg font-bold ${statusColor}`}>{statusIcon}</span>
        {loading && <span className="text-xs text-gray-400 animate-pulse">analyzing...</span>}
      </h3>

      {error && (
        <p className="text-xs text-red-500 mb-2">{error}</p>
      )}

      {result && (
        <div className="flex flex-col gap-1.5 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Production:</span>
            <span className="font-medium">
              {result.optimizer_result ? `${result.optimizer_result.final_production.toExponential(2)}/s` : 'N/A'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Dead Upgrades:</span>
            <span className={`font-medium ${result.dead_upgrades.length > 0 ? 'text-amber-500' : ''}`}>
              {result.dead_upgrades.length}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Progression Walls:</span>
            <span className={`font-medium ${result.progression_walls.length > 0 ? 'text-amber-500' : ''}`}>
              {result.progression_walls.length}
            </span>
          </div>
          {result.dominant_strategy?.dominant_gen && (
            <div className="flex justify-between">
              <span className="text-gray-500 dark:text-gray-400">Dominant:</span>
              <span className="font-medium text-amber-500">
                {result.dominant_strategy.dominant_gen} ({result.dominant_strategy.ratio.toFixed(1)}x)
              </span>
            </div>
          )}
        </div>
      )}

      {!result && !error && nodes.length === 0 && (
        <p className="text-xs text-gray-400">Add nodes to see analysis...</p>
      )}
    </div>
  )
}
```

**Step 2: Wire into EditorPage**

In `frontend/src/pages/EditorPage.tsx`, place `<LiveAnalysisPanel>` inside the right sidebar, after `<PropertyPanel>`:

```tsx
import LiveAnalysisPanel from '../editor/LiveAnalysisPanel'

// In JSX, after PropertyPanel (inside a wrapper div for the right sidebar):
<div className="w-72 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 overflow-y-auto flex flex-col">
  <PropertyPanel selectedNode={selectedNode} onUpdateNode={onUpdateNode} />
  <LiveAnalysisPanel nodes={nodes} edges={edges} gameName={gameName} />
</div>
```

Note: PropertyPanel needs to be refactored slightly — remove its own `<aside>` wrapper and return just the inner content, so both panels can share the outer `<aside>` container.

**Step 3: Verify and commit**

Run: `cd frontend && npx tsc --noEmit`

```bash
git add frontend/src/editor/LiveAnalysisPanel.tsx frontend/src/pages/EditorPage.tsx
git commit -m "feat: live analysis panel with debounced REST polling"
```

---

### Task 10: Validation Bar

**Files:**
- Create: `frontend/src/editor/ValidationBar.tsx`
- Modify: `frontend/src/pages/EditorPage.tsx`

**Step 1: Create ValidationBar**

Create `frontend/src/editor/ValidationBar.tsx`:

```tsx
import { useMemo } from 'react'
import type { Node, Edge } from '@xyflow/react'
import type { EditorNodeData } from './types'

interface ValidationBarProps {
  nodes: Node[]
  edges: Edge[]
}

interface ValidationError {
  message: string
  nodeId?: string
}

function validate(nodes: Node[], edges: Edge[]): ValidationError[] {
  const errors: ValidationError[] = []
  const nodeIds = new Set(nodes.map((n) => n.id))

  // Check for duplicate IDs
  const seenIds = new Set<string>()
  for (const n of nodes) {
    if (seenIds.has(n.id)) {
      errors.push({ message: `Duplicate node ID: ${n.id}`, nodeId: n.id })
    }
    seenIds.add(n.id)
  }

  // Check for missing names
  for (const n of nodes) {
    const data = n.data as EditorNodeData
    if ('name' in data && !(data as Record<string, unknown>).name) {
      errors.push({ message: `Node ${n.id} has no name`, nodeId: n.id })
    }
  }

  // Check edge references
  for (const e of edges) {
    if (!nodeIds.has(e.source)) {
      errors.push({ message: `Edge ${e.id}: source '${e.source}' not found` })
    }
    if (!nodeIds.has(e.target)) {
      errors.push({ message: `Edge ${e.id}: target '${e.target}' not found` })
    }
  }

  // Check generators have required fields > 0
  for (const n of nodes) {
    const data = n.data as EditorNodeData
    if (data.nodeType === 'generator') {
      if (data.cost_base <= 0) errors.push({ message: `Generator ${n.id}: cost_base must be > 0`, nodeId: n.id })
      if (data.cost_growth_rate <= 0) errors.push({ message: `Generator ${n.id}: cost_growth_rate must be > 0`, nodeId: n.id })
      if (data.base_production <= 0) errors.push({ message: `Generator ${n.id}: base_production must be > 0`, nodeId: n.id })
    }
  }

  // Check at least one resource node exists
  const hasResource = nodes.some((n) => (n.data as EditorNodeData).nodeType === 'resource')
  if (nodes.length > 0 && !hasResource) {
    errors.push({ message: 'Game must have at least one resource node' })
  }

  return errors
}

export default function ValidationBar({ nodes, edges }: ValidationBarProps) {
  const errors = useMemo(() => validate(nodes, edges), [nodes, edges])

  return (
    <div className={`flex items-center gap-4 px-4 py-1.5 text-xs border-t ${
      errors.length > 0
        ? 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800'
        : 'bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800'
    }`}>
      <span className={`font-medium ${errors.length > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
        {errors.length > 0 ? `${errors.length} error${errors.length > 1 ? 's' : ''}` : '\u2713 Valid'}
      </span>
      <span className="text-gray-500 dark:text-gray-400">
        {nodes.length} nodes, {edges.length} edges
      </span>
      {errors.length > 0 && (
        <div className="flex gap-3 overflow-x-auto">
          {errors.slice(0, 3).map((err, i) => (
            <span key={i} className="text-red-500 whitespace-nowrap">{err.message}</span>
          ))}
          {errors.length > 3 && <span className="text-red-400">+{errors.length - 3} more</span>}
        </div>
      )}
    </div>
  )
}
```

**Step 2: Wire into EditorPage**

Add `<ValidationBar>` at the bottom of the editor layout:

```tsx
import ValidationBar from '../editor/ValidationBar'

// In JSX, after the three-panel flex div:
<ValidationBar nodes={nodes} edges={edges} />
```

**Step 3: Verify and commit**

Run: `cd frontend && npx tsc --noEmit`

```bash
git add frontend/src/editor/ValidationBar.tsx frontend/src/pages/EditorPage.tsx
git commit -m "feat: validation bar with real-time error checking"
```

---

### Task 11: JSON Preview Panel

**Files:**
- Create: `frontend/src/editor/JsonPreview.tsx`
- Modify: `frontend/src/pages/EditorPage.tsx`

**Step 1: Create JsonPreview toggle panel**

Create `frontend/src/editor/JsonPreview.tsx`:

```tsx
import { useMemo, useState } from 'react'
import type { Node, Edge } from '@xyflow/react'
import { graphToGame } from './conversion'

interface JsonPreviewProps {
  nodes: Node[]
  edges: Edge[]
  gameName: string
}

export default function JsonPreview({ nodes, edges, gameName }: JsonPreviewProps) {
  const [open, setOpen] = useState(false)

  const json = useMemo(() => {
    if (!open) return ''
    const game = graphToGame(nodes, edges, { name: gameName || 'untitled', stacking_groups: {} })
    return JSON.stringify(game, null, 2)
  }, [open, nodes, edges, gameName])

  return (
    <div className="border-t border-gray-200 dark:border-gray-700">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-1.5 text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 text-left"
      >
        {open ? '\u25BC' : '\u25B6'} JSON Preview
      </button>
      {open && (
        <pre className="px-4 py-2 text-xs font-mono bg-gray-900 text-green-400 overflow-auto max-h-64">
          {json}
        </pre>
      )}
    </div>
  )
}
```

**Step 2: Wire into EditorPage**

Add below `<ValidationBar>`:

```tsx
import JsonPreview from '../editor/JsonPreview'

<JsonPreview nodes={nodes} edges={edges} gameName={gameName} />
```

**Step 3: Verify and commit**

Run: `cd frontend && npx tsc --noEmit`

```bash
git add frontend/src/editor/JsonPreview.tsx frontend/src/pages/EditorPage.tsx
git commit -m "feat: JSON preview panel with live game definition output"
```

---

### Task 12: Assemble Final EditorPage

**Files:**
- Modify: `frontend/src/pages/EditorPage.tsx` (final assembly of all parts)

This task integrates all the pieces from Tasks 1-11 into the final EditorPage. All imports, state management, and layout in one coherent file.

**Step 1: Write the complete EditorPage**

Rewrite `frontend/src/pages/EditorPage.tsx` to assemble all components:

```tsx
import { useCallback, useState } from 'react'
import {
  ReactFlow,
  ReactFlowProvider,
  Controls,
  MiniMap,
  Background,
  addEdge,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type OnConnect,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { editorNodeTypes } from '../editor/nodes'
import { editorEdgeTypes } from '../editor/edges'
import NodePalette from '../editor/NodePalette'
import PropertyPanel from '../editor/PropertyPanel'
import LiveAnalysisPanel from '../editor/LiveAnalysisPanel'
import EditorToolbar from '../editor/EditorToolbar'
import ValidationBar from '../editor/ValidationBar'
import JsonPreview from '../editor/JsonPreview'
import { defaultNodeData, nextNodeId, type EditorNode, type EditorNodeData } from '../editor/types'

function EditorCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [gameName, setGameName] = useState('Untitled Game')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const { screenToFlowPosition } = useReactFlow()

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null

  const onConnect: OnConnect = useCallback(
    (params) => {
      const edge = {
        ...params,
        type: 'resource',
        label: 'resource flow',
        data: { edgeType: 'resource_flow' },
      }
      setEdges((eds) => addEdge(edge, eds))
    },
    [setEdges],
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      const nodeType = event.dataTransfer.getData('application/reactflow')
      if (!nodeType) return

      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY })
      const id = nextNodeId()
      const newNode: Node = {
        id,
        type: nodeType,
        position,
        data: defaultNodeData(nodeType, id),
      }
      setNodes((nds) => [...nds, newNode])
    },
    [screenToFlowPosition, setNodes],
  )

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id)
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null)
  }, [])

  const onUpdateNode = useCallback((nodeId: string, updates: Partial<EditorNodeData>) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, ...updates } } : n,
      ),
    )
  }, [setNodes])

  const onLoadGraph = useCallback((newNodes: EditorNode[], newEdges: Edge[]) => {
    setNodes(newNodes)
    setEdges(newEdges)
  }, [setNodes, setEdges])

  return (
    <div className="flex flex-col h-[calc(100vh-57px)]">
      <EditorToolbar
        nodes={nodes}
        edges={edges}
        gameName={gameName}
        onSetGameName={setGameName}
        onLoadGraph={onLoadGraph}
      />

      <div className="flex flex-1 min-h-0">
        <NodePalette />

        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={editorNodeTypes}
            edgeTypes={editorEdgeTypes}
            fitView
          >
            <Controls />
            <MiniMap />
            <Background />
          </ReactFlow>
        </div>

        <aside className="w-72 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 overflow-y-auto flex flex-col">
          <PropertyPanel selectedNode={selectedNode} onUpdateNode={onUpdateNode} />
          <LiveAnalysisPanel nodes={nodes} edges={edges} gameName={gameName} />
        </aside>
      </div>

      <ValidationBar nodes={nodes} edges={edges} />
      <JsonPreview nodes={nodes} edges={edges} gameName={gameName} />
    </div>
  )
}

export default function EditorPage() {
  return (
    <ReactFlowProvider>
      <EditorCanvas />
    </ReactFlowProvider>
  )
}
```

**Step 2: Verify it compiles and builds**

Run: `cd frontend && npx tsc --noEmit`
Run: `cd frontend && npm run build`

**Step 3: Commit**

```bash
git add frontend/src/pages/EditorPage.tsx
git commit -m "feat: assemble complete editor page with all panels"
```

---

### Task 13: Backend Tests for Editor Workflow

**Files:**
- Create: `tests/test_api/test_editor_workflow.py`

Test the round-trip: create game via API, load it, verify structure.

**Step 1: Write tests**

Create `tests/test_api/test_editor_workflow.py`:

```python
"""Tests for the editor workflow: create → load → analyze round-trip."""
import json

import pytest
from fastapi.testclient import TestClient

from server.app import app

client = TestClient(app)


class TestEditorRoundTrip:
    """Test creating a game via API and analyzing it."""

    def _minimal_game(self) -> dict:
        return {
            "schema_version": "1.0",
            "name": "Editor Test Game",
            "stacking_groups": {"default": "multiplicative"},
            "nodes": [
                {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
                {
                    "id": "gen1",
                    "type": "generator",
                    "name": "Worker",
                    "base_production": 1.0,
                    "cost_base": 10.0,
                    "cost_growth_rate": 1.07,
                    "cycle_time": 1.0,
                },
                {
                    "id": "upg1",
                    "type": "upgrade",
                    "name": "Boost",
                    "upgrade_type": "multiplicative",
                    "magnitude": 2.0,
                    "cost": 100.0,
                    "target": "gen1",
                    "stacking_group": "default",
                },
            ],
            "edges": [
                {"id": "e1", "source": "gen1", "target": "cash", "edge_type": "resource_flow"},
            ],
        }

    def test_create_and_load(self):
        game = self._minimal_game()
        resp = client.post("/api/v1/games/", json=game)
        assert resp.status_code == 200
        game_id = resp.json()["id"]

        resp = client.get(f"/api/v1/games/{game_id}")
        assert resp.status_code == 200
        loaded = resp.json()
        assert loaded["name"] == "Editor Test Game"
        assert len(loaded["nodes"]) == 3

    def test_create_and_analyze(self):
        game = self._minimal_game()
        resp = client.post("/api/v1/games/", json=game)
        assert resp.status_code == 200
        game_id = resp.json()["id"]

        resp = client.post("/api/v1/analysis/run", json={
            "game_id": game_id,
            "simulation_time": 60,
        })
        assert resp.status_code == 200
        result = resp.json()
        assert "dead_upgrades" in result
        assert "progression_walls" in result

    def test_create_invalid_game_fails(self):
        resp = client.post("/api/v1/games/", json={"name": "bad"})
        assert resp.status_code == 422 or resp.status_code == 400

    def test_create_game_all_node_types(self):
        """Verify a game with many node types can be created and loaded."""
        game = {
            "schema_version": "1.0",
            "name": "All Types Test",
            "stacking_groups": {"default": "multiplicative"},
            "nodes": [
                {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
                {"id": "gen1", "type": "generator", "name": "Worker",
                 "base_production": 1, "cost_base": 10, "cost_growth_rate": 1.07, "cycle_time": 1},
                {"id": "upg1", "type": "upgrade", "name": "Boost",
                 "upgrade_type": "multiplicative", "magnitude": 2, "cost": 100,
                 "target": "gen1", "stacking_group": "default"},
                {"id": "ach1", "type": "achievement", "name": "First Cash",
                 "condition_type": "single_threshold",
                 "targets": [{"node_id": "cash", "property": "current_value", "threshold": 100}]},
            ],
            "edges": [
                {"id": "e1", "source": "gen1", "target": "cash", "edge_type": "resource_flow"},
            ],
        }
        resp = client.post("/api/v1/games/", json=game)
        assert resp.status_code == 200
        game_id = resp.json()["id"]

        resp = client.get(f"/api/v1/games/{game_id}")
        assert resp.status_code == 200
        assert len(resp.json()["nodes"]) == 4
```

**Step 2: Run tests**

Run: `python3 -m pytest tests/test_api/test_editor_workflow.py -v`
Expected: All pass

**Step 3: Commit**

```bash
git add tests/test_api/test_editor_workflow.py
git commit -m "test: editor workflow round-trip tests"
```

---

### Task 14: Polish + Final Verification

**Files:**
- Modify: Various editor files for polish

**Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -q`
Expected: All tests pass (430+ tests)

**Step 2: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 4: Fix any issues found**

Address compilation errors, type mismatches, or test failures.

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: Phase 3 complete — React Flow node editor with all 16 types"
```

---

## Execution Order

Tasks are mostly sequential but some can be parallelized:

```
Task 1 (canvas shell)
  → Task 2 (types) + Task 4 (edge types) [parallel]
    → Task 3 (node components)
      → Task 5 (palette + DnD)
        → Task 6 (conversion) + Task 7 (property panel) [parallel]
          → Task 8 (import/export)
            → Task 9 (live analysis) + Task 10 (validation bar) + Task 11 (JSON preview) [parallel]
              → Task 12 (assemble)
                → Task 13 (backend tests) + Task 14 (polish) [parallel]
```

**Parallelizable groups:**
- Group A: Tasks 2 + 4
- Group B: Tasks 6 + 7
- Group C: Tasks 9 + 10 + 11
- Group D: Tasks 13 + 14
