import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import AppsPage from "./pages/AppsPage";
import BimDemoPage from "./pages/BimDemoPage";
import CfdDemosPage from "./pages/CfdDemosPage";
import CfdPage from "./pages/CfdPage";
import ChatPage from "./pages/ChatPage";
import ConvertPage from "./pages/ConvertPage";
import Dashboard from "./pages/Dashboard";
import DepotPage from "./pages/DepotPage";
import Fluidx3dPage from "./pages/Fluidx3dPage";
import HelpPage from "./pages/HelpPage";
import LogsPage from "./pages/LogsPage";
import MarketplacePage from "./pages/MarketplacePage";
import ModelsPage from "./pages/ModelsPage";
import PartsPage from "./pages/PartsPage";
import PipelinePage from "./pages/PipelinePage";
import SettingsPage from "./pages/SettingsPage";
import ToyCarDemoPage from "./pages/ToyCarDemoPage";

export default function App() {
	return (
		<AppLayout>
			<Routes>
				<Route path="/" element={<Dashboard />} />
				<Route path="/parts" element={<PartsPage />} />
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
