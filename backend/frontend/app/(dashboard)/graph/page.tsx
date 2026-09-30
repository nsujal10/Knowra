"use client";

import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
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
import { Card, CardContent, CardHeader, CardTitle, Badge, Spinner, EmptyState } from "@/components/ui/card";
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
  Share2,
  Layers,
  ArrowRight,
  ExternalLink,
  ChevronRight,
  Sliders,
  Maximize2,
  Compass,
  CheckCircle2,
  Network,
  HelpCircle,
} from "lucide-react";

// ─── Visual Type Tokens ──────────────────────────────────────────────────────

const NODE_TYPE_CONFIG: Record<
  string,
  {
    color: string;
    bg: string;
    border: string;
    icon: React.ReactNode;
    label: string;
    badge: string;
    description: string;
  }
> = {
  person: {
    color: "#2563eb",
    bg: "rgba(37,99,235,0.08)",
    border: "rgba(37,99,235,0.28)",
    icon: <Users size={12} />,
    label: "Person",
    badge: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800",
    description: "Meeting participants, project owners, and decision makers",
  },
  topic: {
    color: "#7c3aed",
    bg: "rgba(124,58,237,0.08)",
    border: "rgba(124,58,237,0.28)",
    icon: <Brain size={12} />,
    label: "Topic",
    badge: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800",
    description: "Technical domains, architectural patterns, and strategic subjects",
  },
  decision: {
    color: "#d97706",
    bg: "rgba(217,119,6,0.08)",
    border: "rgba(217,119,6,0.28)",
    icon: <CheckSquare size={12} />,
    label: "Decision",
    badge: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800",
    description: "Confirmed commitments, architectural choices, and policies",
  },
  meeting: {
    color: "#4f46e5",
    bg: "rgba(79,70,229,0.08)",
    border: "rgba(79,70,229,0.28)",
    icon: <FileText size={12} />,
    label: "Meeting",
    badge: "bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-800",
    description: "Recorded conversations, syncs, executive reviews, and standups",
  },
  action: {
    color: "#059669",
    bg: "rgba(5,150,105,0.08)",
    border: "rgba(5,150,105,0.28)",
    icon: <Zap size={12} />,
    label: "Action",
    badge: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800",
    description: "Assigned engineering tasks, follow-ups, and deliverables",
  },
  entity: {
    color: "#db2777",
    bg: "rgba(219,39,119,0.08)",
    border: "rgba(219,39,119,0.28)",
    icon: <GitBranch size={12} />,
    label: "Entity",
    badge: "bg-pink-50 text-pink-700 border-pink-200 dark:bg-pink-950/40 dark:text-pink-300 dark:border-pink-800",
    description: "External systems, databases, frameworks, and third-party tools",
  },
};

const NODE_TYPES_LIST = Object.keys(NODE_TYPE_CONFIG);

// ─── Custom ReactFlow Node Component ─────────────────────────────────────────

interface CustomNodeData {
  rawNode: GraphNode;
  isSelected: boolean;
  isDimmed: boolean;
}

