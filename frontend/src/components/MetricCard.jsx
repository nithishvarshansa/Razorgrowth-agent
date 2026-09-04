export default function MetricCard({ icon: Icon, label, value, foot, loading }) {
  return (
    <div className="metric-card">
      <div className="m-head">
        {label}
        <span className="m-icon"><Icon width={15} height={15} /></span>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 28, width: '55%', marginTop: 14 }} />
      ) : (
        <div className={'m-value' + (value === '--' ? ' dim' : ' gradient-text')}>{value}</div>
      )}
      {foot && !loading && <div className="m-foot">{foot}</div>}
    </div>
  )
}
