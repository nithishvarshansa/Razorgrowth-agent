import { IconChevron } from './icons'

// Satellite nodes placed at compass points around the AI core.
const SATELLITES = [
  { x: 150, y: 40, label: 'Merchant Data' },
  { x: 258, y: 130, label: 'Evidence' },
  { x: 150, y: 220, label: 'Opportunity' },
  { x: 42, y: 130, label: 'Guardrail' },
]

export default function AIVisualization({ active = true }) {
  return (
    <div className="viz-wrap" aria-hidden="true">
      <svg viewBox="0 0 300 260" role="img" aria-label="Merchant data flowing into a central AI core, which reasons about evidence and guardrails to select a ranked opportunity">
        <defs>
          <radialGradient id="coreGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#c9c3ff" stopOpacity=".9" />
            <stop offset="100%" stopColor="#8b7ffb" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#8b7ffb" stopOpacity=".5" />
            <stop offset="100%" stopColor="#8b7ffb" stopOpacity="0" />
          </radialGradient>
        </defs>

        {SATELLITES.map((n) => (
          <line key={n.label} x1="150" y1="130" x2={n.x} y2={n.y} stroke="#4a4590" strokeWidth="1.3" opacity=".55" />
        ))}
        {active && SATELLITES.map((n, i) => (
          <line key={n.label + '-flow'} x1="150" y1="130" x2={n.x} y2={n.y} className="viz-flow-line" stroke="#c9c3ff" strokeWidth="1.4" opacity=".8" style={{ animationDelay: `${i * .3}s` }} />
        ))}

        {/* AI core */}
        <circle cx="150" cy="130" r="40" fill="url(#coreGlow)" opacity=".35" />
        {active && <circle cx="150" cy="130" r="16" className="viz-ring" fill="none" stroke="#8b7ffb" strokeWidth="1.2" />}
        <circle cx="150" cy="130" r="15" fill="#141026" stroke="#c9c3ff" strokeWidth="1.8" className={active ? 'viz-core' : ''} />
        <circle cx="150" cy="130" r="4" fill="#fff" />

        {SATELLITES.map((n, i) => (
          <g key={n.label} className={active ? 'viz-drift' : ''} style={{ animationDelay: `${i * .4}s` }}>
            <circle cx={n.x} cy={n.y} r="20" fill="url(#nodeGlow)" className="viz-glow" />
            <circle cx={n.x} cy={n.y} r="7" fill="#141826" stroke="#c9c3ff" strokeWidth="1.4" />
            <circle cx={n.x} cy={n.y} r="2.4" fill="#fff" />
            <text x={n.x} y={n.y + (n.y < 130 ? -16 : 26)} textAnchor="middle" className="viz-node-label">{n.label}</text>
          </g>
        ))}
      </svg>
      <div className="viz-caption">
        <b>Data</b><IconChevron width={10} height={10} /><b>Analysis</b><IconChevron width={10} height={10} /><b>Opportunity</b><IconChevron width={10} height={10} /><b>Action</b>
      </div>
    </div>
  )
}
