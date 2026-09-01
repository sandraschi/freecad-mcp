import { useEffect, useRef } from "react";

export interface DemoParams {
	wingAngleDeg: number;
	riverSpeed: number;
	pyroIntensity: number;
	poolDropPending: boolean;
	onPoolDropHandled: () => void;
}

function clamp(v: number, lo: number, hi: number): number {
	return Math.max(lo, Math.min(hi, v));
}

function lerp(a: number, b: number, t: number): number {
	return a + (b - a) * t;
}

function hsl(h: number, s: number, l: number): string {
	return `hsl(${h} ${s}% ${l}%)`;
}

function drawPool(
	ctx: CanvasRenderingContext2D,
	w: number,
	h: number,
	t: number,
	params: DemoParams,
	state: { height: Float32Array; vx: Float32Array; vy: Float32Array; drop: boolean },
) {
	const cols = 96;
	const rows = 64;
	const cellW = w / cols;
	const cellH = h / rows;

	if (state.drop || params.poolDropPending) {
		const cx = cols * 0.5;
		const cy = rows * 0.42;
		for (let y = 0; y < rows; y += 1) {
			for (let x = 0; x < cols; x += 1) {
				const d = Math.hypot(x - cx, y - cy);
				if (d < 8) {
					const idx = y * cols + x;
					state.height[idx] += 0.35 * (1 - d / 8);
				}
			}
		}
		params.onPoolDropHandled();
		state.drop = false;
	}

	const damp = 0.992;
	const spread = 0.18;
	for (let y = 1; y < rows - 1; y += 1) {
		for (let x = 1; x < cols - 1; x += 1) {
			const idx = y * cols + x;
			const avg =
				(state.height[idx - 1] + state.height[idx + 1] + state.height[idx - cols] + state.height[idx + cols]) / 4;
			state.vx[idx] += (avg - state.height[idx]) * spread;
			state.vy[idx] += (avg - state.height[idx]) * spread;
		}
	}

	for (let y = 1; y < rows - 1; y += 1) {
		for (let x = 1; x < cols - 1; x += 1) {
			const idx = y * cols + x;
			state.height[idx] += state.vx[idx];
			state.vx[idx] *= damp;
			state.vy[idx] *= damp;
			if (x <= 1 || x >= cols - 2 || y <= 1 || y >= rows - 2) {
				state.height[idx] *= 0.65;
			}
		}
	}

	ctx.fillStyle = "#0c1929";
	ctx.fillRect(0, 0, w, h);

	for (let y = 0; y < rows; y += 1) {
		for (let x = 0; x < cols; x += 1) {
			const idx = y * cols + x;
			const wave = state.height[idx];
			const hue = lerp(195, 210, clamp(wave * 2.5 + 0.5, 0, 1));
			const light = lerp(28, 62, clamp(wave * 3 + 0.45, 0, 1));
			ctx.fillStyle = hsl(hue, 85, light);
			ctx.fillRect(x * cellW, y * cellH, cellW + 1, cellH + 1);
		}
	}

	const ballX = w * 0.5;
	const ballY = h * 0.38 + Math.sin(t * 0.004) * 3;
	const grad = ctx.createRadialGradient(ballX, ballY, 2, ballX, ballY, 18);
	grad.addColorStop(0, "#fef08a");
	grad.addColorStop(1, "#f97316");
	ctx.fillStyle = grad;
	ctx.beginPath();
	ctx.arc(ballX, ballY, 14, 0, Math.PI * 2);
	ctx.fill();
}

