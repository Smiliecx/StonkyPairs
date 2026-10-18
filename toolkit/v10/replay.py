#!/usr/bin/env python3
"""replay.py -- the replay gate (spec v10, Stage 5b "Replay gate").

  python3 replay.py gate      # self-test (all five modes) + compatibility replay vs expected_v7.json + the stored
                              # own-mode replays replay_v7.1.json, replay_v8.json, replay_v9.json (--spec v9) and
                              # replay_v10.json (v10) + the v9 N2 fixture; exit 1 on failure
  python3 replay.py v10       # replays the reference execution under this toolkit's own arithmetic (SPEC v10: Simon out
                              # of the roster, every other seat as reported) and writes replay/ADBE_v7/replay_v10.*
  python3 replay.py v9        # the same under SPEC v9 arithmetic (replay_v9.*; kept from toolkit v9, never re-run)
  python3 replay.py v8        # the same under SPEC v8 arithmetic (replay_v8.*; kept from toolkit v8, never re-run)
  python3 replay.py v71       # the same under SPEC v7.1 arithmetic (replay_v7.1.*; kept from toolkit v7.1)

The reference execution (replay/ADBE_v7/) is orchestrator-only (Rule O-1, files from prior tickers).
Tolerances: published figures 0.005 unit; ledger and Stage-3 rows 0.01 unit; t, p, beta_k, beta_j 1e-4.
The expected values (replay/ADBE_v7/expected_v7.json) are pinned by SHA-256 in the spec; no version may change them.
"""
import os, sys, json, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "replay", "ADBE_v7")
PINNED_EXPECTED_SHA = "908de67b922f0be1346864d3126fd538c352b05c4e8a4e2f80d4145c946c96b6"   # spec v7.1 and v8, Stage 5b "Replay gate"


def run(spec, outdir):
    cfg = json.load(open(os.path.join(REF, "config.json")))
    cfg["spec_version"] = spec
    cpath = os.path.join(outdir, "cfg.json")
    json.dump(cfg, open(cpath, "w"))
    for stage in ("stage3", "stage5"):
        r = subprocess.run([sys.executable, os.path.join(HERE, "frozen_arith.py"), "--spec", spec, stage, cpath, outdir],
                           cwd=HERE, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"{stage} failed:\n{r.stdout}\n{r.stderr}")
    return (json.load(open(os.path.join(outdir, "stage3.json"))), json.load(open(os.path.join(outdir, "stage5.json"))))


