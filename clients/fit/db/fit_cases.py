import os
import math

_CASES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "data", "cases.txt"
)

NON_TRIVIAL_PROVEN = frozenset({2, 3, 5, 6, 7, 8, 10, 13, 14, 15, 22, 24, 33, 35, 46})

_OPTIMAL_CAP = 2048
_FOUND_CAP = 2048


def get_optimal_n():
    optimal = set()
    k = 1
    while k * k <= _OPTIMAL_CAP:
        optimal.add(k * k)
        k += 1
    optimal |= {n for n in NON_TRIVIAL_PROVEN if n <= _OPTIMAL_CAP}
    k = 2
    while k * k - 2 <= _OPTIMAL_CAP:
        optimal.add(k * k - 1)
        optimal.add(k * k - 2)
        k += 1
    return optimal


def load_found_from_file(path=None):
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
    optimal_n = get_optimal_n()
    found_in_file = load_found_from_file(cases_path)
    all_n_from_db = set(db_by_n)
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
