import re
import sys
from collections import defaultdict

from thrifty.utils import NOISE_DIRS, human_size, log_stats, run_command

# Use the date field ("Apr 19 14:02" or "Apr 19  2023") as a stable anchor —
# everything after it is the filename, the last number before it is the size.
# This handles multi-word owner/group names, filenames with spaces, and both
# BSD ls (macOS) and GNU ls (Linux) output formats.
LS_DATE_RE = re.compile(
    r"\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+(?:\d{4}|\d{2}:\d{2})\s+"
)


def run(args: list[str]) -> None:
    show_all = any(
        (a.startswith("-") and not a.startswith("--") and "a" in a) or a == "--all"
        for a in args
    )

    # Always force -la for consistent parsing; strip flags we handle ourselves
    flags = [a for a in args if a.startswith("-")]
    paths = [a for a in args if not a.startswith("-")] or ["."]

    cmd = ["ls", "-la"] + flags + paths
    code, raw, err = run_command(cmd)
    if code != 0:
        print(err or "ls failed", file=sys.stderr)
        sys.exit(code)

    entries, summary = compact_ls(raw, show_all)
    filtered = entries + summary
    log_stats("ls", raw, filtered)
    print(filtered, end="")


def compact_ls(raw: str, show_all: bool = False) -> tuple[str, str]:
    """Parse ls -la output into compact (entries, summary) strings."""
    dirs: list[str] = []
    files: list[tuple[str, str]] = []  # (name, human_size)
    by_ext: dict[str, int] = defaultdict(int)

    for line in raw.splitlines():
        if line.startswith("total ") or not line.strip():
            continue
        parsed = _parse_ls_line(line)
        if parsed is None:
            continue
        file_type, size, name = parsed

        if name in (".", ".."):
            continue
        if not show_all and name in NOISE_DIRS:
            continue

        if file_type == "d":
            dirs.append(name)
        elif file_type in ("-", "l"):
            ext = name[name.rfind("."):] if "." in name else "(no ext)"
            by_ext[ext] += 1
            files.append((name, human_size(size)))

    if not dirs and not files:
        return "(empty)\n", ""

    entries = ""
    for d in dirs:
        entries += f"{d}/\n"
    for name, size in files:
        entries += f"{name}  {size}\n"

    # Summary: top 5 extensions by count
    summary = f"\nSummary: {len(files)} files, {len(dirs)} dirs"
    if by_ext:
        top = sorted(by_ext.items(), key=lambda x: -x[1])[:5]
        ext_str = ", ".join(f"{c} {e}" for e, c in top)
        if len(by_ext) > 5:
            ext_str += f", +{len(by_ext) - 5} more"
        summary += f" ({ext_str})"
    summary += "\n"

    return entries, summary


def _parse_ls_line(line: str) -> tuple[str, int, str] | None:
    """Parse one ls -la line into (file_type_char, size_bytes, name)."""
    m = LS_DATE_RE.search(line)
    if not m:
        return None

    name = line[m.end():]
    before = line[:m.start()]
    parts = before.split()
    if len(parts) < 4:
        return None

    perms = parts[0]
    file_type = perms[0] if perms else "-"

    # Size is the rightmost numeric token before the date anchor
    size = 0
    for part in reversed(parts):
        if part.isdigit():
            size = int(part)
            break

    return file_type, size, name
