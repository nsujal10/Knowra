"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { EVALUATION } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import {
  type EvaluationRun,
  type AITrace,
  type QualityOverview,
  type CostSummary,
} from "@/lib/types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Spinner,
} from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  Legend,
} from "recharts";
import { formatMetric, formatCost, metricColor, formatDate, cn } from "@/lib/utils";
import { CheckCircle2, XCircle, AlertCircle, Zap, DollarSign, Clock } from "lucide-react";

const TABS = ["Overview", "Runs", "Traces", "Costs"] as const;
type Tab = (typeof TABS)[number];

export default function EvaluationPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Overview");

  const { data: quality } = useQuery({
    queryKey: queryKeys.evaluation.quality(),
    queryFn: () => api.get<QualityOverview>(EVALUATION.quality()),
  });

  const { data: costs } = useQuery({
    queryKey: queryKeys.evaluation.costs(),
    queryFn: () => api.get<CostSummary>(EVALUATION.costs()),
  });

  const { data: runs = [], isLoading: runsLoading } = useQuery({
    queryKey: queryKeys.evaluation.runs(),
    queryFn: () => api.get<EvaluationRun[]>(EVALUATION.runs()),
  });

  const { data: traces = [], isLoading: tracesLoading } = useQuery({
    queryKey: queryKeys.evaluation.traces(),
    queryFn: () =>
      api.get<AITrace[]>(`${EVALUATION.traces()}?limit=50`),
  });

  const chartData = runs.slice(-10).map((r) => ({
    name: r.dataset_name.slice(0, 12),
    Faithfulness: r.metrics.faithfulness ?? 0,
    Relevance: r.metrics.answer_relevance ?? 0,
    Precision: r.metrics.context_precision ?? 0,
    WER: r.metrics.wer ?? 0,
  }));

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)] pb-0">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-all",
              activeTab === tab
                ? "border-[var(--primary)] text-[var(--primary)]"
                : "border-transparent text-[var(--muted-strong)] hover:text-[var(--foreground)]"
            )}
            id={`eval-tab-${tab.toLowerCase()}`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "Overview" && quality && (
        <div className="space-y-5">
          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard
              label="Faithfulness"
              value={formatMetric(quality.avg_faithfulness)}
              icon={<Zap size={16} />}
              color="primary"
              sub="Avg across runs"
            />
            <KPICard
              label="Answer Relevance"
              value={formatMetric(quality.avg_answer_relevance)}
              icon={<CheckCircle2 size={16} />}
              color="success"
              sub="Response alignment"
            />
            <KPICard
              label="Hallucination Rate"
              value={formatMetric(quality.hallucination_rate)}
              icon={<AlertCircle size={16} />}
              color="warning"
              sub="Lower is better"
            />
            <KPICard
              label="Pass Rate"
              value={`${quality.passed_runs}/${quality.total_runs}`}
              icon={<CheckCircle2 size={16} />}
              color="success"
              sub="Regression gates"
            />
          </div>

          {/* Chart */}
          {chartData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>RAG Metrics Trend (Last 10 Runs)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={chartData} margin={{ left: -10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#6b7280" }} />
                    <YAxis
                      tick={{ fontSize: 10, fill: "#6b7280" }}
                      domain={[0, 1]}
                      tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--surface-2)",
                        border: "1px solid var(--border)",
                        borderRadius: 8,
                        fontSize: 11,
                        color: "var(--foreground)",
                      }}
                      formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="Faithfulness" stroke="#4f7cff" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="Relevance" stroke="#10b981" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="Precision" stroke="#a78bfa" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {activeTab === "Runs" && (
        <Card>
          <CardHeader>
            <CardTitle>Evaluation Run History</CardTitle>
            {runsLoading && <Spinner size={14} />}
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)]">
                    {["Dataset", "Pipeline", "Status", "Faithfulness", "WER", "DER", "Date"].map((h) => (
                      <th key={h} className="text-left text-[10px] text-[var(--muted)] uppercase tracking-wider pb-2 pr-4 font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {runs.map((run) => (
                    <tr key={run.id} className="hover:bg-[var(--surface-2)] transition-colors">
                      <td className="py-3 pr-4 text-[var(--foreground)] font-medium max-w-[120px] truncate">{run.dataset_name}</td>
                      <td className="py-3 pr-4 text-[var(--muted)] font-mono text-xs">{run.pipeline_version}</td>
                      <td className="py-3 pr-4">
                        <Badge variant={run.status === "PASSED" ? "success" : run.status === "FAILED" ? "danger" : "warning"}>
                          {run.status === "PASSED" ? <CheckCircle2 size={9} /> : <XCircle size={9} />}
                          {run.status}
                        </Badge>
                      </td>
                      <td className={cn("py-3 pr-4 font-mono text-xs", metricColor(run.metrics.faithfulness))}>
                        {formatMetric(run.metrics.faithfulness)}
                      </td>
                      <td className={cn("py-3 pr-4 font-mono text-xs", metricColor(run.metrics.wer ? 1 - run.metrics.wer : null))}>
                        {formatMetric(run.metrics.wer)}
                      </td>
                      <td className={cn("py-3 pr-4 font-mono text-xs", metricColor(run.metrics.der ? 1 - run.metrics.der : null))}>
                        {formatMetric(run.metrics.der)}
                      </td>
                      <td className="py-3 text-xs text-[var(--muted)]">{formatDate(run.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {runs.length === 0 && !runsLoading && (
                <p className="text-sm text-[var(--muted)] text-center py-8">No evaluation runs yet.</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === "Traces" && (
        <Card>
          <CardHeader>
            <CardTitle>AI Execution Traces</CardTitle>
            {tracesLoading && <Spinner size={14} />}
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {traces.map((trace) => (
                <div key={trace.id} className="flex items-center gap-4 p-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)]">
                  <div className="w-20 shrink-0">
                    <Badge
                      variant={
                        trace.stage === "GENERATION"
                          ? "primary"
                          : trace.stage === "RETRIEVAL"
                          ? "secondary"
                          : "default"
                      }
                    >
                      {trace.stage.slice(0, 5)}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-[var(--foreground)] font-mono w-20">
                    <Clock size={10} className="text-[var(--muted)]" />
                    {trace.latency_ms}ms
                  </div>
                  <div className="flex items-center gap-1 text-xs text-[var(--muted)] w-24">
                    <Zap size={10} />
                    {trace.prompt_tokens + trace.completion_tokens} tok
                  </div>
                  <div className="flex items-center gap-1 text-xs w-20">
                    <DollarSign size={10} className="text-[var(--muted)]" />
                    <span className={cn("font-mono", trace.estimated_cost_usd > 0.01 ? "text-[var(--warning)]" : "text-[var(--muted-strong)]")}>
                      {formatCost(trace.estimated_cost_usd)}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0 text-[10px] text-[var(--muted)] font-mono truncate">
                    req:{trace.request_id.slice(0, 12)}
                  </div>
                  {trace.error_message && (
                    <span className="text-[10px] text-[var(--danger)]">ERR</span>
                  )}
                </div>
              ))}
              {traces.length === 0 && !tracesLoading && (
                <p className="text-sm text-[var(--muted)] text-center py-8">No traces recorded yet.</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === "Costs" && costs && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            <KPICard
              label={`Total Cost (${costs.period_days}d)`}
              value={formatCost(costs.total_cost_usd)}
              icon={<DollarSign size={16} />}
              color="warning"
              sub="Estimated USD"
            />
            <KPICard
              label="Prompt Tokens"
              value={costs.total_prompt_tokens.toLocaleString()}
              icon={<Zap size={16} />}
              color="primary"
              sub="Input tokens"
            />
            <KPICard
              label="Completion Tokens"
              value={costs.total_completion_tokens.toLocaleString()}
              icon={<Zap size={16} />}
              color="secondary"
              sub="Output tokens"
            />
          </div>
          {costs.cost_by_stage && (
            <Card>
              <CardHeader><CardTitle>Cost by Pipeline Stage</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={Object.entries(costs.cost_by_stage).map(([k, v]) => ({ name: k, Cost: v }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#6b7280" }} />
                    <YAxis tick={{ fontSize: 10, fill: "#6b7280" }} tickFormatter={(v) => `$${v.toFixed(3)}`} />
                    <Tooltip
                      contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 11 }}
                      formatter={(v: number) => [`$${v.toFixed(4)}`, "Cost"]}
                    />
                    <Bar dataKey="Cost" fill="var(--primary)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function KPICard({
  label,
  value,
  icon,
  color,
  sub,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  color: "primary" | "success" | "warning" | "secondary";
  sub: string;
}) {
  const colorMap = {
    primary: "text-[var(--primary)] bg-[var(--primary-muted)]",
    success: "text-[var(--success)] bg-[var(--success-muted)]",
    warning: "text-[var(--warning)] bg-[var(--warning-muted)]",
    secondary: "text-[var(--secondary)] bg-[var(--secondary-muted)]",
  };
  return (
    <Card>
      <CardContent>
        <div className="flex items-start gap-3">
          <div className={cn("p-2 rounded-[var(--radius-sm)]", colorMap[color])}>
            {icon}
          </div>
          <div>
            <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider font-medium">{label}</p>
            <p className="text-xl font-bold text-[var(--foreground)] leading-tight font-mono">{value}</p>
            <p className="text-[10px] text-[var(--muted)] mt-0.5">{sub}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
