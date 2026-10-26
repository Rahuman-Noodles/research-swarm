"""CLI: one-shot + interactive REPL. Stdlib only, rich optional."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from .config import ANGLE_PRESETS, DEPTH_PRESETS, SwarmConfig
from .orchestrator import run_swarm
from .report import console_preview, save_markdown

try:
    from rich.console import Console  # type: ignore
    from rich.markdown import Markdown  # type: ignore
    _RICH = True
except Exception:
    _RICH = False


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="research-swarm",
        description="Fan out parallel researcher agents, then synthesize a cited report.",
    )
    p.add_argument("query", nargs="*", help="research question (or omit for --interactive)")
    p.add_argument("-i", "--interactive", action="store_true", help="chat REPL")
    p.add_argument("--angles", type=int, default=4, help="1-8 parallel researchers (default 4)")
    p.add_argument("--depth", default="standard", choices=sorted(DEPTH_PRESETS),
                   help="quick | standard | deep")
    p.add_argument("--provider", default="auto", choices=["auto", "mock", "openai", "ollama"])
    p.add_argument("--model", default="", help="override model (else $RESEARCH_MODEL)")
    p.add_argument("--out-dir", default="reports")
    p.add_argument("--offline", action="store_true", help="force canned search results")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--list-angles", action="store_true", help="show lens presets and exit")
    p.add_argument("--max-parallel", type=int, default=4)
    return p


def _print(md: str) -> None:
    if _RICH:
        Console().print(Markdown(md))
    else:
        print(console_preview(md, lines=60))


async def run_once(cfg: SwarmConfig) -> str:
    print(f"\nSwarming '{cfg.query}' — {cfg.angles} angles, {cfg.depth}, provider={cfg.provider}")
    result = await run_swarm(cfg, progress=print)
    path = save_markdown(result.final_markdown, query=cfg.query, out_dir=cfg.out_dir)
    print(f"\nDone in {result.elapsed_s:.1f}s via {result.provider} "
          f"({result.total_tool_calls} tool calls). Saved: {path}\n")
    _print(result.final_markdown)
    if cfg.verbose:
        for r in result.reports:
            print(f"\n--- trace:{r.angle} ---")
            for t in r.trace[:4]:
                print("  ", t[:300].replace("\n", " | "))
    return path


async def repl(base: SwarmConfig) -> None:
    print("Research Swarm REPL — type a question, or help / quit.\n")
    while True:
        try:
            q = input("swarm> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return
        if not q:
            continue
        if q.lower() in ("quit", "exit", "q"):
            print("bye")
            return
        if q.lower() == "help":
            print("Type any research question. Commands: help, quit. "
                  "Flags come from startup (--angles/--depth/--provider).")
            continue
        cfg = SwarmConfig(query=q, angles=base.angles, depth=base.depth,
                          provider=base.provider, model=base.model,
                          out_dir=base.out_dir, offline=base.offline,
                          verbose=base.verbose, max_parallel=base.max_parallel)
        try:
            await run_once(cfg)
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)


async def amain(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_angles:
        for a in ANGLE_PRESETS:
            print(f"- {a['name']}: {a['lens'][:90]}...")
        return 0
    offline = args.offline or os.environ.get("RESEARCH_OFFLINE") == "1"
    base = SwarmConfig(query="repl", angles=args.angles, depth=args.depth,
                       provider=args.provider, model=args.model,
                       out_dir=args.out_dir, offline=offline,
                       verbose=args.verbose, max_parallel=args.max_parallel)
    if args.interactive or not args.query:
        if not args.query and not args.interactive:
            build_parser().print_help()
            print('\nTip: research-swarm "is nuclear fusion close?" --depth quick --provider mock')
            return 2
        await repl(base)
        return 0
    base.query = " ".join(args.query)
    await run_once(base)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(amain()))


if __name__ == "__main__":
    main()
