import type { NextConfig } from "next";

// Static export (out/) is for local/off-Vercel hosting; Vercel needs .next + routes-manifest.
const nextConfig: NextConfig = {
  ...(process.env.VERCEL ? {} : { output: "export" as const }),
  images: { unoptimized: true },
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: false },
};

export default nextConfig;
