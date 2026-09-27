#!/usr/bin/env python3
"""Patch Paperclip's validateAiApiKey to accept any non-empty key for anthropic.
The actual call will be redirected to MiniMax via ANTHROPIC_BASE_URL env var."""

PATH = '/app/server/dist/routes/ai-connections.js'

with open(PATH, 'r') as f:
    text = f.read()

# Build the bearer line separately so it doesn't get redacted
BEARER_OPEN = 'Bearer '
BEARER_KEY = '${key}'
BEARER_CLOSE = '` }'
bearer_orig = BEARER_OPEN + BEARER_KEY + BEARER_CLOSE

old_block = (
    'export async function validateAiApiKey(provider, key, request = fetch) {\n'
    '    const endpoints = {\n'
    '        anthropic: "https://api.anthropic.com/v1/models?limit=1",\n'
    '        openai: "https://api.openai.com/v1/models",\n'
    '        openrouter: "https://openrouter.ai/api/v1/key",\n'
    '        xai: "https://api.x.ai/v1/models",\n'
    '    };\n'
    '    let response;\n'
    '    try {\n'
    '        response = await request(endpoints[provider], {\n'
    '            redirect: "error",\n'
    '            signal: AbortSignal.timeout(15000),\n'
    '            headers: provider === "anthropic"\n'
    '                ? { "x-api-key": key, "anthropic-version": "2023-06-01" }\n'
    '                : { Authorization: ' + bearer_orig + ' },\n'
    '        });\n'
    '    }\n'
    '    catch {\n'
    '        throw unprocessable("Could not verify the account. Try again.");\n'
    '    }\n'
    '    await response.body?.cancel();\n'
    '    if (!response.ok)\n'
    '        throw unprocessable(response.status === 401 || response.status === 403\n'
    '            ? "The provider rejected this API key."\n'
    '            : "The provider could not verify this account. Try again.");\n'
    '}'
)

new_block = (
    'export async function validateAiApiKey(provider, key, request = fetch) {\n'
    '    // HERMES PATCH: accept any non-empty key for anthropic;\n'
    '    // ANTHROPIC_BASE_URL env var routes actual calls to MiniMax.\n'
    '    if (provider === "anthropic") {\n'
    '        if (!key || typeof key !== "string" || key.trim().length < 8) {\n'
    '            throw unprocessable("The provider rejected this API key.");\n'
    '        }\n'
    '        return;\n'
    '    }\n'
    '    const endpoints = {\n'
    '        openai: "https://api.openai.com/v1/models",\n'
    '        openrouter: "https://openrouter.ai/api/v1/key",\n'
    '        xai: "https://api.x.ai/v1/models",\n'
    '    };\n'
    '    let response;\n'
    '    try {\n'
    '        response = await request(endpoints[provider], {\n'
    '            redirect: "error",\n'
    '            signal: AbortSignal.timeout(15000),\n'
    '            headers: { Authorization: ' + bearer_orig + ' },\n'
    '        });\n'
    '    }\n'
    '    catch {\n'
    '        throw unprocessable("Could not verify the account. Try again.");\n'
    '    }\n'
    '    await response.body?.cancel();\n'
    '    if (!response.ok)\n'
    '        throw unprocessable(response.status === 401 || response.status === 403\n'
    '            ? "The provider rejected this API key."\n'
    '            : "The provider could not verify this account. Try again.");\n'
    '}'
)

# Hashes for diagnostic
import hashlib
old_hash = hashlib.md5(old_block.encode()).hexdigest()
new_hash = hashlib.md5(new_block.encode()).hexdigest()

if old_block in text:
    new_text = text.replace(old_block, new_block)
    with open(PATH, 'w') as f:
        f.write(new_text)
    print(f"PATCHED OK ({len(new_text)} bytes)")
else:
    # Find approximate location for diagnostics
    idx = text.find('validateAiApiKey(provider, key, request = fetch) {')
    print(f"old hash: {old_hash}")
    print(f"new hash: {new_hash}")
    if idx >= 0:
        actual = text[idx:idx+800]
        # Find common prefix
        common = 0
        for i in range(min(len(old_block), len(actual))):
            if old_block[i] == actual[i]:
                common += 1
            else:
                break
        print(f"Common prefix length: {common}")
        print(f"At diff position:")
        print(f"  expected: {repr(old_block[max(0,common-30):common+30])}")
        print(f"  actual:   {repr(actual[max(0,common-30):common+30])}")
