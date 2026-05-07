import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Wifi, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch("/api/v1/status");
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
