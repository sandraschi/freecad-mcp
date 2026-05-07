import { Route, Routes, Navigate, NavLink } from "react-router-dom";
import { Box, Info, Upload } from "lucide-react";
import ConvertPage from "./pages/ConvertPage";
import ModelsPage from "./pages/ModelsPage";
import StatusPage from "./pages/StatusPage";

export default function App() {
  return (
    <div className="flex h-full">
      <nav className="w-56 bg-[#0f0f12] border-r border-white/5 p-4 flex flex-col gap-2">
        <h1 className="text-lg font-bold text-white mb-4">FreeCAD MCP</h1>
        {[
          { path: "/convert", label: "Convert", icon: Upload },
          { path: "/models", label: "Models", icon: Box },
          { path: "/status", label: "Status", icon: Info },
        ].map(({ path, label, icon: Icon }) => (
          <NavLink key={path} to={path} className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium ${isActive ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"}`}>
            <Icon size={16} /> {label}
          </NavLink>
        ))}
      </nav>
      <main className="flex-1 p-6 overflow-y-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/convert" replace />} />
          <Route path="/convert" element={<ConvertPage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/status" element={<StatusPage />} />
        </Routes>
      </main>
    </div>
  );
}
