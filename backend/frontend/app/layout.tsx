import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Knowra — Enterprise Meeting Intelligence",
    template: "%s | Knowra",
  },
  description:
    "AI-powered meeting intelligence platform with transcription, diarization, and organizational knowledge management.",
  keywords: ["meeting intelligence", "transcription", "diarization", "RAG", "AI"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
