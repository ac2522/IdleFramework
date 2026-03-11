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
