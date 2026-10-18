# TOOLKIT_MANIFEST — toolkit v10 (SPEC v10)

Shipped 2026-10-14 with SPEC v10, after the ICE v9 execution, the three-debater debate and the v10 change list (`claude/CHANGES_v10_simple.md`), and after one review round by three independent reviewers and a closing check (`claude/SPEC_v10_REVIEW_RECORD.md`). The SHA-256 of this file is the value pre-registered as ⟨SCRIPT_SHA⟩ (Appendix G). Every file below is used unchanged; any change makes a new version, which must pass the replay gate first. `replay/ADBE_v7/expected_v7.json` is pinned in the spec (SHA-256 `908de67b922f0be1346864d3126fd538c352b05c4e8a4e2f80d4145c946c96b6`). The own-mode replays `replay/ADBE_v7/replay_v7.1.json`, `replay_v8.json`, `replay_v9.json` (each reproduced in its mode) and `replay_v10.json` (hashes below) are also part of the gate.

## Changes from v9

- **`FRAMEWORK_v10.md` (T5).** New: the FRAMEWORK every subagent receives, edited to agree with Appendix B (seven seats; one discount rate; cash flow to equity with debt counted once; a register of every risk and upside driver with its size; Walter's symmetric grade with Simon's gates and written gate criteria; Graham without rate credits; Claire in one non-rate channel; Sophie's priced-in filter without market data; the quality premium as the margin's first part; the neutral Rule-10 example built in). Hashed here; staged verbatim.
- **`frozen_arith.py`.** Default mode v10, with `--spec v9`, `--spec v8`, `--spec v7.1` and `--spec v7` compatibility modes; the seat, margin and BUY arithmetic is v9's (the same functions).
  - T4: seven seated investors; a seat named Simon is outside the roster (logged C5, kept out of every statistic).
  - T1–T4 checks (`v10_checks`; logged, never corrected, moving no number): the rate and `fair_value_macro_base` against MARKET_INPUTS' macro base (a missing rate and a wrong run base included), the run's macro base against risk-free + ERP and MARKET_INPUTS (C2); a claim deducted from cash flow to equity (C1); missing debt fields and the risk class (C8); the risk register (closed channels incl. `non_break_branch`, sizes, `fv_mapping` only for Walter or Alexander, double entries by label, seats with no entry; C6); Walter's grade and gates and Alexander's mapping (C5).
  - T4: a reported NO BUY is honoured only for Walter with two or more FAIL gates (or a verifier patch); any other is logged (C7) and the seat kept.
  - T2: the ledger row "Debt: net claims deducted again (the v9 count)", card lever ⟨CARD_L12⟩ (n/a when no retained run is measured; never the largest sensitivity).
  - T6: the Stage-3 channel monitor (per run and over the retained runs), with each register channel's derived BUY effect, and a seat-mapping table; induced-field rows for the rate rule and the debt rule.
  - Card: `CARD_TEMPLATE_V10` (the debt lever; a status line with ⟨CARD_OFFBASE⟩, ⟨CARD_OFFBASE_FOLD⟩, ⟨CARD_DEBTDED⟩, ⟨CARD_SRC_D/A/C⟩, ⟨CARD_WMULT⟩).
  - `rebase` (fair value to the macro-base value, non-break branches scaled, break held) and `undebt` (the deducted claims added back) commands; a folded rebase finding is labelled approximate.
  - Self-tests: every earlier case still runs in v10 mode (with "Simon" as an ordinary seated name and the v10 NO-BUY rule off for those cases only), plus V10a–V10q, including six runs end to end through Stages 3 and 5.
