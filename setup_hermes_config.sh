#!/bin/bash
# Setup Hermes config in Paperclip container

MM_KEY_PLACEHOLDER

mkdir -p /home/node/.hermes

cat > /home/node/.hermes/config.yaml << 'CFG'
model:
  default: MiniMax-M3
  provider: minimax
  base_url: ''
  api_key: ''
database:
  journal_mode: wal
runtime:
  nofile_soft_limit: 4096
agent:
  max_turns: 150
  verbose: false
  reasoning_effort: medium
  personalities: {}
terminal:
  backend: local
  cwd: .
  timeout: 180
  home_mode: auto
web:
  backend: ddgs
browser:
  backend: browser-use
  inactivity_timeout: 120
CFG

cat > /home/node/.hermes/.env << EOF
MINIMAX_API_KEY=${MM_KEY_PLACEHOLDER}
EOF

echo "Config:"
ls -la /home/node/.hermes/
cat /home/node/.hermes/.env | head -3
echo "DONE"
