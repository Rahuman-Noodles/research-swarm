"""Report saving + console preview."""
from __future__ import annotations

import os
import re
from datetime import datetime


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")[:50]
    return s or "report"


def save_markdown(markdown: str, *, query: str, out_dir: str = "reports") -> str:
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(out_dir, f"{stamp}-{slugify(query)}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown)
        if not markdown.endswith("\n"):
            f.write("\n")
    return path


def console_preview(markdown: str, width: int = 100, lines: int = 40) -> str:
    out = []
    for ln in markdown.splitlines()[:lines]:
        out.append(ln[:width])
    if len(markdown.splitlines()) > lines:
        out.append(f"... ({len(markdown.splitlines()) - lines} more lines)")
    return "\n".join(out)
