"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { GRAPH } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { type GraphData, type GraphNode } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, Badge, Spinner, EmptyState } from "@/components/ui/card";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  BackgroundVariant,
} from "reactflow";
import "reactflow/dist/style.css";
import { cn } from "@/lib/utils";
import { GitBranch, Users, Brain, FileText, Zap, CheckSquare, X } from "lucide-react";

const NODE_TYPE_CONFIG: Record<
  string,
  { color: string; bg: string; icon: React.ReactNode; label: string }
> = {
  person: { color: "#60a5fa", bg: "rgba(96,165,250,0.12)", icon: <Users size={10} />, label: "Person" },
  topic:  { color: "#a78bfa", bg: "rgba(167,139,250,0.12)", icon: <Brain size={10} />, label: "Topic" },
  decision: { color: "#f59e0b", bg: "rgba(245,158,11,0.12)", icon: <CheckSquare size={10} />, label: "Decision" },
  meeting: { color: "#4f7cff", bg: "rgba(79,124,255,0.12)", icon: <FileText size={10} />, label: "Meeting" },
  action: { color: "#34d399", bg: "rgba(52,211,153,0.12)", icon: <Zap size={10} />, label: "Action" },
  entity: { color: "#f472b6", bg: "rgba(244,114,182,0.12)", icon: <GitBranch size={10} />, label: "Entity" },
};

const NODE_TYPES_LIST = Object.keys(NODE_TYPE_CONFIG);

function buildFlowNodes(nodes: GraphNode[]): Node[] {
  return nodes.map((n, i) => {
    const config = NODE_TYPE_CONFIG[n.type] ?? NODE_TYPE_CONFIG.entity;
    const angle = (i / nodes.length) * 2 * Math.PI;
    const radius = 280 + (n.mention_count ?? 0) * 5;
    return {
      id: n.id,
      position: { x: 500 + radius * Math.cos(angle), y: 380 + radius * Math.sin(angle) },
      data: {
        label: (
          <div
            style={{
              background: config.bg,
              border: `1px solid ${config.color}40`,
              color: config.color,
              borderRadius: 8,
              padding: "5px 10px",
              fontSize: 11,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: 5,
              maxWidth: 140,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {config.icon}
            <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{n.label}</span>
          </div>
        ),
        rawNode: n,
      },
      style: { background: "transparent", border: "none", padding: 0 },
    };
  });
}

function buildFlowEdges(edges: { id: string; source: string; target: string; label?: string }[]): Edge[] {
  return edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    style: { stroke: "rgba(255,255,255,0.08)", strokeWidth: 1 },
    labelStyle: { fill: "rgba(156,163,175,0.8)", fontSize: 9 },
    animated: false,
  }));
}

export default function GraphPage() {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [activeTypes, setActiveTypes] = useState<Set<string>>(
    new Set(NODE_TYPES_LIST)
  );

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.graph.data(),
    queryFn: () => api.get<GraphData>(GRAPH.nodes()),
  });

  const filteredNodes = (data?.nodes ?? []).filter((n) => activeTypes.has(n.type));
  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = (data?.edges ?? []).filter(
    (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
  );

  const flowNodes = buildFlowNodes(filteredNodes);
  const flowEdges = buildFlowEdges(filteredEdges);

  const toggleType = (type: string) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    setSelectedNode((node.data as { rawNode: GraphNode }).rawNode);
  };

  return (
    <div className="space-y-4 animate-fade-in h-[calc(100vh-56px-48px)] flex flex-col">
      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap shrink-0">
        <span className="text-xs text-[var(--muted)] font-medium">Filter:</span>
        {NODE_TYPES_LIST.map((type) => {
          const config = NODE_TYPE_CONFIG[type];
          const active = activeTypes.has(type);
          return (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all",
                active
                  ? "border-transparent"
                  : "bg-transparent border-[var(--border)] text-[var(--muted)]"
              )}
              style={
                active
                  ? { background: config.bg, color: config.color, borderColor: `${config.color}40` }
                  : undefined
              }
            >
              {config.icon}
              {config.label}
              <span
                className="text-[9px] font-mono"
                style={{ color: active ? config.color : "var(--muted)" }}
              >
                {(data?.nodes ?? []).filter((n) => n.type === type).length}
              </span>
            </button>
          );
        })}
        <span className="ml-auto text-[10px] text-[var(--muted)]">
          {filteredNodes.length} nodes · {filteredEdges.length} edges
        </span>
      </div>

      {/* Graph */}
      <div className="flex gap-4 flex-1 min-h-0">
        <div className="flex-1 rounded-[var(--radius-md)] border border-[var(--border)] overflow-hidden relative">
          {isLoading ? (
            <div className="flex justify-center items-center h-full">
              <Spinner size={32} />
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="flex justify-center items-center h-full">
              <EmptyState
                icon={<GitBranch />}
                title="No graph data"
                description="Process meetings to populate the knowledge graph."
              />
            </div>
          ) : (
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              onNodeClick={handleNodeClick}
              fitView
              attributionPosition="bottom-left"
              minZoom={0.1}
            >
              <Background
                variant={BackgroundVariant.Dots}
                gap={20}
                size={1}
                color="rgba(255,255,255,0.04)"
              />
              <Controls />
              <MiniMap
                nodeColor={(n) => {
                  const raw = (n.data as { rawNode?: GraphNode })?.rawNode;
                  return raw ? NODE_TYPE_CONFIG[raw.type]?.color ?? "#6b7280" : "#6b7280";
                }}
              />
            </ReactFlow>
          )}
        </div>

        {/* Node Detail Panel */}
        {selectedNode && (
          <div className="w-64 animate-slide-in-right shrink-0">
            <Card className="h-full flex flex-col">
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <span style={{ color: NODE_TYPE_CONFIG[selectedNode.type]?.color }}>
                    {NODE_TYPE_CONFIG[selectedNode.type]?.icon}
                  </span>
                  Entity Detail
                </CardTitle>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="p-1 rounded text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
                  aria-label="Close"
                >
                  <X size={13} />
                </button>
              </CardHeader>
              <CardContent className="space-y-4 flex-1 overflow-y-auto">
                <div>
                  <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider mb-1">Label</p>
                  <p className="text-sm font-semibold text-[var(--foreground)]">{selectedNode.label}</p>
                </div>
                <div>
                  <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider mb-1">Type</p>
                  <Badge
                    style={{
                      color: NODE_TYPE_CONFIG[selectedNode.type]?.color,
                      background: NODE_TYPE_CONFIG[selectedNode.type]?.bg,
                    }}
                  >
                    {selectedNode.type}
                  </Badge>
                </div>
                {selectedNode.mention_count !== undefined && (
                  <div>
                    <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider mb-1">Mentions</p>
                    <p className="text-sm text-[var(--foreground)] font-mono">{selectedNode.mention_count}</p>
                  </div>
                )}
                {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
                  <div>
                    <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider mb-2">Metadata</p>
                    <div className="space-y-1.5">
                      {Object.entries(selectedNode.metadata).slice(0, 6).map(([k, v]) => (
                        <div key={k} className="flex justify-between gap-2 text-xs">
                          <span className="text-[var(--muted)] capitalize">{k.replace(/_/g, " ")}</span>
                          <span className="text-[var(--foreground)] font-mono truncate max-w-[100px]">
                            {String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
