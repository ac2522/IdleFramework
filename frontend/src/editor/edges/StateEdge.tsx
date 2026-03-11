import { BaseEdge, getBezierPath, EdgeLabelRenderer, type EdgeProps } from '@xyflow/react'

export default function StateEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, id, label } = props
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  })

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={{ stroke: '#a855f7', strokeWidth: 2, strokeDasharray: '6 3' }} />
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="bg-white dark:bg-gray-800 text-xs px-1.5 py-0.5 rounded border border-purple-300 dark:border-purple-600 text-purple-700 dark:text-purple-300 nopan"
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}
