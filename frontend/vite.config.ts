import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Keep the browser's Host header (changeOrigin: false) so Django sees the same origin
// as the page and its CSRF Origin check passes without extra trusted origins.
const backend = { target: "http://127.0.0.1:8000", changeOrigin: false };

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
