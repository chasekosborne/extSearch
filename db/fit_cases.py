"""
Classify Fit (square packing) cases for the explore page.

Green (known optimal) = three sources only:
  1. Trivial: n = k² (pack in k×k grid → obviously optimal).
  2. Non-trivial proven: n ∈ {2, 3, 5, 6, 7, 8, 10, 13, 14, 15, 22, 24, 33, 35, 46} (Friedman, MathWorld, etc.).
  3. Nagamochi (2005): s(k²−1) = s(k²−2) = k — so n = k²−1 or k²−2 for k ≥ 2.

Grey (interesting to prove) = any other n we show (found but not proved).
"""
import os
import math

# Default path for optional cases file (n-f = found, shown as grey)
_CASES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "cases.txt"
)

# Non-trivial proven cases (famous hard proofs)
NON_TRIVIAL_PROVEN = frozenset({2, 3, 5, 6, 7, 8, 10, 13, 14, 15, 22, 24, 33, 35, 46})

# Max n for derived optimal (perfect squares and Nagamochi); reference uses n ≤ 324
_OPTIMAL_CAP = 2048

# Max n to show in "best found" row — show all n in [1, FOUND_CAP] that aren't optimal
_FOUND_CAP = 2048


def get_optimal_n():
    """
    Set of n that are known optimal (green chips).
    Uses only the three rules: trivial (perfect squares), non-trivial proven list, Nagamochi.
    """
    optimal = set()
    # 1) Trivial: n = k²
    k = 1
    while k * k <= _OPTIMAL_CAP:
        optimal.add(k * k)
        k += 1
    # 2) Non-trivial proven
    optimal |= {n for n in NON_TRIVIAL_PROVEN if n <= _OPTIMAL_CAP}
    # 3) Nagamochi (2005): n = k²−1 or k²−2 for k ≥ 2
    k = 2
    while k * k - 2 <= _OPTIMAL_CAP:
        optimal.add(k * k - 1)
        optimal.add(k * k - 2)
        k += 1
    return optimal


def load_found_from_file(path=None):
    """Set of n listed as found (f) in cases file — shown as grey."""
    path = path or _CASES_PATH
    found = set()
    if os.path.isfile(path):
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("-")
                if len(parts) != 2:
                    continue
                try:
                    n = int(parts[0].strip())
                except ValueError:
                    continue
                if parts[1].strip().lower() == "f":
                    found.add(n)
    return found


def build_explore_groups(db_by_n, cases_path=None):
    """
    Build two lists for the explore page:
    - optimal: green chips (trivial + non-trivial proven + Nagamochi only).
    - found: grey chips (interesting to prove) = all n in [1, FOUND_CAP] not optimal,
      plus any n from cases.txt or DB outside that range.
    """
    optimal_n = get_optimal_n()
    found_in_file = load_found_from_file(cases_path)
    all_n_from_db = set(db_by_n)
    # Grey = full range 1..FOUND_CAP minus optimal, plus any extra from file or DB
    all_n_in_range = set(range(1, _FOUND_CAP + 1))
    found_n = (all_n_in_range | found_in_file | all_n_from_db) - optimal_n

    optimal_list = [
        {"square_count": n, "submission_count": db_by_n.get(n, 0), "status": "optimal"}
        for n in sorted(optimal_n)
    ]
    found_list = [
        {"square_count": n, "submission_count": db_by_n.get(n, 0)}
        for n in sorted(found_n)
    ]
    return optimal_list, found_list
