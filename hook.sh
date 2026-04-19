#!/usr/bin/env bash
# thrifty PreToolUse hook for Claude Code.
# Intercepts Bash tool calls and rewrites supported commands through thrifty filters.
set -euo pipefail

THRIFTY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$THRIFTY_DIR:${PYTHONPATH:-}"

INPUT=$(cat)

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)
[ "$TOOL" != "Bash" ] && exit 0

CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -z "$CMD" ] && exit 0

REWRITTEN=$(python3 -m thrifty rewrite "$CMD" 2>/dev/null) || exit 0

printf '%s' "$(jq -n --arg cmd "$REWRITTEN" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"allow",updatedInput:{command:$cmd}}}')"
