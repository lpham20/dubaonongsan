"""Sync simple Caddy redirects into Cloudflare Pages _redirects.

The VPS is the primary production target, but keeping _redirects aligned makes a
fallback Cloudflare Pages deploy less surprising. Regex/query Caddy matchers are
documented in deploy/redirects.caddy and intentionally left out because
Cloudflare _redirects cannot express them safely.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CADDY_REDIRECTS = ROOT / "deploy" / "redirects.caddy"
CLOUDFLARE_REDIRECTS = ROOT / "frontend" / "public" / "_redirects"
START = "# BEGIN synced from deploy/redirects.caddy"
END = "# END synced from deploy/redirects.caddy"


def _simple_redirects() -> list[str]:
    rows: list[str] = []
    for line in CADDY_REDIRECTS.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*redir\s+(/[^ \t]+)\s+(/[^ \t]+)\s+permanent\s*$", line)
        if match:
            rows.append(f"{match.group(1):<34} {match.group(2):<38} 301")
    return rows


def sync() -> None:
    current = CLOUDFLARE_REDIRECTS.read_text(encoding="utf-8")
    block = "\n".join([START, *_simple_redirects(), END])
    pattern = re.compile(rf"{re.escape(START)}.*?{re.escape(END)}", re.S)
    if pattern.search(current):
        next_text = pattern.sub(block, current)
    else:
        insertion = current.find("\n\n# Static SPA fallback")
        if insertion == -1:
            next_text = f"{current.rstrip()}\n\n{block}\n"
        else:
            next_text = f"{current[:insertion].rstrip()}\n\n{block}{current[insertion:]}"
    CLOUDFLARE_REDIRECTS.write_text(next_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync simple Caddy redirects into frontend/public/_redirects.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero if _redirects is not in sync.")
    args = parser.parse_args()
    before = CLOUDFLARE_REDIRECTS.read_text(encoding="utf-8")
    sync()
    after = CLOUDFLARE_REDIRECTS.read_text(encoding="utf-8")
    if args.check and before != after:
        CLOUDFLARE_REDIRECTS.write_text(before, encoding="utf-8")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
