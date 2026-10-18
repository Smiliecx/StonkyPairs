#!/usr/bin/env python3
"""bridge.py -- toolkit v10: the outcome-bridge rows and the validation comparison (spec v10, T6; Stage 6;
Appendix G validation block; Appendix K, OUTCOME_BRIDGE.md).

Reads only a published per-run data folder (G5: config.json, runs/, verifications/, stage5.json) and recomputes with
this toolkit's frozen_arith.py in the folder's own spec mode. Holds no market data.

  python3 bridge.py row DATA_DIR --date YYYY-MM-DD [--note TEXT] [--append OUTCOME_BRIDGE.md]
      Prints this execution's OUTCOME_BRIDGE.md row: the published BUY (recomputed; it must equal stage5.json's within
      0.005, or no row is written and the script exits 1), the BUY with every seat on its fair_value_macro_base
      (required margin held; as with the rebase patch, the break value is not moved), the same without the seat named Simon (seat and weight dropped), the debt
      row (v10 only), the seats off the macro base and Walter's mean multiplier (v10 only). Every BUY is the Stage-5
      point on the Stage-5b patched summaries. With --append, the row is appended (the header is written first if the
      file does not exist).

  python3 bridge.py compare BASELINE_DATA_DIR NEW_DATA_DIR --baseline SHA256 [--out VALIDATION.md]
      The pre-registered validation comparison (spec Appendix G): bridge change, realised change, realised share with
      its 80% interval, unexplained share, and the channel means with Welch's t. Writes markdown.

  python3 bridge.py selftest
"""
import os, sys, json, math, statistics, copy, hashlib, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frozen_arith as F

HEADER = ("| ticker | execution date | spec | data manifest SHA-256 | published BUY (recomputed) "
          "| BUY, every seat on its macro-base fair value | BUY, macro base, without Simon | debt row (v10 only) "
          "| seats off the macro base | Walter's mean multiplier (v10 only) | notes |")
SEP = "|---|---|---|---|---|---|---|---|---|---|---|"
UNSEATED_FOR_BRIDGE = "simon"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load(data_dir):
    """Folds every run of a published data folder in its own spec mode. Returns a dict of runs and the published stage5."""
    cfg = json.load(open(os.path.join(data_dir, "config.json")))
    s5 = json.load(open(os.path.join(data_dir, "stage5.json")))
    spec = s5.get("spec") or cfg.get("spec_version") or "v9"
    if spec not in F.SPECS:
        raise SystemExit(f"unknown spec {spec}")
    F.SPEC = spec
    runs = []
    for r in cfg["runs"]:
        S = F.load_summary(os.path.join(data_dir, r["run_file"]))
        vp = (cfg.get("verifications") or {}).get(r["token"])
        ver = F.load_verification(os.path.join(data_dir, vp)) if vp else {"rulings": []}
        fo = F.fold_run(S, ver, [], "")
        adj = fo["summary"]
        runs.append(dict(token=r["token"], dossier=r["dossier"], k=float(r.get("k", 1.0)), blind_summary=S,
                         summary=adj, seats=F.recompute_run(adj, []), blind_seats=F.recompute_run(S, []),
                         adjusted=fo["adjusted"] * float(r.get("k", 1.0))))
    return dict(cfg=cfg, s5=s5, spec=spec, runs=runs, dir=data_dir)


def macro_seats(seats, drop=None, counter=None):
    """Every headline seat on its fair_value_macro_base: fair value and BUY scaled by fvmb / fv, required margin held
    (as with the rebase patch the break value is held, so the margin is unchanged). A seat without the field keeps its fair value."""
    out = []
    for s in seats:
        t = dict(s)
        if drop and s["name"] == drop:
            t["irr"] = True
        elif not s["irr"] and not s["no_buy"] and s.get("buy") is not None:
            m = s.get("_fvmb")
            if m is None:
                if counter is not None:
                    counter["missing"] += 1
            else:
                t["fv"], t["buy"] = m, m * (1 - s["required"])
        out.append(t)
    return out


def attach_fvmb(run):
    # read fair_value_macro_base from the F1-normalised summary, the one recompute_run values
    S, _r = F.normalise_denominator(run["summary"], []) if F.v71() else (run["summary"], 1.0)
    for inv, s in zip(S.get("investors", []), run["seats"]):
        s["_fvmb"] = F.num(inv.get("fair_value_macro_base"))


