"""Minimal secp256k1 arithmetic for Ethereum address recovery.

Pure Python, no new dependency. Used for SIWE verification together with the
local Keccak-256 implementation. Not a general-purpose cryptography library.
"""

P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)
Point = tuple[int, int] | None


def _inv(value: int, modulus: int = P) -> int:
    return pow(value % modulus, -1, modulus)


def add(first: Point, second: Point) -> Point:
    if first is None:
        return second
    if second is None:
        return first
    x1, y1 = first
    x2, y2 = second
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if first == second:
        slope = 3 * x1 * x1 * _inv(2 * y1) % P
    else:
        slope = (y2 - y1) * _inv(x2 - x1) % P
    x3 = (slope * slope - x1 - x2) % P
    y3 = (slope * (x1 - x3) - y1) % P
    return (x3, y3)


def negate(point: Point) -> Point:
    if point is None:
        return None
    return (point[0], (-point[1]) % P)


def multiply(scalar: int, point: Point) -> Point:
    result: Point = None
    addend = point
    value = scalar % N
    while value:
        if value & 1:
            result = add(result, addend)
        addend = add(addend, addend)
        value >>= 1
    return result


def on_curve(point: Point) -> bool:
    if point is None:
        return False
    x, y = point
    return 0 <= x < P and 0 <= y < P and (y * y - x * x * x - 7) % P == 0


def recover_public_key(r: int, s: int, recovery: int, digest: bytes) -> Point:
    """Recover Q from an ECDSA signature using Ethereum's recovery id 0/1."""
    if not (1 <= r < N and 1 <= s < N) or recovery not in (0, 1):
        return None
    y_squared = (r * r * r + 7) % P
    y = pow(y_squared, (P + 1) // 4, P)
    if (y % 2) != recovery:
        y = P - y
    r_point = (r, y)
    if not on_curve(r_point):
        return None
    z = int.from_bytes(digest, "big") % N
    candidate = add(multiply(s, r_point), multiply((-z) % N, G))
    if candidate is None:
        return None
    return multiply(_inv(r, N), candidate)


def verify(public_key: Point, r: int, s: int, digest: bytes) -> bool:
    if not on_curve(public_key) or not (1 <= r < N and 1 <= s < N):
        return False
    z = int.from_bytes(digest, "big") % N
    point = add(multiply(z * _inv(s, N) % N, G), multiply(r * _inv(s, N) % N, public_key))
    return point is not None and point[0] % N == r


def public_key_bytes(point: Point) -> bytes:
    """Uncompressed SEC1 encoding (0x04 || x || y)."""
    if point is None:
        raise ValueError("invalid public key")
    if not on_curve(point):
        raise ValueError("invalid public key")
    assert point is not None  # narrows the optional Point for the type checker
    return b"\x04" + point[0].to_bytes(32, "big") + point[1].to_bytes(32, "big")
