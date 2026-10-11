"""Pass 8 (revised): Pomerance's construction via divisor enumeration.

Key insight: instead of sieving [T, T^k], CONSTRUCT p from divisors.
We need d2 | Q3, d1 = 2*d2 - 1 | Q1, with p = 4*d2 - 1 prime.

  (p-1)/2 = d1 must be squarefree, factors only from allow1 (q<T, q=1 mod 4)
  (p+1)/4 = d2 must be squarefree, factors only from allow3 (q<T, q=3 mod 4)
  p = 4*d2 - 1 = 2*d1 + 1  =>  d1 = 2*d2 - 1. Consistent.

Enumerate squarefree d2 | Q3, check d1 = 2*d2-1 | Q1 and squarefree,
then p prime, p=3 mod 8, (5/p)=-1. Then subset-search as before.
"""

import sys
from itertools import combinations
sys.path.insert(0, "/home/hatch/workspace/builds/bpsw")
from utils import primes_upto, _is_probable_prime
from bpsw import jacobi, is_strong_fermat_psp2, is_strong_lucas_psp


def squarefree_divisors(primes):
    """All squarefree divisors (products of subsets) of prod(primes)."""
    divs = [1]
    for q in primes:
        divs += [d * q for d in divs]
    return divs


def pomerance_primes_divisor(T):
    primes_T = [q for q in primes_upto(T - 1)]
    allow1 = sorted(q for q in primes_T if q % 4 == 1)
    allow3 = sorted(q for q in primes_T if q % 4 == 3)
    Q1, Q3 = 1, 1
    for q in allow1:
        Q1 *= q
    for q in allow3:
        Q3 *= q
    cands = []
    for d2 in squarefree_divisors(allow3):
        if d2 == 1:
            continue
        d1 = 2 * d2 - 1
        # d1 | Q1 and squarefree?
        if Q1 % d1 != 0:
            continue
        # squarefree check on d1: no repeated factor (d1 | Q1 squarefree => ok)
        p = 4 * d2 - 1
        if p % 8 != 3:
            continue
        if not _is_probable_prime(p):
            continue
        if jacobi(5, p) != -1:
            continue
        # verify (p-1)/2 == d1 and (p+1)/4 == d2 (sanity)
        assert (p - 1) // 2 == d1 and (p + 1) // 4 == d2
        cands.append(p)
    return sorted(set(cands)), Q1, Q3


def main(T=100, max_ell=9):
    cands, Q1, Q3 = pomerance_primes_divisor(T)
    print(f"T={T}: {len(cands)} candidate primes", flush=True)
    if not cands:
        return
    print(f"candidates: {cands}", flush=True)
    res = [(p % Q1, p % Q3) for p in cands]
    for ell in range(1, max_ell + 1, 2):
        print(f"trying subsets of size {ell}...", flush=True)
        count = 0
        for idx in combinations(range(len(cands)), ell):
            r1 = r3 = 1
            for i in idx:
                r1 = (r1 * res[i][0]) % Q1
                r3 = (r3 * res[i][1]) % Q3
            if r1 == 1 and r3 == Q3 - 1:
                n = 1
                for i in idx:
                    n *= cands[i]
                count += 1
                f2 = is_strong_fermat_psp2(n)
                sl = is_strong_lucas_psp(n)
                print(f"  n={n} ({n.bit_length()}b) from "
                      f"{[cands[i] for i in idx]}: fermat2={f2} lucas={sl}",
                      flush=True)
                if f2 and sl:
                    print(f"*** JACKPOT: {[cands[i] for i in idx]}")
                    return
        print(f"  size {ell}: {count} residue-matching, 0 jackpots", flush=True)


if __name__ == "__main__":
    T = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    main(T)
