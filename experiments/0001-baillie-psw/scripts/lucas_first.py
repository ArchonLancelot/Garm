"""Pass 3: Lucas-first construction (mirror image of Pass 2).

For D=5 (Fibonacci), n=pq with (5/p)=+1, (5/q)=-1 so (5/n)=-1.
Rank of apparition: w(p)|p-1, w(q)|q+1.
Weak Lucas psp  <=>  w(p)|pq+1 and w(q)|pq+1
              <=>  w(p)|q+1   and w(q)|p-1   (derived in dossier)
So: pick p, compute w(p), sieve q=-1 mod w(p) with (5/q)=-1,
keep q with w(q)|p-1. Then n=pq is a weak Lucas psp; test strong + Fermat-2.
"""

import sys, math
sys.path.insert(0, "/home/hatch/workspace/builds/bpsw")
from utils import primes_upto, factorize, v2
from bpsw import jacobi, lucas_uvq, is_strong_fermat_psp2, is_strong_lucas_psp

def rank_of_apparition(p, P=1, Q=-1):
    """Least w>0 with U_w == 0 mod p. w | p-(D/p), D=P^2-4Q."""
    D = P*P - 4*Q
    leg = jacobi(D, p)
    assert leg != 0
    N = p - leg
    # w is the least divisor d of N with U_d == 0
    # find via prime factorization: start with N, try dividing out primes
    fac = factorize(N)
    w = N
    for prime in sorted(set(fac)):
        while w % prime == 0:
            cand = w // prime
            U, _, _ = lucas_uvq(p, P, Q % p, D, cand)
            if U == 0:
                w = cand
            else:
                break
    return w

if __name__ == "__main__":
    # validate rank_of_apparition on known values
    # Fibonacci entry point: p=11 -> 10, p=19 -> 18, p=31 -> 30
    assert rank_of_apparition(11) == 10, rank_of_apparition(11)
    assert rank_of_apparition(19) == 18, rank_of_apparition(19)
    assert rank_of_apparition(31) == 30, rank_of_apparition(31)
    print("rank_of_apparition OK")

    # small-scale: build weak Lucas psps n=pq, verify they pass weak Lucas
    # weak Lucas (D=5): U_{n+1} == 0 mod n
    def is_weak_lucas(n):
        if jacobi(5, n) != -1: return False
        U, _, _ = lucas_uvq(n, 1, (-1) % n, 5, n + 1)
        return U == 0

    found = []
    for p in primes_upto(500):
        if p == 2: continue
        if jacobi(5, p) != 1: continue
        wp = rank_of_apparition(p)
        # q ≡ -1 mod wp, (5/q) = -1, q prime, q != p
        for q in primes_upto(20000):
            if q == 2 or q == p or jacobi(5, q) != -1: continue
            if (q + 1) % wp != 0: continue
            wq = rank_of_apparition(q)
            if (p - 1) % wq != 0: continue
            n = p * q
            if not is_weak_lucas(n):
                print(f"CONSTRUCTION FAILURE: n={n}")
            else:
                found.append((p, q, n))
    print(f"weak Lucas pq tickets found: {len(found)} (expect >0)")
    for p, q, n in found[:5]:
        print(f"  n={n}={p}*{q}: weak-Lucas=True strong-Lucas={is_strong_lucas_psp(n)} fermat2={is_strong_fermat_psp2(n)}")
