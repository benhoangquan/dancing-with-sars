import type { NextConfig } from "next";

// Static export: `next build` writes the whole site to `out/`. A sub-path host (GitHub Pages)
// sets NEXT_PUBLIC_BASE_PATH, for example "/dancing-with-sars"; `src/lib/asset.ts` prefixes assets with it.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  basePath,
  images: { unoptimized: true },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
