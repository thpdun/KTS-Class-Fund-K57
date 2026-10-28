import urllib.request
import json

# Try import or fallback
try:
    import sha3
    def keccak(s):
        return sha3.keccak_256(s.encode('utf-8')).hexdigest()
    print("Using sha3 module")
except Exception:
    pass
    # Let's use pure python keccak
    def keccak_256(data: bytes) -> bytes:
        state = [[0]*5 for _ in range(5)]
        RC = [
            0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
            0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
            0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
            0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
            0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
            0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008
        ]
        rot = [
            [0, 36, 3, 41, 18],
            [1, 44, 10, 45, 2],
            [62, 6, 43, 15, 61],
            [28, 55, 25, 21, 56],
            [27, 20, 39, 8, 14]
        ]
        def rol(val, shift):
            return ((val << shift) | (val >> (64 - shift))) & 0xFFFFFFFFFFFFFFFF
        rate = 136
        pad_len = rate - (len(data) % rate)
        if pad_len == 1:
            pad = b'\x01\x80' # wait: if pad_len == 1, 0x01 | 0x80 = 0x81
            pad = b'\x81'
        else:
            pad = b'\x01' + b'\x00' * (pad_len - 2) + b'\x80'
        msg = data + pad
        for b in range(0, len(msg), rate):
            chunk = msg[b:b+rate]
            for i in range(rate // 8):
                x = i % 5
                y = i // 5
                lane = int.from_bytes(chunk[i*8:(i+1)*8], 'little')
                state[x][y] ^= lane
            for r in range(24):
                # Theta
                C = [state[x][0] ^ state[x][1] ^ state[x][2] ^ state[x][3] ^ state[x][4] for x in range(5)]
                D = [C[(x-1)%5] ^ rol(C[(x+1)%5], 1) for x in range(5)]
                for x in range(5):
                    for y in range(5):
                        state[x][y] ^= D[x]
                # Rho and Pi
                B = [[0]*5 for _ in range(5)]
                for x in range(5):
                    for y in range(5):
                        B[y][(2*x + 3*y)%5] = rol(state[x][y], rot[x][y])
                # Chi
                for x in range(5):
                    for y in range(5):
                        state[x][y] = B[x][y] ^ ((~B[(x+1)%5][y]) & B[(x+2)%5][y])
                # Iota
                state[0][0] ^= RC[r]
        out = b''
        for y in range(5):
            for x in range(5):
                out += state[x][y].to_bytes(8, 'little')
        return out[:32]
    def keccak(s):
        return keccak_256(s.encode('utf-8')).hex()

print("keccak('') =", keccak(''))
print("keccak('advisor()') =", keccak('advisor()')[:8])
print("keccak('classFundBalance()') =", keccak('classFundBalance()')[:8])
print("keccak('activeBCSCount()') =", keccak('activeBCSCount()')[:8])

# Now query Sepolia for Address A
addr_a = '0xe3e1db1da1cae10e92337c36bb13004bf984ee91'
url = 'https://ethereum-sepolia-rpc.publicnode.com'

def rpc_call(to, data):
    payload = {
        'jsonrpc': '2.0',
        'method': 'eth_call',
        'params': [{'to': to, 'data': data}, 'latest'],
        'id': 1
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

for sig in ['advisor()', 'classFundBalance()', 'activeBCSCount()']:
    sel = '0x' + keccak(sig)[:8]
    res = rpc_call(addr_a, sel)
    print(f"{sig} (selector {sel}) -> {res}")
