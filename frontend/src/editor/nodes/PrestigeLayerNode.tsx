import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function PrestigeLayerNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'prestige_layer') return null
  return (
    <BaseNode nodeType="prestige_layer" name={data.name} selected={selected}>
      <div>Layer {data.layer_index}</div>
      <div className="font-mono text-xs">{data.formula_expr}</div>
    </BaseNode>
  )
}
