import type { EdgeTypes } from '@xyflow/react'
import ResourceEdge from './ResourceEdge'
import StateEdge from './StateEdge'

export const editorEdgeTypes: EdgeTypes = {
  resource: ResourceEdge,
  state: StateEdge,
}
