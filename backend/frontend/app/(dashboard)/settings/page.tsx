"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSession } from "@/lib/auth/session";
import { Button } from "@/components/ui/button";
import { User, Shield, Bell, Palette } from "lucide-react";

export default function SettingsPage() {
  const { session, logout } = useSession();

  return (
    <div className="space-y-5 animate-fade-in max-w-2xl">
      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <User size={14} className="text-[var(--primary)]" />
            Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {session?.user ? (
            <div className="space-y-2">
              <Row label="Name" value={session.user.full_name} />
              <Row label="Email" value={session.user.email} />
              <Row label="Role" value={session.user.role_code} />
              <Row label="Tenant ID" value={session.tenantId} mono />
            </div>
          ) : (
            <p className="text-sm text-[var(--muted)]">No session found.</p>
          )}
        </CardContent>
      </Card>

      {/* Security */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Shield size={14} className="text-[var(--success)]" />
            Security
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Row label="Auth Method" value="JWT Bearer (OAuth2)" />
          <Row label="Token Refresh" value="Automatic (silent retry on 401)" />
          <Row label="RBAC" value="Enabled — enforced at SQL predicate level" />
          <div className="pt-2">
            <Button variant="danger" size="sm" onClick={logout} id="settings-logout-btn">
              Sign Out
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Palette size={14} className="text-[var(--secondary)]" />
            Appearance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--muted)]">Dark mode is always on — Knowra is optimized for high-information-density dark UI.</p>
        </CardContent>
      </Card>

      {/* Notifications placeholder */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Bell size={14} className="text-[var(--warning)]" />
            Notifications
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--muted)]">
            Configure email and Slack notification preferences via the Integrations page.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex justify-between items-center gap-4 py-1.5 border-b border-[var(--border)] last:border-0">
      <span className="text-xs text-[var(--muted)] shrink-0">{label}</span>
      <span
        className={`text-xs text-[var(--foreground)] text-right truncate max-w-[240px] ${mono ? "font-mono" : "font-medium"}`}
      >
        {value}
      </span>
    </div>
  );
}
