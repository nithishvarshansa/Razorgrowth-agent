import { IconActivity, IconAnalytics, IconClock, IconOverview, IconPipeline, IconSettings, IconStrategy } from './icons'

const NAV = [
  { id: 'overview', label: 'Overview', icon: IconOverview },
  { id: 'growth-strategy', label: 'Growth Strategy', icon: IconStrategy },
  { id: 'opportunities', label: 'Opportunities', icon: IconPipeline },
  { id: 'agent-activity', label: 'Agent Activity', icon: IconActivity },
  { id: 'experiment-history', label: 'Experiment History', icon: IconClock },
  { id: 'analytics', label: 'Analytics', icon: IconAnalytics },
  { id: 'settings', label: 'Settings', icon: IconSettings },
]

export default function Sidebar({ active, razorpayConnected }) {
  return (
    <aside className="sidebar">
      <a className="sidebar-brand" href="#overview">
        <span className="mark">AI</span>
        <span className="name">RAZORGROWTH<br />AGENT</span>
      </a>
      <nav className="sidebar-nav">
        {NAV.map(({ id, label, icon: Icon }) => (
          <a key={id} href={`#${id}`} className={'nav-item' + (active === id ? ' active' : '')} aria-label={label} title={label}>
            <Icon /> <span className="nav-label">{label}</span>
          </a>
        ))}
      </nav>
      <div className="sidebar-foot">
        <div className={'razorpay-status' + (razorpayConnected ? ' on' : '')}>
          <span className="rz-dot" />
          <span className="rz-text">
            <b>Razorpay</b>
            <span>{razorpayConnected ? 'Connected' : 'Unavailable'}</span>
          </span>
        </div>
      </div>
    </aside>
  )
}
