import socket, json, time

def call(method, path, data=None, timeout=10):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect('/tmp/tailscaled.sock')
    body = ''
    headers = f'{method} {path} HTTP/1.1\r\nHost: local-tailscaled.sock\r\nUser-Agent: tailscale-cli\r\n'
    if data is not None:
        body = json.dumps(data)
        headers += f'Content-Type: application/json\r\nContent-Length: {len(body)}\r\n'
    headers += '\r\n'
    s.sendall((headers + body).encode())
    response = b''
    start = time.time()
    while time.time() - start < timeout:
        try:
            chunk = s.recv(8192)
        except socket.timeout:
            break
        if not chunk: break
        response += chunk
        if b'\r\n\r\n' in response:
            hp = response.split(b'\r\n\r\n')[0]
            if b'Content-Length:' in hp:
                length = int(hp.split(b'Content-Length: ')[1].split(b'\r\n')[0])
                if len(response) >= len(hp) + 4 + length:
                    break
    s.close()
    if b'\r\n\r\n' in response:
        h, b = response.split(b'\r\n\r\n', 1)
        return h.decode(), b.decode()
    return response.decode(), ''

# Find correct endpoint
data = {"authkey": "tskey-auth-kFBFXnZ53p11CNTRL-4civqfKvKYic7a8UHlsrXi7gfs9cUV4DP", "hostname": "hermes-vps"}
for path in ['/localapi/v0/login', '/localapi/v0/prefs']:
    h, b = call('POST', path, data, timeout=10)
    status = h.split('\r\n')[0]
    print(f'POST {path}: {status}')
    if '200' in status or '20' in status:
        print(f'  body: {b[:300]}')
