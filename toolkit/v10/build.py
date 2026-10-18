#!/usr/bin/env python3
"""build.py -- toolkit v10 clean-room builder (spec Rule O-1, Appendix H). SPEC v9 (N1): there is no Stage-1d probe;
Stage-2/4/4b templates still carry MASK_LABEL and MASK_UNIT (fixed labels), while the packs name the company.
SPEC v10 (T5): the staged FRAMEWORK copy is hash-checked against the manifest's FRAMEWORK_v10.md (checks.py framework)
every time it is put into a clean room; a mismatch raises DiffFailure and nothing is launched.

Every text a subagent receives is instantiated from its spec template by tpl.instantiate, diffed by tpl.diff
before it is written or sent, and every launch prompt is saved as sent. A text that fails its diff raises
DiffFailure and is never written. No orchestrator text enters any file.

Usage (from the orchestrator's own glue, never edited per ticker):
    import build
    B = build.Builder(cfg)            # cfg: see Builder.__init__
    job = B.run(token, pack_name, pack_text_or_path)   -> dict(dir, out, prompt, prompt_file)
    ...send job["prompt"] verbatim to a subagent...
"""
import os, sys, shutil, secrets

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tpl
import checks

MASK_LABEL = "the Company"


class DiffFailure(Exception):
    pass


