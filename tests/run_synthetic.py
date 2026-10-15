"""
End-to-end check of hedge.py on simulated prices with known answers.

    python tests/run_synthetic.py

Builds tests/synthetic/ (see make_synthetic.py) and checks that:
  ANCH  the planted relationship (or a close proxy sharing >= 2 of its legs)
        shows up among the reported baskets AND held up on the unseen year
  BRKN  the top pick is flagged as having broken down on the unseen year
  NULL  most one-per-group baskets fail on the unseen year (no false confidence)
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "synthetic"
OUT = HERE / "synthetic_results"


def run(anchor):
    subprocess.run([sys.executable, str(ROOT / "hedge.py"), anchor, "--data", str(DATA / "prices.csv"),
                    "--sims", "0", "--out", str(OUT)], check=True, capture_output=True, text=True)
    return json.loads((OUT / f"{anchor}_report.json").read_text())


def main():
    subprocess.run([sys.executable, str(HERE / "make_synthetic.py"), str(DATA)], check=True, capture_output=True)
    ok = True

    r = run("ANCH")
    true_legs = {"S03_07", "S07_02", "S09_04"}
    hits = [b for b in [r["best"], *r.get("others", [])]
            if len(set(b["tickers"][1:]) & true_legs) >= 2 and b["held"]]
    print(f"ANCH: planted relationship found and held up: {'PASS' if hits else 'FAIL'}"
          + (f"  ({', '.join(hits[0]['tickers'][1:])})" if hits else ""))
    ok &= bool(hits)

    r = run("BRKN")
    broke = not r["best"]["held"]
    print(f"BRKN: top pick flagged as broken on unseen year: {'PASS' if broke else 'FAIL'}")
    ok &= broke

    r = run("NULL")
    good = [g for g in r["grid"] if g["fit_pass"] and g["val_pass"]]
    rate = sum(g["held"] for g in good) / max(1, len(good))
    print(f"NULL: share of surviving baskets that 'held up' by luck = {rate:.0%}: {'PASS' if rate <= 0.3 else 'FAIL'}")
    ok &= rate <= 0.3

    print("ALL PASS" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
