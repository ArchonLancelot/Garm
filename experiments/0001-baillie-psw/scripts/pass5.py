"""Pass 5: two-sided per-prime search.

The injected dossiers' terminal advice: "the next inversion is two-sided
construction." Pomerance's subset-product is intractable, but two-sidedness
is enforceable at the PRIME level: find primes p, q such that EACH prime
simultaneously satisfies the compatibility conditions for BOTH tests.

For n = pq (D=5 for Lucas):
  Fermat (weak): ord_p(2) | pq-1  and  ord_q(2) | pq-1
  Lucas  (weak): w(p) | pq+1      and  w(q) | pq+1     [w = rank of apparition]
  plus (5/p)(5/q) = -1 so Selfridge can pick D=5.

This is the first pass that enforces both tests during construction
instead of constructing for one side and hoping for the other.
"""

import sys
sys.path.insert(0, "/home/hatch/workspace/builds/bpsw")
from utils import primes_upto, order_mod
from lucas_first import rank_of_apparition
from bpsw import jacobi, is_strong_fermat_psp2, is_strong_lucas_psp


def main(p_max=2000):
    primes = [p for p in primes_upto(p_max) if p not in (2, 5)]
    # precompute ord_p(2) and w(p) for D=5
    info = {}
    for p in primes:
        info[p] = (order_mod(2, p), rank_of_apparition(p), jacobi(5, p))
    print(f"precomputed {len(info)} primes", flush=True)

    survivors = []
    n_pairs = 0
    for i, p in enumerate(primes):
        op, wp, lp = info[p]
        for q in primes[i + 1:]:
            oq, wq, lq = info[q]
            if lp * lq != -1:
                continue
            n = p * q
            n_pairs += 1
            # two-sided per-prime conditions
            if (n - 1) % op != 0:
                continue
            if (n + 1) % wp != 0:
                continue
            if (n - 1) % oq != 0:
                continue
            if (n + 1) % wq != 0:
                continue
            survivors.append((p, q, n))
    print(f"checked {n_pairs} sign-compatible pairs, "
          f"{len(survivors)} two-sided survivors", flush=True)

    for p, q, n in survivors:
        f2 = is_strong_fermat_psp2(n)
        sl = is_strong_lucas_psp(n)
        print(f"n={n}={p}*{q}: fermat2={f2} strong-lucas={sl}", flush=True)
        if f2 and sl:
            print(f"*** JACKPOT: factor1={p} factor2={q}")
    return survivors


if __name__ == "__main__":
    bound = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    main(bound)