def opaque(prefix="d", n=6):
    return prefix + secrets.token_hex(n // 2 + 1)[:n]


class Builder:
    def __init__(self, cfg):
        """cfg keys:
            root          opaque clean-room root (e.g. /work/wc7603d45), created if absent
            framework     path of dossier/FRAMEWORK_stage.md
            market_inputs path of the season MARKET_INPUTS file (staged as MARKET_INPUTS.md)
            prompts_dir   final/launch_prompts
            diff_log      final/stage05_diff.jsonl (one JSON line per diffed text)
            mask_unit     e.g. "USD per share"
        """
        self.c = cfg
        os.makedirs(cfg["root"], exist_ok=True)
        os.makedirs(cfg["prompts_dir"], exist_ok=True)

    # ------------------------------------------------------------------ helpers
    def _framework(self):
        """v10 T5: the staged FRAMEWORK must equal the toolkit's FRAMEWORK_v10.md before any subagent receives it."""
        ok, why = checks.verify_framework(self.c["framework"])
        if not ok:
            raise DiffFailure(f"staged FRAMEWORK fails its manifest hash (checks.py framework): {why}")
        return self.c["framework"]

    def _dir(self, d):
        p = os.path.join(self.c["root"], d)
        os.makedirs(os.path.join(p, "scratch"), exist_ok=True)
        return p

    def _log(self, label, name, res):
        import json
        with open(self.c["diff_log"], "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(text=label, template=name, ok=res["ok"], reason=res["reason"]), ensure_ascii=False) + "\n")

    def _text(self, name, slots, label, masked=False):
        t = tpl.instantiate(name, slots)
        res = tpl.diff(name, t, masked_stage=masked)
        self._log(label, name, res)
        if not res["ok"]:
            raise DiffFailure(f"{label}: {res['reason']}")
        return t

    @staticmethod
    def _put(p, name, text=None, src=None, mode=None):
        dst = os.path.join(p, name)
        if src is not None:
            shutil.copyfile(src, dst)
        else:
            open(dst, "w", encoding="utf-8").write(text)
        if mode:
            os.chmod(dst, mode)
        return dst

    def _pack(self, p, name, src_or_text):
        if isinstance(src_or_text, str) and len(src_or_text) < 4096 and os.path.exists(src_or_text):
            return self._put(p, name, src=src_or_text)
        return self._put(p, name, src_or_text)

    def _launch(self, lname, files, slots, stage, token, masked=False):
        lp = self._text(lname, dict(slots, FILES="\n".join(files)), f"launch {stage} {token}", masked)
        pf = os.path.join(self.c["prompts_dir"], f"{stage}_{token}.txt")
        open(pf, "w", encoding="utf-8").write(lp)
        return lp, pf

    def stage2_text(self, pack_name):
        return self._text("B", {"TICKER": MASK_LABEL, "UNIT": self.c["mask_unit"], "PACK": pack_name},
                          f"STAGE2_INSTRUCTIONS {pack_name}", masked=True)

    # ------------------------------------------------------------------ Stage 1: screeners
    def redaction_screener(self, token, d, dossiers):
        """dossiers: list of (opaque_name, src_path_or_text). One screener reads every dossier."""
        p = self._dir(d)
        out = os.path.join(p, f"redaction_{token}.json")
        paths = [self._pack(p, n, src) for n, src in dossiers]
        ins = self._text("H_redaction", {"FILES": "\n".join(paths), "OUT": out}, f"H_redaction {token}")
        f1 = self._put(p, "REDACTION_SCREENER_INSTRUCTIONS.md", ins)
        f2 = self._put(p, "FRAMEWORK.md", src=self._framework())
        lp, pf = self._launch("L_redaction", [f1, f2] + paths, {"OUT": out}, "stage1_redaction", token)
        return dict(dir=p, out=out, prompt=lp, prompt_file=pf)

    def tag_screener(self, token, d, pack_name, src):
        p = self._dir(d)
        out, out2 = os.path.join(p, f"thin_{token}.md"), os.path.join(p, f"tags_{token}.json")
        ins = self._text("H_tag", {"PACK": pack_name, "OUT": out, "OUT2": out2}, f"H_tag {token}")
        f1 = self._put(p, "TAG_SCREENER_INSTRUCTIONS.md", ins)
        f2 = self._put(p, "FRAMEWORK.md", src=self._framework())
        f3 = self._pack(p, pack_name, src)
        lp, pf = self._launch("L_tag", [f1, f2, f3], {"OUT": out, "OUT2": out2}, "stage1_tag", token)
        return dict(dir=p, out=out, out2=out2, prompt=lp, prompt_file=pf)

    # ------------------------------------------------------------------ Stage 2 run
    def run(self, token, d, pack_name, src):
        p = self._dir(d)
        out = os.path.join(p, f"run_{token}.md")
        f1 = self._put(p, "STAGE2_INSTRUCTIONS.md", self.stage2_text(pack_name))
        f2 = self._put(p, "FRAMEWORK.md", src=self._framework())
        f3 = self._pack(p, pack_name, src)
        f4 = self._put(p, "MARKET_INPUTS.md", src=self.c["market_inputs"])
        lp, pf = self._launch("L_run", [f1, f2, f3, f4], {"OUT": out, "SCRATCH": os.path.join(p, "scratch")},
                              "stage2", token, masked=True)
        return dict(dir=p, out=out, prompt=lp, prompt_file=pf)

    # ------------------------------------------------------------------ Stage 4 critic
    def critic(self, token, d, pack_name, pack_src, run_src):
        p = self._dir(d)
        run_name = f"run_{token}.md"
        out, sc = os.path.join(p, f"critique_{token}.md"), os.path.join(p, "scratch")
        ins = self._text("E", {"TICKER": MASK_LABEL, "UNIT": self.c["mask_unit"], "RUN": run_name, "PACK": pack_name,
                               "OUT": out, "SCRATCH": sc}, f"E {token}", masked=True)
        files = [self._put(p, "CRITIC_INSTRUCTIONS.md", ins), self._put(p, run_name, src=run_src),
                 self._pack(p, pack_name, pack_src), self._put(p, "STAGE2_INSTRUCTIONS.md", self.stage2_text(pack_name)),
                 self._put(p, "CHECKLIST.md", tpl.template("C")), self._put(p, "MARKET_INPUTS.md", src=self.c["market_inputs"]),
                 self._put(p, "FRAMEWORK.md", src=self._framework())]
        lp, pf = self._launch("L_critic", files, {"OUT": out, "SCRATCH": sc}, "stage4", token, masked=True)
        return dict(dir=p, out=out, prompt=lp, prompt_file=pf)

    # ------------------------------------------------------------------ Stage 4b verifier
    def verifier(self, token, d, pack_name, pack_src, run_src, crit_src, redlog_text):
        ok, why = checks.verify_file(os.path.join(HERE, "frozen_arith.py"), "frozen_arith.py")   # before anything is staged
        if not ok:
            raise DiffFailure(f"verifier {token}: toolkit frozen_arith.py fails its manifest hash: {why}; nothing staged")
        p = self._dir(d)
        run_name, crit_name, red_name = f"run_{token}.md", f"critique_{token}.md", f"redlog_{token}.md"
        out, sc = os.path.join(p, f"verification_{token}.md"), os.path.join(p, "scratch")
        ins = self._text("F", {"TICKER": MASK_LABEL, "CRITIQUE": crit_name, "RUN": run_name, "PACK": pack_name,
                               "REDLOG": red_name, "OUT": out, "SCRATCH": sc}, f"F {token}", masked=True)
        files = [self._put(p, "VERIFIER_INSTRUCTIONS.md", ins), self._put(p, crit_name, src=crit_src),
                 self._put(p, run_name, src=run_src), self._pack(p, pack_name, pack_src), self._put(p, red_name, redlog_text),
                 self._put(p, "FRAMEWORK.md", src=self._framework()),
                 self._put(p, "STAGE2_INSTRUCTIONS.md", self.stage2_text(pack_name)),
                 self._put(p, "MARKET_INPUTS.md", src=self.c["market_inputs"]),
                 self._put(p, "frozen_arith.py", src=os.path.join(HERE, "frozen_arith.py"), mode=0o444)]
        ok, why = checks.verify_file(files[-1], "frozen_arith.py")   # spec: hash-checked at launch
        if not ok:
            raise DiffFailure(f"verifier {token}: staged frozen_arith.py fails its manifest hash: {why}")
        lp, pf = self._launch("L_verifier", files, {"OUT": out, "SCRATCH": sc}, "stage4b", token, masked=True)
        return dict(dir=p, out=out, prompt=lp, prompt_file=pf, script=files[-1])

    # ------------------------------------------------------------------ Stage 0.5 auditor
    def masked_texts(self):
        """The Stage-2, critic and verifier texts with every ticker slot masked, for the auditor."""
        m = {"TICKER": "⟨TICKER⟩", "UNIT": "⟨UNIT⟩", "PACK": "⟨PACK⟩"}
        return {"STAGE2_INSTRUCTIONS.md": tpl.instantiate("B", m),
                "CRITIC_INSTRUCTIONS.md": tpl.instantiate("E", dict(m, RUN="run_⟨TOKEN⟩.md", OUT="⟨OUT⟩", SCRATCH="⟨SCRATCH⟩")),
                "VERIFIER_INSTRUCTIONS.md": tpl.instantiate("F", dict(TICKER="⟨TICKER⟩", PACK="⟨PACK⟩", CRITIQUE="critique_⟨TOKEN⟩.md",
                                                                      RUN="run_⟨TOKEN⟩.md", REDLOG="redlog_⟨TOKEN⟩.md",
                                                                      OUT="⟨OUT⟩", SCRATCH="⟨SCRATCH⟩")),
                "CHECKLIST.md": tpl.template("C"),
                "REDACTION_SCREENER_INSTRUCTIONS.md": tpl.instantiate("H_redaction", {"FILES": "⟨FILES⟩", "OUT": "⟨OUT⟩"}),
                "TAG_SCREENER_INSTRUCTIONS.md": tpl.instantiate("H_tag", {"PACK": "⟨PACK⟩", "OUT": "⟨OUT⟩", "OUT2": "⟨OUT2⟩"}),
                "WRITER_INSTRUCTIONS.md": tpl.instantiate("H_writer", {"FILES": "⟨FILES⟩"})}

    def auditor(self, token, d, texts):
        """texts: {file name: text}, already masked (PREREGISTRATION, masked_texts(), example launch prompts)."""
        p = self._dir(d)
        out = os.path.join(p, f"audit_{token}.md")
        ins = self._text("H_auditor", {"OUT": out}, f"H_auditor {token}")
        files = [self._put(p, "AUDITOR_INSTRUCTIONS.md", ins)] + [self._put(p, n, t) for n, t in texts.items()]
        files.append(self._put(p, "FRAMEWORK.md", src=self._framework()))
        lp, pf = self._launch("L_auditor", files, {"OUT": out}, "stage05", token)
        return dict(dir=p, out=out, prompt=lp, prompt_file=pf)

    # ------------------------------------------------------------------ Stage 6 writer
    def writer(self, token, d, dossiers):
        p = self._dir(d)
        paths = [self._pack(p, n, src) for n, src in dossiers]
        out = os.path.join(p, f"section_{token}.md")
        ins = self._text("H_writer", {"FILES": "\n".join(paths)}, f"H_writer {token}")
        f1 = self._put(p, "WRITER_INSTRUCTIONS.md", ins)
        lp, pf = self._launch("L_writer", [f1] + paths, {"OUT": out}, "stage6_writer", token)
        return dict(dir=p, out=out, prompt=lp, prompt_file=pf)


def selftest():
    import tempfile, json
    out, ok_all = [], True

    def check(name, cond, detail=""):
        nonlocal ok_all
        ok_all &= bool(cond)
        out.append(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")
    with tempfile.TemporaryDirectory() as td:
        fw = os.path.join(td, "FRAMEWORK_stage.md"); shutil.copyfile(os.path.join(HERE, checks.FRAMEWORK_NAME), fw)
        mi = os.path.join(td, "MI.md"); open(mi, "w").write("market inputs")
        B = Builder(dict(root=os.path.join(td, "root"), framework=fw, market_inputs=mi,
                         prompts_dir=os.path.join(td, "lp"), diff_log=os.path.join(td, "diff.jsonl"), mask_unit="USD per share"))
        j = B.redaction_screener("s1", "d000001", [("pack_a.md", "dossier A text"), ("pack_b.md", "dossier B text")])
        check("B1 redaction screener: one clean room, both dossiers, launch prompt diffed and saved",
              os.path.exists(j["prompt_file"]) and "pack_a.md" in j["prompt"] and "pack_b.md" in j["prompt"])
        j = B.tag_screener("t1", "d000002", "pack_a.md", "dossier A text")
        check("B2 tag screener built", os.path.exists(os.path.join(j["dir"], "TAG_SCREENER_INSTRUCTIONS.md")))
        j = B.run("r1", "d000003", "pack_k3.md", "pack text")
        st2 = open(os.path.join(j["dir"], "STAGE2_INSTRUCTIONS.md")).read()
        check("B3 run: STAGE2 instructions carry MASK_LABEL and MASK_UNIT", "the Company" in st2 and "USD per share" in st2)
        rows = [json.loads(x) for x in open(os.path.join(td, "diff.jsonl"))]
        check("B4 every instantiated text logged as a passing diff", rows and all(r["ok"] for r in rows), f"{len(rows)} texts")
        mt = B.masked_texts()
        ja = B.auditor("z1", "d000004", mt)
        ins_tag = open(os.path.join(td, "root", "d000002", "TAG_SCREENER_INSTRUCTIONS.md")).read()
        ins_aud = open(os.path.join(ja["dir"], "AUDITOR_INSTRUCTIONS.md")).read()
        check("B7 v9: no probe text or method; tag screener lists share counts only; auditor treats pre-registration "
              "slots as slots; writer instructions resolve to the writer block",
              not hasattr(B, "probe") and "PROBE_INSTRUCTIONS.md" not in mt and '"tag":"SHARES"' in ins_tag
              and "PER_SHARE" not in ins_tag and "per-execution slots by design" in ins_aud
              and tpl.template("H_writer").startswith("Read the dossiers in"))
        check("B8 card slot typing: n/a is valid for the margin-rule values R1-R3 and for the alternative lever L11; a "
              "lever is required otherwise",
              all(tpl.slot_type_error(n_, "n/a") is None for n_ in ("CARD_R1", "CARD_R2", "CARD_R3", "CARD_L11"))
              and tpl.slot_type_error("CARD_L11", "+1.00 / +0.10") is None and tpl.slot_type_error("CARD_L11", "zero")
              and tpl.slot_type_error("CARD_R2", "x") and tpl.slot_type_error("CARD_ALT_UP", "1") is None)
        check("B6 auditor gets masked texts (no MASK_LABEL in them) and a diffed launch prompt",
              "the Company" not in mt["STAGE2_INSTRUCTIONS.md"] and "⟨TICKER⟩" in mt["STAGE2_INSTRUCTIONS.md"] and os.path.exists(ja["prompt_file"]))
        try:
            B._text("B", {"TICKER": "Acme Corp", "UNIT": "USD per share", "PACK": "p.md"}, "negative control", masked=True)
            raised = False
        except DiffFailure:
            raised = True
        check("B5 negative control: TICKER not MASK_LABEL raises DiffFailure and writes nothing", raised)
        check("B9 v10: card slot typing for the debt lever (n/a or a lever) and the v10 status counts; the Appendix-G "
              "validation block is dropped unless asked for",
              tpl.slot_type_error("CARD_L12", "n/a") is None and tpl.slot_type_error("CARD_L12", "+1.00 / +0.10") is None
              and tpl.slot_type_error("CARD_WMULT", "1.060") is None and tpl.slot_type_error("CARD_WMULT", "high")
              and tpl.slot_type_error("CARD_DEBTDED", "3") is None and tpl.slot_type_error("CARD_OFFBASE", "x")
              and "⟨BASELINE⟩" not in tpl.strip_conditionals(tpl.template("G"))
              and "⟨BASELINE⟩" in tpl.strip_conditionals(tpl.template("G"), validation=True))
        open(fw, "a").write("\n")
        try:
            B.run("r2", "d000005", "pack_k4.md", "pack text")
            raised_fw = False
        except DiffFailure:
            raised_fw = True
        check("B10 v10: an edited FRAMEWORK copy raises DiffFailure before any launch", raised_fw)
    return ok_all, out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        ok, lines = selftest()
        print("\n".join(lines))
        print("BUILD SELF-TEST " + ("PASSED" if ok else "FAILED"))
        sys.exit(0 if ok else 1)
    print(__doc__)