function drawWing(ctx: CanvasRenderingContext2D, w: number, h: number, t: number, params: DemoParams) {
	const angle = (params.wingAngleDeg * Math.PI) / 180;
	ctx.fillStyle = "#0b1020";
	ctx.fillRect(0, 0, w, h);

	const cx = w * 0.38;
	const cy = h * 0.55;
	const chord = w * 0.22;

	ctx.save();
	ctx.translate(cx, cy);
	ctx.rotate(angle);

	ctx.fillStyle = "#334155";
	ctx.beginPath();
	ctx.moveTo(-chord * 0.5, 0);
	ctx.quadraticCurveTo(0, -chord * 0.18, chord * 0.5, 0);
	ctx.quadraticCurveTo(0, chord * 0.08, -chord * 0.5, 0);
	ctx.fill();
	ctx.restore();

	const cols = 72;
	const rows = 40;
	for (let j = 0; j < rows; j += 1) {
		for (let i = 0; i < cols; i += 1) {
			const x = (i / cols) * w;
			const y = (j / rows) * h;
			const dx = x - cx;
			const dy = y - cy;
			const rotX = dx * Math.cos(-angle) - dy * Math.sin(-angle);
			const rotY = dx * Math.sin(-angle) + dy * Math.cos(-angle);
			const inside = rotX > -chord * 0.45 && rotX < chord * 0.45 && rotY > -chord * 0.12 && rotY < chord * 0.06;
			if (inside) continue;

			const speed = clamp(0.35 + 0.65 * Math.exp(-Math.abs(rotY) / (chord * 0.25)), 0.2, 1);
			const stall = params.wingAngleDeg > 14 ? (params.wingAngleDeg - 14) / 10 : 0;
			const vort = stall * Math.sin(t * 0.01 + rotX * 0.02) * 0.4;
			const hue = lerp(220, 320, speed + vort);
			ctx.fillStyle = hsl(hue, 90, lerp(35, 65, speed));
			ctx.fillRect(x, y, w / cols + 1, h / rows + 1);
		}
	}

	for (let s = 0; s < 14; s += 1) {
		ctx.strokeStyle = hsl(180 + s * 8, 95, 70);
		ctx.lineWidth = 1.2;
		ctx.beginPath();
		let px = 20;
		let py = h * (0.15 + s * 0.05);
		ctx.moveTo(px, py);
		for (let step = 0; step < 80; step += 1) {
			const dx = px - cx;
			const dy = py - cy;
			const rotX = dx * Math.cos(-angle) - dy * Math.sin(-angle);
			const rotY = dx * Math.sin(-angle) + dy * Math.cos(-angle);
			const dist = Math.hypot(rotX, rotY * 2.2);
			const deflect = (chord * 0.35) / (dist + 40);
			px += 4 + deflect;
			py += Math.sin(step * 0.15 + t * 0.002) * 0.4;
			ctx.lineTo(px, py);
			if (px > w - 10) break;
		}
		ctx.stroke();
	}
}

function drawRiver(ctx: CanvasRenderingContext2D, w: number, h: number, t: number, params: DemoParams) {
	ctx.fillStyle = "#071612";
	ctx.fillRect(0, 0, w, h);

	const cols = 100;
	const rows = 56;
	const islands = [
		{ x: 0.42, y: 0.45, r: 0.07 },
		{ x: 0.62, y: 0.58, r: 0.09 },
		{ x: 0.78, y: 0.4, r: 0.06 },
	];

	for (let j = 0; j < rows; j += 1) {
		for (let i = 0; i < cols; i += 1) {
			const nx = i / cols;
			const ny = j / rows;
			const bend = Math.sin(ny * Math.PI * 1.6) * 0.18;
			const cx = nx - bend;
			let blocked = false;
			for (const isl of islands) {
				if (Math.hypot(cx - isl.x, ny - isl.y) < isl.r) {
					blocked = true;
					break;
				}
			}
			if (blocked) {
				ctx.fillStyle = "#14532d";
			} else {
				const speed =
					params.riverSpeed *
					(1.2 + 0.8 * Math.abs(Math.sin(ny * Math.PI * 1.6))) *
					(0.85 + 0.15 * Math.sin(t * 0.003 + nx * 8));
				const hue = lerp(150, 195, clamp(speed, 0, 1));
				ctx.fillStyle = hsl(hue, 80, lerp(30, 58, clamp(speed, 0, 1)));
			}
			ctx.fillRect((i * w) / cols, (j * h) / rows, w / cols + 1, h / rows + 1);
		}
	}

	for (const isl of islands) {
		ctx.fillStyle = "#166534";
		ctx.beginPath();
		ctx.ellipse(isl.x * w, isl.y * h, isl.r * w, isl.r * h * 0.75, 0, 0, Math.PI * 2);
		ctx.fill();
	}
}

