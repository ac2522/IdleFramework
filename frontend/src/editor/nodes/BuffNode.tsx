import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function BuffNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'buff') return null
  return (
    <BaseNode nodeType="buff" name={data.name} selected={selected}>
      <div>{data.multiplier}x ({data.buff_type})</div>
      {data.buff_type === 'timed' && <div>Duration: {data.duration}s</div>}
      {data.buff_type === 'proc' && <div>Chance: {(data.proc_chance * 100).toFixed(0)}%</div>}
      {data.target && <div>Target: {data.target}</div>}
    </BaseNode>
  )
}
