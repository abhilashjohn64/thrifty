import re
import sys

from thrifty.utils import log_stats, run_command, truncate

MAX_STATUS_FILES = 5
MAX_LOG_ENTRIES = 10
MAX_LOG_SUBJECT = 80
MAX_HUNK_LINES = 100

# Flags that indicate the user wants a custom format — don't inject ours.
_FORMAT_FLAGS = ("--oneline", "--pretty", "--format")
# Flags that supply a commit count limit.
_LIMIT_FLAGS = ("-n", "--max-count")


def run(args: list[str]) -> None:
    """Dispatch git subcommands to their filter."""
    # args still contains "git" as args[0]
    sub = args[1] if len(args) > 1 else ""
    rest = args[2:]

    if sub == "status":
        run_status(rest)
    elif sub == "log":
        run_log(rest)
    elif sub == "diff":
        run_diff(rest)
    else:
        # Unknown git subcommand — passthrough
        code, out, err = run_command(["git"] + args[1:])
        if out:
            print(out, end="")
        if err:
            print(err, end="", file=sys.stderr)
        sys.exit(code)


# ---------------------------------------------------------------------------
# git status
# ---------------------------------------------------------------------------

def run_status(args: list[str]) -> None:
    code, raw, err = run_command(["git", "status", "--porcelain", "-b"])
    if code != 0:
        print(err or "git status failed", file=sys.stderr)
        sys.exit(code)
    filtered = format_status_output(raw)
    log_stats("git status", raw, filtered)
    print(filtered)


def format_status_output(porcelain: str) -> str:
    lines = porcelain.splitlines()
    if not lines:
        return "Clean working tree"

    out = []

    # Branch line
    if lines[0].startswith("##"):
        branch_raw = lines[0][3:]
        out.append("* " + _parse_porcelain_branch(branch_raw))

    staged, modified, untracked, conflicts = [], [], [], []

    for line in lines[1:]:
        if len(line) < 3:
            continue
        xy, file = line[:2], line[3:]
        x, y = xy[0], xy[1]

        if x in "MADRC":
            staged.append(file)
        if x == "U" or y == "U" or xy == "AA" or xy == "DD":
            conflicts.append(file)
        if y in "MD":
            modified.append(file)
        if xy == "??":
            untracked.append(file)

    if staged:
        out.append(_format_file_list("Staged", staged, MAX_STATUS_FILES))
    if modified:
        out.append(_format_file_list("Modified", modified, MAX_STATUS_FILES))
    if untracked:
        out.append(_format_file_list("Untracked", untracked, MAX_STATUS_FILES))
    if conflicts:
        out.append(f"Conflicts ({len(conflicts)})")

    if not staged and not modified and not untracked and not conflicts:
        out.append("clean — nothing to commit")

    return "\n".join(out)


def _parse_porcelain_branch(raw: str) -> str:
    """Extract branch name and ahead/behind from '## main...origin/main [ahead 2]'."""
    # Strip tracking remote (everything after '...')
    name = raw.split("...")[0].strip()

    if "no branch" in raw:
        name = "HEAD (detached)"

    extras = []
    ahead = re.search(r"ahead (\d+)", raw)
    behind = re.search(r"behind (\d+)", raw)
    if ahead:
        extras.append(f"ahead: {ahead.group(1)}")
    if behind:
        extras.append(f"behind: {behind.group(1)}")

    return name + (" | " + ", ".join(extras) if extras else "")


def _format_file_list(label: str, files: list[str], max_shown: int) -> str:
    shown = files[:max_shown]
    overflow = len(files) - max_shown
    suffix = f" [+{overflow} more]" if overflow > 0 else ""
    return f"{label} ({len(files)}): {', '.join(shown)}{suffix}"


# ---------------------------------------------------------------------------
# git log
# ---------------------------------------------------------------------------

def run_log(args: list[str]) -> None:
    has_format = any(a.startswith(f) for a in args for f in _FORMAT_FLAGS)
    limit, user_set_limit = _parse_log_limit(args)

    cmd = ["git", "log"]
    if not has_format:
        cmd += ["--pretty=format:%h %s (%ar) <%an>%n%b%n---END---"]
    if not user_set_limit and not has_format:
        cmd += [f"-{MAX_LOG_ENTRIES}"]
    cmd += args

    code, raw, err = run_command(cmd)
    if code != 0:
        print(err or "git log failed", file=sys.stderr)
        sys.exit(code)

    filtered = filter_log_output(raw, limit, user_set_limit, has_format)
    log_stats("git log", raw, filtered)
    print(filtered)


