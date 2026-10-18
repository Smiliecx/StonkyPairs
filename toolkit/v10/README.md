# Toolkit v10 (SPEC v10)

The shipped scripts for the valuation pipeline. **The orchestrator uses them unchanged. It never writes, patches or extends a script during an execution** (spec, "The toolkit and the orchestrator's context"). A defect stops the execution and becomes a new toolkit version, which must pass the replay gate first.

**What is different in v10.** Every seat discounts at the macro base, every run values cash flow to equity with debt counted once, every risk and upside driver is registered once with its size, and the committee has seven seats (Simon merged into Walter) (T1–T4). The frozen script's default mode is v10: Simon is outside the roster; NO BUY only for Walter's two FAILs; the T1–T4 checks are logged and move no number; a new ledger row and card lever put the v9 debt count back (T2; never the largest sensitivity); a channel monitor reports where value is priced, with each register channel's BUY effect (T6); `frozen_arith.py rebase` and `undebt` print the route-(d) patches for a seat off the macro base and a run that deducted debt. `FRAMEWORK_v10.md` ships in the toolkit and is hash-checked wherever it is staged (`checks.py framework`, and `build.Builder` at every launch) (T5). `bridge.py` writes the season's `OUTCOME_BRIDGE.md` rows and the validation comparison, after checking the baseline folder against its manifest and ⟨BASELINE⟩ (T6). `--spec v9` keeps the v9 arithmetic for v9 replays. `stage1.py`, `stage1c.py`, `seal.py` and `extract.py` are unchanged from v9.

**What was different in v9.** Packs are the redacted dossiers, unmasked and unscaled (N1): `stage1.py` runs with `"masking": false` by default, writes one pack per run with k = j = 1, and runs no completeness, masking or consistency check. There is no probe. The frozen script adds the alternative-denominator row (N2), counts no acquisition mismatch at zero spend (N5) and checks `quality_tier_modal` (N6). `checks.py market` verifies the season file's rebased ERP (N4). `extract.py mechanism` lists MECHANISM findings for SPEC_FLAGS (N7). The v8 masked path survives behind `"masking": true` and `--spec v8`, for replays only.

