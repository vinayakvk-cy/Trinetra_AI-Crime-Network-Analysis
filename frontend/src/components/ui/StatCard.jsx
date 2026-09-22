export default function StatCard({ icon, label, value, meta }) {
  return (
    <div className="tn-glass tn-stat-card">
      <div className="tn-stat-card-icon">{icon}</div>
      <div className="tn-stat-card-body">
        <span className="tn-stat-card-label">{label}</span>
        <strong className="tn-stat-card-value">{value ?? "—"}</strong>
        {meta ? <small className="tn-stat-card-meta">{meta}</small> : null}
      </div>
    </div>
  );
}
