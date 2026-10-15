#!/usr/bin/env python3
"""
Mode 2 - protection hedge.

You own (or want to own) an ANCHOR stock. Find 3 positions, longs or shorts,
from the whole universe, that cut the risk of holding it as much as possible.
Unlike hedge.py there is no mean-reversion requirement: the goal is simply that
the hedges move to offset the anchor.

    python protect.py DELL
    python protect.py DELL --pick SMH,QQQ,STX      # evaluate one exact hedge

Pipeline (daily returns, time order)
  TRAINING   (2 yrs)    hedge sizes by regression of the anchor's returns on
                        the hedges' returns; every 3-leg combination of a
                        shortlist is scored by how much volatility it removes.
  VALIDATION (6 mo)     sizes frozen; how much volatility did it remove here?
                        Ranked by the weaker of training and validation, so a
                        hedge has to work in both.
  UNSEEN     (6 mo)     final exam: sizes refit on training+validation, frozen.
                        Volatility cut, drawdown, and how much of the anchor's
                        worst days the hedge absorbed. Compared with simply
                        shorting SPY and with the best single hedge.
  TODAY                 sizes refit on the most recent 2.5 years.
"""

import argparse
import json
import math
import sys
from itertools import combinations, product
from pathlib import Path

import numpy as np

import hedge as core

DEFAULTS = dict(
    years=3.2,
    train_days=504,
    val_days=126,
    test_days=126,
    legs=3,
    shortlist=150,      # candidates by |correlation| with the anchor (SPY always included)
    max_gross=2.0,      # max total hedge dollars per $1 of anchor
    group_size=5,
    buy_only=0,         # 1 = hedges must all be purchases (no shorting)
)


class PCtx:
    def __init__(self, prices, cfg, names):
        L = np.log(prices.values)
        R = np.diff(L, axis=0)
        self.dates = prices.index[1:]
        self.tickers = list(prices.columns)
        self.ix = {t: i for i, t in enumerate(self.tickers)}
        self.names = names
        n = len(R)
        self.te0 = n - cfg["test_days"]
        self.va0 = self.te0 - cfg["val_days"]
        self.tr0 = max(0, self.va0 - cfg["train_days"])
        self.R = R
        self.R_tr, self.R_va = R[self.tr0:self.va0], R[self.va0:self.te0]
        self.R_trva, self.R_te = R[self.tr0:self.te0], R[self.te0:]
        self.R_now = R[-(cfg["train_days"] + cfg["val_days"]):]
        self.C_tr = np.cov(self.R_tr, rowvar=False)
        self.C_va = np.cov(self.R_va, rowvar=False)
        self.C_trva = np.cov(self.R_trva, rowvar=False)

    def span(self, a, b):
        return f"{self.dates[a]:%b %Y}-{self.dates[b - 1]:%b %Y}"


def batch_ols(C, idx, ridge=1e-4):
    """Hedge sizes for many baskets at once: regress anchor returns (col 0)
    on hedge returns. Returns W (B,k) with W[:,0] = 1 and variance reduction."""
    a = idx[:, 0]
    H = C[idx[:, 1:, None], idx[:, None, 1:]]
    ha = C[idx[:, 1:], a[:, None]]
    k = H.shape[1]
    H = H + ridge * np.einsum("bii->b", H)[:, None, None] / k * np.eye(k)
    beta = np.linalg.solve(H, ha[..., None])[..., 0]
    W = np.concatenate([np.ones((len(idx), 1)), -beta], 1)
    return W, realized_vr(C, idx, W)


def realized_vr(C, idx, W):
    """1 - var(anchor + hedges) / var(anchor), using covariance C."""
    q = np.einsum("bi,bij,bj->b", W, C[idx[:, :, None], idx[:, None, :]], W)
    return 1 - q / C[idx[:, 0], idx[:, 0]]


def shortlist(ctx, a, cfg):
    sd = np.sqrt(np.diag(ctx.C_tr))
    c = ctx.C_tr[a] / (sd * sd[a] + 1e-18)
    corr = -c if cfg["buy_only"] else np.abs(c)      # buy-only: most opposite-moving names first
    corr[a] = -np.inf
    picked = list(np.argsort(-corr)[: cfg["shortlist"]])
    if not cfg["buy_only"] and "SPY" in ctx.ix and ctx.ix["SPY"] not in picked and ctx.ix["SPY"] != a:
        picked.append(ctx.ix["SPY"])
    return np.array(picked)


def score(ctx, idx, cfg):
    """Fit on training, freeze, check validation. Score = weaker of the two."""
    W, vr_tr = batch_ols(ctx.C_tr, idx)
    vr_va = realized_vr(ctx.C_va, idx, W)
    gross = np.abs(W[:, 1:]).sum(1)
    ok = gross <= cfg["max_gross"]
    if cfg["buy_only"]:
        ok &= (W[:, 1:] > 0).all(1)
    sc = np.where(ok, np.minimum(vr_tr, vr_va), -np.inf)
    return sc, W, vr_tr, vr_va


