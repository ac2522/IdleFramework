import type { NodeTypes } from '@xyflow/react'
import ResourceNode from './ResourceNode'
import GeneratorNode from './GeneratorNode'
import NestedGeneratorNode from './NestedGeneratorNode'
import UpgradeNode from './UpgradeNode'
import PrestigeLayerNode from './PrestigeLayerNode'
import SacrificeNodeComponent from './SacrificeNodeComponent'
import AchievementNode from './AchievementNode'
import ManagerNode from './ManagerNode'
import ConverterNode from './ConverterNode'
import ProbabilityNode from './ProbabilityNode'
import EndConditionNode from './EndConditionNode'
import UnlockGateNode from './UnlockGateNode'
import ChoiceGroupNode from './ChoiceGroupNode'
import RegisterNode from './RegisterNode'
import GateNode from './GateNode'
import QueueNode from './QueueNode'

export const editorNodeTypes: NodeTypes = {
  resource: ResourceNode,
  generator: GeneratorNode,
  nested_generator: NestedGeneratorNode,
  upgrade: UpgradeNode,
  prestige_layer: PrestigeLayerNode,
  sacrifice: SacrificeNodeComponent,
  achievement: AchievementNode,
  manager: ManagerNode,
  converter: ConverterNode,
  probability: ProbabilityNode,
  end_condition: EndConditionNode,
  unlock_gate: UnlockGateNode,
  choice_group: ChoiceGroupNode,
  register: RegisterNode,
  gate: GateNode,
  queue: QueueNode,
}
