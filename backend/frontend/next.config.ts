import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow cross-origin requests to the backend API in dev
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api"}/:path*`,
      },
    ];
  },
  // Disable development indicators overlay
  devIndicators: false,
  // Enable React strict mode for better DX
  reactStrictMode: true,
};

export default nextConfig;