def evaluate(ctx, idx):
    idx = np.asarray(idx)
    W_tr, vr_tr = batch_ols(ctx.C_tr, idx[None])
    vr_va = realized_vr(ctx.C_va, idx[None], W_tr)
    W, vr_fit = batch_ols(ctx.C_trva, idx[None])           # final-exam sizes
    w = W[0]
    ra = np.expm1(ctx.R_te[:, idx[0]])
    rh = np.expm1(ctx.R_te[:, idx]) @ w                      # anchor + hedges, $ per $1 anchor
    eq_a, eq_h = np.cumsum(ra), np.cumsum(rh)
    dd = lambda e: float((e - np.maximum.accumulate(np.concatenate([[0], e]))[1:]).min())
    worst = np.argsort(ra)[: max(3, len(ra) // 10)]          # anchor's worst 10% of days
    vol = lambda r: float(r.std() * math.sqrt(252))
    return dict(idx=idx, w=w, gross=float(np.abs(w[1:]).sum()),
                vr_tr=float(vr_tr[0]), vr_va=float(vr_va[0]), vr_fit=float(vr_fit[0]),
                vr_te=float(1 - rh.var() / ra.var()), vol_a=vol(ra), vol_h=vol(rh),
                dd_a=dd(eq_a), dd_h=dd(eq_h), ret_a=float(eq_a[-1]), ret_h=float(eq_h[-1]),
                worst_a=float(ra[worst].mean()), worst_h=float(rh[worst].mean()), eq_a=eq_a, eq_h=eq_h)


def today_sizes(ctx, idx):
    C = np.cov(ctx.R_now, rowvar=False)
    W, vr = batch_ols(C, np.asarray(idx)[None])
    return W[0], float(vr[0])


def build_groups(ctx, a, best_idx, sl, cfg):
    legs = list(best_idx[1:])
    cand = [j for j in sl if j not in legs]
    best_slot = {}
    for slot in range(len(legs)):
        idx = np.array([[a] + [c if i == slot else legs[i] for i in range(len(legs))] for c in cand])
        sc, *_ = score(ctx, idx, cfg)
        for r in np.argsort(-sc)[:25]:
            if np.isfinite(sc[r]) and (int(cand[r]) not in best_slot or sc[r] > best_slot[int(cand[r])][1]):
                best_slot[int(cand[r])] = (slot, float(sc[r]))
    groups = []
    for slot, leg in enumerate(legs):
        members = sorted(((-s, j) for j, (sl_, s) in best_slot.items() if sl_ == slot))
        groups.append([leg] + [j for _, j in members[: cfg["group_size"] - 1]])
    return groups


def describe(ctx, ev, title, notional=10_000):
    a = ev["idx"][0]
    w_now, vr_now = today_sizes(ctx, ev["idx"])
    L = [title, "-" * len(title), f"Positions per ${notional:,.0f} of {ctx.tickers[a]} (sized on the last 2.5 years):"]
    for j, w in zip(ev["idx"], w_now):
        L.append(f"   {'BUY  ' if w > 0 else 'SHORT'} ${abs(w) * notional:>8,.0f}  {core.label(ctx, j)}")
    L.append(f"Volatility removed: training {ev['vr_tr'] * 100:.0f}%, validation {ev['vr_va'] * 100:.0f}%, "
             f"unseen {ev['vr_te'] * 100:.0f}% (expected ~{ev['vr_fit'] * 100:.0f}%)")
    L.append(f"Unseen {ctx.span(ctx.te0, len(ctx.R))}: {ctx.tickers[a]} alone vol {ev['vol_a'] * 100:.0f}%, "
             f"max drawdown {ev['dd_a'] * 100:.0f}%, return {ev['ret_a'] * 100:+.0f}%")
    L.append(f"   with hedge: vol {ev['vol_h'] * 100:.0f}%, max drawdown {ev['dd_h'] * 100:.0f}%, "
             f"return {ev['ret_h'] * 100:+.0f}%  (per $1 of {ctx.tickers[a]}, before costs)")
    cushion = 1 - ev["worst_h"] / ev["worst_a"] if ev["worst_a"] < 0 else float("nan")
    L.append(f"   on {ctx.tickers[a]}'s worst 10% of days: avg {ev['worst_a'] * 100:+.1f}% alone vs "
             f"{ev['worst_h'] * 100:+.1f}% hedged -> hedge absorbed {cushion * 100:.0f}% of the hit")
    return "\n".join(L)



def short_legs(ctx, ev):
    return ", ".join(("+" if w > 0 else "-") + ctx.tickers[j] for j, w in zip(ev["idx"][1:], ev["w"][1:]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("anchor")
    ap.add_argument("--pick", help="comma-separated hedge tickers to evaluate exactly")
    ap.add_argument("--data", default="data/prices.csv")
    ap.add_argument("--names", default=None)
    ap.add_argument("--out", default="results")
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", type=type(v), default=v)
    args = ap.parse_args()
    cfg = {k: getattr(args, k) for k in DEFAULTS}

    lcfg = dict(years=cfg["years"], val_days=cfg["val_days"], test_days=cfg["test_days"])
    prices, dropped = core.load_data(args.data, lcfg)
    names = core.load_names(args.names or Path(args.data).with_name("tickers.csv"))
    anchor = args.anchor.upper()
    if anchor not in prices.columns:
        sys.exit(f"{anchor} {'lacks full history' if anchor in dropped else 'is not in the price file'}. "
                 "Add it to extra_tickers.txt or shorten --years.")
    ctx = PCtx(prices, cfg, names)
    a = ctx.ix[anchor]
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    print(f"Data: {len(ctx.tickers)} tickers through {ctx.dates[-1].date()}. Training "
          f"{ctx.span(ctx.tr0, ctx.va0)}, validation {ctx.span(ctx.va0, ctx.te0)}, unseen {ctx.span(ctx.te0, len(ctx.R))}.\n")

    if args.pick:
        legs = [t.strip().upper() for t in args.pick.split(",") if t.strip()]
        miss = [t for t in legs if t not in ctx.ix]
        if miss:
            sys.exit(f"Not in data: {', '.join(miss)}")
        ev = evaluate(ctx, [a] + [ctx.ix[t] for t in legs])
        print(describe(ctx, ev, f"{anchor} hedged with {', '.join(legs)}"))
        return

    sl = shortlist(ctx, a, cfg)
    combos = np.array(list(combinations(sl, cfg["legs"])))
    idx = np.hstack([np.full((len(combos), 1), a), combos])
    sc, *_ = score(ctx, idx, cfg)
    best_idx = idx[int(np.argmax(sc))]
    groups = build_groups(ctx, a, best_idx, sl, cfg)
    grid = [evaluate(ctx, [a, *c]) for c in product(*groups) if len(set(c)) == len(c)]

    singles = np.stack([np.full(len(sl), a), sl], 1)
    s1, *_ = score(ctx, singles, cfg)
    best1 = evaluate(ctx, singles[int(np.argmax(s1))])
    spy = (evaluate(ctx, [a, ctx.ix["SPY"]]) if "SPY" in ctx.ix and a != ctx.ix["SPY"] and not cfg["buy_only"]
           else None)
    best_ev = evaluate(ctx, best_idx)

    print(f"Scored {len(idx):,} three-leg hedges from a shortlist of {len(sl)}.\n")
    print(f"THREE GROUPS for {anchor}: pick one from each ({len(grid)} combinations, all evaluated)\n")
    for gi, members in enumerate(groups):
        print(f"Group {gi + 1}")
        for j in members:
            mine = [g for g in grid if j in g["idx"][1:]]
            side = "buy" if np.mean([g["w"][list(g["idx"]).index(j)] for g in mine]) > 0 else "short"
            vr = np.mean([g["vr_te"] for g in mine]) * 100
            print(f"   {core.label(ctx, j)}  {side:<5}  avg unseen volatility removed {vr:4.0f}%")
        print()
    vrs = np.array([g["vr_te"] for g in grid]) * 100
    print(f"Across all {len(grid)} combinations, unseen volatility removed: median {np.median(vrs):.0f}%, "
          f"range {vrs.min():.0f}% to {vrs.max():.0f}%.\n")

    print(describe(ctx, best_ev, "Top pick (best over training AND validation)") + "\n")
    print("How simpler hedges did on the same unseen period:")
    for name, ev in [("Short SPY only", spy), (f"Best single hedge ({short_legs(ctx, best1)})", best1)]:
        if ev:
            print(f"   {name:<42} volatility removed {ev['vr_te'] * 100:4.0f}%, max drawdown "
                  f"{ev['dd_h'] * 100:5.0f}% (vs {ev['dd_a'] * 100:.0f}% unhedged)")
    print(f"   {'Top 3-leg pick':<42} volatility removed {best_ev['vr_te'] * 100:4.0f}%, max drawdown "
          f"{best_ev['dd_h'] * 100:5.0f}%")
    if spy and best_ev["vr_te"] < spy["vr_te"] + 0.05:
        print("   -> The 3-leg hedge isn't clearly better than just shorting SPY; the simple hedge may be enough.")

    keep = lambda e: {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in e.items() if k not in ("eq_a", "eq_h")}
    rep = dict(anchor=anchor, config=cfg, groups=[[ctx.tickers[j] for j in g] for g in groups],
               best=keep(best_ev) | {"tickers": [ctx.tickers[j] for j in best_ev["idx"]]},
               spy=keep(spy) if spy else None,
               grid=[keep(g) | {"tickers": [ctx.tickers[j] for j in g["idx"]]} for g in grid])
    (out / f"{anchor}_protect.json").write_text(json.dumps(rep, indent=1, default=float))
    print(f"\nFull results: {out / f'{anchor}_protect.json'}")


if __name__ == "__main__":
    main()
