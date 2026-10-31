import { fileURLToPath } from "node:url";
import { build } from "vite";

await build({ configFile: fileURLToPath(new URL("./vite.config.ts", import.meta.url)) });
await build({
  configFile: false,
  build: {
    outDir: fileURLToPath(new URL("../src/plotloom/player_static", import.meta.url)),
    emptyOutDir: true,
    sourcemap: false,
    lib: { entry: fileURLToPath(new URL("./src/player/player.ts", import.meta.url)), formats: ["iife"], name: "PlotloomPlayer", fileName: () => "player.js", cssFileName: "player" },
  },
});
