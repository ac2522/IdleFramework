import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function SynergyNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'synergy') return null
  return (
    <BaseNode nodeType="synergy" name={data.name} selected={selected}>
      <div>f = {data.formula_expr}</div>
      {data.sources.length > 0 && <div>Sources: {data.sources.join(', ')}</div>}
      {data.target && <div>Target: {data.target}</div>}
    </BaseNode>
  )
}
