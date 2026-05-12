# freecad-mcp Webapp

Vite + React 19 dashboard for FreeCAD MCP. Fleet ports **10945** (frontend) proxying to **10944** (backend).

`start.ps1` kills zombies on both ports, starts the Python backend in dual mode, starts `npm run dev`, waits until the frontend is reachable, then opens the default browser.

## Pages

| Route | Page | Description |
|:---|:---|:---|
| `/` | Dashboard | FreeCAD status, file counts, quick action cards |
| `/convert` | Convert | Upload STEP/STP → download STL |
| `/models` | Models | File browser with embedded Three.js STL viewer, G-code column |
| `/marketplace` | Marketplace | Search Printables, Thingiverse, GrabCAD → import to uploads |
| `/chat` | CAD Expert | AI chat via Ollama (gemma3:1b) |
| `/apps` | Apps | Tool launcher cards (step_to_stl, slice_stl, freecad_gui, etc.) |
| `/logs` | Logs | Live SSE log stream with filter and export |
| `/settings` | Settings | Ollama URL + model configuration |
| `/help` | Help | FreeCAD reference: intro, workbenches, scripting, marketplace guide |

## Stack

| Layer | Tech |
|:---|:---|
| **Framework** | React 19, React Router 7 |
| **Build** | Vite 5 |
| **Styling** | Tailwind CSS 3.4 |
| **Animation** | Framer Motion 11 |
| **3D Viewer** | Three.js + STLLoader + OrbitControls |
| **Icons** | Lucide React 0.400 |
| **Linting** | Biome |
| **TypeScript** | 5.6 |

## Development

```powershell
cd webapp
npm install
npm run dev          # :10945, proxies /api → :10944
```

The Vite proxy in `vite.config.ts` forwards `/api/*` to `http://127.0.0.1:10944`.

## Production Build

```powershell
npm run build        # outputs to dist/
npm run preview      # serve dist/ locally
```
