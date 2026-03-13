import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function TickspeedNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'tickspeed') return null
  return (
    <BaseNode nodeType="tickspeed" name={data.name} selected={selected}>
      <div>{data.base_tickspeed}x speed</div>
    </BaseNode>
  )
}
