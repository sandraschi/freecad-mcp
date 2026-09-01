import { create } from "zustand";

type Provider = "ollama" | "lm_studio" | "vllm" | "";

type LlmState = {
  provider: Provider;
  model: string;
  ollamaUrl: string;
  providers: { name: Provider; base: string; models: string[]; status: string }[];
  gpuDetected: boolean;
  setProvider: (p: Provider) => void;
  setModel: (m: string) => void;
  setProviders: (providers: LlmState["providers"]) => void;
  setGpuDetected: (v: boolean) => void;
};

export const useLlmStore = create<LlmState>((set) => ({
  provider: (localStorage.getItem("llm_provider") as Provider) || "ollama",
  model: localStorage.getItem("llm_model") || "gemma3:1b",
  ollamaUrl: localStorage.getItem("ollama_url") || "http://127.0.0.1:11434",
  providers: [],
  gpuDetected: false,
  setProvider: (provider) => {
    localStorage.setItem("llm_provider", provider);
    set({ provider });
  },
  setModel: (model) => {
    localStorage.setItem("llm_model", model);
    set({ model });
  },
  setProviders: (providers) => set({ providers }),
  setGpuDetected: (gpuDetected) => set({ gpuDetected }),
}));
