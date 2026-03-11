import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function GateNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'gate') return null
  return (
    <BaseNode nodeType="gate" name={data.name} selected={selected}>
      <div>Mode: {data.mode}</div>
    </BaseNode>
  )
}
