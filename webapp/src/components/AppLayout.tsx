import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Moon, Sun, Wifi, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import Sidebar from "./Sidebar";

// EXPERIMENTAL light mode (invert hack). Not fleet standard - see index.css.
// Toggling `.dark` off the root flips the invert filter; persisted so the
// choice survives reloads. Delete this + the CSS block to revert.
const THEME_KEY = "freecad-light-mode";

function useExperimentalTheme() {
  const [light, setLight] = useState(() => {
    try {
      return localStorage.getItem(THEME_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", !light);
    try {
      localStorage.setItem(THEME_KEY, light ? "1" : "0");
    } catch {
      // ignore storage errors
    }
  }, [light]);

  return { light, toggle: () => setLight((v) => !v) };
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [connected, setConnected] = useState<boolean | null>(null);
  const { light, toggle } = useExperimentalTheme();

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v1/status`);
        const j = await r.json();
        setConnected(j.freecad_ok === true);
      } catch { setConnected(false); }
    };
    check();
    const id = setInterval(check, 10000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex h-full">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-12 flex items-center justify-end px-6 border-b border-white/5 bg-[#0a0a0c] shrink-0">
          <button
            type="button"
            onClick={toggle}
            className="p-1.5 rounded-md text-slate-400 hover:bg-white/10 hover:text-white transition-colors mr-3"
            title={light ? "Switch to dark (experimental light mode)" : "Switch to light (experimental, ugly)"}
            aria-label="Toggle light mode (experimental)"
          >
            {light ? <Moon size={14} /> : <Sun size={14} />}
          </button>
          <div className="flex items-center gap-2 text-xs">
            {connected === null ? <Loader2 size={12} className="animate-spin text-slate-500" />
              : connected ? <Wifi size={12} className="text-emerald-400" /> : <WifiOff size={12} className="text-red-400" />}
            <span className={connected === true ? "text-emerald-400" : "text-slate-500"}>
              {connected === null ? "Connecting..." : connected ? "FreeCAD Ready" : "FreeCAD Offline"}
            </span>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
