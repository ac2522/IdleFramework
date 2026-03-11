import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function ChoiceGroupNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'choice_group') return null
  return (
    <BaseNode nodeType="choice_group" name={data.name} selected={selected}>
      <div>{data.options.length} options, max {data.max_selections}</div>
      <div>{data.respeccable ? 'Respeccable' : 'Permanent'}</div>
    </BaseNode>
  )
}
