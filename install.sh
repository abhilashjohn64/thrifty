#!/usr/bin/env bash
set -euo pipefail

THRIFTY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_SH="$THRIFTY_DIR/hook.sh"
SETTINGS="$HOME/.claude/settings.json"

chmod +x "$HOOK_SH"
mkdir -p "$HOME/.claude"
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"

python3 - "$SETTINGS" "$HOOK_SH" << 'PYEOF'
import sys, json, os

settings_path, hook_sh = sys.argv[1], sys.argv[2]

with open(settings_path) as f:
    settings = json.load(f)

settings.setdefault("hooks", {})
settings["hooks"].setdefault("PreToolUse", [])

for entry in settings["hooks"]["PreToolUse"]:
    for h in entry.get("hooks", []):
        if h.get("command") == hook_sh:
            print(f"[thrifty] already registered in {settings_path}")
            sys.exit(0)

settings["hooks"]["PreToolUse"].append({
    "hooks": [{"type": "command", "command": hook_sh}],
    "matcher": "Bash"
})

tmp = settings_path + ".tmp"
with open(tmp, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
os.replace(tmp, settings_path)
print(f"[thrifty] registered hook: {hook_sh}")
print(f"[thrifty] settings: {settings_path}")
PYEOF