def gate():
    ok = True
    lines = []
    for spec in ("v10", "v9", "v8", "v7.1", "v7"):
        r = subprocess.run([sys.executable, os.path.join(HERE, "frozen_arith.py"), "--spec", spec, "selftest"],
                           cwd=HERE, capture_output=True, text=True)
        passed = r.returncode == 0
        ok &= passed
        lines.append(f"{'PASS' if passed else 'FAIL'}  self-test, spec {spec}")
    import hashlib
    h = hashlib.sha256(open(os.path.join(REF, "expected_v7.json"), "rb").read()).hexdigest()
    good = h == PINNED_EXPECTED_SHA
    ok &= good
    lines.append(f"{'PASS' if good else 'FAIL'}  expected_v7.json SHA-256 {h} equals the value pinned in the spec")
    exp = json.load(open(os.path.join(REF, "expected_v7.json")))
    with tempfile.TemporaryDirectory() as td:
        s3, s5 = run("v7", td)
    checks = [("blind intermediate", s5["blind_point"], exp["blind_point"], 0.005),
              ("published BUY", s5["point"], exp["point"], 0.005),
              ("interval low", s5["ci"][0], exp["ci"][0], 0.005), ("interval high", s5["ci"][1], exp["ci"][1], 0.005),
              ("replication low", s5["rep"][0], exp["rep"][0], 0.005), ("replication high", s5["rep"][1], exp["rep"][1], 0.005),
              ("committee fair value", s5["fv"], exp["fv"], 0.005), ("run-noise s (adjusted)", s5["s"], exp["s"], 0.005),
              ("run-noise s_w (blind)", s3["s_w"], exp["s_w"], 0.005)]
    got_led = {r["row"]: r["point"] for r in s5["ledger"]}
    for k, v in exp["ledger"].items():
        checks.append(("ledger: " + k, got_led.get(k), v, 0.01))
    for k, v in exp["blind_rows"].items():
        checks.append(("Stage-3 row: " + k, s3["blind_rows"].get(k, {}).get("point"), v, 0.01))
    for name, got, want, tol in checks:
        good = got is not None and abs(got - want) <= tol
        ok &= good
        lines.append(f"{'PASS' if good else 'FAIL'}  {name}: {got} vs {want} (tol {tol})")
    for name, got, want in (("contrast t (adjusted)", s5["contrast_adj"]["t"], exp["contrast_t"]),
                            ("contrast p (adjusted)", s5["contrast_adj"]["p"], exp["contrast_p"]),
                            ("beta_k", s3["memory"]["beta_k"], exp["beta_k"]), ("beta_j", s3["memory"]["beta_j"], exp["beta_j"]),
                            ("memory permutation p", s3["memory"]["p_perm"], exp["memory_p"])):
        good = got is not None and abs(got - want) <= 1e-4
        ok &= good
        lines.append(f"{'PASS' if good else 'FAIL'}  {name}: {got} vs {want} (tol 1e-4)")
    good = s5["headline_sentence"] == exp["headline_sentence"]
    ok &= good
    lines.append(f"{'PASS' if good else 'FAIL'}  headline sentence identical")
    # own-mode replays against the stored replay_v8.json and replay_v9.json (SHA-256 in TOOLKIT_MANIFEST): they pin the v8
    # arithmetic (in --spec v8 mode) and the v9 arithmetic; v9 also checks every ledger row, including the new N2 row
    for tag in ("v7.1", "v8", "v9", "v10"):   # review: v7.1 pinned too, and every stored ledger row
        stored_p = os.path.join(REF, f"replay_{tag}.json")
        if not os.path.exists(stored_p):
            ok = False
            lines.append(f"FAIL  replay_{tag}.json missing (run `replay.py {tag}` once when the version is built, then list it in the manifest)")
            continue
        st = json.load(open(stored_p))
        with tempfile.TemporaryDirectory() as td:
            _s3v, s5v = run(tag, td)
        pairs = [(f"{tag} published BUY", s5v["point"], st["published"]), (f"{tag} blind intermediate", s5v["blind_point"], st["blind"]),
                 (f"{tag} interval low", s5v["ci"][0], st["ci"][0]), (f"{tag} interval high", s5v["ci"][1], st["ci"][1]),
                 (f"{tag} committee fair value", s5v["fv"], st["fv"]),
                 (f"{tag} implied ratio (published)", s5v.get("implied_ratio_published"), st.get("implied_ratio_published"))]
        for name, x in (st.get("lines") or {}).items():
            pairs.append((f"{tag} line: " + name, (s5v["lines"].get(name) or {}).get("point"), x.get("point")))
        if True:
            got_l = {r["row"]: r["point"] for r in s5v["ledger"]}
            for name, x in (st.get("ledger") or {}).items():
                pairs.append((f"{tag} ledger: " + name, got_l.get(name), x.get("point")))
        for name, got, want in pairs:
            if got is None and want is None and "implied ratio" in name and tag == "v7.1":
                continue   # v7.1 has no margin-rule lines or implied ratios
            good = got is not None and want is not None and abs(got - want) <= 0.005
            ok &= good
            lines.append(f"{'PASS' if good else 'FAIL'}  {name}: {got} vs stored {want} (tol 0.005)")
    # v9 N2 fixture (review): a constructed six-run case with an independent hand computation of the
    # alternative-denominator row in Stage 3 and Stage 5 (F1 normalisation, AT CAP, NO BUY, zero weight, a missing
    # field, a non-positive alternative, patched runs)
    fx = os.path.join(HERE, "replay", "V9_N2")
    exp9 = json.load(open(os.path.join(fx, "expected.json")))
    with tempfile.TemporaryDirectory() as td:
        for stage in ("stage3", "stage5"):
            r = subprocess.run([sys.executable, os.path.join(HERE, "frozen_arith.py"), "--spec", "v9", stage,
                                os.path.join(fx, "config.json"), td], cwd=HERE, capture_output=True, text=True)
            if r.returncode != 0:
                raise SystemExit(f"N2 fixture {stage} failed:\n{r.stdout}\n{r.stderr}")
        f3, f5 = json.load(open(os.path.join(td, "stage3.json"))), json.load(open(os.path.join(td, "stage5.json")))
    altrow = "Alternative denominator: every seat on its run's alternative denominator"
    l5 = {r["row"]: r["point"] for r in f5["ledger"]}
    pairs = [("N2 fixture Stage-3 alternative point", f3["blind_rows"][altrow]["point"], exp9["stage3"]["alt_point"]),
             ("N2 fixture Stage-3 blind point", f3["blind_point"], exp9["stage3"]["point"]),
             ("N2 fixture Stage-5 alternative point", l5.get(altrow), exp9["stage5"]["alt_point"]),
             ("N2 fixture Stage-5 published point", f5["point"], exp9["stage5"]["point"])]
    pairs += [(f"N2 fixture Stage-3 run {t}", f3["v9"]["alt"][t]["headline"], v) for t, v in exp9["stage3"]["per_run"].items()]
    pairs += [(f"N2 fixture Stage-5 run {t}", f5["alt_card"]["per_run"][t]["headline"], v) for t, v in exp9["stage5"]["per_run"].items()]
    for name, got, want in pairs:
        good = got is not None and abs(got - want) <= 1e-6
        ok &= good
        lines.append(f"{'PASS' if good else 'FAIL'}  {name}: {got} vs hand {want} (tol 1e-6)")
    print("\n".join(lines))
    print("REPLAY GATE " + ("PASSED" if ok else "FAILED"))
    return ok


