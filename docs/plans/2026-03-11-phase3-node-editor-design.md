# Phase 3: React Flow Node Editor — Design Document

**Date:** 2026-03-11
**Status:** Approved
**Depends on:** Phase 2 + 4 (complete — 430 tests, FastAPI + React frontend)
**Parent design:** `docs/plans/2026-03-10-phases-2-3-4-design.md`

---

## Goal

Visual game designer using React Flow. Users drag-and-drop nodes, connect edges, edit properties, and see live analysis feedback via REST polling. This is the "design your own idle game" tool.

## Key Decisions

- **No WebSocket** — Frontend debounces edits (500ms) and POSTs to `POST /analysis/run` for live analysis. Simpler server, adequate latency.
- **All 16 node types** get custom React Flow node components. The editor is a general-purpose tool for any idle game, not tied to specific fixtures.
- **dagre** for auto-layout when loading existing games (lightweight, standard React Flow companion).
- **Plain textarea + live preview** for formula editing. No CodeMirror. Debounced parse validation shown inline.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Nav: [Play] [Analyze] [Editor]          [Save] [Load]  │
├──────────┬──────────────────────────────┬───────────────┤
│  Palette │  Canvas (React Flow)          │  Properties   │
│  ┌──────┐│                               │  ┌──────────┐│
│  │Resrc ││  ┌───────┐    ┌───────┐      │  │ Selected ││
│  │Gen   ││  │ Cash  │───▶│Lemon  │      │  │ Node     ││
│  │Upg   ││  └───────┘    │ Stand │      │  │          ││
│  │Prest ││               └───┬───┘      │  │ Fields.. ││
│  │Achiev││                   │           │  └──────────┘│
│  │Gate  ││               ┌───▼───┐      │               │
│  │Reg   ││               │ x3    │      │  Live Analysis│
│  │Conv  ││               │Lemon  │      │  ┌──────────┐│
│  │Queue ││               └───────┘      │  │ Prod: 5/s││
│  │...   ││                               │  │ Dead: 0  ││
│  └──────┘│                               │  │ Walls: 0 ││
│          │                               │  └──────────┘│
├──────────┴──────────────────────────────┴───────────────┤
│  Validation: ✓ Valid (2 nodes, 1 edge)  │ JSON Preview  │
└─────────────────────────────────────────────────────────┘
```

## Dependencies

```
@xyflow/react: ^12
@dagrejs/dagre: ^1
```

## Components

### Node Palette (left sidebar)

Categorized list of all 16 node types. Drag from palette onto canvas to create a node with sensible defaults.

**Categories:**
- **Resources:** Resource
- **Producers:** Generator, NestedGenerator, Converter
- **Modifiers:** Upgrade, Manager
- **Meta:** PrestigeLayer, SacrificeNode, Achievement, EndCondition
- **Control:** UnlockGate, Gate, ChoiceGroup, ProbabilityNode
- **Advanced:** Register, Queue

### Canvas (center)

React Flow canvas with 16 custom node components and 2 edge types.

**Edge types:**
- **Resource edges** (resource_flow, consumption, production_target): Solid colored lines
- **State edges** (state_modifier, activator, trigger, unlock_dependency, upgrade_target): Dashed lines

**Node colors:**
| Type | Color |
|------|-------|
| Resource | Blue |
| Generator, NestedGenerator | Green |
| Upgrade, Manager | Orange |
| PrestigeLayer, SacrificeNode | Purple |
| Achievement, EndCondition | Gold |
| UnlockGate, Gate, ChoiceGroup | Teal |
| ProbabilityNode | Pink |
| Register, Queue | Slate |
| Converter | Amber |

Each node displays its key fields inline (name, primary stat). Full editing via property panel.

Includes minimap (bottom-right) and zoom/pan controls.

### Custom Node Components (all 16)

Each node type gets a custom React Flow component showing type-appropriate summary info:

1. **ResourceNode** — name, icon
2. **GeneratorNode** — production/cycle, cost formula
3. **NestedGeneratorNode** — chain target, production
4. **UpgradeNode** — type, magnitude, target
5. **ManagerNode** — target, automation type
6. **PrestigeLayerNode** — formula preview, reset scope
7. **SacrificeNodeNode** — formula preview, sacrifice cost
8. **AchievementNode** — condition summary, bonus
9. **ConverterNode** — inputs → outputs, rate
10. **ProbabilityNodeNode** — probability, outcomes
11. **EndConditionNode** — target threshold
12. **UnlockGateNode** — prerequisites, condition
13. **GateNode** — condition, pass/fail behavior
14. **ChoiceGroupNode** — options count, max selections
15. **RegisterNode** — formula preview
16. **QueueNode** — capacity, processing time

### Property Panel (right sidebar)

Appears when a node or edge is selected. Form fields matching the Pydantic model for that type.

- Inline validation (red borders + error messages)
- Formula fields: plain textarea with debounced live parse preview (shows "Valid" or parse error)
- Stacking group: dropdown populated from game-level `stacking_groups`
- Tags: chip-style input (type + enter to add)
- Edge type: dropdown of valid edge types

### Live Analysis Panel (right sidebar, below properties)

- Triggers 500ms after last graph edit via `POST /analysis/run`
- Shows: total production rate, dead upgrades count, progression wall count, dominant strategy
- Status indicator: green checkmark (healthy), amber warning (walls/dead), red alert (validation errors)
- Expandable for full analysis details

### Validation Bar (bottom)

- Real-time: node count, edge count, validation status
- Mirrors `GameDefinition` Pydantic validation
- Errors: missing required fields, invalid edges, duplicate IDs, broken references
- Clicking an error highlights the affected node/edge on canvas

### Import / Export

- **Save:** React Flow graph → `GameDefinition` JSON → `POST /games/`
- **Load:** `GET /games/{id}` → parse → dagre auto-layout → place on canvas
- **JSON Preview:** Toggle panel showing live-updating raw game JSON
- **Download:** Export current game as `.json` file

## Data Flow

```
User edits graph
  → React Flow state updates (nodes[], edges[])
  → Convert to GameDefinition JSON (graphToGame)
  → Validate locally (field-level, required fields, edge refs)
  → Update validation bar
  → Debounce 500ms
  → POST /analysis/run with game JSON
  → Display results in Live Analysis panel
