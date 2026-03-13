import { useCallback, useState } from 'react'
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
import PropertyPanel from '../editor/PropertyPanel'
import LiveAnalysisPanel from '../editor/LiveAnalysisPanel'
import EditorToolbar from '../editor/EditorToolbar'
import ValidationBar from '../editor/ValidationBar'
import JsonPreview from '../editor/JsonPreview'
import { defaultNodeData, nextNodeId } from '../editor/types'
import type { EditorNode, EditorNodeData } from '../editor/types'

function EditorCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [gameName, setGameName] = useState('Untitled Game')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const { screenToFlowPosition } = useReactFlow()

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null

  const onConnect: OnConnect = useCallback(
    (params) => {
      // Infer edge type from source node type
      const sourceNode = nodes.find((n) => n.id === params.source)
      const sourceType = (sourceNode?.data as EditorNodeData | undefined)?.nodeType
      const stateSourceTypes = new Set([
        'upgrade', 'manager', 'achievement', 'unlock_gate', 'prestige_layer', 'sacrifice',
      ])
      const isState = sourceType != null && stateSourceTypes.has(sourceType)
      const edgeType = isState ? 'state_modifier' : 'resource_flow'
      const rfType = isState ? 'state' : 'resource'

      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: rfType,
            data: { edgeType },
          },
          eds,
        ),
      )
    },
    [setEdges, nodes],
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

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id)
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null)
  }, [])

  const onUpdateNode = useCallback(
    (nodeId: string, data: Partial<EditorNodeData>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n,
        ),
      )
    },
    [setNodes],
  )

  const onLoadGraph = useCallback(
    (newNodes: EditorNode[], newEdges: Edge[]) => {
      setNodes(newNodes)
      setEdges(newEdges)
    },
    [setNodes, setEdges],
  )

  return (
    <div className="flex flex-col h-[calc(100vh-57px)]">
      <EditorToolbar
        nodes={nodes}
        edges={edges}
        gameName={gameName}
        onSetGameName={setGameName}
        onLoadGraph={onLoadGraph}
      />
      <div className="flex flex-1 min-h-0">
        <NodePalette />
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={editorNodeTypes}
            edgeTypes={editorEdgeTypes}
            fitView
          >
            <Controls />
            <MiniMap />
            <Background />
          </ReactFlow>
        </div>
        <aside className="w-72 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            <PropertyPanel
              selectedNode={selectedNode as Node<EditorNodeData> | null}
              onUpdateNode={onUpdateNode}
              allNodes={nodes as unknown as Node<EditorNodeData>[]}
            />
          </div>
          <div className="border-t border-gray-200 dark:border-gray-700 flex-1 overflow-y-auto">
            <LiveAnalysisPanel
              nodes={nodes as unknown as EditorNode[]}
              edges={edges}
              gameName={gameName}
            />
          </div>
        </aside>
      </div>
      <ValidationBar nodes={nodes} edges={edges} />
      <JsonPreview
        nodes={nodes as unknown as EditorNode[]}
        edges={edges}
        gameName={gameName}
      />
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