def point(vals):
    return F.trimmed_point(vals)[0]


def normalised_fvmb(summary):
    """fair_value_macro_base by seat, from the F1-normalised summary (the values recompute_run uses)."""
    S, _r = F.normalise_denominator(summary, []) if F.v71() else (summary, 1.0)
    return {F.canon(i.get("investor")): F.num(i.get("fair_value_macro_base")) for i in S.get("investors", [])}


def bridge_figures(D):
    runs = D["runs"]
    for r in runs:
        attach_fvmb(r)
    pub = point([r["adjusted"] for r in runs])
    cnt = dict(missing=0)
    mb = point([F.headline_of(macro_seats(r["seats"], None, cnt)) * r["k"] for r in runs])
    cnt2 = dict(missing=0)
    nos = point([F.headline_of(macro_seats(r["seats"], UNSEATED_FOR_BRIDGE, cnt2)) * r["k"] for r in runs])
    keep = F.trimmed_point([r["adjusted"] for r in runs])[1]
    off = 0
    for i in keep:
        r = runs[i]
        mbr = F.market_base(D["cfg"].get("market_inputs"), r["blind_summary"].get("frame"))
        fvmb = normalised_fvmb(r["blind_summary"])
        for s in F.headline_seats(r["blind_seats"]):
            off += bool(F.off_base(dict(s, fv_mb_rep=fvmb.get(s["name"])), mbr))
    led = {x["row"]: x for x in D["s5"].get("ledger", [])}
    debt = led.get(F.ROW_DEBT, {}).get("point") if D["spec"] == "v10" else None
    if D["spec"] == "v10" and not (D["s5"].get("debt_card") or {}).get("measured"):
        debt = None
    wm = D["s5"].get("card_wmult") if D["spec"] == "v10" else None
    return dict(published=pub, macro=mb, macro_no_simon=nos, missing=cnt["missing"], debt=debt, off=off, wmult=wm,
                published_file=D["s5"]["point"], keep=keep)


def f4(x):
    return f"{x:.4f}" if x is not None else "n/a"


def row(data_dir, date, note=""):
    D = load(data_dir)
    b = bridge_figures(D)
    if abs(b["published"] - b["published_file"]) > 0.005:
        print(f"published BUY recomputed {b['published']:.6f} differs from stage5.json {b['published_file']:.6f}: no row written")
        return None
    man = os.path.join(data_dir, "DATA_MANIFEST.md")
    notes = [n for n in (note, f"seats without fair_value_macro_base kept at fair value: {b['missing']}" if b["missing"] else "")
             if n]
    cells = [D["cfg"]["ticker"], date, D["spec"], sha(man) if os.path.exists(man) else "n/a", f4(b["published"]),
             f4(b["macro"]), f4(b["macro_no_simon"]), f4(b["debt"]), str(b["off"]),
             f"{b['wmult']:.3f}" if b["wmult"] is not None else "n/a", "; ".join(notes)]
    r = "| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |"
    return r


def run_channels(D, drop=None, debt_fv=False):
    """Per retained run (published retained set), seat-weighted means on the patched summaries. drop: a seat name left
    out (the baseline's Simon); debt_fv: committee fair value on the debt-row seats (v10: the v9 debt count)."""
    out = []
    keep = F.trimmed_point([r["adjusted"] for r in D["runs"]])[1]
    for i in keep:
        r = D["runs"][i]
        seats = [dict(s, irr=True) if (drop and s["name"] == drop) else s for s in r["seats"]]
        invs = r["summary"].get("investors", [])
        for inv, s in zip(invs, seats):
            s.setdefault("tg", F.num(inv.get("terminal_growth")))
            s.setdefault("fg", F.forecast_growth(inv.get("forecast_5y")))
        fv_seats = F.cf_debt(seats, r["summary"].get("frame"))[0] if debt_fv else seats
        w = F.wfv_of(fv_seats)
        out.append(dict(token=r["token"], fv=w * r["k"] if w is not None else None,
                        terminal_growth=F.wmean_field(seats, "tg"), forecast_growth=F.wmean_field(seats, "fg"),
                        quality_score=F.wmean_field(seats, "score"), break_p=F.wmean_field(seats, "p"),
                        tail=F.wmean_field(seats, "tail")))
    return out


