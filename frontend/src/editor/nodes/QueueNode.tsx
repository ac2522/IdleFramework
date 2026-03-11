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
