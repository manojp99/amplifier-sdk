import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "amplifier-sdk": path.resolve(__dirname, "../../sdks/typescript/src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/v1": {
        target: "http://localhost:4096",
        changeOrigin: true,
      },
    },
  },
});
