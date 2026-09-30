"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { GRAPH } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import {
  type GraphData,
  type GraphNode,
  type GraphEdge,
  type GraphMetrics,
  type GraphNodeCitation,
  type GraphChatResponse,
  type GraphSyncResponse,
} from "@/lib/types";
import { PageHeader } from "@/components/ui/page-header";
import { Spinner, EmptyState } from "@/components/ui/card";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  BackgroundVariant,
  Handle,
  Position,
  useReactFlow,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import { cn } from "@/lib/utils";
import {
  GitBranch,
  Users,
  Brain,
  FileText,
  Zap,
  CheckSquare,
  X,
  RefreshCw,
  Search,
  Sparkles,
  Send,
  Bot,
  User,
  Plus,
  Trash2,
  Layers,
  CheckCircle2,
  Network,
  HelpCircle,
  Compass,
  ArrowRight,
  Filter,
  RotateCcw,
} from "lucide-react";

// ─── Visual Tokens & Type Configurations ──────────────────────────────────────

const NODE_TYPE_CONFIG: Record<
  string,
  {
    color: string;
    bg: string;
    border: string;
    badgeBg: string;
    icon: React.ReactNode;
    label: string;
    column: number;
  }
> = {
  meeting: {
    color: "#4f46e5",
    bg: "#eef2ff",
    border: "#c7d2fe",
    badgeBg: "bg-indigo-50 text-indigo-700 border-indigo-200",
    icon: <FileText size={12} />,
    label: "Meeting",
    column: 0,
  },
  decision: {
    color: "#d97706",
    bg: "#fffbeb",
    border: "#fde68a",
    badgeBg: "bg-amber-50 text-amber-700 border-amber-200",
    icon: <CheckSquare size={12} />,
    label: "Decision",
    column: 1,
  },
  action: {
    color: "#059669",
    bg: "#ecfdf5",
    border: "#a7f3d0",
    badgeBg: "bg-emerald-50 text-emerald-700 border-emerald-200",
    icon: <Zap size={12} />,
    label: "Action",
    column: 2,
  },
  person: {
    color: "#2563eb",
    bg: "#eff6ff",
    border: "#bfdbfe",
    badgeBg: "bg-blue-50 text-blue-700 border-blue-200",
    icon: <Users size={12} />,
    label: "Person",
    column: 3,
  },
  topic: {
    color: "#7c3aed",
    bg: "#f5f3ff",
    border: "#ddd6fe",
    badgeBg: "bg-purple-50 text-purple-700 border-purple-200",
    icon: <Brain size={12} />,
    label: "Topic",
    column: 3,
  },
  entity: {
    color: "#db2777",
    bg: "#fdf2f8",
    border: "#fbcfe8",
    badgeBg: "bg-pink-50 text-pink-700 border-pink-200",
    icon: <GitBranch size={12} />,
    label: "Entity",
    column: 3,
  },
};

const NODE_TYPES_LIST = Object.keys(NODE_TYPE_CONFIG);

const COLUMNS_DEF = [
  { id: 0, label: "1. Meetings & Syncs", color: "#4f46e5", bg: "bg-indigo-50/70 border-indigo-200 text-indigo-800" },
  { id: 1, label: "2. Confirmed Decisions", color: "#d97706", bg: "bg-amber-50/70 border-amber-200 text-amber-800" },
  { id: 2, label: "3. Action Commitments", color: "#059669", bg: "bg-emerald-50/70 border-emerald-200 text-emerald-800" },
  { id: 3, label: "4. Owners & Topics", color: "#2563eb", bg: "bg-blue-50/70 border-blue-200 text-blue-800" },
];

// ─── Custom ReactFlow Node Component ─────────────────────────────────────────

interface CustomNodeData {
  rawNode: GraphNode;
  isSelected: boolean;
  isDimmed: boolean;
}

