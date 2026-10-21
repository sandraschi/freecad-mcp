/** API base URL — configurable via VITE_API_BASE env var.
 *
 * Same-origin by default so LAN / Tailscale hostnames work: the Vite dev proxy
 * forwards /api to the backend, and a served build talks to whatever host it was
 * loaded from. Only the Tauri WebView needs an absolute loopback URL, because
 * there is no HTTP origin serving the SPA.
 */
function isTauri(): boolean {
	if (typeof window === "undefined") return false;
	return (
		"__TAURI_INTERNALS__" in window ||
		"__TAURI__" in window ||
		window.location.hostname === "tauri.localhost" ||
		window.location.protocol === "tauri:"
	);
}

export const API_BASE = import.meta.env.VITE_API_BASE || (isTauri() ? "http://127.0.0.1:10944" : "");
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
			const resolved = typeof url === "string" && url.startsWith("/") ? base + url : url;
			super(resolved, config);
		}
	} as typeof EventSource;
}
