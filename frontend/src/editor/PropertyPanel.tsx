import { useState, useRef } from 'react'
import type { Node, Edge } from '@xyflow/react'
import type { EditorNodeData } from './types.ts'
import FormulaField from './FormulaField.tsx'

// --- Reusable sub-components ---

function Field({ label, value, onChange, readOnly = false }: {
  label: string
  value: string
  onChange?: (v: string) => void
  readOnly?: boolean
}) {
  return (
    <div className="mb-3">
      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</label>
      <input
        type="text"
        value={value}
        onChange={onChange ? (e) => onChange(e.target.value) : undefined}
        readOnly={readOnly}
        className={`w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500 ${readOnly ? 'opacity-60 cursor-not-allowed' : ''}`}
      />
    </div>
  )
}

function NumberField({ label, value, onChange, step = 1 }: {
  label: string
  value: number
  onChange: (v: number) => void
  step?: number
}) {
  return (
    <div className="mb-3">
      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</label>
      <input
        type="number"
        value={value}
        step={step}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
    </div>
  )
}

function SelectField({ label, value, options, onChange }: {
  label: string
  value: string
  options: string[]
  onChange: (v: string) => void
}) {
  return (
    <div className="mb-3">
      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    </div>
  )
}

function CheckboxField({ label, checked, onChange }: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="rounded border-gray-300 dark:border-gray-600"
      />
      <label className="text-xs font-medium text-gray-600 dark:text-gray-400">{label}</label>
    </div>
  )
}

