/** API base URL — configurable via VITE_API_BASE env var. */
export const API_BASE = import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? "" : "http://127.0.0.1:10944");
export const API = `${API_BASE}/api/v1`;

export function apiPath(path: string): string {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

/** Patch fetch/EventSource for Tauri production (relative /api paths). */
export function installTauriApiShim(): void {
  if (import.meta.env.DEV) return;

  const base = API_BASE;
  const origFetch = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    if (typeof input === "string" && input.startsWith("/")) {
      return origFetch(base + input, init);
    }
    return origFetch(input, init);
  };

  const OrigES = window.EventSource;
  window.EventSource = class PatchedEventSource extends OrigES {
    constructor(url: string | URL, config?: EventSourceInit) {
      const resolved =
        typeof url === "string" && url.startsWith("/") ? base + url : url;
      super(resolved, config);
    }
  } as typeof EventSource;
}
