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