function drawPyroclastic(ctx: CanvasRenderingContext2D, w: number, h: number, t: number, params: DemoParams) {
	ctx.fillStyle = "#120806";
	ctx.fillRect(0, 0, w, h);

	const slopeGrad = ctx.createLinearGradient(0, 0, w, h);
	slopeGrad.addColorStop(0, "#292524");
	slopeGrad.addColorStop(0.45, "#44403c");
	slopeGrad.addColorStop(1, "#1c1917");
	ctx.fillStyle = slopeGrad;
	ctx.beginPath();
	ctx.moveTo(0, h * 0.35);
	ctx.lineTo(w, h * 0.55);
	ctx.lineTo(w, h);
	ctx.lineTo(0, h);
	ctx.closePath();
	ctx.fill();

	const particles = 900;
	for (let p = 0; p < particles; p += 1) {
		const seed = p * 17.17;
		const life = (t * 0.002 * params.pyroIntensity + seed) % 1;
		const x = ((seed * 13) % 1) * w * 0.25 + life * w * 0.75;
		const y = h * 0.32 + life * life * h * 0.55 + Math.sin(seed + t * 0.004) * 18;
		const heat = clamp(1 - life * 1.1, 0, 1);
		const hue = lerp(15, 55, heat);
		const size = lerp(6, 1.5, life) * params.pyroIntensity;
		ctx.fillStyle = hsl(hue, 95, lerp(40, 68, heat));
		ctx.globalAlpha = 0.35 + heat * 0.45;
		ctx.beginPath();
		ctx.arc(x, y, size, 0, Math.PI * 2);
		ctx.fill();
	}
	ctx.globalAlpha = 1;
}

export function useCfdDemoAnimation(
	canvasRef: React.RefObject<HTMLCanvasElement | null>,
	demoId: string,
	params: DemoParams,
) {
	const poolState = useRef({
		height: new Float32Array(96 * 64),
		vx: new Float32Array(96 * 64),
		vy: new Float32Array(96 * 64),
		drop: false,
	});

	useEffect(() => {
		const canvas = canvasRef.current;
		if (!canvas) return undefined;
		const ctx = canvas.getContext("2d");
		if (!ctx) return undefined;

		let frame = 0;
		let raf = 0;

		const resize = () => {
			const parent = canvas.parentElement;
			if (!parent) return;
			const dpr = window.devicePixelRatio || 1;
			const width = parent.clientWidth;
			const height = Math.max(280, Math.min(420, width * 0.55));
			canvas.width = Math.floor(width * dpr);
			canvas.height = Math.floor(height * dpr);
			canvas.style.width = `${width}px`;
			canvas.style.height = `${height}px`;
			ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		};

		resize();
		window.addEventListener("resize", resize);

		const loop = () => {
			frame += 1;
			const w = canvas.clientWidth;
			const h = canvas.clientHeight;
			if (demoId === "pool-splash") {
				drawPool(ctx, w, h, frame, params, poolState.current);
			} else if (demoId === "wing-flow") {
				drawWing(ctx, w, h, frame, params);
			} else if (demoId === "river-bends") {
				drawRiver(ctx, w, h, frame, params);
			} else if (demoId === "pyroclastic") {
				drawPyroclastic(ctx, w, h, frame, params);
			}
			raf = window.requestAnimationFrame(loop);
		};

		raf = window.requestAnimationFrame(loop);
		return () => {
			window.cancelAnimationFrame(raf);
			window.removeEventListener("resize", resize);
		};
	}, [canvasRef, demoId, params.wingAngleDeg, params.riverSpeed, params.pyroIntensity, params.poolDropPending]);
}
