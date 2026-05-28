export interface CfdDemoGpuPreset {
  case_name: string;
  domain_type: string;
  resolution_x: number;
  resolution_y: number;
  resolution_z: number;
  length_m: number;
  velocity_ms: number;
  time_steps: number;
  write_interval: number;
  free_surface?: boolean;
  fill_fraction?: number;
  thermal?: boolean;
  beta?: number;
  profile_shape?: string;
}

export interface CfdDemoDefinition {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  gradient: string;
  accent: string;
  gpuPreset: CfdDemoGpuPreset;
}

export const CFD_DEMOS: CfdDemoDefinition[] = [
  {
    id: "pool-splash",
    title: "Pool Splash",
    subtitle: "Free-surface waves",
    description:
      "Drop a ball into a rectangular pool and watch circular waves reflect off tiled walls.",
    gradient: "from-cyan-400 via-sky-500 to-blue-700",
    accent: "text-cyan-300",
    gpuPreset: {
      case_name: "demo_pool_splash",
      domain_type: "box",
      resolution_x: 128,
      resolution_y: 128,
      resolution_z: 64,
      length_m: 4.0,
      velocity_ms: 0.0,
      time_steps: 8000,
      write_interval: 400,
      free_surface: true,
      fill_fraction: 0.62,
    },
  },
  {
    id: "wing-flow",
    title: "Wing Flow",
    subtitle: "Angle of attack",
    description:
      "Airflow over a cambered airfoil. Drag the angle slider to see stall, separation, and vortex shedding.",
    gradient: "from-indigo-400 via-violet-500 to-fuchsia-700",
    accent: "text-violet-300",
    gpuPreset: {
      case_name: "demo_wing_flow",
      domain_type: "channel",
      resolution_x: 384,
      resolution_y: 128,
      resolution_z: 64,
      length_m: 2.0,
      velocity_ms: 0.08,
      time_steps: 12000,
      write_interval: 600,
      profile_shape: "uniform",
    },
  },
  {
    id: "river-bends",
    title: "River Bends",
    subtitle: "Islands and meanders",
    description:
      "Meandering channel with mid-stream islands. Faster water hugs the outer bank; eddies form in lee zones.",
    gradient: "from-emerald-400 via-teal-500 to-green-800",
    accent: "text-emerald-300",
    gpuPreset: {
      case_name: "demo_river_bends",
      domain_type: "channel",
      resolution_x: 512,
      resolution_y: 192,
      resolution_z: 32,
      length_m: 6.0,
      velocity_ms: 0.05,
      time_steps: 10000,
      write_interval: 500,
      profile_shape: "parabolic",
    },
  },
  {
    id: "pyroclastic",
    title: "Pyroclastic Flow",
    subtitle: "Gravity-driven surge",
    description:
      "Hot ash-laden current racing down a volcanic slope, expanding and slowing as it spreads across the plain.",
    gradient: "from-amber-400 via-orange-500 to-red-800",
    accent: "text-orange-300",
    gpuPreset: {
      case_name: "demo_pyroclastic",
      domain_type: "box",
      resolution_x: 256,
      resolution_y: 128,
      resolution_z: 96,
      length_m: 3.0,
      velocity_ms: 0.12,
      time_steps: 15000,
      write_interval: 750,
      thermal: true,
      beta: 0.003,
    },
  },
];
