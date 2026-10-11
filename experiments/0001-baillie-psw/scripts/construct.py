"""Construct strong base-2 pseudoprimes n = p*q with proof, then Lucas-test them.

Construction S(r, p): p prime, ord_p(2) = 2^{r+1} * m (m odd). Find prime
q = 1 mod 2^{r+1}*m with v2(ord_q(2)) = r+1 and oddpart(ord_q(2)) | m.
Then n = p*q satisfies 2^{d*2^r} = -1 mod p and mod q (d = (n-1)/2^s, r < s),
so n is a strong Fermat pseudoprime to base 2 -- by construction, no luck.
Each keeper is then put through the strong Lucas test.
"""

import sys, math, time
sys.path.insert(0, "/home/hatch/workspace/builds/bpsw")
from utils import primes_upto, factorize, order_mod, v2, _is_probable_prime
from bpsw import is_strong_fermat_psp2, is_strong_lucas_psp


def segmented_ap_primes(lo, hi, mod, rem):
    """Primes q in [lo, hi] with q % mod == rem. Segmented sieve."""
    assert rem < mod
    # sieve only numbers = rem mod mod
    n_terms = (hi - rem) // mod - max(0, (lo - 1 - rem) // mod)
    # index i <-> value v = first + i*mod
    first = rem + mod * ((lo - rem + mod - 1) // mod)
    if first < lo:
        first += mod
    count = (hi - first) // mod + 1 if first <= hi else 0
    is_p = bytearray(b"\x01") * max(count, 0)
    for sp in primes_upto(int(hi ** 0.5) + 1):
        if sp == 2 and mod % 2 == 0:
            continue
        # find first multiple of sp in the progression >= max(sp*sp, first)
        # multiples: v = rem + i*mod = sp * k  =>  i*mod = sp*k - rem
        start = max(sp * sp, first)
        # smallest i with rem + i*mod >= start and sp | (rem + i*mod)
        # i = i0 + t*(sp/g), g = gcd(mod, sp)
        g = math.gcd(mod, sp)
        if (rem % g) != 0:
            continue  # sp never divides the progression
        # solve i*mod' = -rem' (mod sp'), mod'=mod/g, sp'=sp/g, rem'=rem/g
        mod_r, sp_r, rem_r = mod // g, sp // g, rem // g
        inv = pow(mod_r, -1, sp_r)
        i0 = ((-rem_r * inv) % sp_r)
        v0 = rem + i0 * mod
        if v0 < start:
            step = sp_r * mod
            skip = (start - v0 + step - 1) // step
            v0 += skip * step
            i0 += skip * sp_r
        for v in range(v0, hi + 1, sp_r * mod):
            if v == sp:
                continue
            idx = (v - first) // mod
            if 0 <= idx < count:
                is_p[idx] = 0
    out = []
    for i in range(count):
        val = first + i * mod
        if is_p[i] and val >= 2:
            out.append(val)
    return out


def keepers_for_p(p, q_lo, q_hi, verbose=False):
    """Yield (q, n) keepers for prime p. n = p*q is a proven strong psp2."""
    op = order_mod(2, p)
    r1 = v2(op)
    assert r1 >= 1
    r = r1 - 1
    m = op >> r1
    M = (1 << r1) * m
    qs = segmented_ap_primes(q_lo, q_hi, M, 1 % M)
    kept = []
    for q in qs:
        if q == p:
            continue
        oq = order_mod(2, q)
        if v2(oq) != r1:
            continue
        mq = oq >> r1
        if m % mq != 0:
            continue
        n = p * q
        kept.append((q, n))
    return kept, dict(p=p, r=r, m=m, M=M, nq=len(qs))


if __name__ == "__main__":
    # small-scale validation: every keeper must pass strong-Fermat-2 (proof check)
    p = 1009
    t0 = time.time()
    kept, info = keepers_for_p(p, 10_000, 400_000)
    print("info:", info, f"[{time.time()-t0:.1f}s]")
    bad = 0
    lucas_hits = []
    for q, n in kept:
        if not is_strong_fermat_psp2(n):
            bad += 1
            print("PROOF FAILURE:", n)
        if is_strong_lucas_psp(n):
            lucas_hits.append(n)
    print(f"keepers: {len(kept)}, proof failures: {bad}, Lucas passes: {lucas_hits} (expect none < 2^64)")
