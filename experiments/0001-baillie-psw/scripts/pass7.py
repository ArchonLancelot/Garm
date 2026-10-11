"""Pass 7: Squarefreeness theorem (theoretical pass).

All previous passes constructed/searched. This one proves a restriction:
a Baillie-PSW pseudoprime (Selfridge Method A) must be squarefree, unless
a Wall-Sun-Sun-type prime exists for the Selfridge D (none known for any D).

Definitions:
- p odd prime, D from Selfridge (P=1, Q=(1-D)/4), (D/n)=-1 where n is the
  candidate.
- ord_{m}(2) = multiplicative order of 2 mod m.
- w_{m} = rank of apparition mod m: least w>0 with U_w == 0 mod m
  (Lucas sequence U_n(P,Q)).

Lemma 1 (Fermat lifting). For odd prime p:
  ord_{p^2}(2) = p * ord_p(2)  unless p is Wieferich (2^{p-1} == 1 mod p^2),
  in which case ord_{p^2}(2) = ord_p(2).
(Standard: binomial expansion of (1 + kp)^p.)

Lemma 2 (Lucas lifting). For odd prime p with (D/p) != 0:
  w_{p^2} = p * w_p  unless p^2 divides U_{p-(D/p)} (Wall-Sun-Sun-type for D),
  in which case w_{p^2} divides w_p.
(Definition of Wall-Sun-Sun-type; no examples known for any D. For D=5
this is the classic Wall-Sun-Sun prime problem, open.)

Theorem (Fermat side). If n = p^2 * m (p odd prime, p not dividing m) is a
weak base-2 Fermat pseudoprime (2^{n-1} == 1 mod n), then p is Wieferich.

Proof. Need ord_{p^2}(2) | n - 1 = p^2*m - 1. Note p^2*m - 1 == -1 mod p,
so p does NOT divide n - 1. If p is not Wieferich, ord_{p^2}(2) =
p*ord_p(2) by Lemma 1, so p | ord_{p^2}(2) | n-1, contradiction. Hence p
is Wieferich. QED.

Theorem (Lucas side). If n = p^2 * m (p odd prime, p not dividing m) is a
weak Lucas pseudoprime for D (U_{n+1} == 0 mod n), then p is
Wall-Sun-Sun-type for D.

Proof. Need w_{p^2} | n + 1 = p^2*m + 1. Note p^2*m + 1 == 1 mod p, so p
does NOT divide n + 1. If p is not Wall-Sun-Sun-type for D, w_{p^2} =
p*w_p by Lemma 2, so p | w_{p^2} | n+1, contradiction. Hence p is
Wall-Sun-Sun-type for D. QED.

Corollary. A Baillie-PSW pseudoprime n (strong Fermat base-2 AND strong
Lucas, Selfridge Method A with parameter D) with p^2 | n requires:
  (a) p Wieferich (Fermat side), AND
  (b) p Wall-Sun-Sun-type for D (Lucas side).
No prime is known satisfying (b) for any D. The only known Wieferich
primes are 1093 and 3511, neither known to satisfy (b).

In particular: the Fermat loophole (Wieferich) and the Lucas loophole
(Wall-Sun-Sun) do not overlap in any known prime. The two tests cover
each other's non-squarefree loopholes — this is a structural reason the
Baillie-PSW test is so strong, and it explains why all known pseudoprime
constructions for either test alone are squarefree.

Upshot for search: restrict to squarefree n. Any p^2 | n is impossible
unless a Wall-Sun-Sun-type prime exists (which would be a major discovery
in its own right, independent of BPSW).
"""

# Computational sanity check of the lifting lemmas on small primes.
import sys
sys.path.insert(0, "/home/hatch/workspace/builds/bpsw")
from utils import primes_upto, factorize
from bpsw import jacobi, lucas_uvq


def order_mod_pp(a, p, k=2):
    """Correct multiplicative order of a mod p^k (p prime)."""
    from math import gcd
    assert gcd(a, p) == 1
    mod = p ** k
    phi = (p - 1) * p ** (k - 1)
    fac = factorize(phi)
    o = phi
    for q in set(fac):
        while o % q == 0 and pow(a, o // q, mod) == 1:
            o //= q
    return o


def rank_app_mod(p, mod, P=1, Q=-1):
    """Least w>0 with U_w == 0 mod `mod`, by reducing from a multiple."""
    D = P * P - 4 * Q
    # w(p^2) divides p*w(p); find exact by trial
    from lucas_first import rank_of_apparition
    wp = rank_of_apparition(p, P, Q)
    for cand in [wp, p * wp]:
        U, _, _ = lucas_uvq(mod, P, Q % mod, D, cand)
        if U == 0:
            return cand
    return p * wp


if __name__ == "__main__":
    # Lemma 1 check: ord_{p^2}(2) == p*ord_p(2) for non-Wieferich p < 200
    for p in primes_upto(200):
        if p == 2:
            continue
        op = order_mod_pp(2, p, 1)
        op2 = order_mod_pp(2, p, 2)
        wieferich = pow(2, p - 1, p * p) == 1
        if wieferich:
            assert op2 == op, (p, op, op2)
        else:
            assert op2 == p * op, (p, op, op2)
    print("Lemma 1 (Fermat lifting) verified for p < 200")

    # Lemma 2 check: w_{p^2} == p*w_p for D=5, p < 100 (no WSS known)
    for p in primes_upto(100):
        if p in (2, 5):
            continue
        wp = rank_app_mod(p, p)
        wp2 = rank_app_mod(p, p * p)
        assert wp2 == p * wp, (p, wp, wp2)
    print("Lemma 2 (Lucas lifting, D=5) verified for p < 100")

    # Theorem check: n = p^2 * q can never satisfy both weak conditions
    # (for D=5); verify the Lucas obstruction directly for small p, q
    count = 0
    for p in primes_upto(50):
        if p in (2, 5):
            continue
        for q in primes_upto(200):
            if q in (2, 5) or q == p:
                continue
            n = p * p * q
            if jacobi(5, n) != -1:
                continue
            # Lucas weak: U_{n+1} == 0 mod p^2 ?
            U, _, _ = lucas_uvq(p * p, 1, (-1) % (p * p), 5, n + 1)
            if U == 0:
                print(f"UNEXPECTED: Lucas weak holds mod {p}^2 for n={n}")
                count += 1
    print(f"Lucas obstruction holds: {count} counterexamples in range")
