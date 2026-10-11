"""Pass 2 full run: factor 2^E-1 for many p, harvest keepers, Lucas-test all.

Logs to transcript.log. Each keeper n=p*q is a PROVEN strong base-2 psp > 2^64.
Lucas-tests every keeper (no (5/n) filter -- the filter idea was refuted).
"""
import sys, time
sys.path.insert(0, "/home/hatch/workspace/builds/bpsw")
from factor_search import keepers_from_E, TWO64
from utils import primes_upto, order_mod, v2
from bpsw import is_strong_fermat_psp2, is_strong_lucas_psp, jacobi

def oddpart(n):
    return n >> v2(n)

def main():
    log = open("/home/hatch/workspace/builds/bpsw/transcript.log", "a")
    def say(s):
        print(s, flush=True)
        log.write(s + "\n"); log.flush()

    say("=== PASS 2 RUN started " + time.strftime("%Y-%m-%d %H:%M:%S"))
    total_p = total_E_ok = total_keepers = total_lucas = 0
    lucas_passes = []
    proof_failures = 0
    t_start = time.time()

    for p in primes_upto(3000):
        if p < 50: continue
        total_p += 1
        op = order_mod(2, p)
        r1 = v2(op); m = op >> r1
        if r1 < 1: continue
        ODD = oddpart(p - 1)
        E = (1 << r1) * ODD
        if E < 60 or E > 800: continue
        total_E_ok += 1
        keepers, stats = keepers_from_E(p, E, r1, m, budget=40)
        if keepers:
            say(f"p={p} E={E}: {len(keepers)} keeper(s) q={[str(q)[:12]+'...' for q in keepers]}")
        for q in keepers:
            total_keepers += 1
            n = p * q
            if not is_strong_fermat_psp2(n):
                proof_failures += 1
                say(f"  PROOF FAILURE: n={n}")
                continue
            j5 = jacobi(5, n)
            total_lucas += 1
            if is_strong_lucas_psp(n):
                lucas_passes.append((p, q, n))
                say(f"  *** LUCAS PASS: n={n} (p={p}, q={q})")
            # else: expected; just count
    say(f"=== PASS 2 done in {time.time()-t_start:.0f}s")
    say(f"p tried: {total_p}, E in range: {total_E_ok}, keepers: {total_keepers}, "
        f"lucas-tested: {total_lucas}, proof failures: {proof_failures}, LUCAS PASSES: {len(lucas_passes)}")
    for p, q, n in lucas_passes:
        say(f"JACKPOT factor1={p} factor2={q}")
    log.close()

if __name__ == "__main__":
    main()
