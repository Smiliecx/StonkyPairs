#!/usr/bin/env python3
"""
Puts planner: protect a long stock position with put options.

Give a name (and position size). The tool compares puts on the stock itself, on
ETFs and on the stocks most tied to it, at ~3, 6 and 12 months out:
  * which contract (expiry, strike), its price, how many to buy, total cost
  * what the stock + puts position returns at expiry if the stock ends at
    -40% ... +30%, including a "stock-specific drop" case where the stock falls
    but the other underlying doesn't (the risk of hedging with something else)

    python puts.py NVDA --plan                 # which tickers to fetch option chains for
    python puts.py NVDA --amount 25000         # full report (needs options/puts.csv)
    python puts.py NVDA --hedges NVDA,SMH,AMD --otm 0.15 --months 6,12

How other underlyings are projected: from ~3 years of overlapping 3-month returns,
the tool measures how much each one moved per 1% move in your stock, separately
for down and up periods (beta), plus how far it typically strayed from that
(the range shown in scenarios). Projections are at expiry, using mid prices.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import hedge as core

DEFAULTS = dict(
    amount=10000.0,
    months="3,6,12",
    otm=0.10,           # strike ~10% below today's price
    coverage=1.0,       # 1.0 = puts sized to cover the beta-equivalent of the full position
    scenario_months=6,  # expiry used for the scenario table
    lookback_years=3.0,
    horizon_days=63,    # beta measured on 3-month moves
    n_related=4,
    scenarios="-40,-30,-20,-10,0,10,20,30",
)
ETFS = ["SMH", "SOXX", "QQQ", "XLK", "IWF", "SPY", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLC", "IGV",
        "XBI", "KRE", "ITB", "XRT", "IWM"]


def horizon_moves(prices, a, b, cfg):
    """Overlapping horizon log returns (every 5 days) for a and b."""
    s = prices[[a, b]].dropna()
    s = s.loc[s.index >= s.index.max() - pd.DateOffset(days=int(cfg["lookback_years"] * 365.25))]
    L = np.log(s.values)
    h = cfg["horizon_days"]
    if len(L) < h + 60:
        return None
    r = (L[h:] - L[:-h])[::5]
    return r[:, 0], r[:, 1]


def betas(prices, name, u, cfg):
    if u == name:
        return dict(b_dn=1.0, b_up=1.0, rho=1.0, resid=0.0, n=0)
    m = horizon_moves(prices, name, u, cfg)
    if m is None:
        return None
    x, y = m
    # through-origin fits on each side: "per 1% the stock moved, this one moved b%"
    side = lambda mask: float((x[mask] @ y[mask]) / (x[mask] @ x[mask])) if mask.sum() >= 8 else float((x @ y) / (x @ x))
    b_dn, b_up = side(x < 0), side(x > 0)
    pred = np.where(x < 0, b_dn * x, b_up * x)
    return dict(b_dn=b_dn, b_up=b_up, rho=float(np.corrcoef(x, y)[0, 1]),
                resid=float(np.std(y - pred)), n=len(x))


def suggest(prices, name, cfg):
    """Own stock + best ETFs + most closely tied stocks (by protection per $)."""
    cand = {}
    for u in prices.columns:
        if u == name:
            continue
        bt = betas(prices, name, u, cfg)
        if bt and bt["n"] >= 30:
            cand[u] = bt["rho"] * max(bt["b_dn"], 0)
    etfs = sorted([u for u in cand if u in ETFS], key=lambda u: -cand[u])[:3]
    stocks = sorted([u for u in cand if u not in ETFS], key=lambda u: -cand[u])[: cfg["n_related"]]
    return [name] + etfs + stocks


def implied_vol(price, S, K, days, r=0.04):
    """Black-Scholes put implied volatility by bisection (Yahoo's own value is
    unreliable outside market hours)."""
    from statistics import NormalDist
    N, T = NormalDist().cdf, max(days, 1) / 365

    def put(sig):
        d1 = (math.log(S / K) + (r + sig * sig / 2) * T) / (sig * math.sqrt(T))
        return K * math.exp(-r * T) * N(-(d1 - sig * math.sqrt(T))) - S * N(-d1)
    lo, hi = 0.01, 5.0
    if not put(lo) < price < put(hi):
        return float("nan")
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if put(mid) < price else (lo, mid)
    return (lo + hi) / 2


def pick_contract(ch, months, otm):
    target = months * 30.4
    ex = ch[ch["days"] >= 0.75 * target]
    if ex.empty:
        return None
    exp = ex.loc[(ex["days"] - target).abs().idxmin(), "expiry"]
    c = ch[ch["expiry"] == exp].copy()
    spot = c["spot"].iloc[0]
    c["mid"] = np.where((c["bid"] > 0) & (c["ask"] > 0), (c["bid"] + c["ask"]) / 2, c["last"])
    c = c[c["mid"] > 0]
    if c.empty:
        return None
    row = c.loc[(c["strike"] - spot * (1 - otm)).abs().idxmin()].copy()
    row["quoted"] = bool(row["bid"] > 0 and row["ask"] > 0)
    row["iv_calc"] = implied_vol(row["mid"], spot, row["strike"], row["days"])
    return row


def scenario_value(row, bt, r, contracts, cost, amount, is_own, band=0.0):
    """Net return of stock + puts at expiry if the stock moves r (fraction)."""
    if is_own:
        ru = r
    else:
        b = bt["b_dn"] if r < 0 else bt["b_up"]
        lr = b * math.log1p(r) + band
        ru = math.expm1(lr)
    payoff = contracts * 100 * max(row["strike"] - row["spot"] * (1 + ru), 0.0)
    return (amount * r + payoff - cost) / amount



def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--plan", action="store_true", help="print the tickers to fetch option chains for")
    ap.add_argument("--hedges", help="comma-separated underlyings to compare (default: suggested)")
    ap.add_argument("--data", default="data/prices.csv")
    ap.add_argument("--options", default="options/puts.csv")
    ap.add_argument("--out", default="results")
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", type=type(v), default=v)
    args = ap.parse_args()
    cfg = {k: getattr(args, k) for k in DEFAULTS}
    name = args.name.upper()

    prices = pd.read_csv(args.data, index_col=0, parse_dates=True).sort_index().ffill(limit=5)
    if name not in prices.columns:
        sys.exit(f"{name} is not in the price file; add it to extra_tickers.txt.")
    names = core.load_names(Path(args.data).with_name("tickers.csv"))
    nm = lambda t: names.get(t, (t, ""))[0][:24]

    unders = [t.strip().upper() for t in args.hedges.split(",")] if args.hedges else suggest(prices, name, cfg)
    if args.plan:
        print("\n".join(unders))
        return

    if not Path(args.options).exists():
        sys.exit(f"No option data at {args.options}. Fetch chains for: {', '.join(unders)}")
    ch_all = pd.read_csv(args.options)
    meta_p = Path(args.options).with_name("meta.json")
    asof = json.loads(meta_p.read_text())["downloaded_at_utc"] if meta_p.exists() else "unknown"
    have = set(ch_all["ticker"])
    missing = [u for u in unders if u not in have]
    unders = [u for u in unders if u in have]
    if name not in have:
        print(f"Note: no option chain for {name} itself in the file.")
    amount = cfg["amount"]
    spot0 = ch_all.loc[ch_all["ticker"] == name, "spot"].iloc[0] if name in have else prices[name].dropna().iloc[-1]
    print(f"{name} at ${spot0:,.2f}; position ${amount:,.0f} (~{amount / spot0:,.0f} shares). Option prices as of "
          f"{asof}." + (f" No chains for: {', '.join(missing)}." if missing else "") + "\n")

    print(f"How each underlying moved per 1% move in {name} (3-month moves, last {cfg['lookback_years']:.0f} years):")
    bts = {}
    for u in unders:
        bt = betas(prices, name, u, cfg) if u in prices.columns else None
        if bt is None:
            continue
        bts[u] = bt
        if u == name:
            continue
        print(f"   {u:<5} {nm(u):<24} down moves {bt['b_dn']:.2f}x, up moves {bt['b_up']:.2f}x, "
              f"correlation {bt['rho']:.2f}  -> if {name} falls 20%, {u} typically ~{math.expm1(bt['b_dn'] * math.log(0.8)) * 100:.0f}%")
    print()

    months = [float(m) for m in cfg["months"].split(",")]
    table, chosen = [], []
    for u in unders:
        if u not in bts:
            continue
        ch = ch_all[ch_all["ticker"] == u]
        bt = bts[u]
        own = u == name
        beta_eff = 1.0 if own else max(bt["b_dn"], 0.2)
        for m in months:
            row = pick_contract(ch, m, cfg["otm"])
            if row is None:
                continue
            k = cfg["coverage"] * amount * beta_eff / (row["spot"] * 100)     # exact (fractional) contracts
            cost = k * 100 * row["mid"]
            min_pos = amount / k if k > 0 else float("inf")                  # position size where k = 1
            spread = (row["ask"] - row["bid"]) / row["mid"] if row["bid"] > 0 and row["ask"] > 0 else float("nan")
            if not row["quoted"]:
                liq = "last trade (no live quote)"
            else:
                liq = "thin" if (row["open_interest"] < 100 or not spread <= 0.15) else "ok"
            table.append(dict(underlying=u, expiry=row["expiry"], days=int(row["days"]), strike=row["strike"],
                              otm=1 - row["strike"] / row["spot"], mid=row["mid"], iv=row["iv_calc"],
                              contracts=k, min_pos=min_pos, cost=cost, cost_pct=cost / amount,
                              cost_ann=cost / amount * 365 / max(row["days"], 1), oi=row["open_interest"], liq=liq))
            if abs(m - cfg["scenario_months"]) < 1e-9:
                chosen.append((f"{u} puts", row, bt, k, cost, own))

    print(f"PUT CANDIDATES (strike ~{cfg['otm'] * 100:.0f}% below today; sized for ${amount:,.0f} of {name})")
    print(f"   {'under':<6}{'expiry':<12}{'days':>5}{'strike':>9}{'below':>7}{'price':>8}{'IV':>6}{'contracts':>10}"
          f"{'cost':>9}{'% pos':>7}{'%/yr':>7}{'1 contract per':>17}  liquidity")
    for t in table:
        print(f"   {t['underlying']:<6}{t['expiry']:<12}{t['days']:>5}{t['strike']:>9.2f}{t['otm'] * 100:>6.0f}%"
              f"{t['mid']:>8.2f}{t['iv'] * 100:>5.0f}%{t['contracts']:>10.2f}{t['cost']:>9,.0f}"
              f"{t['cost_pct'] * 100:>6.1f}%{t['cost_ann'] * 100:>6.1f}%{'$' + format(t['min_pos'], ',.0f'):>17}"
              f"  {t['liq']}")
    print("   contracts: exact number needed (round to whole contracts when you buy). '1 contract per': the position")
    print(f"   size of {name} that one contract covers - below that, a single contract over-hedges.")
    print("   price = midpoint of bid/ask (or the last trade when there's no live quote, e.g. outside market hours -")
    print("   last trades can be stale). IV = implied volatility worked out from that price. 'thin' = open interest")
    print("   < 100 or a wide bid/ask spread.\n")
    if not any(t["liq"] != "last trade (no live quote)" for t in table):
        print("   NOTE: these chains were downloaded outside market hours, so prices are last trades, not live quotes.")
        print("   For live quotes, fetch again during US market hours (9:30am-4pm ET).\n")

    scen = [float(x) / 100 for x in cfg["scenarios"].split(",")]
    print(f"SCENARIOS at expiry (~{cfg['scenario_months']:.0f}-month puts): return on the ${amount:,.0f} position "
          f"including what the puts cost")
    hdr = f"   {'':<14}" + "".join(f"{s * 100:>+8.0f}%" for s in scen) + f"{'stock-only -30%':>17}"
    print(hdr)
    print(f"   {name + ' alone':<14}" + "".join(f"{s * 100:>+8.0f}%" for s in scen) + f"{-30:>+16.0f}%")
    rows_json = []
    for lab, row, bt, k, cost, own in chosen:
        vals = [scenario_value(row, bt, s, k, cost, amount, own) for s in scen]
        idio = scenario_value(row, dict(b_dn=0, b_up=0), -0.30, k, cost, amount, own) if not own else vals[scen.index(-0.3)] if -0.3 in scen else float("nan")
        print(f"   {lab:<14}" + "".join(f"{v * 100:>+8.0f}%" for v in vals) + f"{idio * 100:>+16.0f}%")
        if not own:
            sd = bt["resid"] * math.sqrt(max(row["days"], 1) / cfg["horizon_days"])
            lo = [scenario_value(row, bt, s, k, cost, amount, own, +sd) for s in scen]
            hi = [scenario_value(row, bt, s, k, cost, amount, own, -sd) for s in scen]
            print(f"   {'  range':<14}" + "".join(f"{(a_ * 100):>+4.0f}/{(b_ * 100):<+3.0f}" for a_, b_ in zip(lo, hi)))
        rows_json.append(dict(hedge=lab, expiry=row["expiry"], strike=row["strike"], contracts=k, cost=cost,
                              scenarios=dict(zip([f"{s * 100:+.0f}%" for s in scen], vals)), stock_only_drop=idio))
    print("\n   'stock-only -30%': the stock falls 30% but the other underlying doesn't move - puts on other tickers "
          "don't help then.")
    print("   'range': typical spread of outcomes (one standard deviation) because other tickers don't track the "
          "stock exactly.")
    print("   Values are at expiry. Before expiry, puts are worth more than these payoffs (remaining time value).")

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}_puts.json").write_text(json.dumps(dict(name=name, amount=amount, options_asof=asof,
                                                           candidates=table, scenarios=rows_json), indent=1, default=float))
    print(f"\nFull results: {out / f'{name}_puts.json'}")
    print("Not investment advice; projections use historical relationships, which can change.")


if __name__ == "__main__":
    main()
