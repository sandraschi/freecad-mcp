# Agentic CFD Pipeline — Implementation Spec

Four features that turn freecad-mcp from a tool collection into an autonomous engineering agent.

## 1. Agentic Design Loop

**Tool**: `freecad_design_loop(goal: str, ctx: Context)`

Uses `ctx.sample()` to plan and execute an autonomous CAD→simulate→analyze→refine loop.

Flow:
1. LLM parses goal (e.g. "design a lightweight bracket for 500N")
2. LLM decides which tools to call and in what order
3. Server executes each call, feeds results back to LLM
4. Loop terminates when goal is met or max iterations reached

No new infrastructure — pure orchestration of existing 50+ tools.

## 2. FluidX3D Parametric Sweeps

**Tool**: `cfd_fluidx3d_sweep(base_case, parameter, values, run)`

Mirrors `cfd_parametric_study` for the GPU path. Copies the base case's `.f3d_config.json`, modifies one parameter across N values, runs each.

No new compilation — uses the pre-built runner path (config.json changes only). Each case runs sequentially on the same GPU.

## 3. Real-time WebSocket Dashboard

**Endpoint**: `WS /api/v1/fluidx3d/ws/{case_name}`

Streams `run.log` lines as they're written. Webapp subscribes and renders:
- Live force history chart (STEP vs Fx/Fy/Fz) using Recharts
- MLUPS gauge
- Time step counter
- Completion badge

Backend change: `cfd_fluidx3d_run` writes to a log file that a background asyncio task tails via `inotify`/polling → WebSocket.

## 4. Neural Surrogate Training

**Tools**: `cfd_fluidx3d_train_surrogate(case_name, hidden_layers, epochs)` + `cfd_surrogate_predict(params)`

Trains a small MLP (PyTorch) on sweep data to predict forces from input parameters.
- `train`: reads sweep results, trains `params → forces` MLP, saves to disk
- `predict`: loads saved model, returns predicted forces for new params

Requires PyTorch (optional — tools return clear error if missing). Model is a simple 3-layer MLP ~50KB.
