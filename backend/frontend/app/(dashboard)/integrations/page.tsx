"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { INTEGRATIONS } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import {
  type Integration,
  type IntegrationProvider,
} from "@/lib/types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Input,
  Spinner,
  EmptyState,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn, formatDate } from "@/lib/utils";
import { Plug, Plus, CheckCircle2, XCircle, AlertCircle, RefreshCw } from "lucide-react";

const PROVIDER_META: Record<
  IntegrationProvider,
  { label: string; icon: string; color: string }
> = {
  SLACK: { label: "Slack", icon: "💬", color: "rgba(74,144,226,0.15)" },
  TEAMS: { label: "Microsoft Teams", icon: "🟣", color: "rgba(111,66,193,0.15)" },
  JIRA: { label: "Jira", icon: "🔵", color: "rgba(0,82,204,0.15)" },
  WEBHOOK: { label: "Custom Webhook", icon: "🔗", color: "rgba(79,124,255,0.12)" },
};

const STATUS_BADGE: Record<string, "success" | "danger" | "warning"> = {
  ACTIVE: "success",
  INACTIVE: "warning",
  ERROR: "danger",
};

export default function IntegrationsPage() {
  const [showForm, setShowForm] = useState(false);
  const [provider, setProvider] = useState<IntegrationProvider>("WEBHOOK");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [channelOrProject, setChannelOrProject] = useState("");
  const qc = useQueryClient();

  const { data: integrations = [], isLoading } = useQuery({
    queryKey: queryKeys.integrations.list(),
    queryFn: () => api.get<Integration[]>(INTEGRATIONS.list()),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.post<Integration>(INTEGRATIONS.create(), {
        provider,
        webhook_url: webhookUrl || undefined,
        channel_or_project: channelOrProject || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.integrations.list() });
      setShowForm(false);
      setWebhookUrl("");
      setChannelOrProject("");
    },
  });

  const testMutation = useMutation({
    mutationFn: (id: string) =>
      api.post(`${INTEGRATIONS.test(id)}`),
  });

  const PROVIDERS: IntegrationProvider[] = ["SLACK", "TEAMS", "JIRA", "WEBHOOK"];

  return (
    <div className="space-y-5 animate-fade-in max-w-4xl">
      {/* Header Actions */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-[var(--muted)]">
          Connect Knowra to your external tools. Events are dispatched with HMAC-signed payloads.
        </p>
        <Button
          variant="primary"
          size="sm"
          onClick={() => setShowForm((v) => !v)}
          id="add-integration-btn"
        >
          <Plus size={14} />
          {showForm ? "Cancel" : "Add Integration"}
        </Button>
      </div>

      {/* Add Integration Form */}
      {showForm && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle>New Integration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Provider Selector */}
            <div>
              <p className="text-xs font-medium text-[var(--muted-strong)] uppercase tracking-wider mb-2">Provider</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {PROVIDERS.map((p) => {
                  const meta = PROVIDER_META[p];
                  return (
                    <button
                      key={p}
                      onClick={() => setProvider(p)}
                      className={cn(
                        "flex items-center gap-2 p-3 rounded-[var(--radius-sm)] border text-sm transition-all",
                        provider === p
                          ? "border-[var(--primary)] bg-[var(--primary-muted)] text-[var(--primary)]"
                          : "border-[var(--border)] text-[var(--muted-strong)] hover:border-[var(--border-strong)]"
                      )}
                    >
                      <span>{meta.icon}</span>
                      <span className="font-medium text-xs">{meta.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <Input
              id="integration-webhook-url"
              label="Webhook URL"
              type="url"
              placeholder="https://hooks.slack.com/services/..."
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
            />
            <Input
              id="integration-channel"
              label={provider === "JIRA" ? "Project Key" : "Channel / Project"}
              placeholder={provider === "JIRA" ? "PROJ" : "#channel-name"}
              value={channelOrProject}
              onChange={(e) => setChannelOrProject(e.target.value)}
            />
            <Button
              variant="primary"
              isLoading={createMutation.isPending}
              onClick={() => createMutation.mutate()}
              id="save-integration-btn"
            >
              Save Integration
            </Button>
            {createMutation.isError && (
              <p className="text-xs text-[var(--danger)]">
                {createMutation.error instanceof Error
                  ? createMutation.error.message
                  : "Failed to create integration."}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Integrations List */}
      <Card>
        <CardHeader>
          <CardTitle>Active Integrations</CardTitle>
          {isLoading && <Spinner size={14} />}
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="skeleton h-16 w-full rounded-[var(--radius-sm)]" />
              ))}
            </div>
          ) : integrations.length === 0 ? (
            <EmptyState
              icon={<Plug />}
              title="No integrations configured"
              description="Connect Slack, Teams, Jira, or custom webhooks to automate event dispatching."
            />
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {integrations.map((integration) => {
                const meta = PROVIDER_META[integration.provider] ?? {
                  label: integration.provider,
                  icon: "🔗",
                  color: "transparent",
                };
                return (
                  <div
                    key={integration.id}
                    className="flex items-center gap-4 py-4"
                  >
                    {/* Icon */}
                    <div
                      className="w-10 h-10 rounded-[var(--radius-sm)] flex items-center justify-center text-xl shrink-0"
                      style={{ background: meta.color }}
                    >
                      {meta.icon}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-[var(--foreground)]">
                          {meta.label}
                        </p>
                        <Badge variant={STATUS_BADGE[integration.status]}>
                          {integration.status === "ACTIVE" ? <CheckCircle2 size={9} /> : integration.status === "ERROR" ? <AlertCircle size={9} /> : <XCircle size={9} />}
                          {integration.status}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 mt-0.5">
                        {integration.webhook_url && (
                          <p className="text-[10px] text-[var(--muted)] font-mono truncate max-w-[200px]">
                            {integration.webhook_url}
                          </p>
                        )}
                        {integration.channel_or_project && (
                          <p className="text-[10px] text-[var(--muted)]">
                            → {integration.channel_or_project}
                          </p>
                        )}
                        <p className="text-[10px] text-[var(--muted)]">
                          Added {formatDate(integration.created_at)}
                        </p>
                      </div>
                    </div>

                    {/* Test Button */}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => testMutation.mutate(integration.id)}
                      isLoading={testMutation.isPending && testMutation.variables === integration.id}
                      title="Send test event"
                      id={`test-integration-${integration.id}`}
                    >
                      <RefreshCw size={13} />
                      Test
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Panel */}
      <Card>
        <CardContent>
          <div className="flex gap-3">
            <AlertCircle size={16} className="text-[var(--primary)] shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-xs font-medium text-[var(--foreground)]">Security</p>
              <p className="text-xs text-[var(--muted)] leading-relaxed">
                All outbound webhook payloads are signed with <code>HMAC-SHA256</code>.
                Inbound webhooks require signature verification before processing.
                Credentials are encrypted at rest using AES-256 (Fernet).
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