| File | What it does | Spec |
|---|---|---|
| `spec_v10.md` | Template copy of the spec. Every subagent text is extracted from it. | all appendices |
| `FRAMEWORK_v10.md` | The FRAMEWORK every subagent receives (v10, T5). Copied verbatim to `dossier/FRAMEWORK_stage.md`; never edited. | Stage 1 |
| `bridge.py` | `row`: the execution's `OUTCOME_BRIDGE.md` row from its published data folder; `compare`: the pre-registered validation comparison (`final/VALIDATION.md`). | Stage 6, Appendices G and K |
| `tpl.py` | Template extraction, instantiation and the mechanical diff (slots only; inline conditionals optional). | Stage 0.5 Step 1 |
| `build.py` | Clean-room builder. Every text is instantiated, diffed before it is written, and its launch prompt saved as sent. | Rule O-1, Appendix H |
| `stage1.py` | Redaction check, redactions and methodology notes from the screeners' JSON; under v9 the packs (the redacted dossier per run) and redlogs. The SHARES list fails closed, and a backstop refuses any span containing a share count. | Stages 1 and 1c |
| `stage1c.py` | The v7–v8 factor draws, rescaling, masking and checks, used only with `"masking": true` (replays). | Stage 1c (v8) |
| `seal.py` | Sealed store (`openssl enc -aes-256-cbc -pbkdf2`; passphrase in env `PP`; directory in env `SEAL_DIR`). | Rule O-1 |
| `frozen_arith.py` | All arithmetic: per-seat recompute, the margin-rule alternatives, Stage 3, Stage 5, the Stage-5b fold and the Decision Card; the v10 checks, debt row, channel monitor and `rebase`. Default mode v10; `--spec v9`, `--spec v8` (masked v8 executions, memory test), `--spec v7.1` (step tiers, back-tests) and `--spec v7` (replay gate). | Appendix B, Stages 3, 5, 5b, Appendix I |
| `checks.py` | Toolkit, staged-script, staged-FRAMEWORK (v10) and MARKET_INPUTS hash checks; the v9 season-file checks (ERP equation, range, currency, date); the v8 probe scorer (replays only). | Stage 0.5, 1, 4b, Appendix J |
| `configure.py` | Builds the Stage-3/5 configuration from the sealed manifest, run files, verifications, MARKET_INPUTS and thinness lists (⟨CARD_THIN⟩). | Stages 3, 5 |
| `rollup.py` | Season roll-up rows (`mechanism_version` v10, with `debt_path`, `systematic_risk_class` and VALIDATION columns and their own header; "n/a" in the memory cells; `--validation` marks rows). Appended only after Stage 6 is published. | Stage 3 |
| `extract.py` | MACHINE SUMMARY, Phase-6 section, verification JSON, critic checklist and the MECHANISM list, so the orchestrator never reads whole files. | F3, Stage 6 (N7) |
| `replay.py` | The replay gate (`gate`: ADBE v7 in `--spec v7`, the stored v7.1, v8, v9 and v10 replays, and the N2 fixture) and the reference replays under v10 (`v10`), v9 (`v9`), v8 (`v8`) and v7.1 (`v71`). | Stage 5b, "Replay gate" |
| `publish.py` | Per-run data publication (replayable copy) and the outcome-ledger row. Run after Stage 6 is published. | Stage 6, Appendix K |
| `toolkit_selftest.py` | Runs every self-test and the replay gate; save its output as `final/script_selftest.txt`. | Stage 0 |
| `replay/ADBE_v7/` | The reference execution (orchestrator-only). | Stage 5b |
| `replay/V9_N2/` | A constructed six-run case with an independent hand computation of the alternative-denominator row (v9 review). | Stage 5b |
| `replay/ICE_v9/` | ICE v9 (2026-10-13) per-run data (runs, verifications, configuration, a trimmed `stage5.json`) and the stored bridge figures, for `bridge.py selftest` (orchestrator-only). | Stage 5b |

## Procedure, stage by stage

1. **Before Stage 0.**
   - Restore the toolkit from `BUNDLE.tar.gz.b64` (see `RESTORE.md`), then copy this folder read-only into `./TICKER/orch/`.
   - Run `python3 checks.py toolkit` (every SHA-256 against `TOOLKIT_MANIFEST.md`) and `python3 checks.py market STAGED SEASON ROLLUP`. Under v9 and v10 the second also checks that the season file is on the v9 Appendix-J template and that its ERP equals ERP_RAW + ERP_RF − RF; a v8-template file fails, and the orchestrator asks the user for a v9 file.
   - Run `python3 toolkit_selftest.py > final/script_selftest.txt`. It must end `TOOLKIT SELF-TEST PASSED`.
   - Put the SHA-256 of `TOOLKIT_MANIFEST.md` in the pre-registration as ⟨SCRIPT_SHA⟩.
2. **Stage 0 / 0.5.**
   - Build PREREGISTRATION with `tpl.instantiate("G", …)`.
   - Build the auditor with `build.Builder(cfg).auditor(token, dir, texts)`, where the texts are `Builder.masked_texts()` plus the masked PREREGISTRATION and one launch prompt per stage.
   - Every diff result lands in `final/stage05_diff.jsonl`.
