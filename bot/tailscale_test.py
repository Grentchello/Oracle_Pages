import socket, json, time

def call(method, path, data=None, timeout=30):
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
        try: chunk = s.recv(8192)
        except socket.timeout: break
        if not chunk: break
        response += chunk
        if b'\r\n\r\n' in response:
            hp = response.split(b'\r\n\r\n')[0]
            if b'Content-Length:' in hp:
                length = int(hp.split(b'Content-Length: ')[1].split(b'\r\n')[0])
                if len(response) >= len(hp) + 4 + length: break
    s.close()
    if b'\r\n\r\n' in response:
        h, b = response.split(b'\r\n\r\n', 1)
        return h.decode(), b.decode()
    return response.decode(), ''

# 1. Set WantRunning=true via PATCH
data = {'WantRunning': True}
h, b = call('PATCH', '/localapi/v0/prefs', data, timeout=15)
print(f'PATCH WantRunning=true: {h.split(chr(10))[0]}')

# 2. POST /start with authkey
data2 = {'authkey': 'tskey-auth-kFBFXnZ53p11CNTRL-4civqfKvKYic7a8UHlsrXi7gfs9cUV4DP', 'hostname': 'hermes-vps'}
h2, b2 = call('POST', '/localapi/v0/start', data2, timeout=15)
print(f'POST start: {h2.split(chr(10))[0]}')

# 3. Wait and check status
time.sleep(8)
h3, b3 = call('GET', '/localapi/v0/status', timeout=10)
status = json.loads(b3)
print(f'\n=== Status ===')
print(f'BackendState: {status.get("BackendState")}')
print(f'AuthURL: {status.get("AuthURL")}')
print(f'IP: {status.get("TailscaleIPs")}')
print(f'Hostname: {status.get("Self", {}).get("HostName")}')
