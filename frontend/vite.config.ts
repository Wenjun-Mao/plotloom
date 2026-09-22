import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiOrigin = env.PLOTLOOM_API_ORIGIN || "http://127.0.0.1:8775";
  return {
    base: "/v2/",
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      proxy: { "/api/v2": { target: apiOrigin, changeOrigin: true } },
    },
    build: {
      outDir: fileURLToPath(new URL("../src/plotloom/static", import.meta.url)),
      emptyOutDir: true,
      sourcemap: false,
      rollupOptions: {
        input: {
          main: fileURLToPath(new URL("./index.html", import.meta.url)),
          "u1a-workflow-navigation-demo": fileURLToPath(new URL("./e2e/u1a-workflow-navigation-demo.html", import.meta.url)),
        },
        output: {
          entryFileNames: (chunk) => chunk.name === "main" ? "workbench.js" : `e2e/${chunk.name}.js`,
          chunkFileNames: "assets/[name]-[hash].js",
          assetFileNames: (asset) => asset.names.some((name) => name.endsWith(".css")) ? "workbench.css" : "assets/[name]-[hash][extname]",
        },
      },
    },
  };
});
