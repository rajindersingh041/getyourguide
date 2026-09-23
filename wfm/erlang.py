"""Erlang B / C and the staffing solver.

Implemented from first principles so every step is auditable, with a numerically
stable recursion for Erlang B (the factorial form overflows above ~170 agents).
"""
from __future__ import annotations
import math


def erlang_b(n: int, a: float) -> float:
    """Blocking probability, M/M/n/n. Recursive form:  B(0,a)=1,
    B(k,a) = a*B(k-1,a) / (k + a*B(k-1,a)).  Overflow-free."""
    if a <= 0:
        return 0.0
    b = 1.0
    for k in range(1, n + 1):
        b = (a * b) / (k + a * b)
    return b


def erlang_c(n: int, a: float) -> float:
    """Probability an arriving contact must wait (M/M/n, infinite queue).
    C = B / (1 - rho*(1-B)) with rho = a/n.  Requires n > a for stability."""
    if a <= 0:
        return 0.0
    if n <= a:
        return 1.0
    b = erlang_b(n, a)
    return b / (1.0 - (a / n) * (1.0 - b))


def service_level(n: int, a: float, target_seconds: float, aht_seconds: float) -> float:
    """P(wait <= t) = 1 - C * exp(-(n - a) * t / AHT)."""
    if a <= 0:
        return 1.0
    if n <= a:
        return 0.0
    return 1.0 - erlang_c(n, a) * math.exp(-(n - a) * target_seconds / aht_seconds)


def avg_speed_of_answer(n: int, a: float, aht_seconds: float) -> float:
    """ASA = C * AHT / (n - a)."""
    if a <= 0:
        return 0.0
    if n <= a:
        return math.inf
    return erlang_c(n, a) * aht_seconds / (n - a)


def agents_required(a: float, target: float, target_seconds: float,
                    aht_seconds: float, max_agents: int = 100_000) -> int:
    """Smallest integer n with service_level(n) >= target.

    Service level is monotonically increasing in n, so a linear scan from
    ceil(a) is exact. Guard rails: a=0 -> 0 agents."""
    if a <= 0:
        return 0
    n = max(1, math.ceil(a))
    while n < max_agents:
        if service_level(n, a, target_seconds, aht_seconds) >= target:
            return n
        n += 1
    raise RuntimeError(f"no solution below {max_agents} agents for a={a}")


def traffic_intensity(contacts: float, aht_seconds: float, period_hours: float) -> float:
    """Offered load in erlangs = contact-hours of work per hour of clock time."""
    return contacts * aht_seconds / 3600.0 / period_hours


def solve_queue(contacts: float, aht_seconds: float, period_hours: float,
                target: float, target_seconds: float,
                concurrency: float = 1.0) -> dict:
    """Full result for one real-time queue."""
    a = traffic_intensity(contacts, aht_seconds, period_hours)
    n = agents_required(a, target, target_seconds, aht_seconds)
    return {
        "contacts": contacts,
        "aht_seconds": aht_seconds,
        "erlangs": a,
        "seats_raw": n,
        "seats": n / concurrency,
        "concurrency": concurrency,
        "occupancy": (a / n) if n else 0.0,
        "service_level": service_level(n, a, target_seconds, aht_seconds),
        "asa_seconds": avg_speed_of_answer(n, a, aht_seconds),
        "workload_hours": contacts * aht_seconds / 3600.0,
    }


# ---- normal inverse CDF (no scipy in this environment) ----
def norm_ppf(p: float) -> float:
    """Acklam's rational approximation to the inverse standard normal CDF.
    |error| < 1.15e-9 over the whole open interval."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
