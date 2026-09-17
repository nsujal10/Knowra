import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
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

        <div
          className="flex-1 flex flex-col min-w-0 transition-[margin] duration-200 ease-in-out"
          style={{ marginLeft: "var(--sidebar-current)" }}
        >
          <Topbar />
          <main
            className="flex-1 overflow-y-auto px-8 py-6 bg-slate-50"
            style={{ marginTop: "var(--topbar-height)" }}
          >
            {children}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
