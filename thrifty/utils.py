import os
import re
import subprocess

NOISE_DIRS = frozenset([
    "node_modules", ".git", "target", "__pycache__", ".next",
    "dist", "build", ".cache", ".turbo", ".vercel", ".pytest_cache",
    ".mypy_cache", ".tox", ".venv", "venv", "env", ".env",
    "coverage", ".nyc_output", ".DS_Store", ".idea", ".vscode",
])

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """Run a subprocess, returning (exit_code, stdout, stderr). Never raises."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout, r.stderr
    except OSError as e:
        return 127, "", str(e)
    except subprocess.TimeoutExpired:
        return 1, "", "timed out"


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def truncate(s: str, width: int) -> str:
    return s if len(s) <= width else s[:width - 3] + "..."


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f}K"
    return f"{n / 1024 ** 2:.1f}M"


def log_stats(cmd: str, raw: str, filtered: str) -> None:
    """Print savings % to stderr when THRIFTY_STATS=1."""
    if os.environ.get("THRIFTY_STATS") != "1":
        return
    raw_c, filt_c = len(raw), len(filtered)
    pct = round(100 - (filt_c * 100 / max(raw_c, 1)))
    import sys
    print(f"[thrifty] {cmd}: {raw_c} → {filt_c} chars ({pct}% reduction)", file=sys.stderr)
