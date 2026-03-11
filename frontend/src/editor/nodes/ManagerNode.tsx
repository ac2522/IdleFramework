import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function ManagerNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'manager') return null
  return (
    <BaseNode nodeType="manager" name={data.name} selected={selected}>
      <div>{data.automation_type} | Target: {data.target}</div>
    </BaseNode>
  )
}
