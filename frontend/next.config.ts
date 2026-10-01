import type { NextConfig } from "next";
const config: NextConfig = {
  allowedDevOrigins: ["terminal.local"],
  output: process.env.STATIC_EXPORT === "1" ? "export" : "standalone",
  trailingSlash: true,
  images: { unoptimized: true },
};
export default config;
