import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function RegisterNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'register') return null
  return (
    <BaseNode nodeType="register" name={data.name} selected={selected}>
      <div className="font-mono text-xs">{data.formula_expr}</div>
    </BaseNode>
  )
}
