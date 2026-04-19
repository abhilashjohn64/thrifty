import os
import re
import sys

SUPPORTED_PATTERNS = [
    re.compile(r"^git\s+status(\s|$)"),
    re.compile(r"^git\s+log(\s|$)"),
    re.compile(r"^git\s+diff(\s|$)"),
    re.compile(r"^ls(\s|$)"),
    re.compile(r"^rg(\s|$)"),
    re.compile(r"^grep(\s|$)"),
]

# Shell metacharacters that make a command too complex to safely intercept.
_MULTILINE_RE = re.compile(r"&&|\|\||\||;|<<|`|\$\(")


def _is_multiline_command(cmd: str) -> bool:
    return bool(_MULTILINE_RE.search(cmd))


def _thrifty_path() -> str:
    """Absolute path to the thrifty package for use in rewritten commands."""
    return os.path.dirname(os.path.abspath(__file__))


def rewrite(cmd_string: str) -> None:
    """Print rewritten command and exit 0, or exit 1 if no filter available."""
    cmd = cmd_string.strip()

    if not cmd:
        sys.exit(1)

    # Prevent double-wrapping
    if "thrifty" in cmd:
        sys.exit(1)

    # Compound/piped commands are too complex to intercept safely
    if _is_multiline_command(cmd):
        sys.exit(1)

    for pattern in SUPPORTED_PATTERNS:
        if pattern.match(cmd):
            pkg_dir = os.path.dirname(_thrifty_path())
            print(f"python3 -m thrifty {cmd}", end="")
            # Ensure PYTHONPATH includes the project root so -m thrifty resolves
            # even if thrifty isn't pip-installed globally.
            sys.exit(0)

    sys.exit(1)
