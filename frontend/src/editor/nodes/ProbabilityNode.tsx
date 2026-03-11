import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function ProbabilityNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'probability') return null
  return (
    <BaseNode nodeType="probability" name={data.name} selected={selected}>
      <div>EV: {data.expected_value}</div>
      {data.crit_chance > 0 && <div>Crit: {data.crit_chance * 100}% x{data.crit_multiplier}</div>}
    </BaseNode>
  )
}
