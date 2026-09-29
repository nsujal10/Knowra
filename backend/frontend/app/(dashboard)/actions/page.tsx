"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { ACTIONS } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import type { EnterpriseActionsResponse, ActionItem } from "@/lib/types";
import {
  CheckSquare,
  Square,
  Search,
  ArrowRight,
  User,
  Clock,
  Video,
  AlertCircle,
  CheckCircle2,
  Calendar,
  Sparkles,
  Quote,
  Filter,
  RefreshCw,
  Flame,
  ListTodo,
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";

const STATUS_FILTERS = ["ALL", "PENDING", "COMPLETED"];
const PRIORITY_FILTERS = ["ALL", "URGENT", "HIGH", "MEDIUM", "LOW"];

export default function GlobalActionsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selectedMeeting, setSelectedMeeting] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [selectedPriority, setSelectedPriority] = useState<string>("ALL");
  const [selectedOwner, setSelectedOwner] = useState<string>("ALL");

  // Fetch real action items from backend
  const { data, isLoading, refetch, isFetching } = useQuery<EnterpriseActionsResponse>({
    queryKey: [
      ...queryKeys.actions.byMeeting(selectedMeeting === "ALL" ? undefined : selectedMeeting),
      selectedStatus,
      selectedPriority,
      selectedOwner,
    ],
    queryFn: () =>
      api.get<EnterpriseActionsResponse>(
        ACTIONS.list({
          meetingId: selectedMeeting === "ALL" ? undefined : selectedMeeting,
          status: selectedStatus === "ALL" ? undefined : selectedStatus,
          priority: selectedPriority === "ALL" ? undefined : selectedPriority,
          owner: selectedOwner === "ALL" ? undefined : selectedOwner,
        })
      ),
  });

  // Toggle mutation
  const toggleMutation = useMutation({
    mutationFn: (actionId: string) => api.patch<ActionItem>(ACTIONS.toggle(actionId), {}),
    onMutate: async (actionId) => {
      // Optimistic update
      const currentQueryKey = [
        ...queryKeys.actions.byMeeting(selectedMeeting === "ALL" ? undefined : selectedMeeting),
        selectedStatus,
        selectedPriority,
        selectedOwner,
      ];
      await queryClient.cancelQueries({ queryKey: currentQueryKey });
      const previousData = queryClient.getQueryData<EnterpriseActionsResponse>(currentQueryKey);

      if (previousData) {
        queryClient.setQueryData<EnterpriseActionsResponse>(currentQueryKey, {
          ...previousData,
          items: previousData.items.map((item) =>
            item.id === actionId
              ? {
                  ...item,
                  status: item.status === "COMPLETED" ? "OPEN" : "COMPLETED",
                  completed_at: item.status === "COMPLETED" ? null : new Date().toISOString(),
                }
              : item
          ),
          metrics: {
            ...previousData.metrics,
            completed_count:
              previousData.metrics.completed_count +
              (previousData.items.find((i) => i.id === actionId)?.status === "COMPLETED" ? -1 : 1),
            pending_count:
              previousData.metrics.pending_count +
              (previousData.items.find((i) => i.id === actionId)?.status === "COMPLETED" ? 1 : -1),
          },
        });
      }
      return { previousData, currentQueryKey };
    },
    onError: (_err, _actionId, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(context.currentQueryKey, context.previousData);
      }
    },
    onSettled: (_data, _err, _actionId, context) => {
      if (context?.currentQueryKey) {
        queryClient.invalidateQueries({ queryKey: context.currentQueryKey });
      }
      queryClient.invalidateQueries({ queryKey: ["actions"] });
    },
  });

  const items = data?.items ?? [];
  const metrics = data?.metrics ?? {
    total_items: 0,
    pending_count: 0,
    completed_count: 0,
    urgent_count: 0,
    completion_rate: "0%",
  };
  const meetingsList = data?.meetings ?? [];
  const ownersList = data?.owners ?? [];

  // Client-side text search filter
  const filteredItems = useMemo(() => {
    if (!search.trim()) return items;
    const term = search.toLowerCase();
    return items.filter(
      (item) =>
        item.title.toLowerCase().includes(term) ||
        (item.description && item.description.toLowerCase().includes(term)) ||
        (item.assignee && item.assignee.toLowerCase().includes(term)) ||
        (item.owner_raw && item.owner_raw.toLowerCase().includes(term)) ||
        (item.meeting_title && item.meeting_title.toLowerCase().includes(term))
    );
  }, [items, search]);

  const getPriorityBadgeClass = (priority: string) => {
    switch (priority?.toUpperCase()) {
      case "URGENT":
        return "bg-rose-50 text-rose-700 border-rose-200/80";
      case "HIGH":
        return "bg-amber-50 text-amber-700 border-amber-200/80";
      case "LOW":
        return "bg-slate-100 text-slate-600 border-slate-200";
      default:
        return "bg-blue-50 text-blue-700 border-blue-200/80";
    }
  };

  const getStatusBadgeClass = (status: string) => {
    if (status === "COMPLETED") {
      return "bg-emerald-50 text-emerald-700 border-emerald-200/80";
    }
    if (status === "IN_PROGRESS") {
      return "bg-sky-50 text-sky-700 border-sky-200/80";
    }
    if (status === "REVIEW_REQUIRED") {
      return "bg-purple-50 text-purple-700 border-purple-200/80";
    }
    return "bg-slate-100 text-slate-700 border-slate-200";
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16 animate-fade-in">
      {/* ── ENTERPRISE PAGE HEADER ─────────────────────────────────────────── */}
      <PageHeader
        title="Action Items Tracker"
        subtitle="Centrally tracked deliverables, owners, and verbal commitments extracted by AI from company meetings."
        icon={ListTodo}
        statusDot={true}
        badge={
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
            {metrics.total_items} Tracked Deliverables
          </span>
        }
        actions={
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 shadow-xs transition-all cursor-pointer disabled:opacity-50"
            title="Refresh action items from database"
          >
            <RefreshCw size={13} className={isFetching ? "animate-spin" : ""} />
            <span>Sync Actions</span>
          </button>
        }
      />

      {/* ── METRIC CARDS ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Action Items */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
          <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
            Total Deliverables
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-3xl font-bold text-slate-900 tracking-tight">
              {isLoading ? "—" : metrics.total_items}
            </span>
            <div className="bg-indigo-50 text-indigo-600 p-2 rounded-lg shrink-0">
              <CheckSquare size={18} />
            </div>
          </div>
        </div>

        {/* Pending Items */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
          <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
            Pending Execution
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <div className="space-y-0.5">
              <span className="text-3xl font-bold text-slate-900 tracking-tight">
                {isLoading ? "—" : metrics.pending_count}
              </span>
              <p className="text-[11px] text-amber-600 font-medium">Awaiting completion</p>
            </div>
            <div className="bg-amber-50 text-amber-600 p-2 rounded-lg shrink-0">
              <Clock size={18} />
            </div>
          </div>
        </div>

        {/* Completed Items */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
          <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
            Completed Tasks
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <div className="space-y-0.5">
              <span className="text-3xl font-bold text-emerald-600 tracking-tight">
                {isLoading ? "—" : metrics.completed_count}
              </span>
              <p className="text-[11px] text-emerald-600 font-medium">{metrics.completion_rate}</p>
            </div>
            <div className="bg-emerald-50 text-emerald-600 p-2 rounded-lg shrink-0">
              <CheckCircle2 size={18} />
            </div>
          </div>
        </div>

        {/* Urgent & High Priority */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
          <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
            High Priority
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <div className="space-y-0.5">
              <span className="text-3xl font-bold text-rose-600 tracking-tight">
                {isLoading ? "—" : metrics.urgent_count}
              </span>
              <p className="text-[11px] text-rose-600 font-medium">Urgent deadlines</p>
            </div>
            <div className="bg-rose-50 text-rose-600 p-2 rounded-lg shrink-0">
              <Flame size={18} />
            </div>
          </div>
        </div>
      </div>

      {/* ── FILTER & SEARCH BAR ─────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3.5">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search action items, assignees, or keywords…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-9 pl-9 pr-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-100 transition-all"
            />
          </div>

          {/* Dropdown Filters (Meeting, Owner, Priority) */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Meeting Filter Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-600">
              <Video size={13} className="text-slate-400 shrink-0" />
              <select
                value={selectedMeeting}
                onChange={(e) => setSelectedMeeting(e.target.value)}
                className="bg-transparent border-none text-xs font-medium text-slate-800 outline-none cursor-pointer max-w-[180px] truncate"
              >
                <option value="ALL">All Meetings ({metrics.total_items})</option>
                {meetingsList.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.title} ({m.action_count})
                  </option>
                ))}
              </select>
            </div>

            {/* Owner Filter Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-600">
              <User size={13} className="text-slate-400 shrink-0" />
              <select
                value={selectedOwner}
                onChange={(e) => setSelectedOwner(e.target.value)}
                className="bg-transparent border-none text-xs font-medium text-slate-800 outline-none cursor-pointer max-w-[150px] truncate"
              >
                <option value="ALL">All Owners</option>
                {ownersList.map((owner) => (
                  <option key={owner} value={owner}>
                    {owner}
                  </option>
                ))}
              </select>
            </div>

            {/* Priority Filter Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-600">
              <Filter size={13} className="text-slate-400 shrink-0" />
              <select
                value={selectedPriority}
                onChange={(e) => setSelectedPriority(e.target.value)}
                className="bg-transparent border-none text-xs font-medium text-slate-800 outline-none cursor-pointer"
              >
                {PRIORITY_FILTERS.map((p) => (
                  <option key={p} value={p}>
                    Priority: {p === "ALL" ? "All" : p}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Status Tabs */}
        <div className="flex items-center gap-2 pt-1 border-t border-slate-100">
          <button
            onClick={() => setSelectedStatus("ALL")}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
              selectedStatus === "ALL"
                ? "bg-slate-900 text-white shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            All ({metrics.total_items})
          </button>
          <button
            onClick={() => setSelectedStatus("PENDING")}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
              selectedStatus === "PENDING"
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Pending ({metrics.pending_count})
          </button>
          <button
            onClick={() => setSelectedStatus("COMPLETED")}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
              selectedStatus === "COMPLETED"
                ? "bg-emerald-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Completed ({metrics.completed_count})
          </button>
        </div>
      </div>

      {/* ── ACTION ITEMS LIST ────────────────────────────────────────────── */}
      {isLoading ? (
        <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100 shadow-sm overflow-hidden animate-pulse">
          {[1, 2, 3, 4, 5].map((n) => (
            <div key={n} className="p-5 flex items-start gap-4">
              <div className="w-5 h-5 bg-slate-200 rounded mt-0.5"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 w-3/4 bg-slate-200 rounded"></div>
                <div className="h-3 w-1/2 bg-slate-100 rounded"></div>
              </div>
              <div className="h-5 w-16 bg-slate-200 rounded"></div>
            </div>
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3 shadow-sm">
          <div className="bg-slate-50 text-slate-400 w-12 h-12 rounded-full flex items-center justify-center mx-auto">
            <CheckSquare size={24} />
          </div>
          <h3 className="text-base font-semibold text-slate-800">
            No action items match your filters
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            {search
              ? `No results for "${search}". Try adjusting your query or resetting filters.`
              : "No action items found for the selected criteria."}
          </p>
          {(search || selectedMeeting !== "ALL" || selectedStatus !== "ALL" || selectedPriority !== "ALL" || selectedOwner !== "ALL") && (
            <button
              onClick={() => {
                setSearch("");
                setSelectedMeeting("ALL");
                setSelectedStatus("ALL");
                setSelectedPriority("ALL");
                setSelectedOwner("ALL");
              }}
              className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 text-xs font-semibold text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer"
            >
              <span>Reset all filters</span>
            </button>
          )}
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100 shadow-sm overflow-hidden">
          {filteredItems.map((item) => {
            const isDone = item.status === "COMPLETED";
            return (
              <div
                key={item.id}
                className="p-5 hover:bg-slate-50/70 transition-colors flex items-start gap-4 group"
              >
                {/* Interactive Checkbox Toggle */}
                <button
                  type="button"
                  onClick={() => toggleMutation.mutate(item.id)}
                  disabled={toggleMutation.isPending}
                  className="mt-0.5 text-slate-400 hover:text-indigo-600 transition-all cursor-pointer shrink-0 disabled:opacity-60"
                  title={isDone ? "Mark as Open" : "Mark as Completed"}
                >
                  {isDone ? (
                    <CheckSquare size={20} className="text-emerald-600 fill-emerald-50" />
                  ) : (
                    <Square size={20} className="hover:text-slate-700" />
                  )}
                </button>

                {/* Content */}
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p
                      className={`text-sm font-semibold tracking-tight transition-all ${
                        isDone
                          ? "line-through text-slate-400"
                          : "text-slate-900 group-hover:text-indigo-600"
                      }`}
                    >
                      {item.title}
                    </p>

                    {/* Status & Priority Badges */}
                    <div className="flex items-center gap-2 shrink-0">
                      {item.priority && (
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${getPriorityBadgeClass(
                            item.priority
                          )}`}
                        >
                          {item.priority}
                        </span>
                      )}
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${getStatusBadgeClass(
                          item.status
                        )}`}
                      >
                        {item.status === "REVIEW_REQUIRED" ? "AI SUGGESTED" : item.status}
                      </span>
                    </div>
                  </div>

                  {item.description && (
                    <p className="text-xs text-slate-600 leading-relaxed">
                      {item.description}
                    </p>
                  )}

                  {/* Metadata Chips: Owner, Due Date, Meeting, Timestamp */}
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-500 pt-0.5">
                    <span className="inline-flex items-center gap-1.5">
                      <User size={13} className="text-slate-400" />
                      <span>Owner:</span>
                      <strong className="text-slate-700 font-medium">
                        {item.assignee || item.owner_raw || "Team"}
                      </strong>
                    </span>

                    {(item.due_date_raw || item.due_date) && (
                      <span className="inline-flex items-center gap-1.5">
                        <Calendar size={13} className="text-slate-400" />
                        <span>Due:</span>
                        <strong className="text-slate-700 font-medium">
                          {item.due_date_raw || (item.due_date ? item.due_date.split("T")[0] : "N/A")}
                        </strong>
                      </span>
                    )}

                    {item.timestamp && (
                      <span className="inline-flex items-center gap-1 font-mono text-[11px] text-slate-400">
                        <Clock size={12} />
                        <span>Recorded @ {item.timestamp}</span>
                      </span>
                    )}

                    {item.meeting_title && (
                      <Link
                        href={`/meetings/${item.meeting_id}/actions`}
                        className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-700 font-medium hover:underline ml-auto"
                      >
                        <Video size={12} />
                        <span className="max-w-[200px] truncate">{item.meeting_title}</span>
                        <ArrowRight size={11} />
                      </Link>
                    )}
                  </div>

                  {/* Provenance Snippet */}
                  {item.evidence_snippet && (
                    <div className="mt-1.5 p-2 rounded-lg bg-slate-50 border border-slate-200/60 text-xs text-slate-600 flex items-start gap-2">
                      <Quote size={12} className="text-indigo-400 shrink-0 mt-0.5 rotate-180" />
                      <p className="italic text-[11px] text-slate-600 leading-relaxed">
                        &ldquo;{item.evidence_snippet.trim()}&rdquo;
                      </p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
