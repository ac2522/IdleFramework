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
