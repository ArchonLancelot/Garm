"""Pass 2: factor 2^E-1 (E from p's order) to harvest keeper q's directly.

For prime p with ord_p(2) = 2^{r+1}*m: keepers q are prime divisors of
2^E-1 (E = 2^{r+1}*ODD_p) with v2(ord_q(2)) = r+1. Factor 2^E-1, take large
prime factors q > 2^64/p, filter, form n = p*q (proven strong base-2 psp),
Lucas-test. No sieving for needles.
"""

import sys, math, time, random
sys.path.insert(0, "/home/hatch/workspace/builds/bpsw")
from utils import primes_upto, order_mod, v2, _is_probable_prime, _pollard_rho
from bpsw import is_strong_fermat_psp2, is_strong_lucas_psp, jacobi

TWO64 = 1 << 64


def factor_partial(n, deadline):
    """Return (prime_factors, cofactor). Time-boxed by deadline (epoch secs)."""
    factors = []
    def _factor(m):
        if time.time() > deadline:
            return [m]  # give up: return as-is (may be composite)
        if m == 1:
            return []
        if _is_probable_prime(m):
            return [m]
        d = _pollard_rho(m)
        return _factor(d) + _factor(m // d)
    parts = _factor(n)
    primes, cof = [], 1
    for x in parts:
        if _is_probable_prime(x):
            primes.append(x)
        else:
            cof *= x
    return primes, cof


def keepers_from_E(p, E, r1, m, budget=60):
    """Factor 2^E-1 (budget secs), yield keeper q's. Returns (keepers, stats)."""
    N = (1 << E) - 1
    t0 = time.time()
    primes, cof = factor_partial(N, t0 + budget)
    # the cofactor itself may be a prime keeper (do NOT ignore it)
    cands = list(primes)
    if cof > 1 and _is_probable_prime(cof):
        cands.append(cof)
    stats = {"E": E, "time": time.time() - t0,
             "cofactor_bits": cof.bit_length() if cof > 1 else 0,
             "cofactor_prime": cof > 1 and _is_probable_prime(cof)}
    keepers = []
    for q in cands:
        if q <= TWO64 // p:
            continue
        if q % m != 1:
            continue
        if pow(2, E // 2, q) == 1:
            continue  # v2(ord_q(2)) < r+1
        s = v2(p * q - 1)
        if r1 - 1 >= s:
            continue
        keepers.append(q)
    # de-duplicate (cofactor may repeat a prime)
    keepers = sorted(set(keepers))
    return keepers, stats


if __name__ == "__main__":
    # feasibility: 4 small p's, see if 2^E-1 yields large prime factors
    for p in [101, 257, 1009, 1531]:
        op = order_mod(2, p)
        r1 = v2(op); m = op >> r1
        tmp = p - 1; ODD = tmp >> v2(tmp)
        E = (1 << r1) * ODD
        print(f"p={p} ord=2^{r1}*{m} E={E} (2^E-1 has {E*0.301:.0f} digits)")
        keepers, stats = keepers_from_E(p, E, r1, m, budget=30)
        print(f"  factored in {stats['time']:.1f}s, cofactor bits={stats['cofactor_bits']}, keepers={keepers}")
