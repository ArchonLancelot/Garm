"""Pass 6: three-prime weak two-sided search.

Pass 5 showed per-prime two-sidedness for n=pq is over-constrained to
emptiness. With n=pqr there are more CRT degrees of freedom: the six
divisibilities (ord and omega for each of three primes) have more room
to be satisfied simultaneously without forcing any single prime to be
pathologically smooth.

Weak conditions for n=pqr, D=5:
  ord_s(2) | n-1  and  w(s) | n+1  for each s in {p,q,r}
  plus (5/n) = -1.
Survivors get the full strong tests.
"""

import sys
from itertools import combinations
sys.path.insert(0, "/home/hatch/workspace/builds/bpsw")
from utils import primes_upto, order_mod
from lucas_first import rank_of_apparition
from bpsw import jacobi, is_strong_fermat_psp2, is_strong_lucas_psp


def main(p_max=150):
    primes = [p for p in primes_upto(p_max) if p not in (2, 5)]
    info = {}
    for p in primes:
        info[p] = (order_mod(2, p), rank_of_apparition(p))
    print(f"precomputed {len(info)} primes", flush=True)

    survivors = []
    n_triples = 0
    for p, q, r in combinations(primes, 3):
        n = p * q * r
        if jacobi(5, n) != -1:
            continue
        n_triples += 1
        ok = True
        for s in (p, q, r):
            o, w = info[s]
            if (n - 1) % o != 0 or (n + 1) % w != 0:
                ok = False
                break
        if ok:
            survivors.append((p, q, r, n))
    print(f"checked {n_triples} sign-compatible triples, "
          f"{len(survivors)} weak two-sided survivors", flush=True)

    for p, q, r, n in survivors:
        f2 = is_strong_fermat_psp2(n)
        sl = is_strong_lucas_psp(n)
        print(f"n={n}={p}*{q}*{r}: fermat2={f2} strong-lucas={sl}", flush=True)
        if f2 and sl:
            print(f"*** JACKPOT: {p} {q} {r}")
    return survivors


if __name__ == "__main__":
    bound = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    main(bound)
