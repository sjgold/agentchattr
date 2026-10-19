#!/usr/bin/env sh
if [ "$#" -eq 0 ]; then
    exec sh "$(dirname -- "$0")/start_cli_agent.sh" kilo
else
    exec sh "$(dirname -- "$0")/start_cli_agent.sh" kilo -- -m "$1"
fi
