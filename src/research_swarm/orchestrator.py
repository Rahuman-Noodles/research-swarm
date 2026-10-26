"""Orchestrator: plan angles, fan out researchers in parallel, synthesize."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable

from .agents import AgentReport, ResearcherAgent, critique, synthesize
from .config import SwarmConfig
from .providers import get_provider


@dataclass
class SwarmResult:
    query: str
    reports: list[AgentReport]
    final_markdown: str
    critique_text: str = ""
    elapsed_s: float = 0.0
    provider: str = ""
    total_tool_calls: int = 0


async def run_swarm(config: SwarmConfig,
                    progress: Callable[[str], None] | None = None) -> SwarmResult:
    t0 = time.time()
    provider = get_provider(config.provider, config.model)
    specs = config.angle_specs()
    rounds = config.depth_cfg["rounds"]

    sem = asyncio.Semaphore(max(1, config.max_parallel))

    async def _one(spec: dict, idx: int) -> AgentReport:
        async with sem:
            agent = ResearcherAgent(
                angle=spec["name"], lens=spec["lens"],
                provider=provider, offline=config.offline, max_rounds=rounds,
            )
            rep = await agent.research(config.query)
            if progress:
                progress(f"[{idx + 1}/{len(specs)}] {spec['name']} done "
                         f"({rep.tool_calls} tools, {len(rep.citations)} cites)")
            return rep

    reports = await asyncio.gather(*(_one(s, i) for i, s in enumerate(specs)))
    reports = list(reports)

    final = await synthesize(provider=provider, question=config.query, reports=reports)
    crit = ""
    if config.depth_cfg["synth_passes"] >= 2:
        crit = await critique(provider=provider, draft=final)
        final = f"{final.rstrip()}\n\n---\n\n## Critic pass\n\n{crit}\n"

    return SwarmResult(
        query=config.query,
        reports=reports,
        final_markdown=final,
        critique_text=crit,
        elapsed_s=time.time() - t0,
        provider=provider.name,
        total_tool_calls=sum(r.tool_calls for r in reports),
    )
