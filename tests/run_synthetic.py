"""
End-to-end check of hedge.py on simulated prices with known answers.

    python tests/run_synthetic.py

Builds tests/synthetic/ (see make_synthetic.py) and checks that:
  ANCH  the planted relationship (or a close proxy sharing >= 2 of its legs)
        shows up among the reported baskets AND held up on the unseen year
  BRKN  the top pick is flagged as having broken down on the unseen year
  NULL  most one-per-group baskets fail on the unseen year (no false confidence)
  HEDG  protect.py hedges it with the planted names (S04_01, S06_02, SPY)
  theme.py --pick: the planted 4-stock basket's track record ranks in the top
        10% of all baskets in its theme; four unrelated names do not
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


THEME = ("ANCH,S03_07,S07_02,S09_04,S01_03,S02_08,S03_11,S04_05,S05_02,S05_09,S06_14,S07_17,"
         "S08_01,S08_12,S09_15,S10_06,S10_19,S02_19,S04_16,ETF2")


def theme_pick(pick):
    subprocess.run([sys.executable, str(ROOT / "theme.py"), "--tickers", THEME, "--pick", pick,
                    "--data", str(DATA / "prices.csv"), "--out", str(OUT)], check=True, capture_output=True, text=True)
    return json.loads((OUT / "theme_custom.json").read_text())["picks"][0]


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

    subprocess.run([sys.executable, str(ROOT / "protect.py"), "HEDG", "--data", str(DATA / "prices.csv"),
                    "--out", str(OUT)], check=True, capture_output=True, text=True)
    r = json.loads((OUT / "HEDG_protect.json").read_text())
    legs = set(r["best"]["tickers"][1:])
    good = legs == {"S04_01", "S06_02", "SPY"}
    print(f"HEDG: protection hedge uses the planted names: {'PASS' if good else 'FAIL'}  ({', '.join(sorted(legs))})")
    ok &= good

    real = theme_pick("ANCH,S03_07,S07_02,S09_04")
    rand = theme_pick("S01_03,S05_09,S08_12,S10_06")
    good = real["pct_held"] >= 90 and rand["pct_held"] < 90
    print(f"THEME: planted basket record beats {real['pct_held']:.0f}% of baskets, unrelated names "
          f"{rand['pct_held']:.0f}%: {'PASS' if good else 'FAIL'}")
    ok &= good

    print("ALL PASS" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
