import type { NodeProps } from '@xyflow/react'
import type { EditorNode } from '../types'
import BaseNode from './BaseNode'

export default function AchievementNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'achievement') return null
  return (
    <BaseNode nodeType="achievement" name={data.name} selected={selected}>
      <div>{data.condition_type} ({data.targets.length} targets)</div>
      <div>{data.permanent ? 'Permanent' : 'Temporary'}</div>
    </BaseNode>
  )
}
