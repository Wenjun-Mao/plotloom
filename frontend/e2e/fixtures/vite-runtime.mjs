import { createServer as createHttpServer } from "node:http";
import { createServer } from "vite";

const listener = createHttpServer();
let vite;
async function close() {
  await vite?.close();
  listener.closeAllConnections();
  if (listener.listening) await new Promise((resolve, reject) => listener.close(error => error ? reject(error) : resolve()));
}
try {
  // Bind before Vite initializes: its injected HMR fallback also needs the
  // actual positive port, not a released reservation or startup port zero.
  await new Promise((resolve, reject) => {
    listener.once("error", reject);
    listener.listen(0, "127.0.0.1", () => {
      listener.removeListener("error", reject);
      resolve();
    });
  });
  const address = listener.address();
  if (!address || typeof address === "string") throw new Error("Vite has no loopback listener.");
  vite = await createServer({ server: {
    host: "127.0.0.1", port: address.port, strictPort: true,
    middlewareMode: { server: listener },
    hmr: { server: listener, clientPort: address.port },
  } });
  listener.on("request", vite.middlewares);
  console.log("PLOTLOOM_E2E_LISTENER " + JSON.stringify({ role: "frontend", host: address.address, port: address.port }));
  const exit = async () => { await close(); process.exit(0); };
  process.once("SIGTERM", exit);
  process.once("SIGINT", exit);
} catch (error) {
  await close();
  throw error;
}
