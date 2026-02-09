import type { NextConfig } from "next";

const nextConfig: NextConfig = {

  typescript: {
    ignoreBuildErrors: true,
  },
  productionBrowserSourceMaps: false,
  output: "standalone",
  reactCompiler: true,
};

export default nextConfig;
