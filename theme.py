#!/usr/bin/env python3
"""
Mode 3 - theme baskets.

Give a theme (a list of tickers in themes/<name>.txt). The theme defines what the
basket is ABOUT, not where it can look: every basket holds 1-2 theme stocks, and
its other legs come from the WHOLE market (S&P 500 + ETFs), shortlisted as the
names most tied to the theme in either direction - the strongest co-movers and
the strongest opposite-movers (e.g. software vs AI hardware). Baskets are
balanced long/short and must swing around a steady average.

    python theme.py ai_infrastructure
    python theme.py ai_infrastructure --pick NVDA,ADBE,MU,WDAY    # one exact basket, any tickers
    python theme.py --tickers NVDA,AMD,AVGO,MU,TSM,ASML,ANET      # ad-hoc theme

Method
  LINKS      theme index = equal-weight theme returns. Every other stock's daily
             returns are correlated with it after removing the market (SPY), over
             the fit window. The most negative and most positive are shortlisted.
  GATE       every 4-stock basket (1-2 theme names + the rest from the shortlist)
             is fitted on the last 12 months (Box-Tiao weights, $1 gross) and must
             pass a cointegration test with a 3-30 day half-life, be roughly
             balanced (net long/short <= 50% of gross), every leg >= 5%.
  RANK       survivors ranked by their TRACK RECORD over the prior 24 months: each
             month refit on the 12 months before it, trade the next month with
             weights frozen. "Held up" = stayed within 3 sd and came back to its
             average. Each pick also gets a percentile among comparable baskets.
  CHECK      the whole procedure walk-forward over another 24 months, using only
             past data each month.
  CHANCE     the identical procedure on random-walk prices with the real
             volatilities and correlations.
Needs ~5 years of history (12-month fit + 24 + 24 months).
"""

import argparse
import json
import math
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

import hedge as core

DEFAULTS = dict(
    fit_days=252,       # ~12 months per fit (6 months is too short to tell real from luck)
    step_days=21,       # ~1 month forward test, then slide
    rec_months=24,      # track-record months used to rank baskets
    n_tests=24,         # walk-forward months used to check the procedure
    size=4,             # stocks per basket
    min_theme=1,        # theme stocks per basket
    max_theme=2,
    n_neg=12,           # outside names shortlisted: strongest opposite-movers ...
    n_pos=12,           # ... and strongest co-movers (market-adjusted)
    min_hl=3.0,         # faster "reversion" is mostly day-to-day noise
    max_hl=30.0,
    min_sd=0.01,        # min swing (1 sd) as a fraction of gross $
    min_leg=0.05,       # every leg at least 5% of gross
    max_net=0.5,        # |longs - shorts| at most 50% of gross
    max_cand=3000,      # gate survivors whose track records are scored (random sample if more)
    entry_z=1.5,
    cost_bps=5.0,
    top=5,
    sims=2,
    seed=7,
)


def read_theme(arg, tickers_opt):
    if tickers_opt:
        return "Custom", [t.strip().upper() for t in tickers_opt.split(",") if t.strip()]
    root = Path(__file__).resolve().parent / "themes"
    p = Path(arg) if Path(arg).exists() else root / f"{arg}.txt"
    if not p.exists():
        sys.exit(f"Theme '{arg}' not found. Themes: " + ", ".join(x.stem for x in root.glob("*.txt")))
    tick = []
    for line in p.read_text().splitlines():
        t = line.split("#")[0].strip().upper()
        if t and t not in tick:
            tick.append(t)
    return p.stem.replace("_", " ").title(), tick


# ------------------------------------------------------------- engine ----

def links(L, theme, others, mkt):
    """Market-adjusted correlation of each `others` column with the equal-weight
    theme index over window L. Returns array aligned with `others`."""
    R = np.diff(L, axis=0)
    ti = R[:, theme].mean(1)
    def resid(x):
        if mkt is None:
            return x - x.mean(0)
        m = R[:, mkt] - R[:, mkt].mean()
        x = x - x.mean(0)
        return x - np.outer(m, (m @ x) / (m @ m))
    a = resid(ti[:, None])[:, 0]
    B = resid(R[:, others])
    return (B.T @ a) / (np.linalg.norm(B, axis=0) * np.linalg.norm(a) + 1e-18)


