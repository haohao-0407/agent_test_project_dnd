import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8766",
      "/ws": {
        target: "ws://127.0.0.1:8766",
        ws: true
      },
      "/character-assets": "http://127.0.0.1:8766",
      "/module-assets": "http://127.0.0.1:8766"
    }
  }
});
