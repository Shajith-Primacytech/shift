import type { NextConfig } from "next";

// Same-origin proxy keeps the existing HttpOnly session cookie working on Vercel.
// This setting is an origin only; AMD credentials belong exclusively to FastAPI.
const backend = new URL(
  process.env.SHIFT_BACKEND_URL || "http://127.0.0.1:8000",
);
if (
  !["http:", "https:"].includes(backend.protocol) ||
  backend.username ||
  backend.password ||
  backend.search ||
  backend.hash ||
  backend.pathname !== "/" ||
  (process.env.VERCEL &&
    (!process.env.SHIFT_BACKEND_URL || backend.protocol !== "https:"))
)
  throw new Error("SHIFT_BACKEND_URL must be a backend HTTPS origin on Vercel");

const config: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backend.origin}/api/v1/:path*`,
      },
    ];
  },
};
export default config;
