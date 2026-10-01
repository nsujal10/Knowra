"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { ACTIONS, MEETINGS } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import type { EnterpriseActionsResponse, ActionItem, Meeting } from "@/lib/types";
import {
  CheckSquare,
  Square,
  Clock,
  User,
  AlertCircle,
  CheckCircle2,
  Calendar,
  ArrowLeft,
  RefreshCw,
  Video,
  Quote,
  Flame,
} from "lucide-react";
import { toast } from "@/components/ui/toast";

export default function MeetingActionsPage() {
  const params = useParams();
  const rawMeetingId = params?.id as string;
  const queryClient = useQueryClient();

  // Fetch meeting metadata
  const { data: meeting } = useQuery<Meeting>({
    queryKey: queryKeys.meetings.detail(rawMeetingId),
    queryFn: () => api.get<Meeting>(MEETINGS.get(rawMeetingId)),
    enabled: !!rawMeetingId && rawMeetingId !== "m-001",
    retry: false,
  });

  // Fetch real action items for this meeting
  const { data, isLoading, refetch, isFetching } = useQuery<EnterpriseActionsResponse>({
    queryKey: queryKeys.actions.byMeeting(rawMeetingId),
    queryFn: () =>
      api.get<EnterpriseActionsResponse>(
        ACTIONS.list({
          meetingId: rawMeetingId !== "m-001" ? rawMeetingId : undefined,
        })
      ),
  });

  // Toggle mutation
  const toggleMutation = useMutation({
    mutationFn: (actionId: string) => api.patch<ActionItem>(ACTIONS.toggle(actionId), {}),
    onMutate: async (actionId) => {
      const currentQueryKey = queryKeys.actions.byMeeting(rawMeetingId);
      await queryClient.cancelQueries({ queryKey: currentQueryKey });
      const previousData = queryClient.getQueryData<EnterpriseActionsResponse>(currentQueryKey);

      if (previousData) {
        const itemToUpdate = previousData.items.find((i) => i.id === actionId);
        const willBeCompleted = itemToUpdate?.status !== "COMPLETED";

        queryClient.setQueryData<EnterpriseActionsResponse>(currentQueryKey, {
          ...previousData,
          items: previousData.items.map((item) =>
            item.id === actionId
              ? {
                  ...item,
                  status: willBeCompleted ? "COMPLETED" : "OPEN",
                  completed_at: willBeCompleted ? new Date().toISOString() : null,
                }
              : item
          ),
          metrics: {
            ...previousData.metrics,
            completed_count:
              previousData.metrics.completed_count + (willBeCompleted ? 1 : -1),
            pending_count:
              previousData.metrics.pending_count + (willBeCompleted ? -1 : 1),
          },
        });

        if (willBeCompleted) {
          toast.success("Deliverable marked as completed");
        } else {
          toast.info("Deliverable moved to pending");
        }
      }
      return { previousData, currentQueryKey };
    },
    onError: (_err, _actionId, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(context.currentQueryKey, context.previousData);
      }
      toast.error("Could not update deliverable status");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.actions.byMeeting(rawMeetingId) });
      queryClient.invalidateQueries({ queryKey: ["actions"] });
    },
  });

  const items = data?.items ?? [];
  const metrics = data?.metrics ?? {
    total_items: items.length,
    pending_count: items.filter((i) => i.status !== "COMPLETED").length,
    completed_count: items.filter((i) => i.status === "COMPLETED").length,
    urgent_count: items.filter((i) => i.priority === "HIGH" || i.priority === "URGENT").length,
    completion_rate: "0%",
  };

  const meetingTitle = meeting?.title || items[0]?.meeting_title || "Meeting Session Deliverables";

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
    <div className="space-y-6 max-w-6xl mx-auto pb-16 animate-fade-in">
      {/* ── BREADCRUMB & HEADER ─────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Link
              href="/actions"
              className="hover:text-indigo-600 transition-colors flex items-center gap-1 font-medium"
            >
              <ArrowLeft size={12} />
              <span>All Action Items</span>
            </Link>
            <span>/</span>
            <span className="text-slate-800 font-medium truncate max-w-xs">{meetingTitle}</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>{meetingTitle}</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold border border-slate-200">
              Deliverables
            </span>
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 shadow-sm transition-all cursor-pointer disabled:opacity-50"
          >
            <RefreshCw size={13} className={isFetching ? "animate-spin" : ""} />
            <span>Sync</span>
          </button>

          {rawMeetingId && rawMeetingId !== "m-001" && (
            <Link
              href={`/meetings/${rawMeetingId}`}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 text-xs font-medium transition-all"
            >
              <Video size={13} />
              <span>Meeting Recap</span>
            </Link>
          )}
        </div>
      </div>

      {/* ── METRIC CARDS ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4.5 flex items-center justify-between hover:border-slate-300 transition-all">
          <div>
            <span className="text-xs text-slate-500 uppercase font-semibold">Total Deliverables</span>
            <p className="text-2xl font-bold text-slate-900 mt-1">{isLoading ? "—" : items.length}</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
            <CheckSquare size={20} />
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4.5 flex items-center justify-between hover:border-slate-300 transition-all">
          <div>
            <span className="text-xs text-slate-500 uppercase font-semibold">Completed</span>
            <p className="text-2xl font-bold text-emerald-600 mt-1">
              {isLoading ? "—" : `${metrics.completed_count} of ${items.length}`}
            </p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <CheckCircle2 size={20} />
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4.5 flex items-center justify-between hover:border-slate-300 transition-all">
          <div>
            <span className="text-xs text-slate-500 uppercase font-semibold">Pending Review</span>
            <p className="text-2xl font-bold text-amber-600 mt-1">
              {isLoading ? "—" : metrics.pending_count}
            </p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
            <AlertCircle size={20} />
          </div>
        </div>
      </div>

      {/* ── ACTION ITEMS LIST ────────────────────────────────────────────── */}
      {isLoading ? (
        <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100 shadow-sm overflow-hidden animate-pulse">
          {[1, 2, 3].map((n) => (
            <div key={n} className="p-5 flex items-start gap-4">
              <div className="w-5 h-5 bg-slate-200 rounded mt-0.5"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 w-3/4 bg-slate-200 rounded"></div>
                <div className="h-3 w-1/2 bg-slate-100 rounded"></div>
              </div>
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3 shadow-sm">
          <div className="bg-slate-50 text-slate-400 w-12 h-12 rounded-full flex items-center justify-center mx-auto">
            <CheckSquare size={24} />
          </div>
          <h3 className="text-base font-semibold text-slate-800">
            No action items recorded for this meeting
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Action items and verbal commitments are automatically extracted by AI when tasks or deadlines are assigned.
          </p>
          <div className="pt-2">
            <Link
              href="/actions"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors"
            >
              <span>Explore all company action items</span>
            </Link>
          </div>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100 shadow-sm overflow-hidden">
          {items.map((item) => {
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

                  {/* Metadata: Owner, Due Date, Timestamp */}
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
