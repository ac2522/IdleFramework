import { useMemo } from 'react'
import type { Node, Edge } from '@xyflow/react'
import type { EditorNodeData, GeneratorNodeData } from './types.ts'

interface ValidationBarProps {
  nodes: Node[]
  edges: Edge[]
}

interface ValidationError {
  message: string
}

function validateGraph(nodes: Node[], edges: Edge[]): ValidationError[] {
  const errors: ValidationError[] = []

  // Duplicate node IDs
  const idCounts = new Map<string, number>()
  for (const node of nodes) {
    idCounts.set(node.id, (idCounts.get(node.id) ?? 0) + 1)
  }
  for (const [id, count] of idCounts) {
    if (count > 1) {
      errors.push({ message: `Duplicate node ID: "${id}" (appears ${count} times)` })
    }
  }

  // Missing names on nodes
  const nodeIds = new Set(nodes.map((n) => n.id))
  for (const node of nodes) {
    const data = node.data as EditorNodeData | undefined
    if (data && 'name' in data && (!data.name || data.name.trim() === '')) {
      errors.push({ message: `Node "${node.id}" is missing a name` })
    }
  }

  // Edge source/target referencing non-existent nodes
  for (const edge of edges) {
    if (!nodeIds.has(edge.source)) {
      errors.push({ message: `Edge "${edge.id}" references non-existent source "${edge.source}"` })
    }
    if (!nodeIds.has(edge.target)) {
      errors.push({ message: `Edge "${edge.id}" references non-existent target "${edge.target}"` })
    }
  }

  // Generator fields must be > 0
  for (const node of nodes) {
    const data = node.data as EditorNodeData | undefined
    if (data && data.nodeType === 'generator') {
      const gen = data as GeneratorNodeData
      if (gen.cost_base <= 0) {
        errors.push({ message: `Generator "${node.id}": cost_base must be > 0` })
      }
      if (gen.cost_growth_rate <= 0) {
        errors.push({ message: `Generator "${node.id}": cost_growth_rate must be > 0` })
      }
      if (gen.base_production <= 0) {
        errors.push({ message: `Generator "${node.id}": base_production must be > 0` })
      }
    }
  }

  // Must have at least one resource node if any nodes exist
  if (nodes.length > 0) {
    const hasResource = nodes.some((n) => {
      const data = n.data as EditorNodeData | undefined
      return data?.nodeType === 'resource'
    })
    if (!hasResource) {
      errors.push({ message: 'Graph has nodes but no resource node' })
    }
  }

  return errors
}

const MAX_DISPLAYED_ERRORS = 3

export default function ValidationBar({ nodes, edges }: ValidationBarProps) {
  const errors = useMemo(() => validateGraph(nodes, edges), [nodes, edges])
  const isValid = errors.length === 0
  const remaining = errors.length - MAX_DISPLAYED_ERRORS

  return (
    <div
      className={`flex items-center gap-4 px-4 py-2 text-sm font-medium border-t ${
        isValid
          ? 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900 dark:text-green-200 dark:border-green-700'
          : 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900 dark:text-red-200 dark:border-red-700'
      }`}
    >
      {/* Status badge */}
      <span className="shrink-0 font-bold">
        {isValid ? 'Valid' : `${errors.length} error${errors.length === 1 ? '' : 's'}`}
      </span>

      {/* Separator */}
      <span className="shrink-0 opacity-50">|</span>

      {/* Node and edge counts */}
      <span className="shrink-0">
        {nodes.length} node{nodes.length === 1 ? '' : 's'}, {edges.length} edge{edges.length === 1 ? '' : 's'}
      </span>

      {/* Error messages */}
      {!isValid && (
        <>
          <span className="shrink-0 opacity-50">|</span>
          <span className="truncate">
            {errors.slice(0, MAX_DISPLAYED_ERRORS).map((e) => e.message).join('; ')}
            {remaining > 0 && ` +${remaining} more`}
          </span>
        </>
      )}
    </div>
  )
}
