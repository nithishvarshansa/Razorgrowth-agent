import { IconRefresh } from './icons'

const TITLES = {
  overview: 'Overview',
  'growth-strategy': 'Growth Strategy',
  opportunities: 'Opportunities',
  'agent-activity': 'Agent Activity',
  'experiment-history': 'Experiment History',
  analytics: 'Analytics',
  settings: 'Settings',
}

export default function Header({ active, razorpayConnected, onRefresh, refreshing }) {
  return (
    <header className="topbar">
      <div className="titles">
        <small>Merchant workspace</small>
        <h1>{TITLES[active] || 'Overview'}</h1>
      </div>
      <span className="badge badge-test"><span className="ring" />TEST MODE · Razorpay Test Environment</span>
      <span className={'conn-pill' + (razorpayConnected ? ' on' : '')}><span className="dot" />{razorpayConnected ? 'Razorpay connected' : 'Razorpay unavailable'}</span>
      <button className="btn-ghost-icon" onClick={onRefresh} disabled={refreshing} aria-label={refreshing ? 'Refreshing' : 'Refresh'}>
        <IconRefresh style={refreshing ? { animation: 'spin .8s linear infinite' } : undefined} /> <span className="btn-label">{refreshing ? 'Refreshing…' : 'Refresh'}</span>
      </button>
      <span className="workspace-chip" title="Merchant workspace">M</span>
    </header>
  )
}
