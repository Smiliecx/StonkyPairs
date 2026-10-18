#!/usr/bin/env python3
"""extract.py -- toolkit v9 extractor, so the orchestrator never reads whole run, critique or verification files.

  python3 extract.py summary RUN.md        # the MACHINE SUMMARY JSON
  python3 extract.py phase6 RUN.md         # the Phase-6 section only (for Stage-6 synthesis)
  python3 extract.py verification VER.md   # the verification JSON block
  python3 extract.py checklist CRIT.md     # the critic's C1-C8 JSON block
  python3 extract.py mechanism VER.md [...] # v9 N7: every MECHANISM finding (critic tag or verifier "mechanism": true),
                                           # with its ruling, for final/SPEC_FLAGS.md
  python3 extract.py selftest
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frozen_arith as F


def phase6(path):
    t = open(path, encoding="utf-8").read()
    m = re.search(r"^## PHASE 6.*?$", t, re.M | re.I)
    if not m:
        return ""
    rest = t[m.start():]
    n = re.search(r"^## MACHINE SUMMARY", rest, re.M)
    return rest[:n.start()] if n else rest


def checklist(path):
    t = open(path, encoding="utf-8").read()
    for obj in reversed(F.extract_json_objects(t)):
        if isinstance(obj, dict) and "C1" in obj:
            return obj
    return None


def mechanism(path):
    """v9 N7: the rulings of one verification that are MECHANISM findings (tag2 MECHANISM or "mechanism": true)."""
    V = F.load_verification(path) or {}
    out = []
    for r in V.get("rulings") or []:
        if not isinstance(r, dict):
            continue
        flag = r.get("mechanism")
        flag = flag is True or (isinstance(flag, str) and flag.strip().lower() == "true")   # as frozen_arith.mech_flag (v9)
        if flag or "MECHANISM" in str(r.get("tag2", "")).upper():
            out.append({k: r.get(k) for k in ("finding", "ruling", "tag1", "tag2", "mechanism", "quantified",
                                              "spec_change_or_null")})
    return out


def selftest():
    import tempfile
    v = {"rulings": [{"finding": 1, "ruling": "CONFIRMED", "quantified": True, "mechanism": False, "tag1": "SPECIFIC",
                      "tag2": "ARITHMETIC", "changed_inputs": []},
                     {"finding": 2, "ruling": "CONFIRMED", "quantified": False, "mechanism": True, "tag1": "TRANSFERABLE",
                      "tag2": "RULE-VIOLATION", "changed_inputs": []},
                     {"finding": 3, "ruling": "REFUTED", "quantified": False, "mechanism": False, "tag1": "TRANSFERABLE",
                      "tag2": "MECHANISM", "changed_inputs": []},
                     {"finding": 4, "ruling": "CONFIRMED", "quantified": False, "mechanism": "true", "tag1": "SPECIFIC",
                      "tag2": "MECHANISM; RULE-VIOLATION", "spec_change_or_null": "Cap terminal growth at the macro base.",
                      "changed_inputs": []},
                     {"finding": 5, "ruling": "CONFIRMED", "quantified": True, "mechanism": "false", "tag1": "SPECIFIC",
                      "tag2": "ARITHMETIC", "changed_inputs": []}],
         "joint_changed_inputs": []}
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "verification_x.md")
        open(p, "w", encoding="utf-8").write("# Verification\n\ntext\n\n```json\n" + json.dumps(v) + "\n```\n")
        ms = mechanism(p)
        got = [m["finding"] for m in ms]
    ok = got == [2, 3, 4] and ms[2]["spec_change_or_null"] == "Cap terminal growth at the macro base."
    print(f"{'PASS' if ok else 'FAIL'}  X1 v9: MECHANISM findings listed by verifier flag (true or \"true\", never \"false\") or "
          f"critic tag (also within a combined tag), whatever the ruling, with the spec_change sentence: {got}")
    print("EXTRACT SELF-TEST " + ("PASSED" if ok else "FAILED"))
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if len(sys.argv) > 2 and sys.argv[1] == "mechanism":
        for pth in sys.argv[2:]:
            for m in mechanism(pth):
                print(json.dumps(dict(m, verification=os.path.basename(pth)), ensure_ascii=False))
        sys.exit(0)
    cmd, path = sys.argv[1], sys.argv[2]
    if cmd == "summary":
        print(json.dumps(F.load_summary(path), indent=1, ensure_ascii=False))
    elif cmd == "phase6":
        sec = phase6(path)
        if not sec.strip():
            print(f"no '## PHASE 6' section in {path}", file=sys.stderr)
            sys.exit(2)
        print(sec)
    elif cmd == "verification":
        print(json.dumps(F.load_verification(path), indent=1, ensure_ascii=False))
    elif cmd == "checklist":
        print(json.dumps(checklist(path), indent=1, ensure_ascii=False))
    else:
        print(__doc__)
