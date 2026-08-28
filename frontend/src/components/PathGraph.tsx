import { useMemo } from 'react'
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from 'reactflow'
import 'reactflow/dist/style.css'
import type { LearningPath } from '../api/types'

const NODE_TYPES = {}
const EDGE_TYPES = {}

const ROW_HEIGHT = 130
const TOP_PADDING = 60
const LEFT_X = 40
const RIGHT_X = 340
const NODE_WIDTH = 250

export default function PathGraph({ path }: { path: LearningPath | null }) {
  const { nodes, edges, canvasHeight } = useMemo(() => {
    if (!path || !path.steps) return { nodes: [] as Node[], edges: [] as Edge[], canvasHeight: 0 }

    const newNodes: Node[] = path.steps.map((step, i) => ({
      id: step.skill_id,
      position: { x: i % 2 === 0 ? LEFT_X : RIGHT_X, y: i * ROW_HEIGHT + TOP_PADDING },
      data: {
        label: (
          <div style={{ padding: '10px', textAlign: 'center' }}>
            <strong>{step.order}. {step.skill_name}</strong>
            <div style={{ fontSize: '0.8rem', color: '#b8461f', marginTop: '4px', fontWeight: 600 }}>
              {step.estimated_weeks} weeks
            </div>
          </div>
        ),
      },
      style: {
        background: '#ffffff', color: '#241d12', border: '1.5px solid #241d12',
        borderRadius: '10px', width: NODE_WIDTH, boxShadow: '2px 2px 0 rgba(36,29,18,0.08)',
      },
    }))

    const newEdges: Edge[] = []
    for (let i = 0; i < path.steps.length - 1; i++) {
      newEdges.push({
        id: `e-${path.steps[i].skill_id}-${path.steps[i + 1].skill_id}`,
        source: path.steps[i].skill_id,
        target: path.steps[i + 1].skill_id,
        animated: true,
        style: { stroke: '#d15633', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#d15633' },
      })
    }

    // Sized to the content — fitView only needs to center it, never shrink
    // nodes below a readable size the way a fixed-height box forced it to.
    const canvasHeight = path.steps.length * ROW_HEIGHT + TOP_PADDING * 2

    return { nodes: newNodes, edges: newEdges, canvasHeight }
  }, [path])

  if (!path) return null

  return (
    <div className="panel" style={{ padding: 0 }}>
      <div style={{ padding: '20px', borderBottom: '1px solid #e8dcc4', background: 'var(--panel-bg)' }}>
        <h2 style={{ margin: 0 }}>Interactive Learning Path ({path.total_weeks} weeks)</h2>
        <p className="hint" style={{ margin: 0 }}>{path.rationale}</p>
      </div>
      <div className="rf-canvas" style={{ width: '100%', height: `${canvasHeight}px` }}>
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={NODE_TYPES} edgeTypes={EDGE_TYPES} fitView>
          <Background color="#e8dcc4" gap={16} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  )
}
