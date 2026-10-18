#!/usr/bin/env python3
"""publish.py -- toolkit v10: per-run data publication and the outcome-ledger row (spec Stage 6, G4 and G5; unchanged
from v9 apart from the default spec label; the outcome-bridge row is bridge.py's).

Run only after this ticker's Stage 6 is published (the data carry per-token figures; k = j = 1 under SPEC v9).

  python3 publish.py data CFG.json STAGE_DIR OUT_DIR
      Writes a self-contained, replayable copy of the execution's numbers to OUT_DIR:
        runs/<token>.json            every run's MACHINE SUMMARY (run units, as returned; masked units before v9)
        verifications/<token>.json   every verification's JSON block
        config.json                  the Stage-3/5 configuration with k and j, paths rewritten to the copies above
        stage3.json, stage5.json, decision_card.md, fold_log.md   (copied from STAGE_DIR)
        DATA_MANIFEST.md             SHA-256 of every file
      Then replays Stage 3 and Stage 5 from the copy with this toolkit's frozen_arith.py and checks that the
      published BUY, the blind intermediate and the interval reproduce exactly (exit 1 if not).

  python3 publish.py ledger CFG.json STAGE_DIR --date YYYY-MM-DD --data DURABLE_DATA_PATH [--spec v9] [--toolkit SHA]
      Prints this execution's row for OUTCOME_LEDGER_EXECUTIONS.md (spec Appendix K). The row holds no market data;
      outcomes go only to the separate observations file, written by the ledger-update procedure, never by an execution.
"""
import os, sys, json, shutil, hashlib, subprocess, tempfile, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frozen_arith as F

LEDGER_HEADER = ("| ticker | execution date | spec | toolkit manifest SHA-256 | AS_OF | pack as-of date(s) | valuation date(s) "
                 "| published BUY | 80% interval | committee FV | effective margin | quality premium (w) | tail term (w) "
                 "| step tiers | EV rule (tuned Victor) | expectile rule (tuned Max) | EV × (1 − π) "
                 "| implied upside ÷ downside (published / step / EV rule / expectile rule / EV × (1 − π)) "
                 "| mean quality score | seats within 3 points of a cut-off | seats without a valid tree "
                 "| mean break_p | mean break horizon (years) | data |")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def data(cfg_path, stage_dir, out_dir):
    cfg = json.load(open(cfg_path))
    os.makedirs(os.path.join(out_dir, "runs"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "verifications"), exist_ok=True)
    new = json.loads(json.dumps(cfg))
    for r in new["runs"]:
        S = F.load_summary(r["run_file"])
        dst = os.path.join("runs", f"{r['token']}.json")
        json.dump(S, open(os.path.join(out_dir, dst), "w"), indent=1, ensure_ascii=False)
        r["run_file"] = dst
    new["bridge_runs"] = []
    for b in cfg.get("bridge_runs", []):
        S = F.load_summary(b["run_file"])
        dst = os.path.join("runs", f"{b['token']}_bridge.json")
        json.dump(S, open(os.path.join(out_dir, dst), "w"), indent=1, ensure_ascii=False)
        new["bridge_runs"].append(dict(b, run_file=dst))
    vers = {}
    for t, vp in (cfg.get("verifications") or {}).items():
        V = F.load_verification(vp)
        dst = os.path.join("verifications", f"{t}.json")
        json.dump(V, open(os.path.join(out_dir, dst), "w"), indent=1, ensure_ascii=False)
        vers[t] = dst
    new["verifications"] = vers
    json.dump(new, open(os.path.join(out_dir, "config.json"), "w"), indent=1, ensure_ascii=False)
    for f in ("stage3.json", "stage5.json", "decision_card.md", "fold_log.md"):
        if os.path.exists(os.path.join(stage_dir, f)):
            shutil.copyfile(os.path.join(stage_dir, f), os.path.join(out_dir, f))
    # replay from the copy, in a temporary folder, with the paths relative to out_dir
    s5_pub = json.load(open(os.path.join(stage_dir, "stage5.json")))
    with tempfile.TemporaryDirectory() as td:
        new_spec = s5_pub.get("spec") or new.get("spec_version") or F.SPEC
        new["spec_version"] = new_spec
        json.dump(new, open(os.path.join(out_dir, "config.json"), "w"), indent=1, ensure_ascii=False)
        args = []
        for stage in ("stage3", "stage5"):
            r = subprocess.run([sys.executable, os.path.join(HERE, "frozen_arith.py")] + args + [stage, "config.json", td],
                               cwd=out_dir, capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stdout, r.stderr)
                return False
        s5 = json.load(open(os.path.join(td, "stage5.json")))
    checks = [("published BUY", s5["point"], s5_pub["point"]), ("blind intermediate", s5["blind_point"], s5_pub["blind_point"]),
              ("interval low", s5["ci"][0], s5_pub["ci"][0]), ("interval high", s5["ci"][1], s5_pub["ci"][1])]
    ok = all(abs(a - b) <= 1e-9 for _n, a, b in checks)
    lines = ["# DATA_MANIFEST", "", f"Replay from this folder: {'MATCH' if ok else 'MISMATCH'} "
             + "; ".join(f"{n} {a:.6f} vs {b:.6f}" for n, a, b in checks), "", "| file | SHA-256 |", "|---|---|"]
    for root, _d, files in os.walk(out_dir):
        for fn in sorted(files):
            if fn == "DATA_MANIFEST.md":
                continue
            p = os.path.join(root, fn)
            lines.append(f"| `{os.path.relpath(p, out_dir)}` | `{sha(p)}` |")
    open(os.path.join(out_dir, "DATA_MANIFEST.md"), "w").write("\n".join(lines) + "\n")
    print(f"data written to {out_dir}; replay {'MATCH' if ok else 'MISMATCH'}")
    return ok