- **`bridge.py` (T6).** New: `row` (the `OUTCOME_BRIDGE.md` row from a published data folder), `compare` (the Appendix-G validation comparison, after checking the baseline against its manifest, ⟨BASELINE⟩ and its published BUY), `selftest` 17a–17g on `replay/ICE_v9/`.
- **`checks.py` (T5).** `framework` checks a staged FRAMEWORK copy against this manifest; `market` defaults to v10 (the v9 Appendix-J checks apply); self-test K9.
- **`build.py` (T5).** Every FRAMEWORK staging is hash-checked (`DiffFailure` on a mismatch); self-tests B9–B10; the self-test stages the real FRAMEWORK_v10.md.
- **`tpl.py`.** Reads `spec_v10.md`; Appendix G's multi-line validation block (kept only with `validation=True`); slot ⟨BASELINE⟩ (a SHA-256); slot rules for the new card slots.
- **`configure.py`, `rollup.py`, `publish.py`.** `spec_version` v10 by default; v10 roll-up rows carry `debt_path`, `systematic_risk_class` and VALIDATION columns under their own header (`--validation [in-sample]`); the publish self-test expects a v10 ledger row.
- **`replay.py`, `toolkit_selftest.py`.** The gate runs the self-test in all five modes and checks the stored v7.1, v8, v9 and v10 replays; `replay.py v10` writes `replay_v10.*`; the toolkit self-test adds the v9-mode self-test and `bridge.py selftest`.
- **`spec_v10.md`** replaces `spec_v9.md`. **`replay/ICE_v9/`** added (per-run data of the ICE v9 execution and its stored bridge figures).
- **Unchanged:** `stage1.py`, `stage1c.py`, `seal.py` and `extract.py` are byte-identical to v9; the replay inputs and the stored v7.1, v8 and v9 replays and the N2 fixture are unchanged.

## Files

