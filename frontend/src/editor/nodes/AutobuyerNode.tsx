import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function AutobuyerNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'autobuyer') return null
  return (
    <BaseNode nodeType="autobuyer" name={data.name} selected={selected}>
      <div>Target: {data.target || '(none)'}</div>
      <div>Every {data.interval}s | Bulk: {data.bulk_amount}</div>
      {!data.enabled && <div className="text-red-500 font-medium">Disabled</div>}
    </BaseNode>
  )
}