```

```
User loads game
  → GET /games/{id}
  → Convert GameDefinition → React Flow nodes/edges (gameToGraph)
  → Apply dagre auto-layout
  → Render on canvas
```

## Key Conversion Functions

Two core functions bridge React Flow and the game model:

- `graphToGame(nodes, edges, metadata)` → `GameDefinition` JSON
- `gameToGraph(game)` → `{ nodes: Node[], edges: Edge[] }` with dagre positions

These are pure functions, independently testable.

## Testing

| Layer | Tool | What |
|-------|------|------|
| Conversion functions | Vitest | graphToGame / gameToGraph round-trip, all 16 node types |
| Node components | Vitest + RTL | Render each of 16 types, verify displayed fields |
| Property panel | Vitest + RTL | Edit fields, verify validation, formula preview |
| Integration | Playwright | Create game from scratch, load existing, edit, save, verify analysis updates |

## Estimated Scope

~10-12 tasks, building incrementally:
1. React Flow setup + canvas + edge types
2. Node palette with drag-and-drop
3. Custom node components (batch 1: Resource, Generator, NestedGenerator, Upgrade, Manager, Converter)
4. Custom node components (batch 2: Prestige, Sacrifice, Achievement, EndCondition, ProbabilityNode)
5. Custom node components (batch 3: UnlockGate, Gate, ChoiceGroup, Register, Queue)
6. Property panel with validation + formula preview
7. Graph ↔ GameDefinition conversion functions + tests
8. Import/export (save, load with dagre layout, download)
9. Live analysis panel (debounced REST polling)
10. Validation bar with error highlighting
11. JSON preview panel
12. Polish + Playwright E2E tests
