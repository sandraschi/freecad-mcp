"""
Lightweight neural surrogate for FluidX3D force prediction.

Trains a small MLP on parametric sweep results to predict forces
from input parameters. Optional - requires PyTorch.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("freecad-mcp.nn_surrogate")

try:
    import numpy as np  # noqa: F401

    HAS_NP = True
except ImportError:
    HAS_NP = False

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


MODEL_DIR = Path.home() / ".cache" / "freecad-mcp" / "surrogates"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


class ForceMLP(nn.Module):
    """Simple 3-layer MLP for params → forces prediction."""

    def __init__(self, input_dim: int = 4, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden // 2),
            nn.ReLU(),
            nn.Linear(hidden // 2, 3),  # Fx, Fy, Fz
        )

    def forward(self, x):
        return self.net(x)


def _parse_sweep_results(sweep_dir: str, param_key: str) -> list[dict]:
    """Parse sweep variant results into training data."""
    samples = []
    for entry in sorted(os.listdir(sweep_dir)):
        variant_dir = os.path.join(sweep_dir, entry)
        if not os.path.isdir(variant_dir):
            continue
        # Read config
        cfg_path = os.path.join(variant_dir, ".f3d_config.json")
        log_path = os.path.join(variant_dir, "run.log")
        if not os.path.isfile(cfg_path) or not os.path.isfile(log_path):
            continue
        with open(cfg_path) as f:
            cfg = json.load(f)
        with open(log_path) as f:
            log = f.read()
        # Parse result
        forces = {"Fx": 0.0, "Fy": 0.0, "Fz": 0.0}
        for line in log.split("\n"):
            m = __import__("re").search(r"FORCES ([\d.e+\-]+) ([\d.e+\-]+) ([\d.e+\-]+)", line)
            if m:
                forces = {"Fx": float(m.group(1)), "Fy": float(m.group(2)), "Fz": float(m.group(3))}
                break
        # Extract param value
        param_val = cfg.get(
            {
                "velocity_ms": "si_velocity",
                "viscosity_m2s": "si_viscosity",
                "density_kgm3": "si_density",
                "time_steps": "time_steps",
            }.get(param_key, param_key),
            0.0,
        )
        if isinstance(param_val, (int, float)):
            samples.append(
                {
                    "param": float(param_val),
                    "Fx": forces["Fx"],
                    "Fy": forces["Fy"],
                    "Fz": forces["Fz"],
                    "source": entry,
                }
            )
    return samples


def train_surrogate(
    sweep_cases: list[dict],
    model_name: str = "default",
    hidden_dim: int = 64,
    epochs: int = 200,
    lr: float = 0.01,
) -> dict:
    """Train an MLP surrogate on sweep data.

    Args:
        sweep_cases: List of dicts with 'param', 'Fx', 'Fy', 'Fz' keys
        model_name: Name to save/load the model
        hidden_dim: Hidden layer size
        epochs: Training epochs
        lr: Learning rate

    Returns: dict with success, loss_history, model_path
    """
    if not HAS_TORCH:
        return {"success": False, "error": "PyTorch not installed. Run: uv pip install torch"}
    if not HAS_NP:
        return {"success": False, "error": "NumPy not installed. Run: uv pip install numpy"}
    if len(sweep_cases) < 3:
        return {"success": False, "error": f"Need at least 3 samples, got {len(sweep_cases)}"}

    # Build dataset
    xs = torch.tensor([[s["param"]] for s in sweep_cases], dtype=torch.float32)
    ys = torch.tensor([[s["Fx"], s["Fy"], s["Fz"]] for s in sweep_cases], dtype=torch.float32)

    # Normalize
    x_mean, x_std = xs.mean(), xs.std().clamp(min=1e-8)
    y_mean, y_std = ys.mean(0), ys.std(0).clamp(min=1e-8)
    xs_norm = (xs - x_mean) / x_std
    ys_norm = (ys - y_mean) / y_std

    model = ForceMLP(input_dim=1, hidden=hidden_dim)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    losses = []
    for epoch in range(epochs):
        optimizer.zero_grad()
        pred = model(xs_norm)
        loss = criterion(pred, ys_norm)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.item()))

    # Save
    model_path = MODEL_DIR / f"{model_name}.pt"
    torch.save(
        {
            "model_state": model.state_dict(),
            "x_mean": x_mean,
            "x_std": x_std,
            "y_mean": y_mean,
            "y_std": y_std,
            "hidden_dim": hidden_dim,
            "samples": len(sweep_cases),
            "param_key": sweep_cases[0].get("source", "unknown"),
        },
        model_path,
    )

    return {
        "success": True,
        "loss_history": [round(loss, 6) for loss in losses],
        "final_loss": round(losses[-1], 6),
        "model_path": str(model_path),
        "samples": len(sweep_cases),
    }


def predict(model_name: str, param_value: float) -> dict:
    """Predict forces for a given parameter value.

    Args:
        model_name: Model name (without .pt)
        param_value: Parameter value to predict for

    Returns: dict with success, Fx, Fy, Fz
    """
    if not HAS_TORCH:
        return {"success": False, "error": "PyTorch not installed"}
    model_path = MODEL_DIR / f"{model_name}.pt"
    if not model_path.exists():
        return {"success": False, "error": f"Model '{model_name}' not found at {model_path}"}

    checkpoint = torch.load(model_path, map_location="cpu")
    model = ForceMLP(input_dim=1, hidden=checkpoint["hidden_dim"])
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    x = torch.tensor([[param_value]], dtype=torch.float32)
    x_norm = (x - checkpoint["x_mean"]) / checkpoint["x_std"]
    with torch.no_grad():
        y_norm = model(x_norm)
    y = y_norm * checkpoint["y_std"] + checkpoint["y_mean"]

    return {
        "success": True,
        "Fx": round(float(y[0, 0]), 6),
        "Fy": round(float(y[0, 1]), 6),
        "Fz": round(float(y[0, 2]), 6),
        "param_value": param_value,
        "model": model_name,
    }


def list_models() -> list[dict]:
    """List all trained surrogate models."""
    models = []
    for f in MODEL_DIR.glob("*.pt"):
        try:
            ckpt = torch.load(f, map_location="cpu")
            models.append(
                {
                    "name": f.stem,
                    "samples": ckpt.get("samples", 0),
                    "hidden_dim": ckpt.get("hidden_dim", 64),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                }
            )
        except Exception as e:
            logger.debug("Failed to load model %s: %s", f.name, e)
    return models
