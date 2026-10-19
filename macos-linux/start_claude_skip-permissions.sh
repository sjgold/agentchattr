#!/usr/bin/env sh
exec sh "$(dirname -- "$0")/start_cli_agent.sh" claude --dangerously-skip-permissions "$@"
