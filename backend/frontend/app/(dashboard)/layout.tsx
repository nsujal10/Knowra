import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

export const metadata: Metadata = {
  title: "Dashboard | Knowra",
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <div className="flex-1 flex flex-col" style={{ marginLeft: "256px" }}>
        <Topbar />
        <main
          className="flex-1 overflow-y-auto p-6"
          style={{ marginTop: "56px" }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