def shortlist(L, theme, others, mkt, cfg):
    c = links(L, theme, others, mkt)
    order = np.argsort(c)
    neg = [others[i] for i in order[: cfg["n_neg"]]]
    pos = [others[i] for i in order[::-1][: cfg["n_pos"]]]
    return neg, pos, c


def compositions(theme, outside, cfg):
    rows = []
    for m in range(cfg["min_theme"], cfg["max_theme"] + 1):
        if m > len(theme) or cfg["size"] - m > len(outside):
            continue
        for tc in combinations(theme, m):
            for oc in combinations(outside, cfg["size"] - m):
                rows.append(tc + oc)
    return np.array(rows, dtype=int)


def _quad(S, idx, W):
    return np.einsum("bi,bij,bj->b", W, S[idx[:, :, None], idx[:, None, :]], W)


def gate(L, idx, cfg, seed=0):
    """Fit every basket on window L; keep those passing half-life, swing, balance
    and a cointegration test (5% MacKinnon critical value, DF in batch)."""
    from statsmodels.tsa.adfvalues import mackinnoncrit
    tab = core.Tables(L)
    n = len(L) - 1
    nu, W, sd = core.batch_fit(tab, idx, norm="gross")
    vz, vy, cyz = _quad(tab.Szz, idx, W), _quad(tab.Syy, idx, W), _quad(tab.Syz, idx, W)
    with np.errstate(divide="ignore", invalid="ignore"):
        phi = cyz / vz
        t = (phi - 1) / np.sqrt((vy - phi * cyz) / (n * vz))
        hl = np.where((phi > 0) & (phi < 1), -math.log(2) / np.log(phi), np.inf)
    crit = mackinnoncrit(N=idx.shape[1], regression="c", nobs=n)[1]
    ok = np.isfinite(t) & (t <= crit) & (sd >= cfg["min_sd"]) & (hl >= cfg["min_hl"]) & (hl <= cfg["max_hl"])
    ok &= (np.abs(W).min(1) >= cfg["min_leg"]) & (np.abs(W.sum(1)) <= cfg["max_net"])
    keep = np.where(ok)[0]
    if len(keep) > cfg["max_cand"]:          # random sample: ranking by t favours noisy, fast baskets
        keep = np.sort(np.random.default_rng(cfg["seed"] + seed).choice(keep, cfg["max_cand"], replace=False))
    return idx[keep], W[keep], hl[keep]


def month_ends(n, months, cfg):
    return [n - (months - t) * cfg["step_days"] for t in range(months)
            if n - (months - t) * cfg["step_days"] - cfg["fit_days"] >= 0]


def _trade(Lf, W, mu, sd, cfg):
    """One forward month for many baskets with frozen weights/mean/sd.
    Lf: (m, B, k) log prices starting on the last fit day."""
    z = (np.einsum("tbk,bk->tb", Lf, W) - mu) / sd
    crossed = (np.sign(z[1:]) != np.sign(z[:-1])).any(0)
    held = (np.abs(z).max(0) <= 3) & (crossed | (np.abs(z[-1]) <= 1))
    leg = np.einsum("tbk,bk->tb", np.expm1(np.diff(Lf, axis=0)), W)
    pos, p = np.zeros_like(z), np.zeros(z.shape[1])
    for t in range(len(z)):
        enter = (p == 0) * ((z[t] <= -cfg["entry_z"]).astype(float) - (z[t] >= cfg["entry_z"]).astype(float))
        p = np.where(((p == 1) & (z[t] >= 0)) | ((p == -1) & (z[t] <= 0)), 0, p + enter)
        pos[t] = p
    chg = np.abs(np.diff(np.vstack([np.zeros(z.shape[1]), pos]), axis=0))
    ret = (pos[:-1] * leg).sum(0) - chg[1:].sum(0) * cfg["cost_bps"] / 1e4
    return held, ret


