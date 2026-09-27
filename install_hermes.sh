#!/bin/bash
# Install Hermes Agent CLI on container boot if not already present

set -e

HERMES_BIN="/usr/local/bin/hermes"

if [ ! -f "$HERMES_BIN" ]; then
    echo "[hermes-bootstrap] Installing hermes-agent..."
    # Install pip via ensurepip
    python3 -m ensurepip --upgrade 2>&1 | tail -3 || true

    # Install via uv if available, else pip
    if command -v uv >/dev/null 2>&1; then
        uv pip install --system hermes-agent 2>&1 | tail -3
    else
        # Try installing uv first
        curl -LsSf https://astral.sh/uv/install.sh | sh 2>&1 | tail -3
        export PATH="$HOME/.local/bin:$PATH"
        uv pip install --system hermes-agent 2>&1 | tail -3
    fi
fi

if [ ! -f "$HERMES_BIN" ]; then
    echo "[hermes-bootstrap] ERROR: hermes not found after install"
    exit 1
fi

# Set up config dir for the paperclip user
mkdir -p /home/paperclip/.config/hermes

# Copy config from /paperclip (volume mount) if exists, else use defaults
if [ -f /paperclip/.hermes-config/config.yaml ]; then
    cp /paperclip/.hermes-config/config.yaml /home/paperclip/.config/hermes/config.yaml
fi
if [ -f /paperclip/.hermes-config/.env ]; then
    cp /paperclip/.hermes-config/.env /home/paperclip/.config/hermes/.env
fi

# Ensure MiniMax is the model
cat > /home/paperclip/.config/hermes/config.yaml << 'HERMES_CONFIG'
model:
  default: MiniMax-M3
  provider: minimax
api_key: ${MINIMAX_API_KEY:-}
HERMES_CONFIG

chown -R paperclip:paperclip /home/paperclip/.config 2>/dev/null || true

echo "[hermes-bootstrap] Hermes installed: $(hermes --version 2>&1 | head -1)"