3. **Stage 1 / 1c.**
   - Copy `FRAMEWORK_v10.md` byte for byte to `dossier/FRAMEWORK_stage.md` and run `python3 checks.py framework dossier/FRAMEWORK_stage.md` (v10, T5). `Builder` re-checks it at every launch.
   - Launch one redaction screener over every dossier (`Builder.redaction_screener`) and one tag screener per dossier (`Builder.tag_screener`). Under v9 the tag screener returns the thinness list and the SHARES list only.
   - Run `python3 stage1.py run stage1_config.json` (format in its docstring; `"masking"` is false by default), with `"out": {"sealed": true}`. It writes `redacted_<d>.md`, one `pack_<token>_<pack>` per run (the redacted dossier), the redlogs, `manifest.json` (k = j = 1) and `REDACTION_LOG.md`.
   - Exit code 2 means STOP; the report names which screener to relaunch (same template).
   - Write `orch/state.json` (no passphrase in it) and compact.
4. **Stage 2 / 4 / 4b.** Use `Builder.run`, `Builder.critic` and `Builder.verifier`. Read only the JSON each subagent returns. Use `extract.py` when a field is needed.
   - **Pipelining (v8, S3).** Launch a run's verifier as soon as its critique has returned. Launch a run's critic as soon as its run has returned and `extract.py summary` parses it, but only where subagents have isolated file systems; on a shared file system (P-2) launch critics after every run has returned and every run directory has been deleted. Delete each subagent directory on collection (archive its scratch folder) and save one clean-room listing per launch. Stages 3, 5 and 5b wait for every run and verification.
5. **Stage 3 / 5 / 5b.**
   - `python3 configure.py input.json cfg.json` (format in its docstring; `spec_version` v10 by default), then `python3 frozen_arith.py stage3 cfg.json OUT` and `python3 frozen_arith.py stage5 cfg.json OUT`.
   - Run `python3 checks.py file orch/frozen_arith.py frozen_arith.py` before Stage 3 and before Stage 5b. `Builder.verifier` runs it at every verifier launch.
6. **Stage 6.**
   - Draw the synthesis sections from `extract.py phase6` (it exits 2 if a run has no `## PHASE 6` section).
   - The Decision Card and headline sentence come from `stage5` unchanged. Diff them separately: `python3 tpl.py diff I_card CARD_FILE --card` and `python3 tpl.py diff I_headline HEADLINE_FILE --card`.
   - Run `python3 extract.py mechanism critiques/verification_*.md` and copy every line it prints (finding, ruling, tags, `spec_change_or_null`) into `final/SPEC_FLAGS.md` by script (N7).
   - Then `python3 rollup.py OUT cfg.json checklists.json [--validation [in-sample]]` and append the rows to the season roll-up, under the "v10 rows" table.
   - Then `python3 publish.py data cfg.json OUT DATA_DIR` (durable storage, `TICKER/v10/data/`; it must print `replay MATCH`), then `python3 bridge.py row DATA_DIR --date YYYY-MM-DD --append OUTCOME_BRIDGE.md` (v10, T6; in a validation execution also `python3 bridge.py compare BASELINE_DATA_DIR DATA_DIR --baseline BASELINE_SHA --out final/VALIDATION.md`), and `python3 publish.py ledger cfg.json OUT --date YYYY-MM-DD --data DATA_PATH --toolkit SCRIPT_SHA`, appending the row to the season `OUTCOME_LEDGER_EXECUTIONS.md` (Appendix K). Never open `OUTCOME_OBSERVATIONS.md` during an execution.

## Making a new toolkit version

1. Change the scripts in a new folder `toolkit/<new version>/`.
2. Run `python3 toolkit_selftest.py`. The replay gate must reproduce ADBE v7 in `--spec v7` mode within 0.005 (published figures) and 0.01 (ledger rows), and the stored `replay_v7.1.json`, `replay_v8.json`, `replay_v9.json` and `replay_v10.json` in their modes within 0.005.
3. Under a new spec version, run `python3 replay.py <version>` once and record the reference replay in the new `TOOLKIT_MANIFEST.md`. Do not re-run `replay.py v71`, `v8`, `v9` or `v10`: their stored outputs are listed in the manifest.
4. Recompute every SHA-256 in the manifest, then rebuild `BUNDLE.tar.gz.b64` (see `RESTORE.md`).
