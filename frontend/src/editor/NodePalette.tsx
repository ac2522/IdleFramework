import { NODE_COLORS } from './types'

interface PaletteItem {
  type: string
  name: string
  description: string
}

interface PaletteCategory {
  label: string
  items: PaletteItem[]
}

const PALETTE_CATEGORIES: PaletteCategory[] = [
  {
    label: 'Resources',
    items: [
      { type: 'resource', name: 'Resource', description: 'Stores a numeric value' },
    ],
  },
  {
    label: 'Producers',
    items: [
      { type: 'generator', name: 'Generator', description: 'Produces resources over time' },
      { type: 'nested_generator', name: 'Nested Gen', description: 'Generates other generators' },
      { type: 'converter', name: 'Converter', description: 'Converts inputs to outputs' },
    ],
  },
  {
    label: 'Modifiers',
    items: [
      { type: 'upgrade', name: 'Upgrade', description: 'Multiplies or adds to production' },
      { type: 'manager', name: 'Manager', description: 'Automates collection or buying' },
    ],
  },
  {
    label: 'Meta',
    items: [
      { type: 'prestige_layer', name: 'Prestige', description: 'Reset layer with bonus' },
      { type: 'sacrifice', name: 'Sacrifice', description: 'Trade resources for bonuses' },
      { type: 'achievement', name: 'Achievement', description: 'Conditional milestone reward' },
      { type: 'end_condition', name: 'End Condition', description: 'Win/lose condition check' },
    ],
  },
  {
    label: 'Control',
    items: [
      { type: 'unlock_gate', name: 'Unlock Gate', description: 'Unlocks content on condition' },
      { type: 'gate', name: 'Gate', description: 'Routes flow deterministically' },
      { type: 'choice_group', name: 'Choice Group', description: 'Player picks from options' },
      { type: 'probability', name: 'Probability', description: 'Random outcome distribution' },
    ],
  },
  {
    label: 'Advanced',
    items: [
      { type: 'register', name: 'Register', description: 'Computes a formula value' },
      { type: 'queue', name: 'Queue', description: 'Delays flow with capacity' },
    ],
  },
]

function onDragStart(event: React.DragEvent, nodeType: string) {
  event.dataTransfer.setData('application/reactflow', nodeType)
  event.dataTransfer.effectAllowed = 'move'
}

export default function NodePalette() {
  return (
    <aside className="w-56 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 overflow-y-auto">
      <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
        Node Palette
      </h3>
      {PALETTE_CATEGORIES.map((category) => (
        <div key={category.label} className="mb-4">
          <h4 className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1.5">
            {category.label}
          </h4>
          <div className="space-y-1">
            {category.items.map((item) => {
              const colors = NODE_COLORS[item.type] ?? {
                bg: 'bg-gray-50 dark:bg-gray-900',
                border: 'border-gray-400',
                text: 'text-gray-800 dark:text-gray-200',
              }
              return (
                <div
                  key={item.type}
                  draggable
                  onDragStart={(e) => onDragStart(e, item.type)}
                  className={`cursor-grab rounded border-l-4 px-2 py-1.5 ${colors.bg} ${colors.border} select-none hover:opacity-80 active:cursor-grabbing`}
                >
                  <div className={`text-xs font-semibold ${colors.text}`}>{item.name}</div>
                  <div className="text-[10px] text-gray-500 dark:text-gray-400 leading-tight">
                    {item.description}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </aside>
  )
}
