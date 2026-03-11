/**
 * Pure conversion functions between React Flow graph state and GameDefinition JSON.
 */

import type { Edge } from '@xyflow/react'
import dagre from '@dagrejs/dagre'

import type { EditorNode, EditorNodeData } from './types.ts'
import { RESOURCE_EDGE_TYPES, resetNodeCounter } from './types.ts'

// ---------- GameDefinition JSON types ----------

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

interface GraphMetadata {
  name: string
  description?: string
  stacking_groups: Record<string, string>
  time_unit?: string
}

// ---------- graphToGame ----------

/**
 * Convert React Flow nodes/edges to a GameDefinition JSON object
 * matching the Python model schema.
 */
export function graphToGame(
  nodes: EditorNode[],
  edges: Edge[],
  metadata: GraphMetadata,
): GameDefinitionJSON {
  const gameNodes: GameNode[] = nodes.map((node) => {
    const data = node.data as EditorNodeData
    // Build game node: id from React Flow node, type from nodeType, all data fields except label/nodeType
    const gameNode: GameNode = { id: node.id, type: data.nodeType }

    for (const [key, value] of Object.entries(data)) {
      if (key === 'label' || key === 'nodeType') continue
      gameNode[key] = value
    }

    return gameNode
  })

  const gameEdges: GameEdge[] = edges.map((edge) => {
    const edgeData = edge.data as { edgeType?: string; rate?: number; formula?: string; condition?: string } | undefined
    const gameEdge: GameEdge = {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      edge_type: edgeData?.edgeType ?? 'resource_flow',
    }

    if (edgeData?.rate != null) gameEdge.rate = edgeData.rate
    if (edgeData?.formula != null) gameEdge.formula = edgeData.formula
    if (edgeData?.condition != null) gameEdge.condition = edgeData.condition

    return gameEdge
  })

  const result: GameDefinitionJSON = {
    schema_version: '1.0',
    name: metadata.name,
    nodes: gameNodes,
    edges: gameEdges,
    stacking_groups: metadata.stacking_groups,
  }

  if (metadata.description) result.description = metadata.description
  if (metadata.time_unit) result.time_unit = metadata.time_unit

  return result
}

// ---------- gameToGraph ----------

const NODE_WIDTH = 200
const NODE_HEIGHT = 80

/**
 * Convert a GameDefinition JSON to React Flow nodes/edges with dagre auto-layout.
 */
export function gameToGraph(game: GameDefinitionJSON): { nodes: EditorNode[]; edges: Edge[] } {
  // Build dagre graph for layout
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', nodesep: 60, ranksep: 120 })

  // Create editor nodes
  const editorNodes: EditorNode[] = game.nodes.map((gameNode) => {
    const nodeType = gameNode.type

    // Build data: copy all fields except id/type, add label and nodeType
    const data: Record<string, unknown> = {
      label: gameNode.name ?? gameNode.id,
      nodeType,
    }

    for (const [key, value] of Object.entries(gameNode)) {
      if (key === 'id' || key === 'type') continue
      data[key] = value
    }

    // Add base defaults if missing
    if (!('tags' in data)) data.tags = []
    if (!('activation_mode' in data)) data.activation_mode = 'automatic'
    if (!('pull_mode' in data)) data.pull_mode = 'pull_any'
    if (!('cooldown_time' in data)) data.cooldown_time = null

    g.setNode(gameNode.id, { width: NODE_WIDTH, height: NODE_HEIGHT })

    return {
      id: gameNode.id,
      type: nodeType,
      position: { x: 0, y: 0 },
      data: data as EditorNodeData,
    } satisfies EditorNode
  })

  // Create editor edges
  const editorEdges: Edge[] = game.edges.map((gameEdge) => {
    const edgeType = gameEdge.edge_type
    const isResource = (RESOURCE_EDGE_TYPES as readonly string[]).includes(edgeType)

    g.setEdge(gameEdge.source, gameEdge.target)

    const edgeData: Record<string, unknown> = { edgeType }
    if (gameEdge.rate != null) edgeData.rate = gameEdge.rate
    if (gameEdge.formula != null) edgeData.formula = gameEdge.formula
    if (gameEdge.condition != null) edgeData.condition = gameEdge.condition

    return {
      id: gameEdge.id,
      source: gameEdge.source,
      target: gameEdge.target,
      type: isResource ? 'resource' : 'state',
      label: edgeType.replace(/_/g, ' '),
      data: edgeData,
    } satisfies Edge
  })

  // Run dagre layout
  dagre.layout(g)

  // Apply computed positions back to nodes
  for (const node of editorNodes) {
    const dagreNode = g.node(node.id)
    if (dagreNode) {
      node.position = {
        x: dagreNode.x - NODE_WIDTH / 2,
        y: dagreNode.y - NODE_HEIGHT / 2,
      }
    }
  }

  // Reset node counter to max existing ID suffix
  let maxId = 0
  for (const node of editorNodes) {
    const match = node.id.match(/\d+$/)
    if (match) {
      const num = parseInt(match[0], 10)
      if (num > maxId) maxId = num
    }
  }
  resetNodeCounter(maxId)

  return { nodes: editorNodes, edges: editorEdges }
}
