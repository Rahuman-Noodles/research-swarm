"""Config: angles, depths, and run settings (stdlib only)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


ANGLE_PRESETS: list[dict] = [
    {
        "name": "academic",
        "lens": "You are an academic researcher. Favor peer-reviewed framing, "
        "definitions, and key papers. Cite sources for every claim.",
    },
    {
        "name": "skeptic",
        "lens": "You are a skeptical fact-checker. Hunt for hype, weak evidence, "
        "conflicts of interest, and counter-examples. Steelman the other side first.",
    },
    {
        "name": "practitioner",
        "lens": "You are a hands-on practitioner. Favor tutorials, costs, pitfalls, "
        "benchmarks, and what actually works in production.",
    },
    {
        "name": "futurist",
        "lens": "You are a technology forecaster. Focus on trajectory, 2-5 year outlook, "
        "second-order effects, and what would change your mind.",
    },
    {
        "name": "historian",
        "lens": "You are a tech historian. Trace origins, prior art, failed attempts, "
        "and why timing matters now.",
    },
    {
        "name": "operator",
        "lens": "You are an operator / cost analyst. Focus on pricing, vendors, "
        "trade-offs, and build-vs-buy math.",
    },
]

DEPTH_PRESETS: dict = {
    "quick": {"rounds": 1, "synth_passes": 1, "search_k": 4},
    "standard": {"rounds": 2, "synth_passes": 2, "search_k": 5},
    "deep": {"rounds": 3, "synth_passes": 3, "search_k": 6},
}


@dataclass
class SwarmConfig:
    query: str
    angles: int = 4
    depth: str = "standard"
    provider: str = "auto"  # auto | mock | openai | ollama
    model: str = ""
    out_dir: str = "reports"
    offline: bool = False
    verbose: bool = False
    max_parallel: int = 4

    def __post_init__(self) -> None:
        if self.depth not in DEPTH_PRESETS:
            raise ValueError(f"unknown depth {self.depth!r}, pick one of {sorted(DEPTH_PRESETS)}")
        if self.angles < 1 or self.angles > 8:
            raise ValueError("angles must be between 1 and 8")
        if self.provider not in ("auto", "mock", "openai", "ollama"):
            raise ValueError(f"unknown provider {self.provider!r}")
        if os.environ.get("RESEARCH_OFFLINE") == "1":
            self.offline = True
        elif os.environ.get("RESEARCH_OFFLINE") == "0":
            self.offline = False
        elif self.provider == "mock":
            self.offline = True  # mock demos stay fast/offline unless forced live

    @property
    def depth_cfg(self) -> dict:
        return DEPTH_PRESETS[self.depth]

    def angle_specs(self) -> list[dict]:
        """Cycle presets so any angle count 1-8 gets named lenses."""
        specs: list[dict] = []
        for i in range(self.angles):
            base = ANGLE_PRESETS[i % len(ANGLE_PRESETS)]
            if i < len(ANGLE_PRESETS):
                specs.append(dict(base))
            else:
                specs.append({
                    "name": f"{base['name']}-{i // len(ANGLE_PRESETS) + 1}",
                    "lens": base["lens"],
                })
        return specs
