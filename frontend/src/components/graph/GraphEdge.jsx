import { BaseEdge, EdgeLabelRenderer, getBezierPath } from "reactflow";

function confidence(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return Math.round(value <= 1 ? value * 100 : value);
}

export default function GraphEdge({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data }) {
  const [path, labelX, labelY] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, curvature: 0.18 });
  const score = confidence(data?.confidence);

  return (
    <>
      <BaseEdge path={path} className="tn-intelligence-edge" />
      <EdgeLabelRenderer>
        <div className="tn-intelligence-edge-label" style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}>
          <span>{String(data?.relationshipType || "CONNECTED").replace(/_/g, " ")}</span>
          {score !== null && <small>{score}%</small>}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
