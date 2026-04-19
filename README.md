# thrifty

A lightweight Claude Code token filter. Intercepts the Bash commands Claude runs and compresses their output before Claude reads it — saving 60–80% of tokens on the most common development operations.

## How it works

Claude Code supports `PreToolUse` hooks that fire before any Bash command is executed. Thrifty registers itself as one of those hooks.

```
Claude runs "git status"
  → hook.sh intercepts the call
  → rewrites it to: python3 -m thrifty git status
  → thrifty runs real git status, filters the output
  → Claude sees a compact summary instead of the full output
```

No changes to how you use Claude Code. Fully transparent.

## Supported commands

| Command | What gets filtered | Target savings |
|---------|--------------------|----------------|
| `git status` | Replaces verbose output with branch + file counts | 75% |
| `git log` | One line per commit: hash, subject, date, author | 80% |
| `git diff` | `--stat` summary + first 100 changed lines per hunk | 75% |
| `ls` / `ls -la` | Strips permissions, owner, timestamps; hides noise dirs | 74% |
| `grep` / `rg` | Groups matches by file, caps at 10/file and 50 total | 80% |

All other commands pass through unchanged.

---

## Installation

### Prerequisites

- Python 3.11+
- `jq` (for the hook shell script)
- Claude Code

### 1. Install thrifty as a Python package

```bash
# From the project root
python3 -m pip install -e ".[dev]"
```

If `pip` is not available on your system:

```bash
# Bootstrap pip first
curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
python3 /tmp/get-pip.py --user --break-system-packages

# Then install
~/.local/bin/pip install --break-system-packages -e ".[dev]"
```

### 2. Register the Claude Code hook

```bash
bash install.sh
```

This writes the hook entry into `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [{"type": "command", "command": "/abs/path/to/hook.sh"}],
        "matcher": "Bash"
      }
    ]
  }
}
```

### 3. Restart Claude Code

Hooks are loaded at startup. Restart the Claude Code session (or the IDE extension) to activate thrifty.

---

## Testing locally

### Run the test suite

```bash
python3 -m pytest -v
```

Expected output: 57 tests, all passing.

### Test individual filters

Run thrifty manually from any git repository:

```bash
# git status
python3 -m thrifty git status

# git log (last 10 commits)
python3 -m thrifty git log -10

# git diff against previous commit
python3 -m thrifty git diff HEAD~1

# ls with sizes, no permissions/timestamps
python3 -m thrifty ls -la

# grep / rg
python3 -m thrifty rg "def " thrifty/
python3 -m thrifty grep -rn "import" thrifty/
```

### Measure token savings

Set `THRIFTY_STATS=1` to print a before/after character count to stderr:

```bash
THRIFTY_STATS=1 python3 -m thrifty git log -20
THRIFTY_STATS=1 python3 -m thrifty ls -la
THRIFTY_STATS=1 python3 -m thrifty git diff HEAD~1
```

Example output:
```
[thrifty] ls: 639 → 165 chars (74% reduction)
```

### Test hook wiring (without restarting Claude Code)

```bash
# Should return JSON with the rewritten command
echo '{"tool_name":"Bash","tool_input":{"command":"git status"}}' | bash hook.sh

# Should return nothing (correct passthrough for unsupported commands)
echo '{"tool_name":"Bash","tool_input":{"command":"npm install"}}' | bash hook.sh
```

### Test the rewrite registry

```bash
# These should exit 0 and print the rewritten command
python3 -m thrifty rewrite "git status"
python3 -m thrifty rewrite "git log -10"
python3 -m thrifty rewrite "ls -la"
python3 -m thrifty rewrite "rg -n pattern src/"

# These should exit 1 silently (not supported or unsafe)
python3 -m thrifty rewrite "npm install"
python3 -m thrifty rewrite "git status && git log"   # compound command
python3 -m thrifty rewrite "git log | head -5"       # pipe
```

---

## Project structure

```
thrifty/
├── thrifty/                  # Python package
│   ├── __main__.py           # Entry point and command dispatch
│   ├── rewrite.py            # Hook rewrite registry
│   ├── utils.py              # Shared helpers (run_command, strip_ansi, etc.)
│   └── filters/
│       ├── git.py            # git status, log, diff
│       ├── system.py         # ls
│       └── search.py         # grep / rg
├── tests/
│   ├── conftest.py           # Shared _savings() helper
│   ├── test_git.py
│   ├── test_system.py
│   ├── test_search.py
│   └── test_rewrite.py
├── hook.sh                   # PreToolUse hook script (called by Claude Code)
├── install.sh                # Registers hook into ~/.claude/settings.json
└── pyproject.toml            # Package config and pytest settings
```

---

## Uninstalling

Remove the hook entry from `~/.claude/settings.json` manually, or run:

```bash
python3 -c "
import json, os
p = os.path.expanduser('~/.claude/settings.json')
with open(p) as f: s = json.load(f)
s['hooks']['PreToolUse'] = [
    h for h in s['hooks'].get('PreToolUse', [])
    if not any('thrifty' in c.get('command', '') for c in h.get('hooks', []))
]
with open(p, 'w') as f: json.dump(s, f, indent=2); f.write('\n')
print('thrifty hook removed')
"
```

Then restart Claude Code.

---

