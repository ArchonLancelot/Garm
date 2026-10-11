"""Pass 8: Pomerance's heuristic construction (from Baillie-Fiori-Wagstaff 2021).

The literature's own attack — the two-sided construction my Pass 5 dossier
pointed at, now with the actual details:

  Primes p in [T, T^k] with:
    (1) p = 3 mod 8 and (5/p) = -1
    (2) (p-1)/2 squarefree, prime factors q < T with q = 1 mod 4
    (3) (p+1)/4 squarefree, prime factors q < T with q = 3 mod 4
  Q1 = prod{q < T : q = 1 mod 4}, Q3 = prod{q < T : q = 3 mod 4}
  n = product of ODD count of such primes with n = 1 mod Q1, n = -1 mod Q3
  => n is strong base-2 psp AND Lucas/v-psp (heuristic; BFW say the
     computer search is "very slow" — let's see how slow).

This is the first pass with a heuristic existence guarantee behind it.
"""

import sys
from itertools import combinations
sys.path.insert(0, "/home/hatch/workspace/builds/bpsw")
from utils import primes_upto, _is_probable_prime
from bpsw import jacobi, is_strong_fermat_psp2, is_strong_lucas_psp


def squarefree_with_factors_from(n, allowed):
    """n squarefree and all prime factors in `allowed` set?"""
    if n <= 0:
        return False
    tmp = n
    for q in sorted(allowed):
        if tmp % q == 0:
            tmp //= q
            if tmp % q == 0:
                return False  # not squarefree
    return tmp == 1


def pomerance_primes(T, k):
    """Find primes p in [T, T^k] satisfying Pomerance's 4 conditions."""
    primes_T = [q for q in primes_upto(T - 1)]
    allow1 = {q for q in primes_T if q % 4 == 1}
    allow3 = {q for q in primes_T if q % 4 == 3}
    cands = []
    for p in primes_upto(T ** k):
        if p < T:
            continue
        if p % 8 != 3:
            continue
        if jacobi(5, p) != -1:
            continue
        if (p - 1) % 2 != 0:
            continue
        if not squarefree_with_factors_from((p - 1) // 2, allow1):
            continue
        if (p + 1) % 4 != 0:
            continue
        if not squarefree_with_factors_from((p + 1) // 4, allow3):
            continue
        cands.append(p)
    Q1, Q3 = 1, 1
    for q in allow1:
        Q1 *= q
    for q in allow3:
        Q3 *= q
    return cands, Q1, Q3


def main(T=30, k=2, max_ell=7):
    cands, Q1, Q3 = pomerance_primes(T, k)
    print(f"T={T} k={k}: {len(cands)} candidate primes, Q1={Q1} Q3={Q3}",
          flush=True)
    if not cands:
        return
    print(f"candidates: {cands[:20]}{'...' if len(cands)>20 else ''}", flush=True)
    mod = Q1 * Q3
    # residues of each candidate mod Q1, mod Q3
    res = [(p % Q1, p % Q3) for p in cands]
    # odd-sized subsets, by increasing size
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
                print(f"  n={n} ({n.bit_length()} bits) from "
                      f"{[cands[i] for i in idx]}: fermat2={f2} lucas={sl}",
                      flush=True)
                if f2 and sl:
                    print(f"*** JACKPOT: {[cands[i] for i in idx]}")
                    return
        print(f"  size {ell}: {count} residue-matching subsets, 0 jackpots",
              flush=True)


if __name__ == "__main__":
    T = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    main(T, k)
