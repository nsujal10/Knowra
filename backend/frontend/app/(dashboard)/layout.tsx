import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/sidebar";
import { DashboardMain } from "@/components/layout/dashboard-main";
import { AuthGuard } from "@/components/auth/auth-guard";

export const metadata: Metadata = {
  title: "Dashboard | Knowra",
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-slate-50">
        <Sidebar />
        <DashboardMain>{children}</DashboardMain>
      </div>
    </AuthGuard>
  );
}
