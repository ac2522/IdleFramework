import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function UpgradeNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'upgrade') return null
  return (
    <BaseNode nodeType="upgrade" name={data.name} selected={selected}>
      <div>{data.upgrade_type} x{data.magnitude}</div>
      <div>Cost: {data.cost} | Target: {data.target}</div>
    </BaseNode>
  )
}
