import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function SacrificeNodeComponent({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'sacrifice') return null
  return (
    <BaseNode nodeType="sacrifice" name={data.name} selected={selected}>
      <div className="font-mono text-xs">{data.formula_expr}</div>
      <div>{data.bonus_type}</div>
    </BaseNode>
  )
}
