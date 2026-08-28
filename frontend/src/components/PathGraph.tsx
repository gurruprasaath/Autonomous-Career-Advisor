import { useMemo } from 'react'
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from 'reactflow'
import 'reactflow/dist/style.css'
import type { LearningPath } from '../api/types'

const NODE_TYPES = {}
const EDGE_TYPES = {}

export default function PathGraph({ path }: { path: LearningPath | null }) {
  const { nodes, edges } = useMemo(() => {
    if (!path || !path.steps) return { nodes: [] as Node[], edges: [] as Edge[] }

    const newNodes: Node[] = path.steps.map((step, i) => ({
      id: step.skill_id,
      position: { x: 250, y: i * 150 + 50 },
      data: {
        label: (
          <div style={{ padding: '10px', textAlign: 'center' }}>
            <strong>{step.order}. {step.skill_name}</strong>
            <div style={{ fontSize: '0.8rem', color: '#d3a02a', marginTop: '4px' }}>
              {step.estimated_weeks} weeks
            </div>
          </div>
        ),
      },
      style: {
        background: 'rgba(36, 29, 18, 0.85)', color: '#fbf5ea', border: '1px solid #6e6248',
        borderRadius: '10px', width: 250, backdropFilter: 'blur(12px)',
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

    return { nodes: newNodes, edges: newEdges }
  }, [path])

  if (!path) return null

  return (
    <div className="panel" style={{ height: '600px', padding: 0 }}>
      <div style={{ padding: '20px', borderBottom: '1px solid #e8dcc4', background: 'var(--panel-bg)' }}>
        <h2 style={{ margin: 0 }}>Interactive Learning Path ({path.total_weeks} weeks)</h2>
        <p className="hint" style={{ margin: 0 }}>{path.rationale}</p>
      </div>
      <div style={{ width: '100%', height: 'calc(100% - 80px)' }}>
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={NODE_TYPES} edgeTypes={EDGE_TYPES} fitView>
          <Background color="#e8dcc4" gap={16} />
          <Controls style={{ background: '#241d12', fill: '#fbf5ea' }} />
        </ReactFlow>
      </div>
    </div>
  )
}