def records(L, idx, cfg, months):
    """Vectorized track record of many baskets over the `months` months ending
    at len(L): refit on the prior fit window, trade the next month."""
    cols = np.unique(idx)
    remap = {c: i for i, c in enumerate(cols)}
    Ls = L[:, cols]
    sub_idx = np.vectorize(remap.get)(idx) if len(idx) else idx
    B = len(idx)
    held, n, tot = np.zeros(B), np.zeros(B), np.zeros(B)
    for e in month_ends(len(Ls), months, cfg):
        f0, f1 = e - cfg["fit_days"], min(e + cfg["step_days"], len(Ls))
        ok = ~np.isnan(Ls[f0:f1][:, sub_idx]).any(axis=(0, 2)) if B else np.zeros(0, bool)
        if not ok.any():
            continue
        sub = sub_idx[ok]
        _, W, _ = core.batch_fit(core.Tables(np.nan_to_num(Ls[f0:e])), sub, norm="gross")
        s_fit = np.einsum("tbk,bk->tb", Ls[f0:e][:, sub], W)
        h, r = _trade(Ls[e - 1:f1][:, sub], W, s_fit.mean(0), s_fit.std(0), cfg)
        held[ok] += h; n[ok] += 1; tot[ok] += r
    return held, n, tot


class Universe:
    def __init__(self, L, tick, theme_names):
        self.L, self.tick = L, tick
        self.theme_set = {tick.index(t) for t in theme_names if t in tick}
        self.mkt = tick.index("SPY") if "SPY" in tick else None

    def window(self, end, fit):
        f0 = end - fit
        av = [j for j in range(self.L.shape[1]) if not np.isnan(self.L[f0:end, j]).any()]
        theme = [j for j in av if j in self.theme_set]
        others = [j for j in av if j not in self.theme_set and j != self.mkt]
        return theme, others


def candidates(U, end, cfg, seed=0):
    """Shortlist outside names, gate on the fit window ending at `end`, rank by
    track record using only data before `end`."""
    theme, others = U.window(end, cfg["fit_days"])
    if not theme:
        return [], [], []
    Lw = U.L[end - cfg["fit_days"]:end]
    neg, pos, _ = shortlist(Lw, theme, others, U.mkt, cfg)
    outside = neg + [j for j in pos if j not in neg]
    idx = compositions(theme, outside, cfg)
    if len(idx) == 0:
        return [], neg, pos
    cols = np.unique(idx)
    remap = {c: i for i, c in enumerate(cols)}
    gi, W, hl = gate(Lw[:, cols], np.vectorize(remap.get)(idx), cfg, seed + end)
    gi = cols[gi]                                         # back to universe indices
    h, n, tot = records(U.L[:end], gi, cfg, cfg["rec_months"])
    out = []
    for r in range(len(gi)):
        if n[r] >= cfg["rec_months"] // 2:
            out.append(dict(idx=gi[r], w=W[r], hl=float(hl[r]), held=int(h[r]), n=int(n[r]),
                            rate=h[r] / n[r], ret=float(tot[r])))
    out.sort(key=lambda d: (-d["rate"], -d["ret"]))
    return out, neg, pos


def walk_forward(U, cfg):
    rec = []
    for e in month_ends(len(U.L), cfg["n_tests"], cfg):
        c, _, _ = candidates(U, e, cfg)
        if not c:
            rec.append(dict(end=e, found=False, held=False, ret=0.0))
            continue
        b = c[0]
        f0, f1 = e - cfg["fit_days"], min(e + cfg["step_days"], len(U.L))
        s = U.L[f0:e][:, b["idx"]] @ b["w"]
        h, r = _trade(U.L[e - 1:f1][:, b["idx"]][:, None, :], b["w"][None], s.mean(), s.std(), cfg)
        rec.append(dict(end=e, found=True, held=bool(h[0]), ret=float(r[0]), idx=b["idx"]))
    return rec


def chance(U, cfg):
    rng = np.random.default_rng(cfg["seed"])
    cols = [j for j in range(U.L.shape[1]) if not np.isnan(U.L[:, j]).any()]
    R = np.diff(U.L[:, cols], axis=0)
    mu, cov = R.mean(0), np.cov(R, rowvar=False)
    vals, vecs = np.linalg.eigh(cov)
    root = vecs * np.sqrt(np.clip(vals, 0, None))
    tick = [U.tick[j] for j in cols]
    theme = [U.tick[j] for j in U.theme_set if j in cols]
    runs = []
    for k in range(cfg["sims"]):
        Ls = np.vstack([U.L[:1, cols], U.L[:1, cols] + np.cumsum(mu + rng.standard_normal(R.shape) @ root.T, 0)])
        runs.append(walk_forward(Universe(Ls, tick, theme), cfg))
        print(f"  chance run {k + 1}/{cfg['sims']}", file=sys.stderr, end="\r")
    print(" " * 30, file=sys.stderr, end="\r")
    return runs


