from __future__ import annotations

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "Crowd Flow Optimiser"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    # ── AI provider ──────────────────────────────────────────────────────────
    hf_token: str = ""
    hf_model: str = "Qwen/Qwen2.5-7B-Instruct"
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    ai_provider_mode: Literal["auto", "ollama", "huggingface", "openrouter", "mock"] = "auto"
    ai_timeout: float = 30.0        # seconds
    ai_cooldown_sim_minutes: float = 5.0   # min sim-minutes between AI calls

    # ── TinyFish live web intelligence ─────────────────────────────────────
    # Keep this backend-only. VITE_* variables are intentionally not used for
    # this credential because Vite exposes them to every browser user.
    tinyfish_api_key: str = ""
    tinyfish_timeout: float = 20.0
    tinyfish_max_results: int = 5

    # ── Simulation ────────────────────────────────────────────────────────────
    simulation_timestep: float = 1.0       # real seconds per tick
    max_simulation_duration: float = 300.0 # sim-minutes
    realtime_update_hz: float = 2.0        # broadcasts per second
    max_agents_rendered: int = 1400        # visual cap matches frontend

    # ── Risk thresholds ───────────────────────────────────────────────────────
    risk_density_moderate: float = 0.35
    risk_density_high: float = 0.60
    risk_density_critical: float = 0.80
    risk_density_emergency: float = 0.90

    risk_utilization_moderate: float = 0.50
    risk_utilization_high: float = 0.70
    risk_utilization_critical: float = 0.85

    # ── Bottleneck thresholds ─────────────────────────────────────────────────
    bottleneck_density_threshold: float = 0.70
    bottleneck_utilization_threshold: float = 0.70
    bottleneck_queue_growth_threshold: float = 5.0   # people/min
    bottleneck_persistence_ticks: int = 2            # ticks before confirmed

    # ── Routing weights ───────────────────────────────────────────────────────
    routing_base_weight: float = 1.0
    routing_congestion_weight: float = 2.0
    routing_risk_weight: float = 1.5
    routing_capacity_weight: float = 1.0

    # ── Route stability ───────────────────────────────────────────────────────
    route_change_cooldown_sim_minutes: float = 3.0
    route_change_threshold: float = 0.15  # min improvement before switching

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./crowd_sim.db"
    persistence_frequency: int = 10   # every N ticks persist summary

    @property
    def effective_ai_mode(self) -> Literal["ollama", "huggingface", "openrouter", "mock"]:
        if self.ai_provider_mode in ("ollama", "mock", "openrouter", "huggingface"):
            return self.ai_provider_mode
        # auto mode: prioritize local GPU Ollama if running
        try:
            import httpx
            with httpx.Client(timeout=0.8) as client:
                r = client.get(f"{self.ollama_base_url}/api/tags")
                if r.status_code == 200:
                    return "ollama"
        except Exception:
            pass
        if self.openrouter_api_key:
            return "openrouter"
        return "huggingface" if self.hf_token else "mock"


# Singleton
settings = Settings()