const CustomNode = React.memo(({ data }: { data: CustomNodeData }) => {
  const { rawNode, isSelected, isDimmed } = data;
  const config = NODE_TYPE_CONFIG[rawNode.type] ?? NODE_TYPE_CONFIG.entity;

  return (
    <div
      className={cn(
        "group relative flex items-center gap-2.5 px-3 py-2 rounded-xl border transition-all duration-200 shadow-xs cursor-pointer select-none",
        isSelected
          ? "ring-2 ring-indigo-500 shadow-md scale-105 z-20"
          : "hover:scale-102 hover:shadow-sm z-10",
        isDimmed && "opacity-25 filter grayscale"
      )}
      style={{
        backgroundColor: config.bg,
        borderColor: isSelected ? config.color : config.border,
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="opacity-0 w-2 h-2 pointer-events-none"
      />

      <div
        className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 text-white shadow-2xs transition-transform group-hover:scale-110"
        style={{ backgroundColor: config.color }}
      >
        {config.icon}
      </div>

      <div className="flex flex-col min-w-0 max-w-[155px]">
        <span
          className="text-xs font-semibold truncate text-slate-900 dark:text-slate-100 tracking-tight"
          title={rawNode.label}
        >
          {rawNode.label}
        </span>
        <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-medium">
          <span>{config.label}</span>
          {rawNode.mention_count !== undefined && rawNode.mention_count > 0 && (
            <>
              <span className="text-slate-300 dark:text-slate-700">•</span>
              <span className="font-mono text-[9px] text-slate-400">
                {rawNode.mention_count} conn
              </span>
            </>
          )}
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="opacity-0 w-2 h-2 pointer-events-none"
      />
    </div>
  );
});

CustomNode.displayName = "CustomNode";

const nodeTypes = {
  customNode: CustomNode,
};

// ─── Radial / Clustered Flow Node Layout ──────────────────────────────────────

function buildFlowNodes(
  nodes: GraphNode[],
  selectedNodeId: string | null,
  searchQuery: string
): Node[] {
  const typeGroups: Record<string, GraphNode[]> = {};
  nodes.forEach((n) => {
    typeGroups[n.type] = typeGroups[n.type] || [];
    typeGroups[n.type].push(n);
  });

  const flowNodes: Node[] = [];
  const q = searchQuery.toLowerCase().trim();

  // Tier 1: Meetings in inner circle (Center: 600, 420)
  const meetings = typeGroups["meeting"] || [];
  meetings.forEach((m, idx) => {
    const angle = (idx / Math.max(1, meetings.length)) * 2 * Math.PI;
    const radius = 230;
    const isSelected = m.id === selectedNodeId;
    const isDimmed = Boolean(q && !m.label.toLowerCase().includes(q));
    flowNodes.push({
      id: m.id,
      position: {
        x: 600 + radius * Math.cos(angle),
        y: 420 + radius * Math.sin(angle),
      },
      data: { rawNode: m, isSelected, isDimmed },
      type: "customNode",
    });
  });

  // Tier 2: Decisions around meetings
  const decisions = typeGroups["decision"] || [];
  decisions.forEach((d, idx) => {
    const angle = (idx / Math.max(1, decisions.length)) * 2 * Math.PI + 0.35;
    const radius = 390;
    const isSelected = d.id === selectedNodeId;
    const isDimmed = Boolean(q && !d.label.toLowerCase().includes(q));
    flowNodes.push({
      id: d.id,
      position: {
        x: 600 + radius * Math.cos(angle),
        y: 420 + radius * Math.sin(angle),
      },
      data: { rawNode: d, isSelected, isDimmed },
      type: "customNode",
    });
  });

  // Tier 3: Actions orbit
  const actions = typeGroups["action"] || [];
  actions.forEach((a, idx) => {
    const angle = (idx / Math.max(1, actions.length)) * 2 * Math.PI + 0.65;
    const radius = 540;
    const isSelected = a.id === selectedNodeId;
    const isDimmed = Boolean(q && !a.label.toLowerCase().includes(q));
    flowNodes.push({
      id: a.id,
      position: {
        x: 600 + radius * Math.cos(angle),
        y: 420 + radius * Math.sin(angle),
      },
      data: { rawNode: a, isSelected, isDimmed },
      type: "customNode",
    });
  });

  // Tier 4: Persons cluster
  const persons = typeGroups["person"] || [];
  persons.forEach((p, idx) => {
    const angle = (idx / Math.max(1, persons.length)) * 2 * Math.PI + 0.95;
    const radius = 690;
    const isSelected = p.id === selectedNodeId;
    const isDimmed = Boolean(q && !p.label.toLowerCase().includes(q));
    flowNodes.push({
      id: p.id,
      position: {
        x: 600 + radius * Math.cos(angle),
        y: 420 + radius * Math.sin(angle),
      },
      data: { rawNode: p, isSelected, isDimmed },
      type: "customNode",
    });
  });

  // Tier 5: Topics outer ring
  const topics = typeGroups["topic"] || [];
  topics.forEach((t, idx) => {
    const angle = (idx / Math.max(1, topics.length)) * 2 * Math.PI + 1.25;
    const radius = 830;
    const isSelected = t.id === selectedNodeId;
    const isDimmed = Boolean(q && !t.label.toLowerCase().includes(q));
    flowNodes.push({
      id: t.id,
      position: {
        x: 600 + radius * Math.cos(angle),
        y: 420 + radius * Math.sin(angle),
      },
      data: { rawNode: t, isSelected, isDimmed },
      type: "customNode",
    });
  });

  // Tier 6: Other entities
  const entities = typeGroups["entity"] || [];
  entities.forEach((e, idx) => {
    const angle = (idx / Math.max(1, entities.length)) * 2 * Math.PI + 1.55;
    const radius = 960;
    const isSelected = e.id === selectedNodeId;
    const isDimmed = Boolean(q && !e.label.toLowerCase().includes(q));
    flowNodes.push({
      id: e.id,
      position: {
        x: 600 + radius * Math.cos(angle),
        y: 420 + radius * Math.sin(angle),
      },
      data: { rawNode: e, isSelected, isDimmed },
      type: "customNode",
    });
  });

  return flowNodes;
}

function buildFlowEdges(
  edges: GraphEdge[],
  selectedNodeId: string | null
): Edge[] {
  return edges.map((e) => {
    const isConnected =
      Boolean(selectedNodeId) &&
      (e.source === selectedNodeId || e.target === selectedNodeId);

    return {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label?.replace(/_/g, " "),
      style: {
        stroke: isConnected ? "#4f46e5" : "rgba(148, 163, 184, 0.28)",
        strokeWidth: isConnected ? 2 : 1,
      },
      labelStyle: {
        fill: isConnected ? "#4338ca" : "rgba(100, 116, 139, 0.75)",
        fontSize: 9,
        fontWeight: isConnected ? 600 : 500,
      },
      animated: isConnected,
    };
  });
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
    title: "Organizational Knowledge Graph",
    updatedAt: "Just now",
    messages: [
      {
        id: "msg-welcome",
        role: "assistant",
        content:
          "Welcome to the **Knowledge Graph Copilot**. I have indexed all participants, decisions, action items, and topic clusters across your workspace meetings.\n\nYou can query relationships, inspect architectural decisions, or click on any citation pill to jump straight to that entity in the graph.",
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

// ─── Inner Canvas Component (for useReactFlow hook access) ───────────────────

function GraphCanvas({
  nodes,
  edges,
  selectedNode,
  onSelectNode,
  onOpenCopilotWithQuery,
}: {
  nodes: Node[];
  edges: Edge[];
  selectedNode: GraphNode | null;
  onSelectNode: (node: GraphNode | null) => void;
  onOpenCopilotWithQuery: (q: string) => void;
}) {
  const reactFlow = useReactFlow();

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    const raw = (node.data as CustomNodeData)?.rawNode;
    if (raw) {
      onSelectNode(raw);
    }
  };

  const handleFocusNode = (x: number, y: number) => {
    reactFlow.setCenter(x, y, { zoom: 1.1, duration: 600 });
  };

  return (
    <div className="relative w-full h-full bg-slate-50/50 dark:bg-slate-950/40 rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onPaneClick={() => onSelectNode(null)}
        fitView
        attributionPosition="bottom-left"
        minZoom={0.15}
        maxZoom={2.2}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1.2}
          color="rgba(148, 163, 184, 0.18)"
        />
        <Controls
          position="bottom-left"
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-md rounded-lg overflow-hidden text-slate-700 dark:text-slate-200"
        />
        <MiniMap
          position="bottom-right"
          className="rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800 shadow-md"
          nodeColor={(n) => {
            const raw = (n.data as CustomNodeData)?.rawNode;
            return raw ? NODE_TYPE_CONFIG[raw.type]?.color ?? "#64748b" : "#64748b";
          }}
          maskColor="rgba(241, 245, 249, 0.65)"
        />
      </ReactFlow>

      {/* Selected Node Floating Inspector */}
      {selectedNode && (
        <div className="absolute top-4 left-4 z-20 w-80 animate-slide-in-right bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xl overflow-hidden flex flex-col max-h-[calc(100%-32px)]">
          <div className="flex items-center justify-between px-3.5 py-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/70 backdrop-blur-xs">
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
              <span className="text-xs font-bold text-slate-800 dark:text-slate-100 truncate">
                Entity Details
              </span>
            </div>
            <button
              onClick={() => onSelectNode(null)}
              className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
              title="Close panel"
            >
              <X size={13} />
            </button>
          </div>

          <div className="p-3.5 space-y-3.5 overflow-y-auto flex-1 text-xs">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Entity Name
              </p>
              <p className="font-semibold text-slate-900 dark:text-slate-100 leading-snug">
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
                    "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium border",
                    NODE_TYPE_CONFIG[selectedNode.type]?.badge
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
                  <span className="font-mono text-xs font-semibold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50 px-2 py-0.5 rounded-md border border-indigo-200 dark:border-indigo-800">
                    {selectedNode.mention_count} links
                  </span>
                </div>
              )}
            </div>

            {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-slate-100 dark:border-slate-800">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  Metadata & Provenance
                </p>
                <div className="bg-slate-50 dark:bg-slate-950/50 rounded-lg p-2.5 space-y-1.5 border border-slate-100 dark:border-slate-800/80">
                  {Object.entries(selectedNode.metadata).map(([k, v]) => (
                    <div
                      key={k}
                      className="flex items-start justify-between gap-2 text-[11px]"
                    >
                      <span className="text-slate-400 capitalize shrink-0">
                        {k.replace(/_/g, " ")}:
                      </span>
                      <span className="font-medium text-slate-700 dark:text-slate-200 text-right break-words line-clamp-3">
                        {String(v)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
              <button
                onClick={() =>
                  onOpenCopilotWithQuery(
                    `Tell me about ${selectedNode.label} and how it connects to other meetings and decisions.`
                  )
                }
                className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-all cursor-pointer"
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

  // Handle Filtering
  const filteredNodes = useMemo(() => {
    return (data?.nodes ?? []).filter((n) => activeTypes.has(n.type));
  }, [data?.nodes, activeTypes]);

  const filteredNodeIds = useMemo(() => {
    return new Set(filteredNodes.map((n) => n.id));
  }, [filteredNodes]);

  const filteredEdges = useMemo(() => {
    return (data?.edges ?? []).filter(
      (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
    );
  }, [data?.edges, filteredNodeIds]);

  const flowNodes = useMemo(() => {
    return buildFlowNodes(filteredNodes, selectedNode?.id ?? null, searchQuery);
  }, [filteredNodes, selectedNode?.id, searchQuery]);

  const flowEdges = useMemo(() => {
    return buildFlowEdges(filteredEdges, selectedNode?.id ?? null);
  }, [filteredEdges, selectedNode?.id]);

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
            s.messages.length <= 1 ? query.slice(0, 32) + "..." : s.title;
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
    // Find matching node in graph
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

  // Metrics extraction
  const metrics: GraphMetrics = data?.metrics ?? {
    total_nodes: filteredNodes.length,
    total_edges: filteredEdges.length,
    active_communities: (data?.nodes ?? []).filter((n) => n.type === "meeting").length || 1,
    density: 0.018,
    type_counts: {},
  };

  return (
    <div className="h-[calc(100vh-56px-32px)] flex flex-col space-y-3.5 animate-fade-in">
      {/* ── ENTERPRISE PAGE HEADER ─────────────────────────────────────────── */}
      <PageHeader
        title="Cross-Meeting Knowledge Graph"
        subtitle="Interactive neural network of participants, topics, decisions, and action items discovered across conversations."
        icon={GitBranch}
        statusDot={true}
        badge={
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-800 flex items-center gap-1.5">
            <Network size={11} />
            <span>
              {filteredNodes.length} Entities • {filteredEdges.length} Relations
            </span>
          </span>
        }
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending || isFetching}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:text-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 shadow-2xs transition-all cursor-pointer disabled:opacity-50"
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
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer shadow-2xs",
                isCopilotOpen
                  ? "bg-indigo-600 text-white border-indigo-600 shadow-indigo-100"
                  : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
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
        <div className="flex items-center justify-between px-3.5 py-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs font-medium animate-fade-in shrink-0">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={14} className="text-emerald-600" />
            <span>{notification}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-emerald-600 hover:text-emerald-800"
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* ── 4-METRIC ENTERPRISE KPI RIBBON ─────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 shrink-0">
        <div className="px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
              Total Entities
            </p>
            <p className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {metrics.total_nodes}
            </p>
          </div>
          <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/50 text-blue-600 flex items-center justify-center">
            <GitBranch size={16} />
          </div>
        </div>

        <div className="px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
              Directed Relations
            </p>
            <p className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {metrics.total_edges}
            </p>
          </div>
          <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 flex items-center justify-center">
            <Network size={16} />
          </div>
        </div>

        <div className="px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
              Active Communities
            </p>
            <p className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {metrics.active_communities}
            </p>
          </div>
          <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 flex items-center justify-center">
            <Layers size={16} />
          </div>
        </div>

        <div className="px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
              Network Density
            </p>
            <p className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {(metrics.density * 100).toFixed(1)}%
            </p>
          </div>
          <div className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-950/50 text-purple-600 flex items-center justify-center">
            <Compass size={16} />
          </div>
        </div>
      </div>

      {/* ── FILTER & SEARCH BAR ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3 flex-wrap shrink-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs font-semibold text-slate-500 mr-1">
            Filter:
          </span>
          {NODE_TYPES_LIST.map((type) => {
            const config = NODE_TYPE_CONFIG[type];
            const active = activeTypes.has(type);
            const count = (data?.nodes ?? []).filter((n) => n.type === type).length;

            return (
              <button
                key={type}
                onClick={() => toggleType(type)}
                className={cn(
                  "flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all cursor-pointer",
                  active
                    ? "shadow-2xs font-semibold"
                    : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-400 opacity-60 hover:opacity-90"
                )}
                style={
                  active
                    ? {
                        backgroundColor: config.bg,
                        color: config.color,
                        borderColor: config.border,
                      }
                    : undefined
                }
              >
                {config.icon}
                <span>{config.label}</span>
                <span
                  className="text-[9px] font-mono px-1 py-0.1 rounded-full ml-0.5"
                  style={{
                    backgroundColor: active ? `${config.color}20` : undefined,
                  }}
                >
                  {count}
                </span>
              </button>
            );
          })}

          <button
            onClick={selectAllTypes}
            className="text-[11px] font-medium text-slate-500 hover:text-indigo-600 px-2 py-0.5 rounded transition-colors"
          >
            Reset
          </button>
        </div>

        {/* Search Node Input */}
        <div className="relative w-64 shrink-0">
          <Search
            size={13}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            type="text"
            placeholder="Highlight node in graph..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:outline-hidden focus:ring-1 focus:ring-indigo-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* ── MAIN WORKSPACE: GRAPH CANVAS + PERSISTENT COPILOT DRAWER ──────── */}
      <div className="flex gap-3.5 flex-1 min-h-0">
        {/* ReactFlow Canvas Container */}
        <div className="flex-1 rounded-xl overflow-hidden relative">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900">
              <Spinner size={32} />
              <p className="text-xs text-slate-500 font-medium">
                Synthesizing cross-meeting knowledge graph...
              </p>
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="flex items-center justify-center h-full border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900">
              <EmptyState
                icon={<GitBranch />}
                title="No Graph Nodes Available"
                description="Click 'Sync Graph' above to parse your meeting transcripts and extract organizational entities."
                action={
                  <button
                    onClick={() => syncMutation.mutate()}
                    className="mt-2 px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 cursor-pointer shadow-xs"
                  >
                    Sync Knowledge Graph Now
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
              />
            </ReactFlowProvider>
          )}
        </div>

        {/* ── RIGHT-SIDE GPT CHAT COPILOT DRAWER ────────────────────────────── */}
        {isCopilotOpen && (
          <div className="w-[390px] shrink-0 flex flex-col rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-md overflow-hidden animate-slide-in-right">
            {/* Drawer Header */}
            <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/60">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-indigo-600 text-white flex items-center justify-center">
                  <Bot size={13} />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    Graph Intelligence Copilot
                  </h3>
                  <p className="text-[10px] text-slate-400">
                    Cross-meeting neural reasoning
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                <button
                  onClick={handleNewSession}
                  className="p-1.5 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                  title="New chat thread"
                >
                  <Plus size={13} />
                </button>
                <button
                  onClick={handleClearSessions}
                  className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors cursor-pointer"
                  title="Reset all threads"
                >
                  <Trash2 size={13} />
                </button>
                <button
                  onClick={() => setIsCopilotOpen(false)}
                  className="p-1.5 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                  title="Collapse panel"
                >
                  <X size={13} />
                </button>
              </div>
            </div>

            {/* Session Switcher Pills */}
            {sessions.length > 1 && (
              <div className="flex items-center gap-1 px-3 py-1.5 border-b border-slate-100 dark:border-slate-800 overflow-x-auto bg-slate-50/30 dark:bg-slate-950/20 text-[11px]">
                {sessions.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setActiveSessionId(s.id)}
                    className={cn(
                      "px-2 py-0.5 rounded-md whitespace-nowrap font-medium transition-all cursor-pointer",
                      s.id === activeSessionId
                        ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 font-semibold"
                        : "text-slate-400 hover:text-slate-600"
                    )}
                  >
                    {s.title}
                  </button>
                ))}
              </div>
            )}

            {/* Chat Messages Log */}
            <div className="flex-1 p-3.5 overflow-y-auto space-y-3.5 text-xs">
              {activeSession.messages.map((msg) => {
                const isUser = msg.role === "user";
                return (
                  <div
                    key={msg.id}
                    className={cn(
                      "flex gap-2.5",
                      isUser ? "flex-row-reverse" : "flex-row"
                    )}
                  >
                    <div
                      className={cn(
                        "w-5 h-5 rounded-md flex items-center justify-center shrink-0 text-[10px] mt-0.5",
                        isUser
                          ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900"
                          : "bg-indigo-600 text-white"
                      )}
                    >
                      {isUser ? <User size={11} /> : <Sparkles size={11} />}
                    </div>

                    <div
                      className={cn(
                        "flex flex-col max-w-[85%] rounded-xl p-3 leading-relaxed",
                        isUser
                          ? "bg-indigo-600 text-white rounded-tr-xs"
                          : "bg-slate-50 dark:bg-slate-800/60 text-slate-800 dark:text-slate-100 border border-slate-100 dark:border-slate-800 rounded-tl-xs"
                      )}
                    >
                      <div className="whitespace-pre-wrap font-normal text-[12px] space-y-1">
                        {msg.content}
                      </div>

                      {/* Interactive Graph Citations */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-2.5 pt-2 border-t border-slate-200/60 dark:border-slate-700/60 space-y-1">
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                            <Compass size={10} />
                            <span>Cited Graph Nodes:</span>
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {msg.citations.map((cite, cIdx) => (
                              <button
                                key={cIdx}
                                onClick={() => handleCitationClick(cite)}
                                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-indigo-600 dark:text-indigo-400 hover:border-indigo-400 transition-colors cursor-pointer shadow-2xs"
                                title={`Inspect: ${cite.label}`}
                              >
                                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                                <span className="font-semibold truncate max-w-[120px]">
                                  {cite.label}
                                </span>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      <span
                        className={cn(
                          "text-[9px] mt-1 self-end",
                          isUser ? "text-indigo-200" : "text-slate-400"
                        )}
                      >
                        {msg.timestamp}
                      </span>
                    </div>
                  </div>
                );
              })}

              {isThinking && (
                <div className="flex gap-2.5">
                  <div className="w-5 h-5 rounded-md bg-indigo-600 text-white flex items-center justify-center shrink-0">
                    <Sparkles size={11} className="animate-pulse" />
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 rounded-xl p-3 text-xs text-slate-500 flex items-center gap-2">
                    <Spinner size={12} />
                    <span>Traversing cross-meeting paths...</span>
                  </div>
                </div>
              )}

              <div ref={chatBottomRef} />
            </div>

            {/* Quick Suggested Queries */}
            {activeSession.messages.length <= 1 && (
              <div className="px-3 pb-2 pt-1 border-t border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-950/20">
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                  <HelpCircle size={10} />
                  <span>Suggested Graph Queries:</span>
                </p>
                <div className="flex flex-col gap-1">
                  {SUGGESTED_QUERIES.map((q, qIdx) => (
                    <button
                      key={qIdx}
                      onClick={() => handleSendMessage(q)}
                      className="text-left text-[11px] text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-800 px-2 py-1 rounded transition-colors truncate"
                    >
                      • {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Chat Input Bar */}
            <div className="p-2.5 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="flex items-center gap-1.5"
              >
                <input
                  type="text"
                  placeholder="Ask Copilot about people, decisions, topics..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={isThinking}
                  className="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-hidden focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || isThinking}
                  className="p-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0 shadow-xs"
                  title="Send query"
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
