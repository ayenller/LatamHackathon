"""Acceptance script — checks each level in turn.

    python verify.py            # all (R1-R3 automatic, R4 printed for human review)
    python verify.py --no-llm   # R1-R3 only, no model calls
"""
import sys

from config import EMBED_MODEL, get_connection

PASS, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"
results = []


def check(level, name, ok, detail=""):
    results.append((level, ok))
    print(f"  [{PASS if ok else FAIL}] {level:<4} {name}")
    if detail:
        print(f"         {detail}")


def main(use_llm=True):
    conn = get_connection()
    cur = conn.cursor()

    print("\n=== PREREQUISITES ===")
    try:
        cur.execute(f'SELECT EMBED_TEXT("{EMBED_MODEL}", "hello")')
        dims = str(cur.fetchone()[0]).count(",") + 1
        check("PRE ", f"EMBED_TEXT available ({dims} dims)", dims == 1024)
    except Exception as exc:
        check("PRE ", "EMBED_TEXT available", False, str(exc)[:80])
        return
    cur.execute("SELECT COUNT(*) FROM airport_semantic")
    n = cur.fetchone()[0]
    check("PRE ", f"index complete ({n} rows)", n == 2862,
          "" if n == 2862 else "expected 2862 — rebuild the index")

    from app import resolve_place, search_similar

    print("\n=== BASELINE structured query ===")
    o, _, _ = resolve_place(conn, "GRU")
    d, _, _ = resolve_place(conn, "Carolina")
    ph = lambda x: ",".join(["%s"] * len(x))
    cur.execute(f"""SELECT f.flightno FROM flight f
                    WHERE f.`from` IN ({ph(o)}) AND f.`to` IN ({ph(d)})
                      AND DATE(f.departure)='2015-06-07'""", o + d)
    rows = [r[0] for r in cur.fetchall()]
    check("BASE", "Sunday GRU -> Carolina", rows == ["TU9679"], f"returned {rows}")

    print("\n=== R1 semantic search ===")
    for probe in ("Santos Dumont", "Galeao"):
        top = search_similar(conn, probe, k=1)[0]
        check("R1", f"{probe!r} -> RIO DE JANEIRO", top[0] == "RIO DE JANEIRO",
              f"got {top[0]}, distance {top[3]:.3f}")

    print("\n=== R2 hybrid search ===")
    q = "main airport serving Rio de Janeiro"
    plain = [r[2] for r in search_similar(conn, q, k=3)]
    hybrid = [r[2] for r in search_similar(conn, q, lexical="INTL", k=3)]
    check("R2", "pure vector top-3 excludes GIG", "GIG" not in plain, f"vector {plain}")
    check("R2", "hybrid top-3 includes GIG", "GIG" in hybrid, f"hybrid {hybrid}")

    print("\n=== R3 layered routing ===")
    for probe in ("GRU", "CGH", "SBGR"):
        ids, label, how = resolve_place(conn, probe)
        ok = label.startswith("SAO PAULO") and how != "vector"
        check("R3", f"{probe!r} -> SAO PAULO (non-vector path)", ok, f"got {label}, via {how}")

    if not use_llm:
        summary()
        return

    from app import answer

    print("\n=== R4 semantic answer / constraint check (human review) ===")
    msg = "Sunday from Codo to Rozas, arrive before 18:00"
    _, res, text = answer(conn, msg)
    print(f"  input : {msg}")
    print(f"  search: {res['note']}, {len(res['rows'])} row(s)")
    print(f"  answer: {text}")
    print("  Check: names CA6175, and states it arrives 19:18 — past the 18:00 limit")

    print("\n=== R4 semantic answer / refusal to invent (human review) ===")
    msg = "Sunday from Sao Paulo to Rio"
    _, res, text = answer(conn, msg)
    print(f"  input : {msg}")
    print(f"  search: {res['note']}, {len(res['rows'])} row(s)")
    print(f"  answer: {text}")
    print("  Check: 1) says the route does not exist  2) lists real reachable destinations")
    print("         3) invents no flight number or connection  4) answers in English")

    summary()


def summary():
    print("\n" + "=" * 56)
    by = {}
    for level, ok in results:
        by.setdefault(level, []).append(ok)
    for level, oks in by.items():
        print(f"  {level:<4} {sum(oks)}/{len(oks)}")
    total_ok = sum(1 for _, ok in results if ok)
    print(f"  automatic checks passed: {total_ok}/{len(results)}")


if __name__ == "__main__":
    main(use_llm="--no-llm" not in sys.argv)
