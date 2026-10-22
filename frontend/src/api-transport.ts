import { providerSessionKeys } from "./session-key";
import { ProjectReadAdmission, projectReadScope } from "./project-read-admission";
import type { ProjectReadTicket } from "./project-read-admission";

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly details?: unknown) { super(message); this.name = "ApiError"; }
}

export class ApiTransport {
  private readonly fetcher: typeof fetch;
  constructor(fetcher: typeof fetch, readonly base: string, readonly reads = new ProjectReadAdmission()) {
    // Browser fetch requires its platform receiver; injected transports retain
    // exactly the same invocation contract.
    this.fetcher = (input, init) => fetcher.call(globalThis, input, init);
  }
  private read<T>(path: string, init: RequestInit, operation: () => Promise<T>) {
    const scope = projectReadScope(path);
    return (init.method ?? "GET").toUpperCase() === "GET" && scope !== undefined
      ? this.reads.run(scope, operation, init.signal ?? undefined) : operation();
  }
  async json<T>(path: string, init: RequestInit = {}, includeSessionKey = false, profileId = "default"): Promise<{ body: T; response: Response }> {
    const result = await this.read(path, init, async () => {
      const headers = new Headers(init.headers); headers.set("Accept", "application/json");
      if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
      if (includeSessionKey) { const key = providerSessionKeys.read(profileId); if (key) headers.set("X-Plotloom-Session-API-Key", key); }
      const response = await this.fetcher(`${this.base}${path}`, { ...init, headers });
      const text = await response.text();
      let body;
      try { body = JSON.parse(text); } catch { body = undefined; }
      return { body: body as T, response };
    });
    const { body, response } = result;
    if (!response.ok) throw new ApiError(body && typeof body === "object" && "message" in body ? String(body.message) : `服务请求失败（HTTP ${response.status}）`, response.status, body);
    return result;
  }
  admitDocument(url: string, signal: AbortSignal): Promise<ProjectReadTicket> {
    const path = url.startsWith(this.base) ? url.slice(this.base.length) : url;
    const scope = projectReadScope(path);
    if (scope === undefined) return Promise.reject(new Error("报告地址不属于当前项目 API。"));
    return this.reads.acquire(scope, signal);
  }
  async reportAvailable(url: string, signal: AbortSignal): Promise<boolean> {
    const path = url.startsWith(this.base) ? url.slice(this.base.length) : url;
    return this.read(path, { signal }, async () => {
      const response = await this.fetcher(url, { signal, headers: { Accept: "text/html" } });
      await response.text();
      return response.ok;
    });
  }
}
