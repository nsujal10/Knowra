"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Topbar } from "@/components/layout/topbar";

export function DashboardMain({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);
  const isMeetingDetail = pathname.startsWith("/meetings/") && segments.length > 1;

  return (
    <div
      className="flex-1 flex flex-col min-w-0 transition-[margin] duration-200 ease-in-out"
      style={{ marginLeft: "var(--sidebar-current)" }}
    >
      <Topbar />
      <main
        className={`flex-1 ${
          isMeetingDetail
            ? "h-screen overflow-hidden flex flex-col px-6 lg:px-8 py-2.5 bg-white"
            : "overflow-y-auto px-6 lg:px-8 py-6 bg-slate-50"
        }`}
        style={{ marginTop: isMeetingDetail ? "0px" : "var(--topbar-height)" }}
      >
        {children}
      </main>
    </div>
  );
}
