"""Baillie-PSW primality test, exactly per the challenge spec. Stdlib only.

Component 1: strong Fermat pseudoprime to base 2 (Miller-Rabin base 2).
Component 2: strong Lucas pseudoprime, Selfridge Method A parameters.
"""

from __future__ import annotations

import math


def jacobi(a: int, n: int) -> int:
    """Jacobi symbol (a/n) for odd positive n."""
    assert n > 0 and n & 1
    a %= n
    result = 1
    while a:
        while a & 1 == 0:
            a >>= 1
            if n & 7 in (3, 5):
                result = -result
        a, n = n, a
        if (a & 3) == 3 and (n & 3) == 3:
            result = -result
        a %= n
    return result if n == 1 else 0


def is_strong_fermat_psp2(n: int) -> bool:
    """Miller-Rabin base-2 probable prime. n odd > 1."""
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    x = pow(2, d, n)
    if x == 1 or x == n - 1:
        return True
    for _ in range(s - 1):
        x = (x * x) % n
        if x == n - 1:
            return True
    return False


def selfridge_D(n: int):
    """First D in 5,-7,9,-11,... with Jacobi (D/n) == -1.

    Returns None if a D shares a *proper* divisor with n (then n is
    definitively composite). If n divides D (possible only for tiny n),
    that D is inconclusive and skipped.
    """
    D = 5
    while True:
        g = math.gcd(D, n)
        if g == 1:
            if jacobi(D, n) == -1:
                return D
        elif g != n:
            return None  # 1 < g < n: nontrivial factor, n composite
        D = -(D + 2) if D > 0 else -(D - 2)


def _lucas_double(U: int, V: int, Qk: int, n: int):
    """(U_{2k}, V_{2k}, Q^{2k}) from (U_k, V_k, Q^k), mod n."""
    return (U * V) % n, (V * V - 2 * Qk) % n, (Qk * Qk) % n


def lucas_uvq(n: int, P: int, Q: int, D: int, k: int):
    """(U_k, V_k, Q^k) mod n via binary doubling. n odd."""
    inv2 = (n + 1) // 2
    U, V, Qk = 0, 2 % n, 1 % n
    for bit in bin(k)[2:]:
        U, V, Qk = _lucas_double(U, V, Qk, n)
        if bit == "1":
            U, V = ((P * U + V) * inv2) % n, ((D * U + P * V) * inv2) % n
            Qk = (Qk * Q) % n
    return U, V, Qk


def is_strong_lucas_psp(n: int) -> bool:
    """Strong Lucas probable prime, Selfridge Method A. n odd > 1."""
    D = selfridge_D(n)
    if D is None:
        return False
    P, Q = 1, (1 - D) // 4
    e = n + 1
    t = 0
    while e % 2 == 0:
        e //= 2
        t += 1
    U, V, Qk = lucas_uvq(n, P, Q, D, e)
    if U == 0:
        return True
    for _ in range(t):
        if V == 0:
            return True
        U, V, Qk = _lucas_double(U, V, Qk, n)
    return False


def is_bpsw_probable_prime(n: int) -> bool:
    """True iff n passes both Baillie-PSW component tests."""
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    return is_strong_fermat_psp2(n) and is_strong_lucas_psp(n)
