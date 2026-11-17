import type { NextConfig } from "next";

const apiOrigin = process.env.FIXFLOW_API_ORIGIN ?? "http://localhost:8001";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiOrigin}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