def verify_folder(data_dir, want_sha=None):
    """Appendix G: every file against DATA_MANIFEST.md, and the manifest against <BASELINE>. Returns (ok, reasons)."""
    man = os.path.join(data_dir, "DATA_MANIFEST.md")
    if not os.path.exists(man):
        return False, ["no DATA_MANIFEST.md"]
    why = []
    if want_sha and sha(man) != want_sha:
        why.append(f"DATA_MANIFEST.md SHA-256 {sha(man)} is not the pre-registered {want_sha}")
    import re
    for m in re.finditer(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", open(man, encoding="utf-8").read(), re.M):
        p = os.path.join(data_dir, m.group(1))
        if not os.path.exists(p) or sha(p) != m.group(2):
            why.append(f"{m.group(1)} missing or not its manifest hash")
    return not why, why


def welch(a, b):
    a = [x for x in a if x is not None]
    b = [x for x in b if x is not None]
    if len(a) < 2 or len(b) < 2:
        return None, None
    va, vb = statistics.variance(a) / len(a), statistics.variance(b) / len(b)
    if va + vb <= 0:
        return None, None
    t = (statistics.mean(b) - statistics.mean(a)) / math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    return t, df


def compare(base_dir, new_dir, baseline_sha=None, check_manifest=True):
    B = load(base_dir)
    bb = bridge_figures(B)
    base_s5 = B["s5"]
    okb, whyb = verify_folder(base_dir, baseline_sha) if check_manifest else (True, [])
    if abs(bb["published"] - bb["published_file"]) > 0.005:
        okb = False
        whyb.append(f"baseline published BUY recomputed {bb['published']:.6f} differs from its stage5.json {bb['published_file']:.6f}")
    base_ch = run_channels(B, drop=UNSEATED_FOR_BRIDGE)
    N = load(new_dir)
    if N["spec"] != "v10":
        raise SystemExit("the new execution must be a v10 execution")
    nb = bridge_figures(N)
    new_s5 = N["s5"]
    new_ch = run_channels(N, debt_fv=True)
    dB = bb["macro_no_simon"] - bb["published"]
    debt = nb["debt"] if nb["debt"] is not None else nb["published"]
    dR = debt - bb["published"]
    hw = math.sqrt(new_s5["hw"] ** 2 + base_s5["hw"] ** 2)
    if not okb or abs(dB) < 2 * hw:
        R = lo = hi = None
    else:
        R = dR / dB
        lo, hi = sorted(((dR - hw) / dB, (dR + hw) / dB))
    na = (lambda x: "n/a") if not okb else (lambda x: x)
    L = ["# VALIDATION (spec v10, Appendix G validation block)", "",
         f"Baseline data manifest SHA-256: `{sha(os.path.join(base_dir, 'DATA_MANIFEST.md')) if os.path.exists(os.path.join(base_dir, 'DATA_MANIFEST.md')) else 'n/a'}` "
         f"(spec {B['spec']}). New execution: spec {N['spec']}. No figure here uses a market price, and none changes a published figure.",
         "" if okb else "**Baseline check failed:** " + "; ".join(whyb) + ". Bridge and channel lines read n/a; only the published BUYs and fair values are compared.",
         "", "| quantity | value |", "|---|---|",
         f"| baseline published BUY | {bb['published_file']:.4f} |",
         f"| baseline BUY, every seat on its macro-base fair value | {na(f4(bb['macro']))} |",
         f"| baseline BUY, macro base, without Simon | {na(f4(bb['macro_no_simon']))} |",
         f"| bridge change Δ_B | {na(f'{dB:+.4f}')} |",
         f"| new published BUY | {nb['published']:.4f} |",
         f"| baseline committee fair value / new committee fair value | {base_s5['fv']:.4f} / {new_s5['fv']:.4f} |",
         f"| new debt row (net claims deducted again, the v9 count) | {f4(nb['debt'])} |",
         f"| T2 correction (published − debt row) | {(nb['published'] - debt):+.4f} |",
         f"| realised change Δ_R (debt row − baseline published) | {na(f'{dR:+.4f}')} |",
         f"| 80% half-width (the two interval half-widths in quadrature) | {hw:.4f} |",
         f"| realised share R = Δ_R ÷ Δ_B (n/a when \\|Δ_B\\| < 2 × half-width) | {f4(R)} (80% interval {f4(lo)} to {f4(hi)}) |",
         f"| unexplained share 1 − R | {f4(1 - R) if R is not None else 'n/a'} |",
         f"| seats off the macro base in the new execution (retained runs) | {nb['off']} |", "",
         "R is not a measure of migration alone: besides any move between channels, Δ_R contains Walter's new grade, the "
         "mapped-dimension rule, the register, the closed ERP route and run noise.", "",
         "## Channels (seat-weighted means on the Stage-5b patched summaries, over each execution's retained runs; baseline without Simon; new committee fair value on its debt-row seats; descriptive)", "",
         "| channel | baseline mean | new mean | difference | Welch t (df) |", "|---|---|---|---|---|"]
    for key, name in (("fv", "committee fair value (weighted FV)"), ("terminal_growth", "terminal growth (%)"),
                      ("forecast_growth", "five-year forecast growth (%)"), ("quality_score", "quality score"),
                      ("break_p", "break_p"), ("tail", "tail term")):
        if not okb:
            L.append(f"| {name} | n/a | n/a | n/a | n/a |")
            continue
        a = [x[key] for x in base_ch]
        b = [x[key] for x in new_ch]
        ma = statistics.mean([x for x in a if x is not None]) if any(x is not None for x in a) else None
        mb_ = statistics.mean([x for x in b if x is not None]) if any(x is not None for x in b) else None
        t, df = welch(a, b)
        L.append(f"| {name} | {f4(ma)} | {f4(mb_)} | {f4((mb_ - ma) if (ma is not None and mb_ is not None) else None)} | "
                 + (f"{t:+.3f} ({df:.1f})" if t is not None else "n/a") + " |")
    if bb["missing"]:
        L.append(f"\nBaseline seats without fair_value_macro_base kept at their fair value: {bb['missing']}.")
    return "\n".join(L) + "\n", dict(dB=dB, dR=dR, R=R, lo=lo, hi=hi, hw=hw, ok=okb, why=whyb)


def selftest():
    ok_all = True
    lines = []

    def check(name, cond, detail=""):
        nonlocal ok_all
        ok_all &= bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")
    fx = os.path.join(HERE, "replay", "ICE_v9")
    exp = json.load(open(os.path.join(fx, "expected_bridge.json")))
    saved = F.SPEC
    try:
        D = load(fx)
        b = bridge_figures(D)
        check("17a ICE v9 fixture: published BUY recomputed from the per-run data", abs(b["published"] - exp["published"]) < 1e-6,
              f"{b['published']} vs {exp['published']}")
        # independent hand computation of the macro-base and without-Simon rows, from the patched summaries alone
        hand_mb, hand_ns = [], []
        for r in D["runs"]:
            S, _ = F.normalise_denominator(r["summary"], [])
            fmb = {F.canon(i.get("investor")): F.num(i.get("fair_value_macro_base")) for i in S.get("investors", [])}
            num_a = den_a = num_b = den_b = 0.0
            for s in r["seats"]:
                if s["irr"] or s["no_buy"] or s.get("buy") is None or not (s["w"] or 0) > 0:
                    continue
                v = fmb.get(s["name"]) if fmb.get(s["name"]) is not None else s["fv"]
                bu = v * (1 - s["required"])
                num_a += s["w"] * bu
                den_a += s["w"]
                if s["name"] != "simon":
                    num_b += s["w"] * bu
                    den_b += s["w"]
            hand_mb.append(num_a / den_a)
            hand_ns.append(num_b / den_b)
        hm, hn = point(hand_mb), point(hand_ns)
        check("17b ICE v9 fixture: macro-base row equals the hand computation and the stored value",
              abs(b["macro"] - hm) < 1e-9 and abs(b["macro"] - exp["macro"]) < 1e-6, f"{b['macro']} vs hand {hm}")
        check("17c ICE v9 fixture: without-Simon row equals the hand computation and the stored value",
              abs(b["macro_no_simon"] - hn) < 1e-9 and abs(b["macro_no_simon"] - exp["macro_no_simon"]) < 1e-6,
              f"{b['macro_no_simon']} vs hand {hn}")
        check("17d ICE v9 fixture: seats off the macro base counted (retained runs)", b["off"] == exp["off"], f"{b['off']}")
        rw = row(fx, "2026-10-13")
        check("17e bridge row has every column of the Appendix-K header", rw is not None and rw.count("|") == HEADER.count("|"), str(rw))
        # compare on a constructed pair: the same ICE runs re-computed in v10 mode (Simon out of the roster; the v9
        # summaries carry no net claims, so the debt row is unmeasured and equals the published BUY)
        import shutil, subprocess
        with tempfile.TemporaryDirectory() as td:
            nd = os.path.join(td, "new")
            shutil.copytree(fx, nd)
            cfg = json.load(open(os.path.join(nd, "config.json")))
            cfg["spec_version"] = "v10"
            json.dump(cfg, open(os.path.join(nd, "config.json"), "w"))
            for st in ("stage3", "stage5"):
                rr = subprocess.run([sys.executable, os.path.join(HERE, "frozen_arith.py"), st, "config.json", "out"],
                                    cwd=nd, capture_output=True, text=True)
                if rr.returncode:
                    raise SystemExit(rr.stdout + rr.stderr)
            shutil.copyfile(os.path.join(nd, "out", "stage5.json"), os.path.join(nd, "stage5.json"))
            new_pub = json.load(open(os.path.join(nd, "stage5.json")))["point"]
            md, c = compare(fx, nd, check_manifest=False)
        R_hand = (new_pub - exp["published"]) / (exp["macro_no_simon"] - exp["published"])
        check("17f compare: Δ_B, Δ_R and the realised and unexplained shares equal the hand computation",
              abs(c["dB"] - (exp["macro_no_simon"] - exp["published"])) < 1e-9 and abs(c["dR"] - (new_pub - exp["published"])) < 1e-9
              and abs(c["R"] - R_hand) < 1e-9 and "unexplained share 1 − R" in md, f"R={c['R']} hand={R_hand}")
        # baseline custody: a folder that fails its manifest (one file edited) gives n/a lines
        with tempfile.TemporaryDirectory() as td:
            bd = os.path.join(td, "base")
            shutil.copytree(fx, bd)
            rows_ = ["# DATA_MANIFEST", "", "| file | SHA-256 |", "|---|---|"]
            for root, _d, files in os.walk(bd):
                for fn in sorted(files):
                    p = os.path.join(root, fn)
                    rows_.append(f"| `{os.path.relpath(p, bd)}` | `{sha(p)}` |")
            open(os.path.join(bd, "DATA_MANIFEST.md"), "w").write("\n".join(rows_) + "\n")
            good, _ = verify_folder(bd, sha(os.path.join(bd, "DATA_MANIFEST.md")))
            wrong_sha, _ = verify_folder(bd, "0" * 64)
            rp = os.path.join(bd, "runs", sorted(os.listdir(os.path.join(bd, "runs")))[0])
            open(rp, "a").write(" ")
            tampered, why_t = verify_folder(bd, sha(os.path.join(bd, "DATA_MANIFEST.md")))
        check("17g baseline custody: a folder matching its manifest and <BASELINE> passes; a wrong <BASELINE> or an edited "
              "file fails", good and not wrong_sha and not tampered, "; ".join(why_t))
    finally:
        F.SPEC = saved
    print("\n".join(lines))
    print("BRIDGE SELF-TEST " + ("PASSED" if ok_all else "FAILED"))
    return ok_all


if __name__ == "__main__":
    a = sys.argv
    def opt(k, d=""):
        return a[a.index(k) + 1] if k in a else d
    if len(a) >= 2 and a[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if len(a) >= 3 and a[1] == "row":
        r = row(a[2], opt("--date"), opt("--note"))
        if r is None:
            sys.exit(1)
        print(r)
        ap = opt("--append")
        if ap:
            new = not os.path.exists(ap)
            with open(ap, "a") as f:
                if new:
                    f.write("# OUTCOME_BRIDGE\n\n" + HEADER + "\n" + SEP + "\n")
                f.write(r + "\n")
        sys.exit(0)
    if len(a) >= 4 and a[1] == "compare":
        md, _ = compare(a[2], a[3], opt("--baseline") or None)
        out = opt("--out")
        if out:
            open(out, "w").write(md)
        print(md)
        sys.exit(0)
    print(__doc__)
