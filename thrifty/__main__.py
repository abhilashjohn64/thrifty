import sys

from thrifty import filters
from thrifty.filters import git, search, system
from thrifty.rewrite import rewrite


def fallback_run(args: list[str]) -> None:
    """Pass an unrecognised command through unchanged, preserving exit code."""
    import subprocess
    r = subprocess.run(args)
    sys.exit(r.returncode)


def main() -> None:
    args = sys.argv[1:]

    if not args:
        print("usage: thrifty <command> [args...]", file=sys.stderr)
        sys.exit(1)

    if args[0] == "rewrite":
        cmd_string = " ".join(args[1:])
        rewrite(cmd_string)
        return  # rewrite() always exits; this is unreachable

    dispatch = {
        "git": git.run,
        "ls": system.run,
        "grep": search.run,
        "rg": search.run,
    }

    handler = dispatch.get(args[0])
    if handler:
        handler(args[1:] if args[0] != "git" else args)
    else:
        fallback_run(args)


if __name__ == "__main__":
    main()
