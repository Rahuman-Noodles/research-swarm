"""Researcher / critic / synthesizer agents over a ReAct tool loop."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .providers import LLMProvider
from .tools import TOOL_HELP, ToolRunner

_TOOL_RE = re.compile(r"```tool\s*(\{.*?\})\s*```", re.S)
_URL_RE = re.compile(r"https?://[^\s\)\]]+")


@dataclass
class AgentReport:
    angle: str
    findings: str
    citations: list[str] = field(default_factory=list)
    tool_calls: int = 0
    trace: list[str] = field(default_factory=list)


def parse_tool_call(text: str) -> tuple[str, dict] | None:
    m = _TOOL_RE.search(text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(1))
        return str(obj.get("name", "")), dict(obj.get("args", {}))
    except Exception:
        return None


def extract_citations(text: str) -> list[str]:
    seen, out = set(), []
    for u in _URL_RE.findall(text):
        u = u.rstrip(".,;")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


class ResearcherAgent:
    def __init__(self, *, angle: str, lens: str, provider: LLMProvider,
                 offline: bool = False, max_rounds: int = 2):
        self.angle = angle
        self.lens = lens
        self.provider = provider
        self.offline = offline
        self.max_rounds = max_rounds

    async def research(self, question: str) -> AgentReport:
        tools = ToolRunner(offline=self.offline)
        system = f"{self.lens}\n\n{TOOL_HELP}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Research from the {self.angle} angle: {question}"},
        ]
        trace: list[str] = []
        final = ""
        for _ in range(self.max_rounds + 1):
            resp = await self.provider.chat(messages)
            trace.append(resp[:400])
            call = parse_tool_call(resp)
            messages.append({"role": "assistant", "content": resp})
            if not call:
                final = resp
                break
            name, args = call
            try:
                result = await tools.run(name, args)
            except Exception as e:
                result = f"tool error: {e}"
            trace.append(f"$ {name} {args} -> {result[:200]}")
            messages.append({"role": "user", "content": f"Tool {name} returned:\n{result}\n\nNow write findings."})
            final = result
        else:
            final = messages[-1]["content"] if messages else ""
        if final.startswith("Results for") or final.startswith("[offline"):
            # Tool-only final (shouldn't happen with mock); wrap it.
            final = f"## {self.angle.title()} findings\n\n{final}\n"
        return AgentReport(
            angle=self.angle,
            findings=final,
            citations=extract_citations(final),
            tool_calls=tools.calls,
            trace=trace,
        )


async def synthesize(*, provider: LLMProvider, question: str,
                     reports: list[AgentReport]) -> str:
    if provider.name == "mock":
        parts = [f"# {question}\n"]
        for r in reports:
            parts.append(f"\n{r.findings}\n")
        parts.append("\n## Verdict\n\nMock synthesis: merge above; every claim has a citation.\n")
        return "\n".join(parts).strip() + "\n"
    joined = "\n\n---\n\n".join(f"[{r.angle}] {r.findings}" for r in reports)
    messages = [
        {"role": "system", "content": "You synthesize multi-angle research into one cited markdown report. Keep every citation URL."},
        {"role": "user", "content": f"Synthesize these {len(reports)} angle reports on '{question}':\n\n{joined}"},
    ]
    return await provider.chat(messages)


async def critique(*, provider: LLMProvider, draft: str) -> str:
    messages = [
        {"role": "system", "content": "You are a critic. List the 3 strongest objections, then a publish/hold verdict."},
        {"role": "user", "content": f"Critique this draft:\n\n{draft[:6000]}"},
    ]
    return await provider.chat(messages)
