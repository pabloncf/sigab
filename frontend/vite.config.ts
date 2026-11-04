import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Without @types/node in the project, declare only what the config reads.
declare const process: { env: Record<string, string | undefined> };

// Keep the browser's Host header (changeOrigin: false) so Django sees the same origin
// as the page and its CSRF Origin check passes without extra trusted origins.
// In Docker the backend is another container, set through SIGAB_BACKEND_URL.
const backend = {
  target: process.env.SIGAB_BACKEND_URL ?? "http://127.0.0.1:8000",
  changeOrigin: false
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": backend,
      "/entrar": backend,
      "/sair": backend,
      "/admin": backend
    }
  }
});
