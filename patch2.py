path = '/app/server/dist/routes/ai-connections.js'
with open(path, 'r') as f:
    text = f.read()

# Inject early-return for anthropic at start of validateAiApiKey function
sentinel = 'export async function validateAiApiKey(provider, key, request = fetch) {'
injection = '''export async function validateAiApiKey(provider, key, request = fetch) {
    // HERMES PATCH: accept any non-empty anthropic key (MiniMax via env var)
    if (provider === "anthropic") {
        if (!key || typeof key !== "string" || key.trim().length < 8) {
            const err = new Error("The provider rejected this API key.");
            err.statusCode = 422;
            throw err;
        }
        return;
    }
'''

if sentinel in text and 'HERMES PATCH' not in text:
    text = text.replace(sentinel, injection, 1)
    with open(path, 'w') as f:
        f.write(text)
    print('PATCHED. New size: ' + str(len(text)) + ' bytes')
else:
    print('SKIP - already patched or sentinel missing')
    if sentinel not in text:
        print('  sentinel NOT FOUND in text')
    if 'HERMES PATCH' in text:
        print('  already patched')
