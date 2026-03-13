import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function DrainNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'drain') return null
  return (
    <BaseNode nodeType="drain" name={data.name} selected={selected}>
      <div>Rate: {data.rate}/s</div>
      {data.condition && <div>If: {data.condition}</div>}
    </BaseNode>
  )
}
