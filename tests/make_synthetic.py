"""
Simulated market for testing hedge.py. 200 stocks + a few ETFs with market and
sector factors (pure random walks, no real mean reversion), plus three anchors:

  ANCH  clear planted relationship (half-life 10d, swing 8%) for the whole
        period: ANCH + 0.6*S03_07 - 0.8*S07_02 + 0.5*S09_04 mean-reverts
        -> should be found, pass validation and hold up on the unseen year
  WEAK  same structure but faint (half-life 15d, swing 5%) -> a hard case;
        it is acceptable for the tool to say "nothing reliable"
  BRKN  clear relationship that stops at the start of the final year
        -> should pass training + validation but BREAK DOWN on unseen data
  NULL  nothing planted -> should report nothing / not beat chance
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
T, n_sec, per_sec = 1512, 10, 20                  # ~6 years of trading days
dates = pd.bdate_range("2020-10-12", periods=T)

mkt = rng.normal(0.0003, 0.010, T)
sec = rng.normal(0, 0.008, (T, n_sec))
cols, rets, info = [], [], []
for s in range(n_sec):
    for k in range(per_sec):
        beta, sb = rng.uniform(0.6, 1.5), rng.uniform(0.5, 1.2)
        r = beta * mkt + sb * sec[:, s] + rng.normal(0, rng.uniform(0.008, 0.02), T)
        t = f"S{s + 1:02d}_{k + 1:02d}"
        cols.append(t); rets.append(r)
        info.append((t, f"Sector {s + 1} stock {k + 1}", f"Sector {s + 1}", "-", "stock"))
logp = np.log(50) + np.cumsum(np.array(rets).T, 0)
df = pd.DataFrame(logp, index=dates, columns=cols)
df["SPY"] = np.log(400) + np.cumsum(mkt + rng.normal(0, 0.001, T))
info.append(("SPY", "Market ETF", "ETF", "-", "etf"))
for s in range(3):
    df[f"ETF{s + 1}"] = np.log(100) + np.cumsum(mkt + sec[:, s] + rng.normal(0, 0.002, T))
    info.append((f"ETF{s + 1}", f"Sector {s + 1} ETF", "ETF", "-", "etf"))


def ou(n, hl, sd):
    phi = np.exp(-np.log(2) / hl)
    x = np.zeros(n)
    eps = rng.normal(0, sd * np.sqrt(1 - phi ** 2), n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t]
    return x


# ANCH = spread - 0.6*B + 0.8*C - 0.5*D, spread mean-reverting
B, C, D = df["S03_07"], df["S07_02"], df["S09_04"]
df["ANCH"] = np.log(80) + ou(T, 10, 0.08) - 0.6 * B + 0.8 * C - 0.5 * D
info.append(("ANCH", "Planted anchor (clear)", "Test", "-", "stock"))
H1, H2, H3 = df["S04_09"], df["S06_13"], df["S10_02"]
df["WEAK"] = np.log(80) + ou(T, 15, 0.05) + 0.5 * H1 - 0.7 * H2 - 0.6 * H3
info.append(("WEAK", "Planted anchor (faint)", "Test", "-", "stock"))

# BRKN: same idea with different partners, relationship stops in the last 252 days
E, F, G = df["S02_05"], df["S05_11"], df["S08_16"]
sp2 = np.log(60) + ou(T, 10, 0.08)
cut = T - 252
rw = np.cumsum(rng.normal(0, 0.02, T))
sp2[cut:] = sp2[cut] + rw[cut:] - rw[cut]
df["BRKN"] = sp2 + 0.7 * E - 0.5 * F - 0.6 * G
info.append(("BRKN", "Planted anchor (breaks)", "Test", "-", "stock"))

df["NULL"] = np.log(70) + np.cumsum(1.1 * mkt + 0.9 * sec[:, 4] + rng.normal(0, 0.015, T))
info.append(("NULL", "No relationship", "Test", "-", "stock"))

out = Path(sys.argv[1] if len(sys.argv) > 1 else "synthetic")
out.mkdir(parents=True, exist_ok=True)
np.exp(df).round(4).rename_axis("date").to_csv(out / "prices.csv")
pd.DataFrame(info, columns=["ticker", "name", "sector", "industry", "type"]).to_csv(out / "tickers.csv", index=False)
print(f"wrote {out}/prices.csv  {df.shape}")
print("ANCH true hedges: BUY 0.6 S03_07, SHORT 0.8 S07_02, BUY 0.5 S09_04")
print("WEAK true hedges: SHORT 0.5 S04_09, BUY 0.7 S06_13, BUY 0.6 S10_02 (faint)")
print("BRKN true hedges: SHORT 0.7 S02_05, BUY 0.5 S05_11, BUY 0.6 S08_16 (breaks in last 252 days)")