def own(spec="v7.1", tag="v7.1"):
    exp = json.load(open(os.path.join(REF, "expected_v7.json")))
    with tempfile.TemporaryDirectory() as td:
        s3, s5 = run(spec, td)
        card = open(os.path.join(td, "decision_card.md")).read()
        tables = open(os.path.join(td, "stage5_tables.md")).read()
    out = dict(published=s5["point"], blind=s5["blind_point"], ci=s5["ci"], rep=s5["rep"], fv=s5["fv"], s=s5["s"],
               retained=s5["retained"], v7_published=exp["point"], v7_blind=exp["blind_point"],
               runs=[{k: r[k] for k in ("token", "dossier", "blind", "adjusted", "wfv_adj")} for r in s5["runs"]],
               ledger={r["row"]: dict(point=r["point"], change=r["change"]) for r in s5["ledger"]},
               v71=s3.get("v71"), card_cap=s5.get("card_cap"), card_acq=s5.get("card_acq"),
               card_acq_undeclared=s5.get("card_acq_undeclared"), card_denom=s5.get("card_denom"),
               stage3_log=s3["log"], stage5_log=s5["log"], headline_sentence=s5["headline_sentence"])
    if spec in ("v8", "v9", "v10"):
        out.update(lines=s5.get("lines"), card_near=s5.get("card_near"), card_notree=s5.get("card_notree"),
                   implied_ratio_published=s5.get("implied_ratio_published"), stage3_v8=s3.get("v8"))
    json.dump(out, open(os.path.join(REF, f"replay_{tag}.json"), "w"), indent=1, default=str, ensure_ascii=False)
    open(os.path.join(REF, f"replay_{tag}_card.md"), "w").write(card)
    open(os.path.join(REF, f"replay_{tag}_tables.md"), "w").write(tables)
    print(json.dumps({k: out[k] for k in ("published", "blind", "ci", "fv", "v7_published", "v7_blind", "card_cap",
                                          "card_denom")}, indent=1))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gate"
    if cmd == "gate":
        sys.exit(0 if gate() else 1)
    if cmd == "v71":
        own("v7.1", "v7.1")
        sys.exit(0)
    if cmd == "v8":
        own("v8", "v8")
        sys.exit(0)
    if cmd == "v9":
        own("v9", "v9")
        sys.exit(0)
    if cmd == "v10":
        own("v10", "v10")
        sys.exit(0)
    print(__doc__)