const CustomNode = React.memo(({ data }: { data: CustomNodeData }) => {
  const { rawNode, isSelected, isDimmed } = data;
  const config = NODE_TYPE_CONFIG[rawNode.type] ?? NODE_TYPE_CONFIG.entity;
  const statusMeta = (rawNode.metadata?.status as string) || (rawNode.metadata?.priority as string);

  return (
    <div
      className={cn(
        "group relative flex flex-col justify-between w-[250px] p-3 rounded-xl border bg-white shadow-2xs transition-all duration-150 cursor-pointer select-none",
        isSelected
          ? "ring-2 ring-indigo-500 shadow-md scale-102 z-20 border-indigo-500"
          : "hover:scale-101 hover:shadow-xs z-10 border-slate-200/90",
        isDimmed && "opacity-25 filter grayscale"
      )}
      style={{
        borderLeftWidth: 4,
        borderLeftColor: config.color,
      }}
    >
      {/* Left Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="opacity-0 w-2 h-2 pointer-events-none"
      />

      {/* Header Row */}
      <div className="flex items-center justify-between gap-1.5 mb-1.5">
        <div className="flex items-center gap-1.5">
          <div
            className="w-5 h-5 rounded-md flex items-center justify-center shrink-0 text-white shadow-2xs text-[10px]"
            style={{ backgroundColor: config.color }}
          >
            {config.icon}
          </div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            {config.label}
          </span>
        </div>

        {statusMeta && (
          <span className="text-[9px] font-mono px-1.5 py-0.2 rounded-md bg-slate-100 border border-slate-200 text-slate-600 truncate max-w-[85px]">
            {statusMeta}
          </span>
        )}
      </div>

      {/* Main Label */}
      <p
        className="text-xs font-semibold text-slate-900 leading-snug line-clamp-2"
        title={rawNode.label}
      >
        {rawNode.label}
      </p>

      {/* Footer Meta Row */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 mt-2 pt-1.5 border-t border-slate-100">
        <span className="truncate max-w-[130px]">
          {rawNode.metadata?.assignee
            ? `Owner: ${String(rawNode.metadata.assignee)}`
            : rawNode.metadata?.decided_by
            ? `By: ${String(rawNode.metadata.decided_by)}`
            : String(rawNode.metadata?.date || "Workspace")}
        </span>
        {rawNode.mention_count !== undefined && (
          <span className="font-mono text-indigo-600 font-medium shrink-0">
            {rawNode.mention_count} links
          </span>
        )}
      </div>

      {/* Right Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="opacity-0 w-2 h-2 pointer-events-none"
      />
    </div>
  );
});

CustomNode.displayName = "CustomNode";

const nodeTypes = {
  customNode: CustomNode,
};

// ─── Hierarchical Left-to-Right Column Layout Algorithm ──────────────────────

function buildHierarchicalFlow(
  nodes: GraphNode[],
  edges: GraphEdge[],
  selectedNodeId: string | null,
  searchQuery: string,
  selectedMeetingId: string,
  allNodes: GraphNode[] = nodes
): { flowNodes: Node[]; flowEdges: Edge[] } {
  const q = searchQuery.toLowerCase().trim();

  let activeNodes = nodes;
  let activeEdges = edges;

  // If a specific meeting is selected, strictly isolate that meeting's lineage DAG
  if (selectedMeetingId !== "ALL") {
    // 1. Locate the target meeting node from allNodes
    const targetMeeting = allNodes.find(
      (n) =>
        n.id === selectedMeetingId ||
        (n.type === "meeting" && String(n.metadata?.meeting_id) === selectedMeetingId) ||
        (n.type === "meeting" && n.label.trim().toLowerCase() === selectedMeetingId.trim().toLowerCase())
    );

    if (targetMeeting) {
      const entityMeetingId = targetMeeting.id;
      const dbMeetingId = targetMeeting.metadata?.meeting_id
        ? String(targetMeeting.metadata.meeting_id)
        : null;

      // Group sibling meeting entity IDs (e.g. if meeting has multiple entity records)
      const siblingMeetingIds = new Set<string>([entityMeetingId]);
      allNodes.forEach((n) => {
        if (n.type !== "meeting") return;
        if (dbMeetingId && String(n.metadata?.meeting_id) === dbMeetingId) {
          siblingMeetingIds.add(n.id);
        } else if (
          targetMeeting.label &&
          n.label.trim().toLowerCase() === targetMeeting.label.trim().toLowerCase()
        ) {
          siblingMeetingIds.add(n.id);
        }
      });

      // 2. Identify Decisions strictly belonging to this meeting
      const meetingDecisions = nodes.filter((n) => {
        if (n.type !== "decision") return false;
        if (dbMeetingId && String(n.metadata?.meeting_id) === dbMeetingId) return true;
        if (siblingMeetingIds.has(String(n.metadata?.meeting_id))) return true;
        return edges.some(
          (e) =>
            (siblingMeetingIds.has(e.source) && e.target === n.id) ||
            (siblingMeetingIds.has(e.target) && e.source === n.id) ||
            (dbMeetingId && e.meeting_id === dbMeetingId && (e.source === n.id || e.target === n.id)) ||
            (siblingMeetingIds.has(String(e.meeting_id)) && (e.source === n.id || e.target === n.id))
        );
      });
      const meetingDecisionIds = new Set(meetingDecisions.map((d) => d.id));

      // 3. Identify Actions strictly belonging to this meeting or its decisions
      const meetingActions = nodes.filter((n) => {
        if (n.type !== "action") return false;
        if (dbMeetingId && String(n.metadata?.meeting_id) === dbMeetingId) return true;
        if (siblingMeetingIds.has(String(n.metadata?.meeting_id))) return true;
        // Direct edge with meeting
        const hasMeetingEdge = edges.some(
          (e) =>
            (siblingMeetingIds.has(e.source) && e.target === n.id) ||
            (siblingMeetingIds.has(e.target) && e.source === n.id) ||
            (dbMeetingId && e.meeting_id === dbMeetingId && (e.source === n.id || e.target === n.id)) ||
            (siblingMeetingIds.has(String(e.meeting_id)) && (e.source === n.id || e.target === n.id))
        );
        if (hasMeetingEdge) return true;
        // Connected to any decision belonging to this meeting
        return edges.some(
          (e) =>
            (meetingDecisionIds.has(e.source) && e.target === n.id) ||
            (meetingDecisionIds.has(e.target) && e.source === n.id)
        );
      });
      const meetingActionIds = new Set(meetingActions.map((a) => a.id));

      // 4. Identify Connected Entities (People, Topics, Entities)
      // Exclude ALL meetings so ONLY targetMeeting appears in Column 0
      const meetingOtherEntities = nodes.filter((n) => {
        if (n.type === "meeting" || n.type === "decision" || n.type === "action") return false;

        // Connected to this meeting
        const hasEdgeToMeeting = edges.some(
          (e) =>
            (siblingMeetingIds.has(e.source) && e.target === n.id) ||
            (siblingMeetingIds.has(e.target) && e.source === n.id)
        );
        if (hasEdgeToMeeting) return true;

        // Connected to this meeting's decisions
        const hasEdgeToDecision = edges.some(
          (e) =>
            (meetingDecisionIds.has(e.source) && e.target === n.id) ||
            (meetingDecisionIds.has(e.target) && e.source === n.id)
        );
        if (hasEdgeToDecision) return true;

        // Connected to this meeting's actions
        const hasEdgeToAction = edges.some(
          (e) =>
            (meetingActionIds.has(e.source) && e.target === n.id) ||
            (meetingActionIds.has(e.target) && e.source === n.id)
        );
        if (hasEdgeToAction) return true;

        // Explicitly tagged with this meeting's ID
        if (dbMeetingId) {
          return edges.some(
            (e) =>
              (e.meeting_id === dbMeetingId || siblingMeetingIds.has(String(e.meeting_id))) &&
              (e.source === n.id || e.target === n.id)
          );
        }

        return false;
      });

      // Assemble strictly isolated activeNodes: exactly 1 meeting node in Column 0!
      activeNodes = [
        targetMeeting,
        ...meetingDecisions,
        ...meetingActions,
        ...meetingOtherEntities,
      ];

      // Normalize edges: rewire any sibling meeting references to targetMeeting.id
      const scopedIds = new Set(activeNodes.map((n) => n.id));
      const normalizedEdges: GraphEdge[] = [];

      edges.forEach((e) => {
        let src = e.source;
        let tgt = e.target;
        if (siblingMeetingIds.has(src)) src = targetMeeting.id;
        if (siblingMeetingIds.has(tgt)) tgt = targetMeeting.id;

        if (scopedIds.has(src) && scopedIds.has(tgt) && src !== tgt) {
          normalizedEdges.push({
            ...e,
            source: src,
            target: tgt,
          });
        }
      });

      activeEdges = normalizedEdges;
    }
  }

  // Partition nodes into 4 structured columns
  const colGroups: Record<number, GraphNode[]> = { 0: [], 1: [], 2: [], 3: [] };
  activeNodes.forEach((n) => {
    const colIdx = NODE_TYPE_CONFIG[n.type]?.column ?? 3;
    colGroups[colIdx].push(n);
  });

  const COLUMN_X = [50, 370, 690, 1010];
  const flowNodes: Node[] = [];

  // Determine which nodes match search query
  const matchingIds = new Set(
    q ? activeNodes.filter((n) => n.label.toLowerCase().includes(q)).map((n) => n.id) : []
  );

  const maxRows = Math.max(
    colGroups[1].length,
    colGroups[2].length,
    colGroups[3].length,
    1
  );

  // Position nodes within columns
  [0, 1, 2, 3].forEach((colIdx) => {
    const group = colGroups[colIdx];
    const xPos = COLUMN_X[colIdx];

    // For Column 0 when a single meeting is isolated, vertically center it alongside decisions
    const isSingleMeeting = colIdx === 0 && group.length === 1 && maxRows > 1;
    const baseY = isSingleMeeting ? 70 + Math.min(220, ((maxRows - 1) * 105) / 2) : 70;

    group.forEach((node, rowIdx) => {
      const isSelected = node.id === selectedNodeId;
      const isDimmed = Boolean(q && !matchingIds.has(node.id));

      flowNodes.push({
        id: node.id,
        position: {
          x: xPos,
          y: baseY + rowIdx * 105,
        },
        data: { rawNode: node, isSelected, isDimmed },
        type: "customNode",
      });
    });
  });

  // Build clean, unidirectional left-to-right edges
  const activeNodeIds = new Set(activeNodes.map((n) => n.id));
  const nodeColMap = new Map<string, number>();
  activeNodes.forEach((n) => {
    nodeColMap.set(n.id, NODE_TYPE_CONFIG[n.type]?.column ?? 3);
  });

  const flowEdges: Edge[] = [];
  const seenEdges = new Set<string>();

  activeEdges.forEach((e) => {
    if (!activeNodeIds.has(e.source) || !activeNodeIds.has(e.target)) return;

    let src = e.source;
    let tgt = e.target;
    const colSrc = nodeColMap.get(src) ?? 0;
    const colTgt = nodeColMap.get(tgt) ?? 0;

    // Direct all edges Left ➔ Right
    if (colSrc > colTgt) {
      src = e.target;
      tgt = e.source;
    }

    const edgeKey = `${src}__${tgt}`;
    if (seenEdges.has(edgeKey)) return;
    seenEdges.add(edgeKey);

    const isConnected =
      Boolean(selectedNodeId) &&
      (src === selectedNodeId || tgt === selectedNodeId);

    flowEdges.push({
      id: e.id,
      source: src,
      target: tgt,
      type: "smoothstep",
      label: e.label?.replace(/_/g, " "),
      style: {
        stroke: isConnected ? "#4f46e5" : "#cbd5e1",
        strokeWidth: isConnected ? 2.5 : 1.2,
      },
      labelStyle: {
        fill: isConnected ? "#4338ca" : "#64748b",
        fontSize: 9,
        fontWeight: isConnected ? 700 : 500,
      },
      animated: isConnected,
    });
  });

  return { flowNodes, flowEdges };
}

// ─── Copilot Chat Interfaces & Storage ───────────────────────────────────────

interface GraphChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  citations?: GraphNodeCitation[];
}

interface GraphChatSession {
  id: string;
  title: string;
  updatedAt: string;
  messages: GraphChatMessage[];
}

const STORAGE_KEY = "knowra_graph_copilot_sessions_v1";

const DEFAULT_GRAPH_SESSIONS: GraphChatSession[] = [
  {
    id: "session-default",
    title: "Knowledge Graph Lineage Copilot",
    updatedAt: "Just now",
    messages: [
      {
        id: "msg-welcome",
        role: "assistant",
        content:
          "Welcome to the **Knowledge Graph Intelligence Copilot**.\n\nYour organizational knowledge is laid out in a clean **Left-to-Right Lineage Flow** (Meetings ➔ Decisions ➔ Actions ➔ Owners & Topics).\n\nAsk me any question about architecture decisions, commitments, or click a citation pill to inspect that entity.",
        timestamp: "Just now",
      },
    ],
  },
];

const SUGGESTED_QUERIES = [
  "What decisions were confirmed regarding PostgreSQL and cloud architecture?",
  "Who are the key contributors and what action items are assigned to Sujal?",
  "Which architectural topics have the highest inter-meeting centrality?",
  "Summarize active engineering commitments across recent syncs",
];

// ─── Canvas Subcomponent (useReactFlow hook access) ──────────────────────────

function GraphCanvas({
  nodes,
  edges,
  selectedNode,
  onSelectNode,
  onOpenCopilotWithQuery,
  selectedMeetingId,
  scopedMeetingName,
}: {
  nodes: Node[];
  edges: Edge[];
  selectedNode: GraphNode | null;
  onSelectNode: (node: GraphNode | null) => void;
  onOpenCopilotWithQuery: (q: string) => void;
  selectedMeetingId: string;
  scopedMeetingName: string | null;
}) {
  const reactFlow = useReactFlow();

  // Smoothly center and fit view whenever selected meeting scope changes
  useEffect(() => {
    const timer = setTimeout(() => {
      reactFlow.fitView({ padding: 0.25, duration: 400 });
    }, 60);
    return () => clearTimeout(timer);
  }, [selectedMeetingId, reactFlow]);

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    const raw = (node.data as CustomNodeData)?.rawNode;
    if (raw) {
      onSelectNode(raw);
    }
  };

  return (
    <div className="relative w-full h-[660px] bg-slate-50/70 rounded-2xl overflow-hidden border border-slate-200/90 shadow-2xs">
      {/* Visual Column Headers Banner */}
      <div className="absolute top-0 left-0 right-0 z-10 grid grid-cols-4 gap-2 px-6 py-2.5 bg-white/90 backdrop-blur-xs border-b border-slate-200/80 pointer-events-none">
        {COLUMNS_DEF.map((col) => (
          <div key={col.id} className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: col.color }}
            />
            <span className="text-xs font-bold text-slate-700 tracking-tight">
              {col.label}
            </span>
          </div>
        ))}
      </div>

      {/* Scoped Meeting Indicator Badge */}
      {selectedMeetingId !== "ALL" && scopedMeetingName && (
        <div className="absolute top-12 right-4 z-10 flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/95 border border-indigo-200/90 shadow-sm backdrop-blur-xs text-xs font-medium text-slate-700 pointer-events-none">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-semibold text-indigo-700 truncate max-w-[200px]">
            {scopedMeetingName}
          </span>
          <span className="text-slate-300">|</span>
          <span className="text-slate-500 text-[11px] font-mono">
            {nodes.length} entities
          </span>
        </div>
      )}

      {/* Friendly Single Node Note */}
      {selectedMeetingId !== "ALL" && nodes.length === 1 && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none text-center bg-white/90 backdrop-blur-xs border border-slate-200 rounded-2xl p-6 shadow-sm max-w-sm">
          <div className="w-8 h-8 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-2">
            <GitBranch size={16} />
          </div>
          <p className="text-xs font-semibold text-slate-800">Isolated Meeting Node</p>
          <p className="text-[11px] text-slate-500 mt-1">
            No confirmed decisions or action items have been mapped to this sync yet.
          </p>
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onPaneClick={() => onSelectNode(null)}
        fitView
        attributionPosition="bottom-left"
        minZoom={0.15}
        maxZoom={2.0}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1.2}
          color="#cbd5e1"
        />
        <Controls
          position="bottom-left"
          className="bg-white border border-slate-200 shadow-sm rounded-lg overflow-hidden text-slate-700"
        />
        <MiniMap
          position="bottom-right"
          className="rounded-lg overflow-hidden border border-slate-200 shadow-sm bg-white"
          nodeColor={(n) => {
            const raw = (n.data as CustomNodeData)?.rawNode;
            return raw ? NODE_TYPE_CONFIG[raw.type]?.color ?? "#64748b" : "#64748b";
          }}
          maskColor="rgba(241, 245, 249, 0.75)"
        />
      </ReactFlow>

      {/* Selected Node Floating Inspector */}
      {selectedNode && (
        <div className="absolute top-14 left-4 z-20 w-80 animate-in fade-in slide-in-from-left-2 duration-150 bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden flex flex-col max-h-[calc(100%-80px)]">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/70">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="w-5 h-5 rounded-md flex items-center justify-center text-white shrink-0 text-xs"
                style={{
                  backgroundColor:
                    NODE_TYPE_CONFIG[selectedNode.type]?.color ?? "#4f46e5",
                }}
              >
                {NODE_TYPE_CONFIG[selectedNode.type]?.icon}
              </span>
              <span className="text-xs font-bold text-slate-800 truncate">
                Entity Details
              </span>
            </div>
            <button
              onClick={() => onSelectNode(null)}
              className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
              title="Close panel"
            >
              <X size={13} />
            </button>
          </div>

          <div className="p-4 space-y-3.5 overflow-y-auto flex-1 text-xs">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Entity Name
              </p>
              <p className="font-semibold text-slate-900 leading-snug">
                {selectedNode.label}
              </p>
            </div>

            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Type
                </p>
                <span
                  className={cn(
                    "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium border",
                    NODE_TYPE_CONFIG[selectedNode.type]?.badgeBg
                  )}
                >
                  {NODE_TYPE_CONFIG[selectedNode.type]?.icon}
                  {NODE_TYPE_CONFIG[selectedNode.type]?.label}
                </span>
              </div>
              {selectedNode.mention_count !== undefined && (
                <div className="text-right">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Connectivity
                  </p>
                  <span className="font-mono text-xs font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md border border-indigo-200">
                    {selectedNode.mention_count} links
                  </span>
                </div>
              )}
            </div>

            {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-slate-100">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  Metadata & Context
                </p>
                <div className="bg-slate-50 rounded-xl p-3 space-y-1.5 border border-slate-100">
                  {Object.entries(selectedNode.metadata).map(([k, v]) => (
                    <div
                      key={k}
                      className="flex items-start justify-between gap-2 text-[11px]"
                    >
                      <span className="text-slate-500 capitalize shrink-0">
                        {k.replace(/_/g, " ")}:
                      </span>
                      <span className="font-medium text-slate-800 text-right break-words line-clamp-3">
                        {String(v)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-2 border-t border-slate-100">
              <button
                onClick={() =>
                  onOpenCopilotWithQuery(
                    `Tell me about ${selectedNode.label} and how it connects to other meetings, decisions, and action items.`
                  )
                }
                className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-2xs transition-all cursor-pointer"
              >
                <Sparkles size={12} />
                <span>Ask Copilot about this</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Graph Page Component ───────────────────────────────────────────────

export default function GraphPage() {
  const queryClient = useQueryClient();

  // Selected State
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [activeTypes, setActiveTypes] = useState<Set<string>>(
    new Set(NODE_TYPES_LIST)
  );
  const [selectedMeetingId, setSelectedMeetingId] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [notification, setNotification] = useState<string | null>(null);

  // Copilot Drawer State
  const [isCopilotOpen, setIsCopilotOpen] = useState(true);
  const [chatInput, setChatInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [sessions, setSessions] = useState<GraphChatSession[]>(DEFAULT_GRAPH_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState<string>("session-default");
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // 1. Fetch Real Graph Data from Backend
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: queryKeys.graph.data(),
    queryFn: () => api.get<GraphData>(GRAPH.nodes()),
  });

  // 2. Sync Graph Mutation
  const syncMutation = useMutation({
    mutationFn: () => api.post<GraphSyncResponse>(GRAPH.sync()),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.graph.data() });
      setNotification(
        `Synchronized: ${res.entities_count} entities and ${res.relations_count} relationships updated.`
      );
      setTimeout(() => setNotification(null), 5000);
    },
    onError: () => {
      setNotification("Failed to synchronize knowledge graph. Please retry.");
      setTimeout(() => setNotification(null), 4000);
    },
  });

  // Load chat sessions from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSessions(parsed);
          setActiveSessionId(parsed[0].id);
        }
      }
    } catch {
      // Fallback
    }
  }, []);

  // Save chat sessions to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    } catch {
      // Ignore storage errors
    }
  }, [sessions]);

  // Current Active Chat Session
  const activeSession = useMemo(() => {
    return sessions.find((s) => s.id === activeSessionId) ?? sessions[0];
  }, [sessions, activeSessionId]);

  // Scroll to bottom of chat
  useEffect(() => {
    if (isCopilotOpen) {
      chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [activeSession?.messages, isThinking, isCopilotOpen]);

  // List of distinct meetings for meeting selector dropdown (deduplicated & alphabetically sorted)
  const meetingOptions = useMemo(() => {
    const raw = (data?.nodes ?? []).filter((n) => n.type === "meeting");
    const seen = new Set<string>();
    const unique: GraphNode[] = [];
    raw.forEach((m) => {
      const key = m.label.toLowerCase().trim();
      if (!seen.has(key)) {
        seen.add(key);
        unique.push(m);
      }
    });
    return unique.sort((a, b) => a.label.localeCompare(b.label));
  }, [data?.nodes]);

  const isMeetingScoped = selectedMeetingId !== "ALL";

  const scopedMeetingName = useMemo(() => {
    if (!isMeetingScoped) return null;
    const m = (data?.nodes ?? []).find(
      (n) =>
        n.id === selectedMeetingId ||
        String(n.metadata?.meeting_id) === selectedMeetingId ||
        (n.type === "meeting" && n.label.toLowerCase() === selectedMeetingId.toLowerCase())
    );
    return m?.label || "Selected Meeting";
  }, [isMeetingScoped, selectedMeetingId, data?.nodes]);

  // Filtered nodes by type
  const filteredNodes = useMemo(() => {
    return (data?.nodes ?? []).filter((n) => activeTypes.has(n.type));
  }, [data?.nodes, activeTypes]);

  // Hierarchical Flow calculation with strict meeting isolation
  const { flowNodes, flowEdges } = useMemo(() => {
    return buildHierarchicalFlow(
      filteredNodes,
      data?.edges ?? [],
      selectedNode?.id ?? null,
      searchQuery,
      selectedMeetingId,
      data?.nodes ?? []
    );
  }, [filteredNodes, data?.edges, selectedNode?.id, searchQuery, selectedMeetingId, data?.nodes]);

  // Toggle Type Filter
  const toggleType = (type: string) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        if (next.size > 1) next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const selectAllTypes = () => {
    setActiveTypes(new Set(NODE_TYPES_LIST));
  };

  // Chat Actions
  const handleNewSession = () => {
    const newId = `session-${Date.now()}`;
    const newSession: GraphChatSession = {
      id: newId,
      title: "New Graph Exploration",
      updatedAt: "Just now",
      messages: [
        {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content:
            "Starting a new graph reasoning thread. Ask anything about meetings, architecture decisions, participants, or connected action items.",
          timestamp: "Just now",
        },
      ],
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newId);
  };

  const handleClearSessions = () => {
    setSessions(DEFAULT_GRAPH_SESSIONS);
    setActiveSessionId(DEFAULT_GRAPH_SESSIONS[0].id);
    localStorage.removeItem(STORAGE_KEY);
  };

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || chatInput).trim();
    if (!query || isThinking) return;

    const userMsg: GraphChatMessage = {
      id: `msg-user-${Date.now()}`,
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === activeSessionId) {
          const updatedTitle =
            s.messages.length <= 1 ? query.slice(0, 30) + "..." : s.title;
          return {
            ...s,
            title: updatedTitle,
            updatedAt: "Just now",
            messages: [...s.messages, userMsg],
          };
        }
        return s;
      })
    );

    setChatInput("");
    setIsThinking(true);

    try {
      const response = await api.post<GraphChatResponse>(GRAPH.query(), {
        query,
        conversation_id: activeSessionId,
        meeting_id: selectedMeetingId !== "ALL" ? selectedMeetingId : undefined,
      });

      const assistantMsg: GraphChatMessage = {
        id: `msg-ai-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        citations: response.citations,
      };

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              updatedAt: "Just now",
              messages: [...s.messages, assistantMsg],
            };
          }
          return s;
        })
      );
    } catch {
      const errorMsg: GraphChatMessage = {
        id: `msg-err-${Date.now()}`,
        role: "assistant",
        content:
          "I encountered an error querying the knowledge graph. Please verify backend connectivity or click **Sync Graph** to re-index entities.",
        timestamp: "Just now",
      };
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              messages: [...s.messages, errorMsg],
            };
          }
          return s;
        })
      );
    } finally {
      setIsThinking(false);
    }
  };

  const handleCitationClick = (citation: GraphNodeCitation) => {
    const found = (data?.nodes ?? []).find(
      (n) => n.id === citation.id || n.label.toLowerCase() === citation.label.toLowerCase()
    );
    if (found) {
      setSelectedNode(found);
    }
  };

  const handleOpenCopilotWithQuery = (prompt: string) => {
    setIsCopilotOpen(true);
    setChatInput(prompt);
  };

  // Dynamic metrics extraction (adapts when meeting is isolated)
  const metrics: GraphMetrics = useMemo(() => {
    if (isMeetingScoped) {
      const typeCounts: Record<string, number> = {};
      flowNodes.forEach((n) => {
        const raw = (n.data as CustomNodeData)?.rawNode;
        if (raw) {
          typeCounts[raw.type] = (typeCounts[raw.type] || 0) + 1;
        }
      });
      const numNodes = flowNodes.length;
      const numEdges = flowEdges.length;
      const density =
        numNodes > 1
          ? Number(((2.0 * numEdges) / (numNodes * (numNodes - 1))).toFixed(3))
          : 1.0;

      return {
        total_nodes: numNodes,
        total_edges: numEdges,
        active_communities: 1,
        density,
        type_counts: typeCounts,
      };
    }

    return (
      data?.metrics ?? {
        total_nodes: filteredNodes.length,
        total_edges: data?.edges?.length ?? 0,
        active_communities:
          (data?.nodes ?? []).filter((n) => n.type === "meeting").length || 1,
        density: 0.038,
        type_counts: {},
      }
    );
  }, [
    isMeetingScoped,
    flowNodes,
    flowEdges,
    data?.metrics,
    filteredNodes.length,
    data?.edges?.length,
    data?.nodes,
  ]);

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      {/* ── 1. ENTERPRISE PAGE HEADER ──────────────────────────────────────── */}
      <PageHeader
        title="Cross-Meeting Knowledge Graph"
        subtitle="Structured lineage flow connecting conversations, decisions, commitments, and team members."
        icon={GitBranch}
        statusDot={true}
        badge={
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 flex items-center gap-1.5 shadow-2xs">
            <Network size={12} />
            <span>
              {isMeetingScoped ? (
                <>
                  <span className="font-bold text-indigo-800">1 Focused Meeting:</span>{" "}
                  {scopedMeetingName} ({flowNodes.length} nodes • {flowEdges.length} edges)
                </>
              ) : (
                <>
                  {filteredNodes.length} Entities • {data?.edges?.length ?? 0} Relations
                </>
              )}
            </span>
          </span>
        }
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending || isFetching}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-50 shadow-2xs transition-all cursor-pointer disabled:opacity-50"
              title="Synchronize knowledge graph from DB meetings"
            >
              <RefreshCw
                size={13}
                className={
                  syncMutation.isPending || isFetching ? "animate-spin" : ""
                }
              />
              <span>
                {syncMutation.isPending ? "Syncing..." : "Sync Graph"}
              </span>
            </button>

            <button
              onClick={() => setIsCopilotOpen((prev) => !prev)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer shadow-2xs",
                isCopilotOpen
                  ? "bg-indigo-600 text-white border-indigo-600 shadow-indigo-100"
                  : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
              )}
            >
              <Sparkles size={13} />
              <span>AI Copilot</span>
              {activeSession.messages.length > 1 && (
                <span className="ml-0.5 px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-500 text-white font-mono">
                  {activeSession.messages.length - 1}
                </span>
              )}
            </button>
          </div>
        }
      />

      {/* Notification Toast Banner */}
      {notification && (
        <div className="flex items-center justify-between px-4 py-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium animate-in fade-in duration-150">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={15} className="text-emerald-600 shrink-0" />
            <span>{notification}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-emerald-600 hover:text-emerald-800 cursor-pointer"
          >
            <X size={13} />
          </button>
        </div>
      )}

      {/* ── 2. 4-METRIC ENTERPRISE KPI RIBBON ───────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Entities */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs p-4 flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Knowledge Entities</span>
            <span className="text-[10px] font-mono bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded border border-blue-200">
              {isMeetingScoped ? "Scoped" : "Live"}
            </span>
          </div>
          <div className="flex items-baseline justify-between mt-3">
            <span className="text-3xl font-bold text-slate-900 tracking-tight">
              {isLoading ? "—" : metrics.total_nodes}
            </span>
            <div className="bg-blue-50 text-blue-600 p-2 rounded-lg shrink-0">
              <GitBranch size={18} />
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {isMeetingScoped
              ? "Entities strictly in this meeting lineage"
              : "People, topics, decisions & meetings"}
          </p>
        </div>

        {/* Directed Relations */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs p-4 flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Directed Relations</span>
            <span className="text-[10px] font-mono bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200">
              Active
            </span>
          </div>
          <div className="flex items-baseline justify-between mt-3">
            <span className="text-3xl font-bold text-indigo-600 tracking-tight">
              {isLoading ? "—" : metrics.total_edges}
            </span>
            <div className="bg-indigo-50 text-indigo-600 p-2 rounded-lg shrink-0">
              <Network size={18} />
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {isMeetingScoped
              ? "Provenances linked directly to this meeting"
              : "Horizontal provenance & decision paths"}
          </p>
        </div>

        {/* Active Communities */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs p-4 flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>{isMeetingScoped ? "Focus Scope" : "Active Communities"}</span>
            <span className="text-[10px] font-mono bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded border border-emerald-200">
              {isMeetingScoped ? "Isolated" : "Clustered"}
            </span>
          </div>
          <div className="flex items-baseline justify-between mt-3">
            <span className="text-3xl font-bold text-emerald-600 tracking-tight">
              {isLoading ? "—" : isMeetingScoped ? "1 Meeting" : metrics.active_communities}
            </span>
            <div className="bg-emerald-50 text-emerald-600 p-2 rounded-lg shrink-0">
              <Layers size={18} />
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-1 truncate" title={scopedMeetingName ?? ""}>
            {isMeetingScoped
              ? (scopedMeetingName ?? "Single meeting focus")
              : "Meeting spheres and project domains"}
          </p>
        </div>

        {/* Network Density */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs p-4 flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>{isMeetingScoped ? "Lineage Completeness" : "Lineage Density"}</span>
            <span className="text-[10px] font-mono bg-purple-50 text-purple-700 px-1.5 py-0.5 rounded border border-purple-200">
              {isMeetingScoped ? "Focused" : "Coverage"}
            </span>
          </div>
          <div className="flex items-baseline justify-between mt-3">
            <span className="text-3xl font-bold text-purple-600 tracking-tight">
              {isLoading ? "—" : isMeetingScoped ? "100%" : `${(metrics.density * 100).toFixed(1)}%`}
            </span>
            <div className="bg-purple-50 text-purple-600 p-2 rounded-lg shrink-0">
              <Compass size={18} />
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {isMeetingScoped
              ? "Direct origin-to-outcome mapping"
              : "Cross-functional connectivity ratio"}
          </p>
        </div>
      </div>

      {/* ── 3. FILTER & SCOPE CONTROL BAR ─────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs p-4 space-y-3.5">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          {/* Meeting Focus Selector */}
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1 shrink-0">
              <Filter size={12} />
              <span>Scope:</span>
            </span>
            <select
              value={selectedMeetingId}
              onChange={(e) => setSelectedMeetingId(e.target.value)}
              className="h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-800 font-semibold focus:outline-hidden focus:border-indigo-600 cursor-pointer shadow-2xs w-full sm:w-72 truncate"
            >
              <option value="ALL">🌐 All Meetings Lineage Flow</option>
              {meetingOptions.map((m) => (
                <option key={m.id} value={m.id}>
                  📋 {m.label}
                </option>
              ))}
            </select>

            {selectedMeetingId !== "ALL" && (
              <button
                onClick={() => setSelectedMeetingId("ALL")}
                className="h-9 px-3 text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold rounded-xl border border-indigo-200 flex items-center gap-1.5 transition-all cursor-pointer shadow-2xs shrink-0"
                title="Clear meeting scope filter"
              >
                <RotateCcw size={12} />
                <span>Reset Scope</span>
              </button>
            )}
          </div>

          {/* Search Node Input */}
          <div className="relative w-full sm:w-72 shrink-0">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
            <input
              type="text"
              placeholder="Filter node in flow..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-9 pl-9 pr-8 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-indigo-600 focus:bg-white transition-all shadow-2xs"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer text-xs"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Entity Type Filter Pills */}
        <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-slate-100">
          <span className="text-[11px] font-semibold text-slate-400 mr-1">
            Display Columns:
          </span>
          {NODE_TYPES_LIST.map((type) => {
            const config = NODE_TYPE_CONFIG[type];
            const active = activeTypes.has(type);
            const count = (isMeetingScoped ? flowNodes : (data?.nodes ?? [])).filter((n) => {
              const raw = (n as any).data ? (n as any).data.rawNode : n;
              return raw?.type === type;
            }).length;

            return (
              <button
                key={type}
                onClick={() => toggleType(type)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold border transition-all cursor-pointer",
                  active
                    ? `${config.badgeBg} shadow-2xs`
                    : "bg-slate-50 border-slate-200 text-slate-400 opacity-60 hover:opacity-100"
                )}
              >
                {config.icon}
                <span>{config.label}</span>
                <span className="text-[10px] font-mono px-1 py-0.2 rounded-full bg-white/70 border border-slate-200/60 ml-0.5">
                  {count}
                </span>
              </button>
            );
          })}

          <button
            onClick={selectAllTypes}
            className="text-[11px] font-semibold text-slate-400 hover:text-indigo-600 px-2 py-1 transition-colors cursor-pointer ml-auto"
          >
            Reset Filters
          </button>
        </div>
      </div>

      {/* ── 4. MAIN SPLIT PANE: HIERARCHICAL CANVAS + GPT COPILOT DRAWER ────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Pane: Hierarchical Flow Canvas */}
        <div
          className={cn(
            "transition-all duration-200",
            isCopilotOpen ? "lg:col-span-8 xl:col-span-8" : "lg:col-span-12"
          )}
        >
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-[660px] gap-2 border border-slate-200 rounded-2xl bg-white shadow-2xs">
              <Spinner size={32} />
              <p className="text-xs text-slate-500 font-medium">
                Loading hierarchical knowledge flow...
              </p>
            </div>
          ) : flowNodes.length === 0 ? (
            <div className="flex items-center justify-center h-[660px] border border-slate-200 rounded-2xl bg-white shadow-2xs">
              <EmptyState
                icon={<GitBranch />}
                title="No Graph Nodes in Selected Scope"
                description="Try selecting 'All Meetings' in the scope selector above or click 'Sync Graph'."
                action={
                  <button
                    onClick={() => {
                      setSelectedMeetingId("ALL");
                      selectAllTypes();
                    }}
                    className="mt-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 cursor-pointer shadow-xs"
                  >
                    Reset Scope to All Meetings
                  </button>
                }
              />
            </div>
          ) : (
            <ReactFlowProvider>
              <GraphCanvas
                nodes={flowNodes}
                edges={flowEdges}
                selectedNode={selectedNode}
                onSelectNode={setSelectedNode}
                onOpenCopilotWithQuery={handleOpenCopilotWithQuery}
                selectedMeetingId={selectedMeetingId}
                scopedMeetingName={scopedMeetingName}
              />
            </ReactFlowProvider>
          )}
        </div>

        {/* Right Pane: GPT Chat Copilot Drawer */}
        {isCopilotOpen && (
          <div className="lg:col-span-4 xl:col-span-4 bg-white rounded-2xl border border-slate-200/90 shadow-lg overflow-hidden flex flex-col h-[660px] sticky top-20 animate-in fade-in slide-in-from-right-4 duration-200">
            {/* Copilot Header */}
            <div className="p-4 border-b border-slate-200 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shrink-0 shadow-2xs">
                  <Bot size={16} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <h3 className="text-xs font-bold text-white truncate">
                      Knowledge Graph Copilot
                    </h3>
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  </div>
                  <p className="text-[10px] text-slate-300 truncate">
                    Neural reasoning across {metrics.total_nodes} entities & {metrics.total_edges} relations
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  onClick={handleNewSession}
                  className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] font-medium text-slate-200 transition-colors flex items-center gap-1 cursor-pointer"
                  title="Start a new chat thread"
                >
                  <Plus size={11} />
                  <span>New</span>
                </button>
                <button
                  onClick={() => setIsCopilotOpen(false)}
                  className="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                  title="Close Copilot"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Scoped Context Pill in Copilot */}
            {isMeetingScoped && scopedMeetingName && (
              <div className="px-4 py-2 bg-indigo-50/80 border-b border-indigo-100 flex items-center justify-between gap-2 shrink-0">
                <div className="flex items-center gap-1.5 text-[11px] text-indigo-900 font-medium truncate">
                  <Sparkles size={12} className="text-indigo-600 shrink-0" />
                  <span className="truncate">
                    Focus: <strong>{scopedMeetingName}</strong>
                  </span>
                </div>
                <button
                  onClick={() =>
                    handleOpenCopilotWithQuery(
                      `Summarize all decisions and action items that originated from "${scopedMeetingName}".`
                    )
                  }
                  className="text-[10px] font-bold text-indigo-600 hover:text-indigo-800 bg-white px-2 py-0.5 rounded-md border border-indigo-200 shrink-0 cursor-pointer shadow-2xs"
                >
                  Summarize
                </button>
              </div>
            )}

            {/* Sessions Selector Bar */}
            <div className="px-3.5 py-1.5 bg-slate-50 border-b border-slate-200/80 flex items-center justify-between text-xs text-slate-600">
              <div className="flex items-center gap-1.5 truncate">
                <Compass size={12} className="text-indigo-600 shrink-0" />
                <span className="font-semibold text-slate-700 truncate max-w-[200px]">
                  {activeSession?.title || "Active Thread"}
                </span>
              </div>
              <button
                onClick={handleClearSessions}
                className="text-[10px] text-slate-400 hover:text-rose-600 transition-colors cursor-pointer"
                title="Reset conversation"
              >
                Clear
              </button>
            </div>

            {/* Chat Messages Area */}
            <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-slate-50/40 text-xs">
              {activeSession.messages.map((m) => {
                const isUser = m.role === "user";

                return (
                  <div
                    key={m.id}
                    className={cn(
                      "flex flex-col space-y-1.5",
                      isUser ? "items-end" : "items-start"
                    )}
                  >
                    <div
                      className={cn(
                        "flex items-start gap-2.5 max-w-[90%]",
                        isUser ? "flex-row-reverse" : "flex-row"
                      )}
                    >
                      <div
                        className={cn(
                          "w-6 h-6 rounded-lg flex items-center justify-center text-xs shrink-0 mt-0.5",
                          isUser
                            ? "bg-slate-800 text-white"
                            : "bg-indigo-600 text-white"
                        )}
                      >
                        {isUser ? <User size={13} /> : <Bot size={13} />}
                      </div>

                      <div
                        className={cn(
                          "rounded-2xl p-3.5 leading-relaxed text-xs shadow-2xs space-y-2",
                          isUser
                            ? "bg-indigo-600 text-white rounded-tr-xs"
                            : "bg-white border border-slate-200/90 text-slate-800 rounded-tl-xs"
                        )}
                      >
                        <div className="whitespace-pre-wrap font-normal leading-relaxed">
                          {m.content}
                        </div>

                        {/* Interactive Graph Citations */}
                        {m.citations && m.citations.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-slate-100 space-y-1.5">
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                              <Compass size={11} />
                              <span>Graph Entity Citations:</span>
                            </span>
                            <div className="flex flex-wrap gap-1">
                              {m.citations.map((cite, cIdx) => (
                                <button
                                  key={cIdx}
                                  onClick={() => handleCitationClick(cite)}
                                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-indigo-50 border border-indigo-200 text-indigo-700 hover:bg-indigo-100 transition-colors cursor-pointer shadow-2xs"
                                  title={`Inspect in graph: ${cite.label}`}
                                >
                                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                                  <span className="truncate max-w-[130px]">
                                    {cite.label}
                                  </span>
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        <div
                          className={cn(
                            "text-[9px] font-mono text-right",
                            isUser ? "text-indigo-200" : "text-slate-400"
                          )}
                        >
                          {m.timestamp}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {isThinking && (
                <div className="flex items-start gap-2.5">
                  <div className="w-6 h-6 rounded-lg bg-indigo-600 text-white flex items-center justify-center shrink-0">
                    <Sparkles size={13} className="animate-spin" />
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-xs p-3 text-xs text-slate-500 flex items-center gap-2 shadow-2xs">
                    <Spinner size={12} />
                    <span>Traversing lineage paths...</span>
                  </div>
                </div>
              )}

              <div ref={chatBottomRef} />
            </div>

            {/* Quick Suggested Queries */}
            {activeSession.messages.length <= 1 && (
              <div className="p-3 border-t border-slate-200/80 bg-slate-50/70">
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <HelpCircle size={11} />
                  <span>Suggested Graph Queries:</span>
                </p>
                <div className="space-y-1">
                  {SUGGESTED_QUERIES.map((q, qIdx) => (
                    <button
                      key={qIdx}
                      onClick={() => handleSendMessage(q)}
                      className="w-full text-left text-[11px] text-slate-700 hover:text-indigo-600 hover:bg-white p-1.5 rounded-lg border border-transparent hover:border-slate-200 transition-all truncate block cursor-pointer"
                    >
                      • {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Chat Input Bar */}
            <div className="p-3 bg-white border-t border-slate-200">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="flex items-center gap-2"
              >
                <input
                  type="text"
                  placeholder="Ask about people, decisions, topics..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={isThinking}
                  className="flex-1 h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-indigo-600 focus:bg-white transition-all"
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || isThinking}
                  className="w-9 h-9 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0 shadow-2xs"
                  title="Send message"
                >
                  <Send size={13} />
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
