"""Search utilities: sieving, Pollard-Rho factoring, multiplicative orders."""

import math, random

def primes_upto(n):
    sieve = bytearray(b"\x01") * (n + 1)
    sieve[:2] = b"\x00\x00"
    for i in range(2, int(n**0.5) + 1):
        if sieve[i]:
            sieve[i*i::i] = b"\x00" * ((n - i*i) // i + 1)
    return [i for i, v in enumerate(sieve) if v]

_SMALL_PRIMES = primes_upto(1000)

def _is_probable_prime(n):
    if n < 2: return False
    for p in _SMALL_PRIMES:
        if n % p == 0: return n == p
    d, s = n - 1, 0
    while d % 2 == 0: d //= 2; s += 1
    for a in (2, 3, 5, 7, 11, 13):
        if a % n == 0: continue
        x = pow(a, d, n)
        if x in (1, n - 1): continue
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1: break
        else:
            return False
    return True

def _pollard_rho(n):
    if n % 2 == 0: return 2
    while True:
        c = random.randrange(1, n)
        f = lambda x: (x * x + c) % n
        x = y = 2
        d = 1
        while d == 1:
            x = f(x); y = f(f(y))
            d = math.gcd(abs(x - y), n)
        if d != n:
            return d

def factorize(n):
    """Return sorted list of prime factors (with multiplicity)."""
    if n == 1: return []
    if _is_probable_prime(n): return [n]
    d = _pollard_rho(n)
    return sorted(factorize(d) + factorize(n // d))

def order_mod(a, n):
    """Multiplicative order of a mod n (assumes gcd(a,n)=1)."""
    from collections import Counter
    phi_factors = Counter(factorize(n - 1)) if _is_probable_prime(n) else None
    # general: factor n-1 via factorization (works for prime n; for our use n is prime)
    fac = factorize(n - 1)
    ord_n = n - 1
    for p in set(fac):
        while ord_n % p == 0 and pow(a, ord_n // p, n) == 1:
            ord_n //= p
    return ord_n

def v2(n):
    k = 0
    while n % 2 == 0:
        n //= 2; k += 1
    return k