def summarize(rec):
    found = [r for r in rec if r["found"]]
    rets = np.array([r["ret"] for r in rec]) if rec else np.zeros(1)
    return dict(n=len(rec), found=len(found), held=sum(r["held"] for r in found),
                total=float(rets.sum()), pos=int((rets > 0).sum()), worst=float(rets.min()))


# ------------------------------------------------------------- report ----


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("theme", nargs="?", default="ai_infrastructure")
    ap.add_argument("--tickers", help="comma-separated tickers instead of a theme file")
    ap.add_argument("--pick", help="evaluate one exact basket (any tickers in the data)")
    ap.add_argument("--data", default="data/prices.csv")
    ap.add_argument("--names", default=None)
    ap.add_argument("--out", default="results")
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", type=type(v), default=v)
    args = ap.parse_args()
    cfg = {k: getattr(args, k) for k in DEFAULTS}

    title, want = read_theme(args.theme, args.tickers)
    prices = pd.read_csv(args.data, index_col=0, parse_dates=True).sort_index().ffill(limit=5)
    span = cfg["fit_days"] + (cfg["rec_months"] + cfg["n_tests"]) * cfg["step_days"]
    prices = prices.iloc[-span:]
    tick = list(prices.columns)
    missing = [t for t in want if t not in tick]
    L, dates = np.log(prices.values), prices.index
    U = Universe(L, tick, want)
    names = core.load_names(args.names or Path(args.data).with_name("tickers.csv"))
    nm = lambda j: names.get(tick[j], (tick[j], ""))[0][:26]
    sec = lambda j: names.get(tick[j], ("", ""))[1][:22]
    stem = "custom" if args.tickers else Path(args.theme).stem
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    n = len(L)
    theme, others = U.window(n, cfg["fit_days"])
    Lw = L[n - cfg["fit_days"]:]
    neg, pos, corr = shortlist(Lw, theme, others, U.mkt, cfg)
    print(f"Theme: {title} - {len(theme)} theme names with 12 months of history"
          + (f" (not in price data: {', '.join(missing)})" if missing else "")
          + f"; other legs searched across {len(others)} names in the whole market.")
    print(f"Fit window {dates[n - cfg['fit_days']]:%b %d %Y} - {dates[-1]:%b %d %Y}.\n")
    cmap = dict(zip(others, corr))
    print("Biggest OPPOSITE-movers to the theme over the past year (market-adjusted correlation):")
    print("   " + ", ".join(f"{tick[j]} {cmap[j]:+.2f}" for j in neg))
    print("Biggest co-movers outside the theme:")
    print("   " + ", ".join(f"{tick[j]} {cmap[j]:+.2f}" for j in pos) + "\n")

    def tagged(j):
        if j in U.theme_set:
            return "theme"
        c = cmap.get(j)
        return "outside" if c is None else ("opposite" if c < 0 else "co-mover")

    if args.pick:
        legs = [t.strip().upper() for t in args.pick.split(",")]
        bad = [t for t in legs if t not in tick]
        if bad:
            sys.exit(f"Not in price data: {', '.join(bad)}")
        idx = np.array([tick.index(t) for t in legs])
        _, W, _ = core.batch_fit(core.Tables(Lw), idx[None], norm="gross")
        s = Lw[:, idx] @ W[0]
        h, nn, t = records(L, idx[None], cfg, cfg["rec_months"])
        picks = [dict(idx=idx, w=W[0], hl=core.ar1_half_life(s), held=int(h[0]), n=int(nn[0]),
                      rate=h[0] / max(1, nn[0]), ret=float(t[0]))]
        print("Evaluating your basket (no search involved, so its track record is a fair test).\n")
    else:
        c, _, _ = candidates(U, n, cfg)
        if not c:
            print("No basket passed the 12-month gate (half-life 3-30 days, balanced, cointegrated). That's a real "
                  "answer: nothing around this theme is moving in a stable relative band right now.")
            return
        picks, seen = [], []
        for r in c:
            if any(len(set(r["idx"]) & s_) > 2 for s_ in seen):
                continue
            seen.append(set(r["idx"]))
            picks.append(r)
            if len(picks) >= cfg["top"]:
                break
        print(f"{len(c)} baskets (1-2 theme names + names from the lists above) passed the 12-month gate; "
              f"ranked by 24-month track record. Showing {len(picks)} distinct ones.\n")

    # reference distribution: comparable baskets (same composition rules), sampled
    outside = neg + [j for j in pos if j not in neg]
    comp = compositions(theme, outside, cfg)
    if len(comp) > 30_000:
        comp = comp[np.random.default_rng(cfg["seed"]).choice(len(comp), 30_000, replace=False)]
    rh, rn, rt = records(L, comp, cfg, cfg["rec_months"])
    good = rn >= cfg["rec_months"] // 2
    pr, pt = rh[good] / rn[good], rt[good]

    rows = []
    for i, b in enumerate(picks):
        s = Lw[:, b["idx"]] @ b["w"]
        z = float((s[-1] - s.mean()) / s.std())
        head = "YOUR BASKET" if args.pick else ("TOP PICK" if i == 0 else f"Alternative {i}")
        print(f"{head}: half-life {core.fmt_hl(b['hl'])}, swing (1 sd) {s.std() * 100:.1f}% of gross")
        for j, w in sorted(zip(b["idx"], b["w"]), key=lambda x: -x[1]):
            print(f"   {'BUY  ' if w > 0 else 'SHORT'} ${abs(w) * 10000:>6,.0f}  {tick[j]:<6} {nm(j):<26} "
                  f"{sec(j):<22} [{tagged(j)}]")
        sig = ("BUY the basket (stretched low)" if z <= -cfg["entry_z"] else
               "SELL the basket (stretched high)" if z >= cfg["entry_z"] else "wait (near its average)")
        print(f"   now: z = {z:+.2f} -> {sig}")
        print(f"   24-month record (refit monthly on prior 12 months, traded next month): held up "
              f"{b['held']}/{b['n']}, P&L summed {b['ret'] * 100:+.0f}% of gross")
        ph, pp = (pr < b["rate"]).mean() * 100, (pt < b["ret"]).mean() * 100
        print(f"      vs {len(pr):,} comparable baskets: held-up rate beats {ph:.0f}%, P&L beats {pp:.0f}% "
              f"(typical basket holds up {np.median(pr) * 100:.0f}% of months)\n")
        rows.append(dict(tickers=[tick[j] for j in b["idx"]], roles=[tagged(j) for j in b["idx"]],
                         w=np.round(b["w"], 4).tolist(), hl=b["hl"], z_now=z, held=b["held"], months=b["n"],
                         ret=b["ret"], pct_held=float(ph), pct_ret=float(pp)))

    rec, sims = [], []
    if not args.pick:
        print("Procedure check: each month over the last 2 years, pick the top basket using only past data, "
              "trade it the next month:")
        rec = walk_forward(U, cfg)
        sr = summarize(rec)
        print(f"   real prices : held up {sr['held']}/{sr['found']} months, P&L summed {sr['total'] * 100:+.0f}% "
              f"of gross, {sr['pos']} positive months, worst month {sr['worst'] * 100:+.1f}%")
        if cfg["sims"] > 0:
            sims = chance(U, cfg)
            ss = [summarize(s_) for s_ in sims]
            ch = np.mean([s_["held"] / max(1, s_["found"]) for s_ in ss]) * 100
            ct = np.mean([s_["total"] for s_ in ss]) * 100
            print(f"   random walks: held up {ch:.0f}% of months, P&L summed {ct:+.0f}% (avg of {cfg['sims']} runs)")
            rh_ = sr["held"] / max(1, sr["found"]) * 100
            if rh_ >= ch + 15 and sr["total"] > 0:
                print("   -> The procedure beats luck on this theme: picks have held up more often than chance.")
            else:
                print("   -> Not clearly better than luck on this theme. Treat picks as ideas; size small.")
        print()
    else:
        print("A record well above comparable baskets is the evidence you want. Picking names for an economic "
              "reason and checking them here avoids the luck that comes with searching.\n")

    rep = dict(theme=title, config=cfg, opposite_movers={tick[j]: float(cmap[j]) for j in neg},
               co_movers={tick[j]: float(cmap[j]) for j in pos}, picks=rows,
               walk_forward=summarize(rec) if rec else None,
               months=[dict(end=str(dates[r["end"] - 1].date()), held=r["held"], ret=r["ret"],
                            tickers=[tick[j] for j in r["idx"]] if r["found"] else []) for r in rec])
    (out / f"theme_{stem}.json").write_text(json.dumps(rep, indent=1, default=float))
    print(f"Full results: {out / f'theme_{stem}.json'}")


if __name__ == "__main__":
    main()