| file | SHA-256 |
|---|---|
| `FRAMEWORK_v10.md` | `6d1d67cf32e97a3e99975a2b682a5b9801db64da4c9af2943a3250d9ce93160f` |
| `README.md` | `40772cfe7c707f5a3820a256d13bd0a98b30b5d6cbd7f0a837d0fa88cef211a2` |
| `bridge.py` | `4c79afd340dfa3d06c076a239c951b46edcc829dd4ce6673bd24c45a82fa87ed` |
| `build.py` | `1f413d01054b5e2e95b56f91cc0cc8c70b4633f93c2c7b05d48c93dcb6f6df49` |
| `checks.py` | `0feeb775faa86470026638703a1cc4d09edaeb2efac7e7a736e04e0fa2e12683` |
| `configure.py` | `2411f455b62b0c0cfbcec6082df387f46bcba9e4d2de846ebad00ba79d68e5de` |
| `extract.py` | `fc3a71b46d1dbd0c52c8d7618125c7e397a65e64ec0da4b7e9defd76af715ca8` |
| `frozen_arith.py` | `358dea2365e649448e67d6de11fdf92cfdb6f5ff6e1b93183973d00f354a9f15` |
| `publish.py` | `40fc82100fe4033788bf966327fbf90c3472489f24dca132ae273af593129991` |
| `replay.py` | `be282d9bdbc2feadd5f1404f697dae42c6acc10186ed75f1c507a5edbb54d48c` |
| `rollup.py` | `11b48e32ce4ce8f4706368029c030e1048473a6ca0c070f051e1f1bfc6d6fe2d` |
| `seal.py` | `888e427cfe248b9044204168f503dd7ad77bd4af666b2bab87f89be71a346694` |
| `spec_v10.md` | `e071cd0c4523ec246448dde0c752daecee26c6ecb32bac321a6caed6fb5d73b4` |
| `stage1.py` | `507800f9c5f410151a1e171020dae47b696ee54d748f41a9a27ba4795d58d915` |
| `stage1c.py` | `bb7a3639e674236768d19ce6a1db94f6c5a71e713ebb81a8d563f7328a223acc` |
| `toolkit_selftest.py` | `7aad15d76a91705b322fa98c0c8d5dba1a2e271e952f76dd86fbdaffeb22c407` |
| `tpl.py` | `3f86ee86a5481fdcc9f9e8b7fa48d944fdc75046afa214984ed05b0f121d8e73` |
| `replay/ADBE_v7/config.json` | `4faeaec743cec27f9dd622ed3c458c596540482f45d65e19fb4601d7e225316e` |
| `replay/ADBE_v7/expected_v7.json` | `908de67b922f0be1346864d3126fd538c352b05c4e8a4e2f80d4145c946c96b6` |
| `replay/ADBE_v7/replay_v10.json` | `703921ae1d630b1f0a8bfa42be0065c74e16e8684364fe4745eec65fdcec0319` |
| `replay/ADBE_v7/replay_v10_card.md` | `9acf0b097459cd919c4fa85a25ff875c5049c51912f38ca58e443be49e211eef` |
| `replay/ADBE_v7/replay_v10_tables.md` | `73b36a490bc31faa2b770b7dcf1eb0bdaf745321c69defd41bedeecfa88fe0f1` |
| `replay/ADBE_v7/replay_v7.1.json` | `8b0545873e9db506a4b15a2f1a598894eb6b4ae67bfc93930868d0b20f269ad9` |
| `replay/ADBE_v7/replay_v7.1_attribution.json` | `ac8762ee824f8f7d6f7c0c9b7f87c416cf286fa29c38125768321ee5b0d582ef` |
| `replay/ADBE_v7/replay_v7.1_card.md` | `9a7bf92031e659b814722e19be0ba06bfe25c27f70f2833bfc021805db456de0` |
| `replay/ADBE_v7/replay_v7.1_tables.md` | `2299fcddbdb97add69e2d813fb6d9c292d91b41c7ac404beeb28b8e4fc1241c8` |
| `replay/ADBE_v7/replay_v8.json` | `57d07005a6c9426a5bff42a9de63660bd0e25c7579cf1a4c527e10fba7c6157b` |
| `replay/ADBE_v7/replay_v8_card.md` | `6921cf8581167f05ccb962f32fa506b567da59f64496540c43e7fc92fff523c0` |
| `replay/ADBE_v7/replay_v8_tables.md` | `ab2ea6ee8a1c57c569cce975452fde27bc2e8bbdc5f1a0c86c7c1dd734930117` |
| `replay/ADBE_v7/replay_v9.json` | `cf8643bda0d505a6f70d6f99e65a9d55922414d71469f814e307c1970f088543` |
| `replay/ADBE_v7/replay_v9_card.md` | `53c8122faca14893acab17fe99800cc1d9408b6700111f57e7f34a4b22bab8d8` |
| `replay/ADBE_v7/replay_v9_tables.md` | `19f406090e07b6dc5fa5c4d683046aaf8408745923088b45a11972ac72b805b5` |
| `replay/ADBE_v7/summaries/d8.json` | `6d3899873f588ad540085a3d7f5e9699ab6438c478bb06f9b7485f71ce990cdf` |
| `replay/ADBE_v7/summaries/f8.json` | `2116467de690b67ee68577c24008a399bd3d07bfcd4ffb47c1a70e1df9c99b77` |
| `replay/ADBE_v7/summaries/g8.json` | `369285294daa17c365cd9ddc0cc2f87ba6a24fe98128b902d4214a9431230fe8` |
| `replay/ADBE_v7/summaries/g9.json` | `e06fa0547fb330e8e3ca62c6315f4f6c11b6438a3ff336ad6797c8c8faa1006c` |
| `replay/ADBE_v7/summaries/j6.json` | `60d24821b9a69792f0c97a9a0ef947a9528880e31206a48131cc7de200953d64` |
| `replay/ADBE_v7/summaries/m4.json` | `3e44a9a6c722439f98137fc559692c0fbb02d96137ea21a8ddef8498027a6c3d` |
| `replay/ADBE_v7/summaries/n7.json` | `5ac910009d0d52a66ea25bfd839a6e0a30089a66adcab21cd2ce3f321a0fbfcc` |
| `replay/ADBE_v7/summaries/p2.json` | `549fa873f129fc9daf0e7982c9e6b3a4a45f0be8c8820129cbb820c0a7706b18` |
| `replay/ADBE_v7/summaries/u7.json` | `8a788e568b88e87708d297b9d92e7853946f98cf9d6b61cd45c24d4550999626` |
| `replay/ADBE_v7/summaries/w6.json` | `48ba7a8acd425a490599e5ee8fac0d1ff2b99746f9d3659b7606d0b93c2266eb` |
| `replay/ADBE_v7/verifications/d8.json` | `1e63d340de555f0aa16f8cb3e08ca692b12ca2eedbaca4669a20892ef66b1418` |
| `replay/ADBE_v7/verifications/f8.json` | `8430040541fb16021a469fa3ec014d8fe19e360d0b30c9cd0bea026a5035f2f3` |
| `replay/ADBE_v7/verifications/g8.json` | `a912f5727f609aa4e3e9af2629104dc5d8a0380d3d3826de45fe82fe5bc421bb` |
| `replay/ADBE_v7/verifications/g9.json` | `408e3744b04b02e41baba381e97ad6dc347a2b1a3f71343ceec5f2a533b8679a` |
| `replay/ADBE_v7/verifications/m4.json` | `36507dcde2ea5afbb41b3ccc6e22c029a8c4934199fe5b259f282d7ad7207d1e` |
| `replay/ADBE_v7/verifications/n7.json` | `6153e7d35bc51311803fee5bd32422e4fda1f76637f06fe136acc06fa95c7ba5` |
| `replay/ADBE_v7/verifications/u7.json` | `75f8ee2fb36ced501dc49352c00e6aea26e5c7871fa5210cad9705c44198e502` |
| `replay/ADBE_v7/verifications/w6.json` | `b6116989782a52d094e2ecebcf92ff008d0996de6d92d46b4f76dee6409c0470` |
| `replay/ICE_v9/config.json` | `f8bb5896a0a0549efafc271806e70998b0082c1b1e26b70f772c12771725e92a` |
| `replay/ICE_v9/expected_bridge.json` | `41796923b4f782d2a617b2bf092dced0d41d4e3a95eb0aaa34d1bd8dcf7d4bc5` |
| `replay/ICE_v9/runs/1060.json` | `a93e4c5bdbb19853eed44b171a49d3df1ed5d575c3cf0e8c0f2503a84c9a5844` |
| `replay/ICE_v9/runs/2253.json` | `7b1924cf03bf6ead6f79d890fb8b433b7d1fc3fb1af15dc251c59f42e5e25d0e` |
| `replay/ICE_v9/runs/29eb.json` | `d604f084e592749b34600fe58d926405985fae148c72cec2baadce0942a7cfd1` |
| `replay/ICE_v9/runs/30d9.json` | `944f03950556f000c2381b07e20bfb1af499fb8fb15c6593869d9bbdab9cad57` |
| `replay/ICE_v9/runs/7aca.json` | `5c8b0625d95270871b283aca438813c7fa7444d4ab88416aab4e401c5c45d040` |
| `replay/ICE_v9/runs/7e13.json` | `e1774be09365c8b5b4b982b64f2c578821f598e8aa2a388b84b3929a159ef939` |
| `replay/ICE_v9/runs/9d63.json` | `7dbc13851f0308b9d34bb4f4ded9dd895d2c2471431a3d4973fb537752dc8420` |
| `replay/ICE_v9/runs/a806.json` | `939652e31b51a0ae3a5faa2de905fd2096d64b891f42885c391f5966aa389ed0` |
| `replay/ICE_v9/stage5.json` | `7d4435dd4746b9d47a66cfabc762b8c219371331a230bea5bcefb13757c473ee` |
| `replay/ICE_v9/verifications/1060.json` | `bd31b52f3e842cd8cff3cd0fcf7891e605a4d5fd360f349468d7b0f64e0adcfb` |
| `replay/ICE_v9/verifications/2253.json` | `e3d5e4918f7003f999077210286990eeec2228a6113d8752eabfa87fb33d2bd1` |
| `replay/ICE_v9/verifications/29eb.json` | `e7a56c52636107569eef27469207c98b1c1f34ec9f550b045c0318ee2486fc71` |
| `replay/ICE_v9/verifications/30d9.json` | `7e12bf6f294163fce6316779d17f1f6a0af23f20e7ed2efbe72ccdbc4138d691` |
| `replay/ICE_v9/verifications/7aca.json` | `6a66d4e0fd0345392d745230b39f77e1f5eed378086a1060e02bd5f6ce05b34a` |
| `replay/ICE_v9/verifications/7e13.json` | `96dedf8bde3a9c9b5f2acef90e764e14bceb415c953b54da2df718f24cddd549` |
| `replay/ICE_v9/verifications/9d63.json` | `8382db3775201d43466947b8bdb6c5237f1f19675fabb204dd2611ff49009471` |
| `replay/ICE_v9/verifications/a806.json` | `7faa7f6e8703d332010e9188c309e1a2a16b63463a41f5f0fead4fcc4debd823` |
| `replay/V9_N2/config.json` | `45c335b9f2d4c8242d3482014bce469f5eb9a23e209a8c81a337744f9c5a181c` |
| `replay/V9_N2/expected.json` | `b2470974db3ce12cadeb594d93c2bee25d9e9129462d8ab44c4811f45fafaf55` |
| `replay/V9_N2/summaries/r1.json` | `e08e8ef9bb345b6b87df63edb649e2cd86abbb17d519e01904444093eafd4058` |
| `replay/V9_N2/summaries/r2.json` | `23067c7e708abb825d1e8acce474d9366f647a02820acd4924b098687f57f31d` |
| `replay/V9_N2/summaries/r3.json` | `cbe8dbdb31734c9953bebe12ab6e88a7e34d7af06ca42b69c07cc858b314a91d` |
| `replay/V9_N2/summaries/r4.json` | `65bfce6c95dcae6942ef44b4bbfbf21de0bfe94a5f1e31e8bb0b42f1896080e7` |
| `replay/V9_N2/summaries/r5.json` | `20ad6de7e83d628d73869566833fe56db31e3c0cdc5ffd9ff0fbc2468314ae94` |
| `replay/V9_N2/summaries/r6.json` | `e20ab4ecbd907d55feb279786957224ecf6f5f4c1eb8c51581c9e22fc5a883b3` |
| `replay/V9_N2/verifications/r1.json` | `d7ae2478222b53adfdf12c8345a8c0dfc7460c2c0706f96e5637c0b0568b44c5` |
| `replay/V9_N2/verifications/r2.json` | `ec9e398942ff00751cc131b01598de9b3b01f61059ca3be171cbdd145d03c976` |
| `replay/V9_N2/verifications/r3.json` | `bafa10d2437ee56a9deb1893dfe9b58a98719159d17a496a6b66607da2ae6d9d` |
| `replay/V9_N2/verifications/r4.json` | `21becd6f291760e86e1af9022b3a9da9f733715dafe393bdc6165d262e6c645e` |
| `replay/V9_N2/verifications/r5.json` | `d6625e9d13cd4f76f37c843d42a53ace040c31f13b388d3a2c8b1d1d561ef95a` |

