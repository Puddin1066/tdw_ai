"use client";

import { useMemo } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { KnowledgeGraphData } from "@/types/artifacts";
import { EmptyState } from "@/components/EmptyState";

export interface KnowledgeGraphViewProps {
  graph: KnowledgeGraphData | null;
}

const nodeColors: Record<string, string> = {
  gene: "#2dd4bf",
  protein: "#38bdf8",
  disease: "#fb7185",
  compound: "#a78bfa",
  trial: "#fbbf24",
  publication: "#94a3b8",
  pathway: "#4ade80",
  biomarker: "#f472b6",
  organization: "#c084fc",
  other: "#64748b",
};

export function KnowledgeGraph({ graph }: KnowledgeGraphViewProps) {
  const { nodes, edges } = useMemo(() => {
    if (!graph?.nodes?.length) {
      return { nodes: [] as Node[], edges: [] as Edge[] };
    }

    const flowNodes: Node[] = graph.nodes.map((node, index) => ({
      id: node.node_id,
      data: { label: node.label },
      position: {
        x: (index % 4) * 180 + 40,
        y: Math.floor(index / 4) * 100 + 40,
      },
      style: {
        background: nodeColors[node.node_type] ?? "#64748b",
        color: "#0f172a",
        border: "1px solid rgba(255,255,255,0.15)",
        borderRadius: 8,
        fontSize: 12,
        padding: "8px 12px",
        minWidth: 100,
      },
    }));

    const flowEdges: Edge[] = (graph.edges ?? []).map((edge) => ({
      id: edge.edge_id,
      source: edge.source,
      target: edge.target,
      label: edge.relationship,
      animated: true,
      style: { stroke: "#64748b" },
    }));

    return { nodes: flowNodes, edges: flowEdges };
  }, [graph]);

  if (!graph || nodes.length === 0) {
    return (
      <EmptyState
        title="No knowledge graph"
        description="knowledge_graph.json is missing or has no nodes to visualize."
      />
    );
  }

  return (
    <div className="h-[480px] overflow-hidden rounded-lg border border-border bg-muted/10">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background gap={16} color="#334155" />
        <Controls />
        <MiniMap nodeStrokeWidth={2} pannable zoomable />
      </ReactFlow>
    </div>
  );
}
