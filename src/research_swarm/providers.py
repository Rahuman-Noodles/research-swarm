"""LLM providers. Mock works offline; OpenAI-compatible covers OpenAI + Ollama."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import urllib.request


class LLMProvider:
    name = "base"

    async def chat(self, messages: list[dict], *, system_extra: str = "") -> str:
        raise NotImplementedError


def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            text = str(m.get("content", ""))
            if not text.startswith("Tool "):
                return text
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content", ""))
    return ""


def _research_question(messages: list[dict]) -> str:
    for m in messages:
        if m.get("role") == "user":
            text = str(m.get("content", ""))
            if "Research from the" in text:
                return text.split("Research from the", 1)[1].split(":", 1)[-1].strip()
            if not text.startswith("Tool "):
                return text
    return _last_user_text(messages)


def _system_text(messages: list[dict]) -> str:
    for m in messages:
        if m.get("role") == "system":
            return str(m.get("content", ""))
    return ""


class MockProvider(LLMProvider):
    """Deterministic offline provider that demos the tool loop.

    First call per conversation emits one tool call, second call returns
    angle-flavored findings with citations. No network, no key.
    """

    name = "mock"

    async def chat(self, messages: list[dict], *, system_extra: str = "") -> str:
        await asyncio.sleep(0.05)  # feel like network
        q = _research_question(messages)
        sys = (_system_text(messages) + " " + system_extra).lower()
        turns = sum(1 for m in messages if m.get("role") == "assistant")

        angle = "generalist"
        for cand in ("academic", "skeptic", "practitioner", "futurist", "historian", "operator"):
            if cand in sys:
                angle = cand
                break

        short = (q.splitlines()[0] if q else "topic")[:90]
        seed = hashlib.md5(f"{angle}:{q}:{turns}".encode()).hexdigest()[:6]

        if turns == 0 and "synthesize" not in sys and "critic" not in sys:
            # Demonstrate exactly one tool call before answering.
            safe_q = short.replace('"', "")
            return (
                f"I'll research this from the {angle} angle.\n"
                '```tool {"name": "web_search", "args": {"query": "%s", "k": 4}}\n```' % safe_q
            )
        if "critic" in sys:
            return (
                f"Critique (seed {seed}):\n"
                f"1. Claim about '{short}' needs a second source.\n"
                "2. One citation looks secondary; prefer the primary.\n"
                "3. Verdict: publishable after those two fixes."
            )
        if "synthesize" in sys:
            return (
                f"# Synthesis draft (seed {seed})\n\n"
                f"Merged findings on '{short}' from all angles. "
                "See per-angle sections for detail. [overview](https://example.com/overview)"
            )
        return (
            f"## {angle.title()} findings on: {short}\n\n"
            f"- Key point A ({angle}, {seed}): the consensus view with one caveat. "
            f"[source-a-{seed}](https://example.com/{angle}-{seed}-a)\n"
            f"- Key point B ({angle}): the strongest counter-point or cost. "
            f"[source-b-{seed}](https://example.com/{angle}-{seed}-b)\n"
            f"- Bottom line: what a {angle} would do next about '{short}'.\n"
        )


class OpenAICompatProvider(LLMProvider):
    """Minimal OpenAI-compatible chat client over urllib (no deps)."""

    def __init__(self, *, base_url: str, api_key: str, model: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.name = "openai-compat"

    async def chat(self, messages: list[dict], *, system_extra: str = "") -> str:
        if system_extra:
            messages = [{"role": "system", "content": system_extra}] + messages
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "temperature": 0.4,
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        def _post() -> str:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
            return str(body["choices"][0]["message"]["content"])

        return await asyncio.to_thread(_post)


def get_provider(name: str, model: str = "") -> LLMProvider:
    name = (name or "auto").lower()
    if name == "mock":
        return MockProvider()
    if name == "ollama":
        return OpenAICompatProvider(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            model=model or os.environ.get("RESEARCH_MODEL", "llama3.1"),
        )
    if name == "openai":
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set (or use --provider mock).")
        return OpenAICompatProvider(
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=key,
            model=model or os.environ.get("RESEARCH_MODEL", "gpt-4o-mini"),
        )
    # auto
    if os.environ.get("OPENAI_API_KEY"):
        return get_provider("openai", model)
    if os.environ.get("OLLAMA_HOST") or os.environ.get("RESEARCH_PROVIDER") == "ollama":
        return get_provider("ollama", model)
    return MockProvider()
