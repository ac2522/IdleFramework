import { useCallback } from 'react'
import {
  ReactFlow,
  ReactFlowProvider,
  Controls,
  MiniMap,
  Background,
  addEdge,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type OnConnect,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { editorEdgeTypes } from '../editor/edges'
import { editorNodeTypes } from '../editor/nodes'
import NodePalette from '../editor/NodePalette'
import { defaultNodeData, nextNodeId } from '../editor/types'

function EditorCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const { screenToFlowPosition } = useReactFlow()

  const onConnect: OnConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      const nodeType = event.dataTransfer.getData('application/reactflow')
      if (!nodeType) return
      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY })
      const id = nextNodeId()
      const newNode: Node = {
        id,
        type: nodeType,
        position,
        data: defaultNodeData(nodeType, id),
      }
      setNodes((nds) => [...nds, newNode])
    },
    [screenToFlowPosition, setNodes],
  )

  return (
    <div className="flex h-[calc(100vh-57px)]">
      <NodePalette />

      {/* Canvas */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={editorNodeTypes}
          edgeTypes={editorEdgeTypes}
          fitView
        >
          <Controls />
          <MiniMap />
          <Background />
        </ReactFlow>
      </div>

      {/* Properties placeholder */}
      <aside className="w-72 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 overflow-y-auto">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
          Properties
        </h3>
        <p className="text-xs text-gray-400">Select a node to edit...</p>
      </aside>
    </div>
  )
}

export default function EditorPage() {
  return (
    <ReactFlowProvider>
      <EditorCanvas />
    </ReactFlowProvider>
  )
}
