import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Parallel dev servers (one per worker) each need their own output folder.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  // The route badge sat over the prompts at 390 in dev screenshots; compile and runtime errors still show.
  devIndicators: false,
};

export default nextConfig;
