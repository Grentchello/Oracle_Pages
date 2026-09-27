#!/bin/bash
# Test claude-agent-acp with a full session lifecycle
exec 3< <(cat << 'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,"clientCapabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}
{"jsonrpc":"2.0","method":"session/new","params":{"cwd":"/tmp","mcpServers":[]}}
{"jsonrpc":"2.0","method":"session/prompt","params":{"sessionId":"REPLACE","prompt":[{"type":"text","text":"say hi"}]}}
EOF
)

cat <&3 | ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" ANTHROPIC_AUTH_TOKEN="$ANTHROPIC_AUTH_TOKEN" timeout 20 /app/packages/adapters/claude-local/node_modules/.bin/claude-agent-acp 2>&1