function TagsField({ label, tags, onChange, suggestions = [] }: {
  label: string
  tags: string[]
  onChange: (tags: string[]) => void
  suggestions?: string[]
}) {
  const [input, setInput] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [highlightIndex, setHighlightIndex] = useState(-1)
  const blurTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const filtered = input.trim()
    ? suggestions.filter((s) => s.toLowerCase().startsWith(input.toLowerCase()))
    : []

  function addTag(tag: string) {
    if (!tags.some((t) => t.toLowerCase() === tag.toLowerCase())) {
      onChange([...tags, tag])
    }
    setInput('')
    setShowDropdown(false)
    setHighlightIndex(-1)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown' && showDropdown && filtered.length > 0) {
      e.preventDefault()
      setHighlightIndex((prev) => (prev + 1) % filtered.length)
    } else if (e.key === 'ArrowUp' && showDropdown && filtered.length > 0) {
      e.preventDefault()
      setHighlightIndex((prev) => (prev <= 0 ? filtered.length - 1 : prev - 1))
    } else if (e.key === 'Enter' && input.trim()) {
      e.preventDefault()
      if (highlightIndex >= 0 && highlightIndex < filtered.length) {
        addTag(filtered[highlightIndex])
      } else if (filtered.length > 0) {
        addTag(filtered[0])
      } else {
        addTag(input.trim())
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false)
      setHighlightIndex(-1)
    }
  }

  function handleInputChange(value: string) {
    setInput(value)
    setShowDropdown(value.trim().length > 0)
    setHighlightIndex(-1)
  }

  function removeTag(tag: string) {
    onChange(tags.filter((t) => t !== tag))
  }

  return (
    <div className="mb-3">
      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</label>
      <div className="flex flex-wrap gap-1 mb-1">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-0.5 rounded-full bg-blue-100 dark:bg-blue-900 px-2 py-0.5 text-xs text-blue-800 dark:text-blue-200"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="ml-0.5 text-blue-600 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-100"
            >
              &times;
            </button>
          </span>
        ))}
      </div>
      <div className="relative">
        <input
          type="text"
          value={input}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => { if (blurTimerRef.current) clearTimeout(blurTimerRef.current); if (input.trim()) setShowDropdown(true) }}
          onBlur={() => { blurTimerRef.current = setTimeout(() => setShowDropdown(false), 150) }}
          placeholder="Type + Enter to add"
          className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        {showDropdown && filtered.length > 0 && (
          <ul className="absolute z-10 mt-1 w-full rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 shadow-lg max-h-32 overflow-y-auto">
            {filtered.map((suggestion, idx) => (
              <li key={suggestion}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => addTag(suggestion)}
                  className={`w-full px-2 py-1.5 text-left text-sm text-gray-900 dark:text-gray-100 ${idx === highlightIndex ? 'bg-blue-50 dark:bg-blue-900/30' : 'hover:bg-blue-50 dark:hover:bg-blue-900/30'}`}
                >
                  {suggestion}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

// --- Type-specific field renderers ---

function TypeFields({ data, update }: { data: EditorNodeData; update: (patch: Partial<EditorNodeData>) => void }) {
  switch (data.nodeType) {
    case 'resource':
      return (
        <>
          <NumberField label="Initial Value" value={data.initial_value} onChange={(v) => update({ initial_value: v } as Partial<EditorNodeData>)} />
          <NumberField label="Capacity" value={(data as Record<string, unknown>).capacity as number ?? 0} onChange={(v) => update({ capacity: v || null } as Partial<EditorNodeData>)} />
          <SelectField label="Overflow Behavior" value={((data as Record<string, unknown>).overflow_behavior as string) ?? 'clamp'} options={['clamp', 'waste']} onChange={(v) => update({ overflow_behavior: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'generator':
      return (
        <>
          <NumberField label="Base Production" value={data.base_production} onChange={(v) => update({ base_production: v } as Partial<EditorNodeData>)} />
          <NumberField label="Cost Base" value={data.cost_base} onChange={(v) => update({ cost_base: v } as Partial<EditorNodeData>)} />
          <NumberField label="Cost Growth Rate" value={data.cost_growth_rate} onChange={(v) => update({ cost_growth_rate: v } as Partial<EditorNodeData>)} step={0.01} />
          <NumberField label="Cycle Time" value={data.cycle_time} onChange={(v) => update({ cycle_time: v } as Partial<EditorNodeData>)} step={0.1} />
        </>
      )

    case 'nested_generator':
      return (
        <>
          <Field label="Target Generator" value={data.target_generator} onChange={(v) => update({ target_generator: v } as Partial<EditorNodeData>)} />
          <NumberField label="Production Rate" value={data.production_rate} onChange={(v) => update({ production_rate: v } as Partial<EditorNodeData>)} />
          <NumberField label="Cost Base" value={data.cost_base} onChange={(v) => update({ cost_base: v } as Partial<EditorNodeData>)} />
          <NumberField label="Cost Growth Rate" value={data.cost_growth_rate} onChange={(v) => update({ cost_growth_rate: v } as Partial<EditorNodeData>)} step={0.01} />
        </>
      )

    case 'upgrade':
      return (
        <>
          <SelectField label="Upgrade Type" value={data.upgrade_type} options={['multiplicative', 'additive', 'percentage']} onChange={(v) => update({ upgrade_type: v } as Partial<EditorNodeData>)} />
          <NumberField label="Magnitude" value={data.magnitude} onChange={(v) => update({ magnitude: v } as Partial<EditorNodeData>)} />
          <NumberField label="Cost" value={data.cost} onChange={(v) => update({ cost: v } as Partial<EditorNodeData>)} />
          <Field label="Target" value={data.target} onChange={(v) => update({ target: v } as Partial<EditorNodeData>)} />
          <Field label="Stacking Group" value={data.stacking_group} onChange={(v) => update({ stacking_group: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'prestige_layer':
      return (
        <>
          <FormulaField label="Formula" value={data.formula_expr} onChange={(v) => update({ formula_expr: v } as Partial<EditorNodeData>)} />
          <NumberField label="Layer Index" value={data.layer_index} onChange={(v) => update({ layer_index: v } as Partial<EditorNodeData>)} />
          <SelectField label="Bonus Type" value={data.bonus_type} options={['multiplicative', 'additive', 'percentage']} onChange={(v) => update({ bonus_type: v } as Partial<EditorNodeData>)} />
          <Field label="Currency ID" value={((data as Record<string, unknown>).currency_id as string) ?? ''} onChange={(v) => update({ currency_id: v } as Partial<EditorNodeData>)} />
          <Field label="Parent Layer" value={((data as Record<string, unknown>).parent_layer as string) ?? ''} onChange={(v) => update({ parent_layer: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'sacrifice':
      return (
        <>
          <FormulaField label="Formula" value={data.formula_expr} onChange={(v) => update({ formula_expr: v } as Partial<EditorNodeData>)} />
          <SelectField label="Bonus Type" value={data.bonus_type} options={['multiplicative', 'additive', 'percentage']} onChange={(v) => update({ bonus_type: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'achievement':
      return (
        <>
          <SelectField label="Condition Type" value={data.condition_type} options={['single_threshold', 'multi_threshold', 'cumulative']} onChange={(v) => update({ condition_type: v } as Partial<EditorNodeData>)} />
          <CheckboxField label="Permanent" checked={data.permanent} onChange={(v) => update({ permanent: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'manager':
      return (
        <>
          <Field label="Target" value={data.target} onChange={(v) => update({ target: v } as Partial<EditorNodeData>)} />
          <SelectField label="Automation Type" value={data.automation_type} options={['collect', 'buy', 'activate']} onChange={(v) => update({ automation_type: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'converter':
      return (
        <>
          <NumberField label="Rate" value={data.rate} onChange={(v) => update({ rate: v } as Partial<EditorNodeData>)} />
          <SelectField label="Recipe Type" value={((data as Record<string, unknown>).recipe_type as string) ?? 'fixed'} options={['fixed', 'scaling']} onChange={(v) => update({ recipe_type: v } as Partial<EditorNodeData>)} />
          <NumberField label="Conversion Limit" value={((data as Record<string, unknown>).conversion_limit as number) ?? 0} onChange={(v) => update({ conversion_limit: v || null } as Partial<EditorNodeData>)} />
        </>
      )

    case 'probability':
      return (
        <>
          <NumberField label="Expected Value" value={data.expected_value} onChange={(v) => update({ expected_value: v } as Partial<EditorNodeData>)} />
          <NumberField label="Variance" value={data.variance} onChange={(v) => update({ variance: v } as Partial<EditorNodeData>)} />
          <NumberField label="Crit Chance" value={data.crit_chance} onChange={(v) => update({ crit_chance: v } as Partial<EditorNodeData>)} step={0.01} />
          <NumberField label="Crit Multiplier" value={data.crit_multiplier} onChange={(v) => update({ crit_multiplier: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'end_condition':
      return <SelectField label="Condition Type" value={data.condition_type} options={['single_threshold', 'multi_threshold', 'cumulative']} onChange={(v) => update({ condition_type: v } as Partial<EditorNodeData>)} />

    case 'unlock_gate':
      return (
        <>
          <SelectField label="Condition Type" value={data.condition_type} options={['single_threshold', 'multi_threshold', 'cumulative']} onChange={(v) => update({ condition_type: v } as Partial<EditorNodeData>)} />
          <CheckboxField label="Permanent" checked={data.permanent} onChange={(v) => update({ permanent: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'choice_group':
      return (
        <>
          <NumberField label="Max Selections" value={data.max_selections} onChange={(v) => update({ max_selections: v } as Partial<EditorNodeData>)} />
          <CheckboxField label="Respeccable" checked={data.respeccable} onChange={(v) => update({ respeccable: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'register':
      return <FormulaField label="Formula" value={data.formula_expr} onChange={(v) => update({ formula_expr: v } as Partial<EditorNodeData>)} />

    case 'gate':
      return <SelectField label="Mode" value={data.mode} options={['deterministic', 'probabilistic']} onChange={(v) => update({ mode: v } as Partial<EditorNodeData>)} />

    case 'queue':
      return (
        <>
          <NumberField label="Delay" value={data.delay} onChange={(v) => update({ delay: v } as Partial<EditorNodeData>)} step={0.1} />
          <NumberField label="Capacity" value={data.capacity ?? 0} onChange={(v) => update({ capacity: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'tickspeed':
      return <NumberField label="Base Tickspeed" value={data.base_tickspeed} onChange={(v) => update({ base_tickspeed: v } as Partial<EditorNodeData>)} step={0.1} />

    case 'autobuyer':
      return (
        <>
          <Field label="Target" value={data.target} onChange={(v) => update({ target: v } as Partial<EditorNodeData>)} />
          <NumberField label="Interval (s)" value={data.interval} onChange={(v) => update({ interval: v } as Partial<EditorNodeData>)} step={0.1} />
          <NumberField label="Priority" value={data.priority} onChange={(v) => update({ priority: v } as Partial<EditorNodeData>)} />
          <Field label="Condition" value={data.condition} onChange={(v) => update({ condition: v } as Partial<EditorNodeData>)} />
          <SelectField label="Bulk Amount" value={data.bulk_amount} options={['1', '10', 'max']} onChange={(v) => update({ bulk_amount: v } as Partial<EditorNodeData>)} />
          <CheckboxField label="Enabled" checked={data.enabled} onChange={(v) => update({ enabled: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'drain':
      return (
        <>
          <NumberField label="Rate" value={data.rate} onChange={(v) => update({ rate: v } as Partial<EditorNodeData>)} step={0.1} />
          <Field label="Condition" value={data.condition} onChange={(v) => update({ condition: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'buff':
      return (
        <>
          <SelectField label="Buff Type" value={data.buff_type} options={['timed', 'proc']} onChange={(v) => update({ buff_type: v } as Partial<EditorNodeData>)} />
          <NumberField label="Duration (s)" value={data.duration} onChange={(v) => update({ duration: v } as Partial<EditorNodeData>)} />
          <NumberField label="Proc Chance" value={data.proc_chance} onChange={(v) => update({ proc_chance: v } as Partial<EditorNodeData>)} step={0.01} />
          <NumberField label="Multiplier" value={data.multiplier} onChange={(v) => update({ multiplier: v } as Partial<EditorNodeData>)} />
          <Field label="Target" value={data.target} onChange={(v) => update({ target: v } as Partial<EditorNodeData>)} />
          <NumberField label="Cooldown (s)" value={data.cooldown} onChange={(v) => update({ cooldown: v } as Partial<EditorNodeData>)} />
        </>
      )

    case 'synergy':
      return (
        <>
          <FormulaField label="Formula" value={data.formula_expr} onChange={(v) => update({ formula_expr: v } as Partial<EditorNodeData>)} />
          <Field label="Target" value={data.target} onChange={(v) => update({ target: v } as Partial<EditorNodeData>)} />
        </>
      )

    default:
      return null
  }
}

// --- Main PropertyPanel ---

// --- Edge property fields ---

function EdgeFields({ edge, onUpdate }: { edge: Edge; onUpdate: (edgeId: string, data: Record<string, unknown>) => void }) {
  const edgeData = (edge.data ?? {}) as Record<string, unknown>
  const edgeType = (edgeData.edgeType as string) ?? 'resource_flow'

  function updateEdge(patch: Record<string, unknown>) {
    onUpdate(edge.id, { ...edgeData, ...patch })
  }

  return (
    <>
      <Field label="Edge Type" value={edgeType} readOnly />
      {edgeData.rate != null && (
        <NumberField label="Rate" value={edgeData.rate as number} onChange={(v) => updateEdge({ rate: v })} />
      )}
      {edgeData.formula != null && (
        <Field label="Formula" value={edgeData.formula as string} onChange={(v) => updateEdge({ formula: v })} />
      )}
      {edgeData.condition != null && (
        <Field label="Condition" value={edgeData.condition as string} onChange={(v) => updateEdge({ condition: v })} />
      )}
      {edgeType === 'state_modifier' && (
        <>
          <Field label="Target Property" value={(edgeData.target_property as string) ?? ''} onChange={(v) => updateEdge({ target_property: v })} />
          <SelectField label="Modifier Mode" value={(edgeData.modifier_mode as string) ?? 'multiply'} options={['set', 'add', 'multiply']} onChange={(v) => updateEdge({ modifier_mode: v })} />
        </>
      )}
    </>
  )
}

// --- Main PropertyPanel ---

interface PropertyPanelProps {
  selectedNode: Node<EditorNodeData> | null
  onUpdateNode: (nodeId: string, data: Partial<EditorNodeData>) => void
  allNodes: Node<EditorNodeData>[]
  selectedEdge?: Edge | null
  onUpdateEdge?: (edgeId: string, data: Record<string, unknown>) => void
}

export default function PropertyPanel({ selectedNode, onUpdateNode, allNodes, selectedEdge, onUpdateEdge }: PropertyPanelProps) {
  // Edge selected takes priority when no node is selected
  if (!selectedNode && selectedEdge && onUpdateEdge) {
    return (
      <div className="p-4 overflow-y-auto h-full">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Edge Properties
        </h3>
        <Field label="ID" value={selectedEdge.id} readOnly />
        <Field label="Source" value={selectedEdge.source} readOnly />
        <Field label="Target" value={selectedEdge.target} readOnly />
        <hr className="my-3 border-gray-200 dark:border-gray-700" />
        <EdgeFields edge={selectedEdge} onUpdate={onUpdateEdge} />
      </div>
    )
  }

  if (!selectedNode) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-gray-400 dark:text-gray-500 px-4 text-center">
        Select a node or edge to edit its properties
      </div>
    )
  }

  const data = selectedNode.data
  const nodeId = selectedNode.id

  const allTags = Array.from(
    new Set(allNodes.flatMap((n) => (n.data as EditorNodeData).tags ?? []))
  ).filter((t) => !data.tags.includes(t))

  function update(patch: Partial<EditorNodeData>) {
    onUpdateNode(nodeId, patch)
  }

  return (
    <div className="p-4 overflow-y-auto h-full">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
        Properties
      </h3>

      <Field label="ID" value={nodeId} readOnly />
      <Field label="Name" value={data.name} onChange={(v) => update({ name: v } as Partial<EditorNodeData>)} />
      <TagsField label="Tags" tags={data.tags} onChange={(tags) => update({ tags } as Partial<EditorNodeData>)} suggestions={allTags} />

      <hr className="my-3 border-gray-200 dark:border-gray-700" />

      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
        {data.nodeType.replace(/_/g, ' ')}
      </p>

      <TypeFields data={data} update={update} />
    </div>
  )
}
