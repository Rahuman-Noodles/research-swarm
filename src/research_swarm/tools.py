"""Agent tools: web_search, web_fetch, calc. Offline-safe with canned fallback."""
from __future__ import annotations

import ast
import html as ihtml
import operator
import re
import urllib.parse
import urllib.request


TOOL_HELP = """You have tools. To use one, emit exactly one fenced block:

```tool {"name": "web_search", "args": {"query": "...", "k": 4}}
```

Available tools:
- web_search(query: str, k: int = 5): web results as numbered title/url/snippet lines.
- web_fetch(url: str): first ~3000 chars of page text.
- calc(expr: str): safe arithmetic like "(1200*0.35)/12".

Rules: one tool per turn, at most the round limit, then write findings with
markdown citations [label](https://...). Never invent URLs you did not see from a tool
(except https://example.com/* in offline demo mode)."""

_CANNED = [
    ("Overview — background and key terms", "https://example.com/overview",
     " widely cited primer covering definitions, history, and open questions."),
    ("Practitioner guide — costs and pitfalls", "https://example.com/guide",
     " hands-on benchmarks, pricing notes, and failure modes to avoid."),
    ("Critical review — what the hype misses", "https://example.com/critique",
     " counter-evidence, weak claims, and what would change the conclusion."),
    ("Forecast — where this goes next", "https://example.com/forecast",
     " trajectory, base/bull/bear cases, and 2-5 year outlook."),
    ("Primary source collection", "https://example.com/primary",
     " links to docs, papers, and datasets worth citing directly."),
    ("Case study roundup", "https://example.com/cases",
     " three real deployments with numbers and lessons learned."),
]


def offline_search(query: str, k: int = 5) -> str:
    q = query[:80] or "topic"
    lines = [f'Results for "{q}" (offline demo mode):']
    for i, (t, u, s) in enumerate(_CANNED[: max(1, min(k, len(_CANNED)))], 1):
        lines.append(f"{i}. {t} — {u}\n   {s}")
    return "\n".join(lines)


def live_search(query: str, k: int = 5) -> str:
    params = urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(
        f"https://html.duckduckgo.com/html/?{params}",
        headers={"User-Agent": "Mozilla/5.0 (research-swarm)"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        page = resp.read().decode("utf-8", "replace")
    links = re.findall(
        r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.S)
    snips = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', page, re.S)
    if not links:
        raise RuntimeError("no results parsed")
    out = [f'Results for "{query[:80]}" (DuckDuckGo):']
    for i, (url, title) in enumerate(links[:k], 1):
        title = re.sub(r"<[^>]+>", "", ihtml.unescape(title)).strip()
        snip = ""
        if i - 1 < len(snips):
            snip = re.sub(r"<[^>]+>", "", ihtml.unescape(snips[i - 1])).strip()[:220]
        out.append(f"{i}. {title} — {ihtml.unescape(url)}\n   {snip}")
    return "\n".join(out)


def web_search(query: str, k: int = 5, *, offline: bool = False) -> str:
    k = max(1, min(int(k or 5), 8))
    if offline:
        return offline_search(query, k)
    try:
        return live_search(query, k)
    except Exception as e:  # network down / parse change -> still useful
        return offline_search(query, k) + f"\n(note: live search failed: {e})"


def web_fetch(url: str, *, offline: bool = False) -> str:
    if offline or "example.com" in url:
        return f"[offline excerpt] {url}\nRelevant background excerpt for citation purposes."
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research-swarm)"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8", "replace")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = ihtml.unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:3000] or "(empty page)"


_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def calc(expr: str) -> str:
    node = ast.parse(expr, mode="eval")

    def _eval(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in _SAFE_OPS:
            return _SAFE_OPS[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _SAFE_OPS:
            return _SAFE_OPS[type(n.op)](_eval(n.operand))
        raise ValueError(f"unsupported: {type(n).__name__}")

    return f"{expr} = {_eval(node)}"


class ToolRunner:
    def __init__(self, *, offline: bool = False):
        self.offline = offline
        self.calls = 0

    async def run(self, name: str, args: dict) -> str:
        self.calls += 1
        if name == "web_search":
            return web_search(str(args.get("query", "")), int(args.get("k", 5)),
                              offline=self.offline)
        if name == "web_fetch":
            return web_fetch(str(args.get("url", "")), offline=self.offline)
        if name == "calc":
            try:
                return calc(str(args.get("expr", "")))
            except Exception as e:
                return f"calc error: {e}"
        return f"unknown tool: {name}"
