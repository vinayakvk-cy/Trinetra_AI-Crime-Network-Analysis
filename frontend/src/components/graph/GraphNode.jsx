import { Handle, Position } from "reactflow";
import { Building2, Landmark, Network, UserRound } from "lucide-react";

function icon(type) {
  const value = String(type || "").toLowerCase();
  if (value === "person") return <UserRound size={15} />;
  if (value === "organization" || value === "org") return <Building2 size={15} />;
  if (value === "bank") return <Landmark size={15} />;
  return <Network size={15} />;
}

function label(type) {
  return String(type || "ENTITY").replace(/_/g, " ").toUpperCase();
}

export default function GraphNode({ data }) {
  return (
    <div className="tn-intelligence-node">
      <Handle type="target" position={Position.Left} className="tn-node-handle" />
      <div className="tn-node-icon">{icon(data.type)}</div>
      <div className="tn-node-copy">
        <span>{label(data.type)}</span>
        <strong title={data.value}>{data.value}</strong>
      </div>
      <Handle type="source" position={Position.Right} className="tn-node-handle" />
    </div>
  );
}
