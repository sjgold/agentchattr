#!/usr/bin/env sh
if [ "$#" -eq 0 ]; then
    echo "Usage: start_api_agent.sh configured-agent-name" >&2
    exit 1
fi
exec sh "$(dirname -- "$0")/start_cli_agent.sh" "$@"