`python3 toolkit_selftest.py` → TOOLKIT SELF-TEST PASSED. It runs:
- the hash check of every file above, and the checks self-test (K1–K9);
- the frozen_arith self-tests in v10, v9, v8, v7.1 and v7 modes;
- the Stage-1 self-test and the extractor self-test (X1);
- the builder self-test B1–B10;
- the publish self-test P1–P2 and the bridge self-test 17a–17g;
- the replay gate.

The replay gate:
- **Compatibility mode (`--spec v7`).** ADBE v7 is reproduced exactly: blind intermediate 236.481205, published BUY 237.866523, interval, replication range, committee fair value, every ledger and Stage-3 row, dossier contrast, β̂ₖ, β̂ⱼ, permutation p and headline sentence.
- **`--spec v7.1`, `--spec v8`, `--spec v9`, own mode (v10).** `replay_v7.1.json`, `replay_v8.json`, `replay_v9.json` and `replay_v10.json` are reproduced, including every ledger row and margin-rule line.
- **N2 fixture.** `replay/V9_N2/` reproduces its independent hand computation of the alternative-denominator row in Stage 3 and Stage 5 to 1e-6 (in `--spec v9` mode).

## Reference replay: "ADBE @ v10 (replay)"

The ADBE v7 MACHINE SUMMARIES and verifications recomputed in v10 mode. v10 changes no seat or BUY arithmetic; the only arithmetic difference from the v9 replay is the roster: Simon's seat leaves every run's headline (his weight dropped). (No ADBE seat reports a NO BUY, so the v10 NO-BUY rule moves nothing here.) Every other seat keeps its reported rate, add-ons included: the summaries predate T1, so the replay cannot rebase them, and the log records each seat off the macro base (C2). The run-side changes (one rate, the flow basis, the register, Walter's grade, FRAMEWORK_v10) cannot be replayed.

| | v7 (published) | ADBE @ v8 (replay) | ADBE @ v9 (replay) | ADBE @ v10 (replay) |
|---|---|---|---|---|
| Published BUY | 237.87 | 239.06 | 239.06 | 248.17 |
| Blind intermediate | 236.48 | 237.14 | 237.14 | 247.15 |
| 80% interval | 233.59–242.15 | 234.50–243.61 | 234.50–243.61 | 243.18–253.17 |
| Committee fair value | 391.29 | 396.07 | 396.07 | 410.21 |

**New ledger row (T2):** "Debt: net claims deducted again (the v9 count)" = 248.17, equal to the published BUY: v7 summaries report no `net_claims_per_share`, so no run is measured and the card prints the lever as n/a. **Card status:** 42 headline seats off the macro base over the retained runs (by rate), 35 still off after the fold (the verifications rebased none; 7 seats' fair values were patched for other reasons); runs with debt deducted 0 (not reported in v7 summaries); risk class 0 in every value; Walter's mean multiplier n/a.

**Approximations** (stated as the replay gate requires): as for the v9 replay; in addition, v7 summaries carry no debt fields, risk class, register, grade or earnings-quality block, so the replay log has a C1, C2, C5, C6 or C8 line per run or seat for each; none moves a number.

## Earlier reference replay: "ADBE @ v9 (replay)" (toolkit v9; kept for the record)

The ADBE v7 MACHINE SUMMARIES and verifications recomputed under v9 arithmetic. v9 changes no seat or BUY arithmetic, so every published figure equals the v8 replay. The run-side changes (unmasked packs, the pack-only rule, the alternative denominator, the pre-write tree checks) cannot be replayed.

| | v7 (published) | ADBE @ v7.1 (replay) | ADBE @ v8 (replay) | ADBE @ v9 (replay) |
|---|---|---|---|---|
| Published BUY | 237.87 | 238.95 | 239.06 | 239.06 |
| Blind intermediate | 236.48 | 237.52 | 237.14 | 237.14 |
| 80% interval | 233.59–242.15 | 234.55–243.34 | 234.50–243.61 | 234.50–243.61 |
| Committee fair value | 391.29 | 396.97 | 396.07 | 396.07 |

**New ledger row (N2):** "Alternative denominator: every seat on its run's alternative denominator" = 239.06, equal to the published BUY: v7 summaries carry no `fair_value_alternative_denominator`, so every seat keeps its fair value, the replay log has a C8 line per run, and the card prints the lever as n/a. The memory-control row is gone from the v9 ledger; the margin-rule lines equal the v8 replay's.

**Approximations** (stated as the replay gate requires): as for the v8 replay, `fair_value_macro_base` is estimated log-linearly and the acquisition fields are absent; v7 summaries carry no `quality_premium`, `horizon_years`, `forecast_5y` or `fair_value_alternative_denominator`, so the replay log has a C7 or C8 line per seat or run for each; none moves a number.

**MELI v8 execution recomputed under v9** (for information; masking was already off there, under deviation D-3): published BUY 497.02, interval 209.69–784.35 and committee fair value 836.23, all unchanged from the v8 publication. The card's acquisition mismatches fall from 8 to 0 (zero acquisition spend, N5). The alternative-denominator lever reads n/a (seats valued 0 of 48), because the v8 runs reported no `fair_value_alternative_denominator`. The card has no memory line.
