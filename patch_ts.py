#!/usr/bin/env python3
import re

PATH = '/app/server/src/routes/ai-connections.ts'

with open(PATH, 'r') as f:
    text = f.read()

# Find the validateAiApiKey function in TypeScript
sentinel = 'export async function validateAiApiKey('
marker = 'HERMES_PATCH_ACCEPT_ANY_ANTHROPIC_KEY'

# Find the function start and end
start = text.find(sentinel)
if start < 0:
    print('SENTINEL NOT FOUND')
    raise SystemExit(1)

# Find the next function or end of validateAiApiKey
# Look for the closing brace at column 0
i = start
depth = 0
while i < len(text):
    if text[i] == '{':
        depth += 1
    elif text[i] == '}':
        depth -= 1
        if depth == 0:
            end = i + 1
            break
    i += 1

print(f'Function at {start}-{end}')

# Build the replacement
old_func = text[start:end]
print(f'Old function (first 200 chars): {old_func[:200]}')

# Inject early-return at start
injection_template = '''export async function validateAiApiKey(
  provider: AiProvider,
  key: string,
  request: typeof fetch = fetch,
) {
  // HERMES_PATCH_ACCEPT_ANY_ANTHROPIC_KEY
  if (provider === "anthropic") {
    if (!key || typeof key !== "string" || key.trim().length < 8) {
      throw unprocessable("The provider rejected this API key.");
    }
    return;
  }
  const endpoints: Record<AiProvider, string> = {'''

# Replace from start of function declaration to first "endpoints"
# Find the endpoints line in old function
endpoints_idx = old_func.find('const endpoints')
if endpoints_idx < 0:
    print('Could not find endpoints in function')
    raise SystemExit(1)

# Cut from "const endpoints" and replace with our version
new_func = injection_template + old_func[endpoints_idx + len('const endpoints: Record<AiProvider, string> = {'):]

# Now insert anthropic back into endpoints in new_func (it was stripped)
# Actually, simpler approach - keep the rest of old_func and just prepend
new_func = injection_template + old_func[endpoints_idx + len('const endpoints: Record<AiProvider, string> = {'):]

# Verify
if marker not in new_func:
    print(f'PATCH FAILED - marker not in new function')

# Apply
new_text = text[:start] + new_func + text[end:]

with open(PATH, 'w') as f:
    f.write(new_text)

print(f'PATCHED. Old file: {len(text)} bytes. New file: {len(new_text)} bytes')
