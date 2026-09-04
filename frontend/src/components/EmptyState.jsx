export default function EmptyState({ icon: Icon, title, description, actionLabel, onAction, actionBusy }) {
  return (
    <div className="empty">
      {Icon && <div className="empty-icon"><Icon width={20} height={20} /></div>}
      <h3>{title}</h3>
      <p>{description}</p>
      {actionLabel && (
        <button className="btn btn-primary" onClick={onAction} disabled={actionBusy}>
          {actionBusy && <span className="spinner" />}
          {actionBusy ? 'Working…' : actionLabel}
        </button>
      )}
    </div>
  )
}