def ledger(cfg_path, stage_dir, date, data_path, spec=None, toolkit_sha=""):
    cfg = json.load(open(cfg_path))
    s3 = json.load(open(os.path.join(stage_dir, "stage3.json")))
    s5 = json.load(open(os.path.join(stage_dir, "stage5.json")))
    spec = spec or s5.get("spec", "v10")
    seats = s5.get("ledger_seats") or []        # adjusted headline seats of the runs retained for the published BUY
    scores = [x["score"] for x in seats if x.get("score") is not None]
    ps = [x["p"] for x in seats if x.get("p") is not None]
    hz = [x["horizon"] for x in seats if x.get("horizon") is not None]
    pack_dates = sorted((s3.get("frame_categorical") or {}).get("pack_as_of_date", {}).keys())
    lines = s5.get("lines") or {}
    lp = lambda n: f"{lines[n]['point']:.4f}" if (n in lines and lines[n]["point"] is not None) else "n/a"
    kr = lambda x: f"{x:.2f}" if x is not None else "n/a"
    ratios = " / ".join([kr(s5.get("implied_ratio_published"))] +
                        [kr((lines.get(n) or {}).get("implied_ratio")) for n in (F.LINE_STEP, F.LINE_VICTOR, F.LINE_MAX, F.LINE_EVP)])
    near = s5.get("card_near")
    cells = [cfg["ticker"], date, spec, toolkit_sha or "", cfg["as_of"],
             ", ".join(pack_dates) or "see stage3.json", ", ".join(s5.get("vdates", [])),
             f"{s5['point']:.4f}", f"{s5['ci'][0]:.4f}–{s5['ci'][1]:.4f}", f"{s5['fv']:.4f}",
             f"{s5['card_M'] * 100:.2f}%", f"{s5['card_base'] * 100:.2f}%", f"{s5['card_tail'] * 100:.2f}%",
             lp(F.LINE_STEP), lp(F.LINE_VICTOR), lp(F.LINE_MAX), lp(F.LINE_EVP), ratios,
             f"{statistics.mean(scores):.2f}" if scores else "n/a",
             f"{near} of {s5.get('n_seats')}" if near is not None else "n/a",
             str(s5.get("card_notree", "n/a")),
             f"{statistics.mean(ps):.4f}" if ps else "n/a",
             f"{statistics.mean(hz):.2f}" if hz else "n/a", data_path]
    row = "| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |"
    print(row)
    return row


def selftest():
    """Publishes the reference execution (ADBE v7 summaries, run under this toolkit's own arithmetic) to a temporary
    folder and checks that the copy replays to the same published BUY, and that a ledger row is produced."""
    ref = json.load(open(os.path.join(HERE, "replay", "ADBE_v7", "config.json")))
    cwd = os.getcwd()
    os.chdir(HERE)
    try:
        with tempfile.TemporaryDirectory() as td:
            cp = os.path.join(td, "cfg.json")
            json.dump(ref, open(cp, "w"))
            st = os.path.join(td, "stage")
            for stage in ("stage3", "stage5"):
                r = subprocess.run([sys.executable, "frozen_arith.py", stage, cp, st], capture_output=True, text=True)
                if r.returncode:
                    print(r.stdout, r.stderr)
                    return False
            ok1 = data(cp, st, os.path.join(td, "data"))
            row = ledger(cp, st, "2026-01-01", "REF/data")
            ok2 = row.startswith("| ADBE | 2026-01-01 | v10 |") and row.count("|") == LEDGER_HEADER.count("|")
    finally:
        os.chdir(cwd)
    print(f"{'PASS' if ok1 else 'FAIL'}  P1 published data replay to the same BUY, blind point and interval")
    print(f"{'PASS' if ok2 else 'FAIL'}  P2 ledger row has every column of the Appendix-K header")
    print("PUBLISH SELF-TEST " + ("PASSED" if ok1 and ok2 else "FAILED"))
    return ok1 and ok2


if __name__ == "__main__":
    a = sys.argv
    if len(a) >= 2 and a[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if len(a) >= 5 and a[1] == "data":
        sys.exit(0 if data(a[2], a[3], a[4]) else 1)
    if len(a) >= 4 and a[1] == "ledger":
        def opt(k, d=""):
            return a[a.index(k) + 1] if k in a else d
        ledger(a[2], a[3], opt("--date"), opt("--data"), opt("--spec", None), opt("--toolkit"))
        sys.exit(0)
    print(__doc__)