def filter_log_output(raw: str, limit: int, user_set_limit: bool, user_format: bool) -> str:
    width = 120 if user_set_limit else MAX_LOG_SUBJECT

    if user_format:
        lines = raw.splitlines()
        cap = len(lines) if user_set_limit else limit
        return "\n".join(truncate(l, width) for l in lines[:cap])

    blocks = raw.split("---END---")
    cap = len(blocks) if user_set_limit else limit
    result = []

    for block in blocks[:cap]:
        block = block.strip()
        if not block:
            continue
        block_lines = block.splitlines()
        header = truncate(block_lines[0].strip(), width)

        body = [
            l.strip() for l in block_lines[1:]
            if l.strip()
            and not l.strip().startswith("Signed-off-by:")
            and not l.strip().startswith("Co-authored-by:")
        ]
        omitted = max(0, len(body) - 3)
        body = body[:3]

        if body:
            entry = header + "".join(f"\n  {truncate(b, width)}" for b in body)
            if omitted:
                entry += f"\n  [+{omitted} lines omitted]"
        else:
            entry = header

        result.append(entry)

    return "\n".join(result).strip()


def _parse_log_limit(args: list[str]) -> tuple[int, bool]:
    """Detect -N / -n N / --max-count=N flags. Returns (limit, user_set_limit)."""
    it = iter(args)
    for arg in it:
        if arg.startswith("-") and len(arg) > 1 and arg[1:].isdigit():
            return int(arg[1:]), True
        if arg in ("-n", "--max-count"):
            nxt = next(it, None)
            if nxt and nxt.isdigit():
                return int(nxt), True
        if arg.startswith("--max-count="):
            val = arg.split("=", 1)[1]
            if val.isdigit():
                return int(val), True
    return MAX_LOG_ENTRIES, False


# ---------------------------------------------------------------------------
# git diff
# ---------------------------------------------------------------------------

def run_diff(args: list[str]) -> None:
    # Print --stat summary first
    code, stat_out, err = run_command(["git", "diff", "--stat"] + args)
    if code != 0:
        print(err or "git diff failed", file=sys.stderr)
        sys.exit(code)
    if stat_out.strip():
        print(stat_out.strip())

    # Then compact diff
    code2, diff_out, _ = run_command(["git", "diff"] + args)
    if diff_out.strip():
        print("\n--- Changes ---")
        compacted = compact_diff(diff_out)
        log_stats("git diff", stat_out + diff_out, stat_out + compacted)
        print(compacted)


def compact_diff(diff_text: str, max_hunk_lines: int = MAX_HUNK_LINES) -> str:
    """Keep hunk headers and first N changed lines per hunk; truncate the rest.

    Uses the diff --git filename line as a section boundary, @@ as hunk start.
    Counts only +/- lines against max_hunk_lines; context lines count too but
    only if we haven't hit the cap yet.
    """
    result = []
    current_file = ""
    added = removed = hunk_shown = hunk_skipped = 0
    in_hunk = False
    was_truncated = False

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if hunk_skipped > 0:
                result.append(f"  ... ({hunk_skipped} lines truncated)")
                was_truncated = True
                hunk_skipped = 0
            if current_file and (added or removed):
                result.append(f"  +{added} -{removed}")
            current_file = line.split(" b/", 1)[-1] if " b/" in line else "unknown"
            result.append(f"\n{current_file}")
            added = removed = hunk_shown = 0
            in_hunk = False

        elif line.startswith("@@"):
            if hunk_skipped > 0:
                result.append(f"  ... ({hunk_skipped} lines truncated)")
                was_truncated = True
                hunk_skipped = 0
            in_hunk = True
            hunk_shown = 0
            result.append(f"  {line}")

        elif in_hunk:
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
                if hunk_shown < max_hunk_lines:
                    result.append(f"  {line}")
                    hunk_shown += 1
                else:
                    hunk_skipped += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1
                if hunk_shown < max_hunk_lines:
                    result.append(f"  {line}")
                    hunk_shown += 1
                else:
                    hunk_skipped += 1
            elif not line.startswith("\\") and hunk_shown < max_hunk_lines and hunk_shown > 0:
                result.append(f"  {line}")
                hunk_shown += 1

    if hunk_skipped > 0:
        result.append(f"  ... ({hunk_skipped} lines truncated)")
        was_truncated = True
    if current_file and (added or removed):
        result.append(f"  +{added} -{removed}")
    if was_truncated:
        result.append("[full diff: git diff (without thrifty)]")

    return "\n".join(result)
