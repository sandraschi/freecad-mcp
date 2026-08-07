import { Route, Routes, Navigate } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import Dashboard from "./pages/Dashboard";
import DepotPage from "./pages/DepotPage";
import ConvertPage from "./pages/ConvertPage";
import ModelsPage from "./pages/ModelsPage";
import ChatPage from "./pages/ChatPage";
import LogsPage from "./pages/LogsPage";
import SettingsPage from "./pages/SettingsPage";
import HelpPage from "./pages/HelpPage";
import AppsPage from "./pages/AppsPage";
import MarketplacePage from "./pages/MarketplacePage";
import BimDemoPage from "./pages/BimDemoPage";
import CfdDemosPage from "./pages/CfdDemosPage";
import ToyCarDemoPage from "./pages/ToyCarDemoPage";
import CfdPage from "./pages/CfdPage";
import Fluidx3dPage from "./pages/Fluidx3dPage";
import PipelinePage from "./pages/PipelinePage";

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/depot" element={<DepotPage />} />
        <Route path="/convert" element={<ConvertPage />} />
        <Route path="/models" element={<ModelsPage />} />
        <Route path="/marketplace" element={<MarketplacePage />} />
        <Route path="/bim-demo" element={<BimDemoPage />} />
        <Route path="/cfd-demos" element={<CfdDemosPage />} />
        <Route path="/toy-car" element={<ToyCarDemoPage />} />
        <Route path="/cfd" element={<CfdPage />} />
        <Route path="/fluidx3d" element={<Fluidx3dPage />} />
        <Route path="/pipeline" element={<PipelinePage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/logs" element={<LogsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/help" element={<HelpPage />} />
        <Route path="/apps" element={<AppsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  );
}
