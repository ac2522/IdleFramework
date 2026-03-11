import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function ConverterNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'converter') return null
  return (
    <BaseNode nodeType="converter" name={data.name} selected={selected}>
      <div>{data.inputs.length} in &rarr; {data.outputs.length} out</div>
      <div>Rate: {data.rate}/s</div>
    </BaseNode>
  )
}
