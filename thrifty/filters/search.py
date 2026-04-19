import sys
from collections import defaultdict

from thrifty.utils import log_stats, run_command

MAX_PER_FILE = 10
MAX_TOTAL = 50
MAX_LINE_LEN = 80


def run(args: list[str]) -> None:
    """rg primary, grep -rn fallback. args[0] is 'grep' or 'rg'."""
    tool = args[0] if args else "rg"
    user_args = args[1:]

    # Extract pattern — first non-flag argument
    pattern = next((a for a in user_args if not a.startswith("-")), "")

    rg_args = _strip_rg_incompatible(user_args)
    code, raw, err = run_command(["rg", "-n", "--no-heading"] + rg_args)

    if code == 127:  # rg not found
        grep_args = user_args if tool == "grep" else ["-rn"] + user_args
        code, raw, err = run_command(["grep"] + grep_args)

    if raw.strip():
        filtered = filter_grep_output(raw, pattern)
        log_stats(tool, raw, filtered)
        print(filtered, end="")
    else:
        msg = f"0 matches for '{pattern}'"
        print(msg)
        if err.strip() and code == 2:
            print(err.strip(), file=sys.stderr)

    sys.exit(0 if raw.strip() else 1)


def filter_grep_output(raw: str, pattern: str) -> str:
    by_file: dict[str, list[tuple[int, str]]] = defaultdict(list)
    total = 0

    for line in raw.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            file, ln, content = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            file, ln, content = "", parts[0], parts[1]
        else:
            continue
        try:
            line_num = int(ln)
        except ValueError:
            continue
        total += 1
        cleaned = _clean_grep_line(content, pattern)
        by_file[file].append((line_num, cleaned))

    if not by_file:
        return f"0 matches for '{pattern}'\n"

    out = f"{total} matches in {len(by_file)} file(s):\n\n"
    shown = 0

    for file in sorted(by_file):
        if shown >= MAX_TOTAL:
            break
        matches = by_file[file]
        display = _compact_path(file)
        out += f"[file] {display} ({len(matches)}):\n"

        for ln, content in matches[:MAX_PER_FILE]:
            out += f"  {ln:>4}: {content}\n"
            shown += 1
            if shown >= MAX_TOTAL:
                break

        if len(matches) > MAX_PER_FILE:
            out += f"  +{len(matches) - MAX_PER_FILE} more\n"
        out += "\n"

    if total > shown:
        out += f"... +{total - shown} more matches\n"

    return out


def _clean_grep_line(content: str, pattern: str, max_len: int = MAX_LINE_LEN) -> str:
    """Truncate long lines to max_len, centering the window around the match."""
    trimmed = content.strip()
    if len(trimmed) <= max_len:
        return trimmed

    lower = trimmed.lower()
    pat_lower = pattern.lower()
    pos = lower.find(pat_lower)

    chars = list(trimmed)
    char_len = len(chars)

    if pos >= 0:
        char_pos = len(trimmed[:pos])
        start = max(0, char_pos - max_len // 3)
        end = min(char_len, start + max_len)
        start = max(0, end - max_len)
        slc = "".join(chars[start:end])
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < char_len else ""
        return f"{prefix}{slc}{suffix}"

    return "".join(chars[: max_len - 3]) + "..."


def _compact_path(path: str, max_len: int = 50) -> str:
    if len(path) <= max_len:
        return path
    parts = path.split("/")
    if len(parts) <= 3:
        return path
    return f"{parts[0]}/.../{parts[-2]}/{parts[-1]}"


def _strip_rg_incompatible(args: list[str]) -> list[str]:
    """Remove flags that mean something different in rg vs grep."""
    return [a for a in args if a not in ("-r", "--recursive")]
