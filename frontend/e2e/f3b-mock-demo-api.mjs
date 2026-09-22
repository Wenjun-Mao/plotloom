import { createServer } from "node:http";

const portIndex = process.argv.indexOf("--port");
const port = Number(process.argv[portIndex + 1] || 8794);
const card = (id) => {
  const letter = id.split("-").at(-1)?.toUpperCase() || "?";
  const prop = id.includes("prop");
  const colors = { A: ["#164e63", "#67e8f9"], B: ["#4c1d95", "#c4b5fd"], C: ["#713f12", "#fde68a"], D: ["#7f1d1d", "#fca5a5"], E: ["#14532d", "#86efac"] }[letter] || ["#334155", "#cbd5e1"];
  const shape = prop ? `<path d="M480 100 690 270 570 440 390 440 270 270Z" fill="${colors[1]}" opacity=".9"/><circle cx="480" cy="270" r="70" fill="${colors[0]}"/>` : `<path d="M120 390 320 170 450 300 590 120 840 390Z" fill="${colors[1]}" opacity=".9"/><circle cx="720" cy="150" r="52" fill="${colors[0]}"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540"><rect width="960" height="540" fill="${colors[0]}"/><path d="M0 0h960v540H0z" fill="url(#g)"/><defs><pattern id="p" width="42" height="42" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><path d="M0 0h42v8H0z" fill="#fff" opacity=".13"/></pattern><linearGradient id="g"><stop stop-color="#020617" stop-opacity=".32"/><stop offset="1" stop-color="#000" stop-opacity=".05"/></linearGradient></defs><rect width="960" height="540" fill="url(#p)"/>${shape}<text x="48" y="70" fill="white" font-family="system-ui" font-size="30" font-weight="700">${prop ? "PROP" : "SCENE"} · MOCK ${letter}</text><text x="48" y="505" fill="white" font-family="system-ui" font-size="18">read-only static test card · no generated media</text></svg>`;
};

createServer((request, response) => {
  const match = request.url?.match(/managed-assets\/(demo-(?:scene|prop)-[a-e])\/display$/i);
  if (!match || request.method !== "GET") { response.writeHead(404).end("Read-only F3B demo asset server"); return; }
  response.writeHead(200, { "Content-Type": "image/svg+xml", "Cache-Control": "no-store" });
  response.end(card(match[1]));
}).listen(port, "127.0.0.1", () => console.log(`F3B read-only mock asset server: http://127.0.0.1:${port}`));
