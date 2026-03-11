import { Handle, Position } from '@xyflow/react'
import { NODE_COLORS } from '../types'

interface BaseNodeProps {
  nodeType: string
  name: string
  selected?: boolean
  children?: React.ReactNode
}

export default function BaseNode({ nodeType, name, selected, children }: BaseNodeProps) {
  const colors = NODE_COLORS[nodeType] ?? NODE_COLORS.resource
  return (
    <div className={`${colors.bg} border-2 ${colors.border} rounded-lg p-3 min-w-48 shadow-sm ${selected ? 'ring-2 ring-blue-500' : ''}`}>
      <Handle type="target" position={Position.Left} className="!w-3 !h-3" />
      <div className={`text-xs font-medium uppercase tracking-wide mb-1 opacity-60 ${colors.text}`}>{nodeType.replace(/_/g, ' ')}</div>
      <div className={`font-semibold ${colors.text}`}>{name || '(unnamed)'}</div>
      {children && <div className={`text-sm mt-1 opacity-75 ${colors.text}`}>{children}</div>}
      <Handle type="source" position={Position.Right} className="!w-3 !h-3" />
    </div>
  )
}
