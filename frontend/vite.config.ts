import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/entrar": "http://127.0.0.1:8000",
      "/sair": "http://127.0.0.1:8000",
      "/admin": "http://127.0.0.1:8000"
    }
  }
});
