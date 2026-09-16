import { Suspense } from "react";
import type { Metadata } from "next";
import { AuthScreen } from "@/components/auth/auth-screen";

export const metadata: Metadata = {
  title: "Create Account — Knowra",
  description: "Create an organization workspace and start turning conversations into enterprise intelligence.",
};

export default function RegisterPage() {
  return (
    <Suspense fallback={null}>
      <AuthScreen initialTab="signup" />
    </Suspense>
  );
}
