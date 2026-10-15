"""
Download today's put option chains for a list of tickers (via yfinance) and save:

    <out>/puts.csv    one row per put: ticker, spot, expiry, strike, bid, ask, last,
                      implied_vol, volume, open_interest, contract
    <out>/meta.json   when it ran, which tickers worked

Triggered on demand: pushing request.txt (one ticker per line) to the 'requests'
branch runs .github/workflows/options.yml, which publishes to the 'options' branch.

    python download_options.py --file request.txt --out out
    python download_options.py --tickers NVDA,SMH --out out
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf


def chains(ticker, max_years=2.5, lo=0.4, hi=1.05):
    tk = yf.Ticker(ticker)
    hist = tk.history(period="5d")
    if hist.empty:
        raise ValueError("no price")
    spot = float(hist["Close"].iloc[-1])
    today = pd.Timestamp.today().normalize()
    rows = []
    for e in tk.options:
        days = (pd.Timestamp(e) - today).days
        if days < 7 or days > max_years * 365:
            continue
        for attempt in range(3):
            try:
                p = tk.option_chain(e).puts
                break
            except Exception:
                time.sleep(2 * (attempt + 1))
        else:
            continue
        p = p[(p["strike"] >= lo * spot) & (p["strike"] <= hi * spot)]
        for r in p.itertuples():
            rows.append(dict(ticker=ticker, spot=spot, expiry=e, days=days, strike=float(r.strike),
                             bid=float(r.bid or 0), ask=float(r.ask or 0), last=float(r.lastPrice or 0),
                             implied_vol=float(r.impliedVolatility or 0), volume=float(r.volume or 0),
                             open_interest=float(r.openInterest or 0), contract=r.contractSymbol))
        time.sleep(0.3)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--tickers")
    ap.add_argument("--out", default="options")
    args = ap.parse_args()
    tick = []
    if args.file:
        tick += [l.split("#")[0].strip().upper() for l in Path(args.file).read_text().splitlines()]
    if args.tickers:
        tick += [t.strip().upper() for t in args.tickers.split(",")]
    tick = [t for t in dict.fromkeys(tick) if t]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, ok, failed = [], [], []
    for t in tick:
        try:
            r = chains(t)
            rows += r
            (ok if r else failed).append(t)
            print(f"{t}: {len(r)} puts")
        except Exception as e:
            failed.append(t)
            print(f"{t}: failed ({e})")
    pd.DataFrame(rows).to_csv(out / "puts.csv", index=False)
    meta = dict(downloaded_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                tickers=ok, failed=failed, n_rows=len(rows))
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    if not ok:
        raise SystemExit("No option data downloaded.")


if __name__ == "__main__":
    main()
