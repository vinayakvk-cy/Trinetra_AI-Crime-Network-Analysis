import { useMemo } from "react";
import ReactFlow, { Background, Controls, MiniMap, Position } from "reactflow";
import { Network } from "lucide-react";
import "reactflow/dist/style.css";
import GraphNode from "./GraphNode";
import GraphEdge from "./GraphEdge";

const nodeTypes = { intelligence: GraphNode };
const edgeTypes = { intelligence: GraphEdge };

function norm(value) {
  return String(value ?? "").trim().toLowerCase();
}

function entity(record, side) {
  if (side === "source") {
    return {
      type: record.source_type ?? record.sourceType ?? record.start_type,
      value: record.source_value ?? record.sourceValue ?? record.start_value,
    };
  }
  return {
    type: record.target_type ?? record.targetType ?? record.neighbor_type ?? record.neighborType,
    value: record.target_value ?? record.targetValue ?? record.neighbor_value ?? record.neighborValue,
  };
}

function nodeId(type, value) {
  return `${norm(type)}:${norm(value)}`;
}

function nodeClass(type) {
  const value = norm(type);
  if (value === "person") return "tn-flow-node tn-flow-node-person";
  if (value === "organization" || value === "org") return "tn-flow-node tn-flow-node-organization";
  if (value === "bank") return "tn-flow-node tn-flow-node-bank";
  if (value === "case") return "tn-flow-node tn-flow-node-case";
  return "tn-flow-node tn-flow-node-default";
}

export default function InvestigationGraph({ relationships = [], loading = false, onNodeClick }) {
  const graph = useMemo(() => {
    const nodeMap = new Map();
    const edgeMap = new Map();
    const adjacency = new Map();

    relationships.forEach((record, index) => {
      const source = entity(record, "source");
      const target = entity(record, "target");
      if (!source?.value || !target?.value) return;

      const sourceId = nodeId(source.type, source.value);
      const targetId = nodeId(target.type, target.value);

      if (!nodeMap.has(sourceId)) {
        nodeMap.set(sourceId, {
          id: sourceId,
          type: "intelligence",
          position: { x: 0, y: 0 },
          className: nodeClass(source.type),
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          data: { type: source.type, value: source.value, label: source.value },
        });
      }
      if (!nodeMap.has(targetId)) {
        nodeMap.set(targetId, {
          id: targetId,
          type: "intelligence",
          position: { x: 0, y: 0 },
          className: nodeClass(target.type),
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          data: { type: target.type, value: target.value, label: target.value },
        });
      }

      const relationshipType = record.relationship_type ?? record.relationshipType ?? "CONNECTED";
      const confidence = record.confidence;
      const pair = [sourceId, targetId].sort().join("|");
      const edgeKey = `${pair}|${String(relationshipType).toUpperCase()}`;

      if (!edgeMap.has(edgeKey)) {
        edgeMap.set(edgeKey, {
          id: `edge-${edgeMap.size}-${index}`,
          source: sourceId,
          target: targetId,
          type: "intelligence",
          animated: true,
          data: {
            relationshipType,
            confidence,
            evidenceText: record.evidence_text ?? record.evidenceText ?? null,
          },
        });
      }

      if (!adjacency.has(sourceId)) adjacency.set(sourceId, new Set());
      if (!adjacency.has(targetId)) adjacency.set(targetId, new Set());
      adjacency.get(sourceId).add(targetId);
      adjacency.get(targetId).add(sourceId);
    });

    const nodes = Array.from(nodeMap.values());
    if (!nodes.length) return { nodes: [], edges: [] };

    // Stable topology-aware layout: focus/hub at left, then BFS layers to the right.
    const hub = nodes.reduce((best, node) => {
      const degree = adjacency.get(node.id)?.size ?? 0;
      const bestDegree = adjacency.get(best.id)?.size ?? -1;
      return degree > bestDegree ? node : best;
    }, nodes[0]);

    const layers = new Map([[hub.id, 0]]);
    const queue = [hub.id];
    while (queue.length) {
      const current = queue.shift();
      const currentLayer = layers.get(current);
      for (const next of adjacency.get(current) ?? []) {
        if (!layers.has(next)) {
          layers.set(next, currentLayer + 1);
          queue.push(next);
        }
      }
    }

    nodes.forEach((node) => {
      if (!layers.has(node.id)) layers.set(node.id, Math.max(...layers.values(), 0) + 1);
    });

    const grouped = new Map();
    nodes.forEach((node) => {
      const layer = layers.get(node.id) ?? 1;
      if (!grouped.has(layer)) grouped.set(layer, []);
      grouped.get(layer).push(node);
    });

    const positions = new Map();
    const columnGap = 300;
    const rowGap = 128;
    const baseY = 340;

    Array.from(grouped.keys()).sort((a, b) => a - b).forEach((layer) => {
      const group = grouped.get(layer);
      const x = layer * columnGap;
      const totalHeight = (group.length - 1) * rowGap;
      group.forEach((node, index) => {
        positions.set(node.id, {
          x,
          y: baseY - totalHeight / 2 + index * rowGap,
        });
      });
    });

    nodes.forEach((node) => {
      node.position = positions.get(node.id) ?? { x: 0, y: 0 };
    });

    return { nodes, edges: Array.from(edgeMap.values()) };
  }, [relationships]);

  if (loading && graph.nodes.length === 0) {
    return (
      <div className="tn-flow-empty">
        <div className="tn-flow-loading-orb" />
        <strong>Resolving live graph</strong>
        <span>Reading connected entities and relationships from Neo4j…</span>
      </div>
    );
  }

  if (!graph.nodes.length) {
    return (
      <div className="tn-flow-empty">
        <div className="tn-flow-empty-icon"><Network size={24} /></div>
        <strong>Graph workspace is ready</strong>
        <span>Choose any entity from the live registry and select Explore graph to populate this canvas.</span>
      </div>
    );
  }

  return (
    <div className="tn-flow-container">
      <ReactFlow
        nodes={graph.nodes}
        edges={graph.edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodeClick={(_, node) => onNodeClick?.(node.data, node)}
        fitView
        fitViewOptions={{ padding: 0.2, minZoom: 0.45, maxZoom: 1.15 }}
        minZoom={0.35}
        maxZoom={1.5}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        panOnDrag
        zoomOnScroll
        zoomOnPinch
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={24} size={1} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable nodeColor="var(--tn-cyan)" />
      </ReactFlow>
      <div className="tn-flow-overlay">
        <div><span>NODES</span><strong>{graph.nodes.length}</strong></div>
        <div><span>LINKS</span><strong>{graph.edges.length}</strong></div>
        <div><span>ENGINE</span><strong>NEO4J</strong></div>
      </div>
    </div>
  );
}
