import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function NestedGeneratorNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'nested_generator') return null
  return (
    <BaseNode nodeType="nested_generator" name={data.name} selected={selected}>
      <div>Target: {data.target_generator}</div>
      <div>Rate: {data.production_rate}/s</div>
    </BaseNode>
  )
}
