import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  productionBrowserSourceMaps: false,
  output: "standalone",
  reactCompiler: true,
};

export default nextConfig;
