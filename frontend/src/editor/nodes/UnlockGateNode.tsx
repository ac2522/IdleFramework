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
