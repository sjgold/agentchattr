#!/usr/bin/env sh
exec sh "$(dirname -- "$0")/start_cli_agent.sh" qwen -i "When asked for a reply or to answer, YOU MUST USE the mcp of agentchattr. When talking about a chat, we are speaking about interaction with tools provided by mcp of agentchattr. The human NEVER SEES your usual CLI interface. Just consider this, other instructions will follow." "$@"
