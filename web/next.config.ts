import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Parallel dev servers (one per worker) each need their own output folder.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
};

export default nextConfig;
