# Multi-stage blind valuation pipeline — SPEC v10

*Template copy (VARIABLES uninstantiated).*

*History:*
- *v6 was drafted 2026-09-29 and revised to v6.1, v6.2 and v6.3 the same day.*
- *v7 was drafted 2026-09-30, after the ADBE v6 and DECK v6 executions. Five participants debated 25 proposals. The five edits below were chosen by Borda vote, with a runoff on the margin arithmetic.*
- *v7.1 was drafted 2026-09-30, after the ADBE v7 execution. Three debaters (a valuation practitioner, a methodologist and a pipeline engineer) reviewed 32 candidate improvements in two rounds. The five edits F1–F5 below won the Borda vote, and each appeared on all three ballots.*
- *v8 was drafted 2026-10-04, after the AGX v7.1 execution. Two structured debates on margin rules (each with two advocates, a neutral analyst and an independent judge), a back-test on the season's executions and a run-time review produced edits G1–G5 and S1–S4 below. An adversarial review preceded release (`claude/SPEC_v8_DEBATE_RECORD.md`).*
- *v9 was drafted 2026-10-06, after the MELI v8 execution. A plain change list (`claude/CHANGES_v9_simple.md`) set out seven edits, N1–N7, and four open questions, which the spec owner decided. One review round by three independent reviewers and a closing check preceded release (`claude/SPEC_v9_REVIEW_RECORD.md`).*
- *v10 was drafted 2026-10-14, after the ICE v9 execution. The spec owner set the direction (no discount-rate add-ons; Simon merged into Walter; Walter's grade moves only Walter's fair value; FRAMEWORK hashed into the toolkit). Three debaters (a valuation practitioner, a methodologist and a spec engineer) argued three rounds and endorsed every item of the final ballot unanimously, with no veto. The plain change list is `claude/CHANGES_v10_simple.md`; one review round preceded release (`claude/SPEC_v10_REVIEW_RECORD.md`).*

*All sets of edits are listed at the end, under "Revision history".*

**What v10 changes.** Six edits (T1–T6), drawn from the ICE v9 execution, the season's record and the three-way debate, with the consequential changes they force. Everything else in v9 stands.
1. **T1 — Every seat discounts at the macro base.**
   - Every seat's discount rate is the macro base: MARKET_INPUTS' risk-free rate plus its rebased ERP. There are no add-ons and no credits, so `fair_value_macro_base` equals `fair_value`. The ERP-departure route is closed (`erp_departure_reason_or_null` is removed).
   - A seat whose rate is not the macro base breaks a STAGE2_INSTRUCTIONS requirement (verification route (d)). The verifier patches it with `frozen_arith.py rebase`: `fair_value` set to `fair_value_macro_base`, every non-break branch scaled by the same ratio and the break value held (an approximation, labelled as one; with the break held, the seat's margin is unchanged). The script logs every such seat (C2), measured against MARKET_INPUTS, and the channel monitor counts them.
   - Market-wide risk (financial leverage, operating leverage, cyclicality) gets no rate term in v10. Each run records a descriptive `systematic_risk_class` (defensive / average / cyclical) that moves no number; the outcome ledger tests whether a term is needed (Appendix K, test 5).
   - Generic uncertainty haircuts are banned, in the cash flows and in the quality score: a base-case haircut names a specific expected drag, and a score cut names a quality dimension (T3). The v8 sentence calling a rate add-on "a separate channel from the quality premium and not a Rule-3 double count" is deleted.
   - *Why. The macro base is the expected return of the average stock, so across companies the seats' add-ons should average about zero. 142 of the 144 seat rates that could be checked sat above it (ICE v9 62 of 64, median +150bp; ADBE v7 80 of 80, median +75bp; the lowest stated GSL and AGX rates were also above their base). Add-ons were asserted, not derived (Rule 2 asked for a name and a size), Simon's gates could only add, Graham's two-sided credits went almost unused, and the v8 carve-out let one risk be priced in the rate, the quality premium and the tail term at once. On ICE, every seat at the macro base with margins held would have moved the BUY from about $45 to about $60 (fair value about $72 to about $97): Simon's add-on about $3 of it, the other seven seats' about $12.*
2. **T2 — Debt is counted once.**
   - Every run values **cash flow to common equity** (the levered basis): after interest, preferred dividends, distributions to minority interests, lease payments and the net borrowing (or repayment) its stated debt path implies. No debt, preferred, minority or lease claim is deducted from value; a balance-sheet asset is added only if its income is not already in the cash flow. Operating balances (balances held for customers or required to operate the business) stay inside the cash flow and are neither added nor deducted. The run states its debt path, how interest income is treated and how leases are treated, and reports `net_claims_per_share` (debt + preferred + minority interests − cash, from the balance sheet) for the debt row only.
   - Cash flow after interest with debt also deducted scores C1 0.0, and the script logs any run that reports a non-zero `debt_deducted_per_share`. A verifier quantifies a confirmed double count with the patch set `frozen_arith.py undebt` prints (the deduction added back to every branch).
   - *Why levered only.* The macro base is an equity return (the average stock's), so the cash flow it discounts must be the equity's. Pre-interest flows at an equity rate lose the tax shield and the spread between the equity rate and the cost of debt, and the debated three-basis rule (unlevered / levered / financial) let a run's choice of basis move ICE's fair value by +$14 to +$49 against v9 (review P2). It also forced a double count on the financial basis (review P1, C1, I6).
   - A new ledger row, **debt: net claims deducted again (the v9 count)**, reports the headline with every seat's value reduced by its run's `net_claims_per_share`, so the effect of the correction is visible apart from everything else. It is excluded from the card's largest sensitivity (it restates the error v10 removes).
   - *Why. All eight ICE v9 runs started from operating cash flow, which is after interest, and also subtracted net debt ($33.18 per share): interest and principal were both charged. On the runs' own flows, removing the second deduction adds $33.18 to every branch value: +$20.7 of ICE's BUY with margins held, +$23.7 with each seat's tail term recomputed (BUY $44.95 → $68.61). "Debt and interest treatment" was an open flag from v7.1, and ADBE v7 and TPR v8 critics had raised it.*
3. **T3 — Each risk is priced once, with its size.**
   - Every run reports a risk register (`risks`): for each seat, each risk it considered and each upside driver behind a branch above its base, the one channel that carries it, and its signed size. The channels are the base-case cash flows (an expected drag or lift, probability × impact, in ⟨UNIT⟩ of fair value), the break branch (the tail term, in pp of p·L), the quality score (a named dimension, in score points), a seat's fixed fair-value mapping (Walter's grade, Alexander's earnings-quality adjustment; % of fair value), and a non-break branch (expected-value effect in ⟨UNIT⟩; reported, never in the margin). "Not priced", with a reason, is allowed.
   - Every item behind a non-break branch whose expected-value effect exceeds 1% of fair value, downside or upside, must be registered; leaving it out is a C6 miss. The rule asks for registration, not pricing: nothing is forced into the margin, so it pushes value in neither direction. (The debated rule, a 1% threshold that made a risk found only in a downside branch a miss unless priced in a margin channel, was replaced in review: every ICE v9 downside branch exceeded 1%, upside had no matching rule, and Appendix A's own example failed it; spec owner's decision on review findings P3 and I1.)
   - The script logs an unknown channel, a missing size, and a risk entered for one seat in more than one channel (C6). Critics check the rest.
   - *Why. Within each ICE run, seats with larger add-ons also cut growth, terminal growth and quality scores and raised break probabilities (Spearman −0.34 to −0.46): one worry priced through several channels, while the double-count check worked only on labels. If the rate channel closes and nothing else does, pessimism moves into growth, scores and break probabilities instead of disappearing; sizes make that move measurable (T6).*
4. **T4 — Seven seats: Simon merges into Walter.**
   - Simon is unseated. His four gates (trust, incentive alignment, board governance, capital-structure distress) become part of Walter's management grade, and two FAILs still mean NO BUY (for Walter's seat).
   - Walter's grade is symmetric and bounded: six components (capital allocation; trust and guidance; incentive alignment; insider transactions; board governance; five-year returns against the sector), each from −2 to +2, a score from −12 to +12, and a fair-value multiplier of 1 + 0.015 × score (0.82 to 1.18), applied to the operating value of every branch. A CAUTION or FAIL on a gate caps its component at −1 or −2. Preferred stock is deducted in the balance-sheet bridge (T2), not through the grade.
   - The mapped-dimension rule: a seat with a fixed fair-value mapping leaves that dimension out of its quality score (Walter: management and governance; Alexander: earnings quality) and applies the mapping to every branch's operating value.
   - Graham loses his rate credits; Claire prices her moat in one non-rate channel.
   - *Why. With a shared rate, Simon's trust-adjusted DCF would repeat Graham's, Walter's and Helena's. What was unique to him (the gates and the uninvestability rule) survives in Walter. Symmetry stops his one-way penalty returning as a one-way multiplier. Each run does about an eighth less seat work.*
5. **T5 — The FRAMEWORK is edited, versioned and hashed.**
   - `toolkit/v10/FRAMEWORK_v10.md` is edited to match Appendix B (the Overview; the margin section and a new "One Discount Rate" principle; Rules 1, 2, 3 and 6; Phases 0.A, 0.B, 1.A, 1.C, 1.D, 1.5, 4 and 6; the committee descriptions, including criteria for Walter's four gates; the cross-investor checks; "What good looks like"), with the ticker-neutral Rule-10 example (Appendix D) built in. It ships in the toolkit bundle, so its SHA-256 is in the pre-registered manifest. Stage 1 copies it verbatim to `dossier/FRAMEWORK_stage.md`, and `checks.py framework` checks the copy's hash; the orchestrator makes no edit of its own.
   - *Why. Every subagent read a FRAMEWORK that still described ten investors, entry prices, tier margins and "base + Σ add-ons" rates, overridden by Appendix B's Precedence (a known cost: "a standing source of confusion"). Route (d) treats FRAMEWORK rules as binding, so leaving Rule 2 and Simon's gates in place would put two conflicting rules in front of every verifier. And the FRAMEWORK was copied from the project at run time with no record of which version a run used.*
6. **T6 — What the season measures.**
   - **Channel monitor (Stage 3, descriptive).** Per execution: seats off the macro base, the mean five-year forecast growth, terminal growth, quality score, break probability and tail term, Walter's mean multiplier, the runs with debt deducted, the risk-class counts, the register by channel with each channel's BUY effect, and the debt row, so a move of value between channels, in either direction, shows up.
   - **Bridge file.** A new season file, `OUTCOME_BRIDGE.md`, written by `bridge.py` from published per-run data (G5): each execution's published BUY, the BUY with every seat on its macro-base fair value (margins held), and that BUY without Simon. The outcome ledger's rows and header stay as they are.
   - **Ledger tests.** Appendix K adds a signed forecast-bias test (test 5), stratified by spec version and `systematic_risk_class`; test 3 is reported by spec version.
   - **Roll-up.** v10 rows carry `mechanism_version` "v10" and two new columns, `debt_path` and `systematic_risk_class` ("n/a" in earlier rows), and a VALIDATION column.
   - **Validation.** The first v10 executions re-run ICE, BBW and HCI on their v9 packs, in fresh sessions, with the same model and MARKET_INPUTS; their rows are marked VALIDATION. Before each starts, the comparison (realised and unexplained shares, channel means) is pre-registered (Appendix G, validation block). The market price is never a criterion.

**Review before release.** One review round by three independent reviewers (arithmetic and code; integrity and neutrality; a practitioner), every finding addressed (`claude/SPEC_v10_REVIEW_RECORD.md`).

**What v10 does NOT change.** Everything in v9 not named above, including:
- the margin arithmetic: the quality premium π(score), the tail term, the clamp, AT CAP and NO BUY (now under FRAMEWORK v10's uninvestability rule);
- the margin-rule alternatives and their constants;
- the share-count rule (F1), the redaction lists and check (F2), the versioned toolkit and replay gate (F3), acquisition matching (F4 and N5) and the alternative denominator (N2);
- MARKET_INPUTS and the rebased ERP (N4);
- 4 + 4 runs, the trimmed mean, the interval and the ledger rules;
- unmasked packs and the pack-only rule (N1);
- the template system and the Stage-0.5 diff, apart from the template edits T1–T6 make;
- the critic and verifier stages, apart from the text changes in the change table below;
- the outcome ledger's execution rows and header, and the per-run data (G4, G5);
- Stage 7 (optional).

**Season comparability (v10).**
- Roll-up rows carry `mechanism_version` "v10". v10 headlines are not comparable with v9's: the rates (T1), the debt treatment (T2), the roster (T4) and the run instructions (T3–T5) all change. `OUTCOME_BRIDGE.md` gives the arithmetic part of the comparison for every execution whose per-run data survives (T6).
- The margin arithmetic (π, the tail term, the clamp, the margin-rule alternatives) is v8's and v9's, so margin-related frame effects may still be pooled across v8-grad, v9 and v10 rows with version as a fixed effect.
- Rows marked VALIDATION are ordinary v10 rows that re-value a ticker already in the season. Pooled tests use one row set per ticker: a ticker's VALIDATION rows replace its earlier rows in v10-only analyses and are excluded from analyses pooled across versions (the ticker's earlier rows stay).

**What v9 changed (carried into v10).** Seven edits (N1–N7), drawn from the MELI v8 execution and the season's record, with the consequential changes they force. Everything else in v8 stands. The spec owner decided the change list's four open questions: A (the alternative denominator, N2), B (the ERP, N4), C (remembered facts, N1) and D (review before release).
1. **N1 — No masking or rescaling; a pack-only rule.**
   - Each run's pack is its redacted dossier as written: the company's name and its real figures, with no secret factors. Six things go: the tag screener's identity and scale tagging with its completeness check; masking and rescaling (Stage 1c) with its masking and consistency checks; the identification probe (Stage 1d); back-scaling in v9 executions; the scale-dependence memory test, per ticker and pooled; and the memory line on the Decision Card.
   - Kept: the redaction lists and the redaction check (F2), methodology-note removal, the no-market-data clause, the clean rooms, web off for every subagent, and the fixed labels MASK_LABEL and MASK_UNIT in the templates, which keep every subagent text identical across tickers (the pack carries the name).
   - The tag screener keeps two jobs: the data-thinness list, and the list of share-count figures the redaction check needs to refuse a redaction over a share count.
   - **The pack-only rule (decision C: all facts).** Runs may recognise the company. They use only the facts and reported figures in the pack and MARKET_INPUTS, and the rules and constants in FRAMEWORK and the instructions: no remembered price, market value, multiple or analyst target, and no other remembered observation about the company, its peers, its industry or its countries (a figure, a market share, a regulatory change, a macro data point, an event after the pack's as-of date). A run's own assumptions (rates and add-ons, growth, margins, probabilities, branch and terminal values) are judgments, stated and justified from the pack; they are not facts. A run that presents a remembered observation as fact breaks a STAGE2_INSTRUCTIONS requirement (verification route (d)); such a finding moves a number only by restoring a figure the pack contains. Critics and verifiers judge the run against the pack alone: a remembered fact is never evidence, and a PACK-GAP names the missing item, never a remembered value.
   - *Why. Every identification probe this season (ADBE, DECK, GSL, AGX, TPR; two per execution) named the company, at stated confidence of 90–97% where recorded. The memory test never flagged: its pooled result over 40 season rows was β̂ₖ +0.0038, β̂ⱼ +0.0417, permutation p 0.64. The Stage-1c checks were the season's most frequent stop: four toolkit point releases (v7.1.1, v7.1.2, v7.1.3, v8.0.1) changed them, and on MELI the tag screeners failed completeness three times each, so that execution ran with masking off (deviation D-3).*
   - *Cost. Price memory is no longer measured. The pack-only rule, the no-market-data clause and the redaction lists are the guard (Known costs).*
2. **N2 — A defined alternative denominator, valued by every seat, with a ledger row (decision A).**
   - In Phase 0 each run chooses an alternative denominator on the same definition as its declared denominator (the same gross line or lines and the same kinds of adjustment, each re-measured for the alternative), differing only in the period it is measured over or in the margin applied to the basis-period revenue, in either direction. The run states what differs and why, or "none" with a reason. The run chooses it; the spec only bounds what may differ (Rule O-2).
   - Every seat reports `fair_value_alternative_denominator`: its base-branch fair value with every forecast cash flow (before any acquisition-spend deduction) multiplied by alternative ÷ declared, and every growth rate, discount rate and terminal parameter held, as one complete input-change line (S2).
   - Stage 3 adds a ledger row: the headline with every seat on that value, its required margin held fixed. It is a lever on the card and a candidate for the largest sensitivity. Because runs choose in either direction and opposite choices net out in the committee row, the card also counts the runs whose alternative lies above or below the declared denominator, and the seats valued; a row no seat valued reads n/a.
   - *MELI v8: eight runs used five denominator definitions; headlines ranged from $293 to $1,984, and 87% of the within-dossier log variance came from fair value. Most of that came from the multiple (forecast path, rate add-ons, terminal growth near the macro base), not from the starting denominator: declared denominators ranged $29–$41 per share, and runs e5 and 0d declared the same $36.75 yet headlined $1,984 and $391. v8 asked for a "leading alternative" but never valued it; seven of the eight named alternatives changed the definition and are barred under N2. N2 reports how far the BUY rests on the starting point the runs chose. It does not reduce run noise.*
3. **N3 — Runs check every branch and tree before writing.** The committee script prints each input-change line from the code's own input differences, rebuilds every branch value from exactly the printed changes to within 0.5%, and asserts the Stage-3 tree checks at Stage 3's tolerances (unique names; one base and one break; probabilities summing to 1 within 0.005; the base equal to fair value within 0.1% and the tree's median; the break the lowest branch) before the output is written. A run that fails fixes the branch values or the tree's shape, never `break_p` alone to pass a check. *MELI: 5 of 8 critics found branch values that could not be rebuilt (C4), and one run's trees all failed the median check, so its eight seats dropped out of the tree-based margin rules.*
4. **N4 — The ERP on the file's own risk-free basis (decision B: rebase).** Appendix J records the source's ERP and the risk-free rate the source measured it against, and states the ERP used as source ERP + source risk-free − file risk-free, which keeps the source's implied market return. It applies only to an implied (forward-looking) premium computed against the same currency's 10-year government yield and dated at most 31 days before the file's rate; a historical or survey premium, one from another currency, or one whose source sets its own pairing with the risk-free rate is not rebased, and the builder asks the spec owner. It applies from the first v9 season file; earlier executions are not recomputed. *The 2026-09-10 file gave Damodaran's 4.09%, measured against a 4.75% Treasury rate, beside a 4.95% risk-free rate; five of eight MELI critics raised it. Rebased on those figures: 4.09 + 4.75 − 4.95 = 3.89%, a macro base of 8.84% rather than 9.04%.*
5. **N5 — No acquisition mismatch without acquisition spend.** When the pack shows no acquisition cash and the run's normalised acquisition spend is 0, every `growth_basis` × `acq_spend_deducted` pair counts as matched, and both acquisition rows equal the headline. Runs are told to use "organic", not deducted, in that case. *MELI's card showed 8 mismatches that moved nothing.*
6. **N6 — Toolkit robustness.** The thinness parser accepts "**Cash flow.**" as well as "**Cash flow**"; `quality_tier_modal` must name a tier, and anything else is logged; the verifier prompt names the `frozen_arith.py verify` command. *MELI: the thin-data line came back empty until it was corrected by hand; one run wrote prose in the modal-tier field; the harness blocked one verifier's `patch` command.*
7. **N7 — Housekeeping.** The auditor treats the pre-registration's per-execution slots as slots (format only); the dossier guideline bars statements about the pipeline or its documents; the Stage-6 checklist copies every MECHANISM finding to SPEC_FLAGS. *The auditor flagged those slots on every ticker; both MELI and both TPR dossiers said the method document could not be found, which was not true; MELI's MECHANISM findings were copied only afterwards.*

**Review before release (decision D).** One review round by three independent reviewers (arithmetic and code; integrity and neutrality; a practitioner), every finding addressed, then a closing check (`claude/SPEC_v9_REVIEW_RECORD.md`).

**What v9 did not change** (carried into v10 except where v10 says otherwise). Everything in v8 not named above, including:
- the seat and BUY arithmetic: the quality premium, the tail term, the clamp, AT CAP, NO BUY and the eight seats;
- the margin-rule alternatives and their constants;
- the share-count rule (F1), the redaction lists and check (F2), the versioned toolkit and replay gate (F3), and acquisition matching (F4) apart from N5;
- MARKET_INPUTS, apart from the ERP's basis;
- 4 + 4 runs, the trimmed mean, the interval and the ledger rules;
- the template system (every subagent text a fixed template) and the Stage-0.5 diff, apart from the template edits N1–N7 make;
- the critic and verifier stages, apart from the text changes in the change table below;
- the outcome ledger and the per-run data (G4, G5);
- Stage 7 (optional) and FRAMEWORK.

**Season comparability (v9).**
- Roll-up rows carry `mechanism_version` "v9", and their `ln_k`, `ln_j` and probe cells read "n/a".
- The BUY arithmetic and the margin rules are v8's: replayed on the reference execution, v9 reproduces the v8 replay's published BUY, and the new row is a ledger row that enters no point. Headlines are not directly comparable with v8's, because runs see unmasked packs under new instructions (N1–N3, N5) and a different macro base (N4).
- The macro base moves by the season file's source risk-free rate minus its risk-free rate, in either direction: −20bp at 2026-09-10 figures, which would raise headlines; MELI's rate lever, −$41 for +50bp, gives the scale.
- The pooled memory test closes at its 40-row result; rows marked D-3 (unmasked) are excluded from it, like BRIDGE rows. MELI v8 stays a v8 row marked D-3: its packs match v9's; its run instructions are v8's.
- v8-grad and v9 rows share their margin arithmetic, so margin-related frame effects may be pooled across them with version as a fixed effect.

**What v8 changed (carried into v9 and v10; G2's eight seats became seven in v10, T4).** Five margin, roster and record edits (G1–G5) and four speed edits (S1–S4), with the consequential changes they force. Everything else in v7.1 stood.
1. **G1 — A continuous quality premium replaces the tier steps.**
   - Each seat's margin is `required = clamp(π(score) + p·L, 0.10, 0.60)`. π is piecewise-linear in the quality score through the old tier constants placed at the tier midpoints, (52.5, 40%), (67.5, 32.5%), (82.5, 22.5%) and (95, 12.5%), and flat outside them.
   - The tier is still derived from the score, as a label (Rule 8, the tier distribution). It no longer sets the margin.
   - The term is renamed for what it is. v7.1 said the tier margin prices the bear branches; on AGX and ADBE it was 4.5–5.2× the probability-weighted bear loss and exceeded the whole tree's expected shortfall in every seat. It is a premium for estimation error and risk aversion, graded by business quality.
   - It is adopted without the levelling constant (−0.73pp, fitted in sample) that debate 2 sketched. The midpoint anchors raise π across the lower half of each tier, so on AGX, whose scores cluster at 60–68, the published BUY falls.
   - *AGX and ADBE: a one-point score change at 60, 75 or 90 moved a seat's margin by 7.5–10pp, and tier flips were 64–79% of each investor's run-to-run margin variance. On those two tickers G1 moves the published BUY by −2.3% (AGX) and +0.05% (ADBE). Debate 2's judge sized the gain in headline accuracy as very small (under 0.05pp of RMS error): G1's value is at seat level, removing arbitrary 7.5–10pp jumps.*
2. **G2 — Eight seats; Victor and Max become script rules.**
   - The council seats Simon, Marcus, Sophie, Claire, Graham, Walter, Helena and Alexander. Victor and Max are not seated, and no seat produces an entry price.
   - Their methods survive as two margin-rule alternatives the script computes from the eight seats' own trees (G3).
   - *Their entry prices never entered the BUY (Rule 6). Priced under the committee rule, they moved it by about 1%: their fair values repeated the committee's. Each cost about a fifth of every run's per-seat work.*
3. **G3 — Margin-rule alternatives on the Decision Card, never averaged.**
   - The script reports the BUY under three other rules on the same seats and trees: the v7.1 step tiers; the EV rule, "tuned Victor" (0.670 × the tree's expected value); and the expectile rule, "tuned Max" (the price at which expected upside is 7.75 × expected downside, the 1/8.75 expectile). It also shows, for every rule, the expected upside ÷ expected downside at its BUY, so the policy each rule implies is visible.
   - The constants were set once, in sample, at the v7.1 step rule's average strictness on AGX and ADBE, and are never re-tuned per ticker. Under G1 the committee is slightly stricter than that, so the alternatives can sit above the published BUY.
   - They are policy alternatives. They are not sensitivity-ledger rows, not in the interval, and never averaged with the published BUY or with each other.
   - *Debate 1: untuned, the profiles were only looser (BUY +14% to +49%). Debate 2: tuned to the committee's average strictness, the three-way blend was judged an expected loss (a 25–35% chance of beating the committee), because the profiles read the committee's own trees (run correlations 0.78–0.94) and ignore quality. Showing the set keeps the policy question visible.*
4. **G4 — An outcome ledger.** A season file records every execution's BUY under each margin rule (and one further challenger rule, EV × (1 − π)), with the implied upside:downside ratios, the mean quality score and break horizon, and the path of the execution's published data, where each seat's five-year base-branch forecast and break horizon are kept (Appendix K). Outcomes go to a separate observations file that no execution opens. Only outcomes, scored with the pre-registered loss in Appendix K, can settle which margin rule is more accurate.
5. **G5 — Per-run data published.** After Stage 6 the toolkit writes a replayable copy of every run's MACHINE SUMMARY, every verification and the configuration with k and j to durable storage. *Only ADBE's per-run data survived the season, so GSL and DECK could not be back-tested.*
6. **S1 — One committee script per run.** Appendix B asks for one shared valuation function and one seat table, and for the output to be written in one pass from the script's tables. *AGX run-time review (from the orchestrator's task records): runs that worked this way took 16–29 tool calls and 25–37 minutes; runs that split the work across many scripts took 42–64 calls and 44–88 minutes, with no better critique results.*
7. **S2 — Full schedules for base and break branches only.** Each run states its valuation mechanics once; every other branch value and extra fair value is stated as its complete input changes from the base branch, reproducible to 0.5%. *Year-by-year schedule tables were 9–28% of each AGX run's output, about half of it for non-base values.*
8. **S3 — Per-run pipelining.** A run's verifier starts as soon as its critique returns. Where subagents have isolated file systems, a run's critic also starts as soon as that run returns. On a shared file system (standing deviation P-2), critics still wait for every run.
9. **S4 — Stage-1 and restore fixes.** The tag screener tags unit and scale labels near share figures as UNSCALED (Appendix H), and the completeness check skips parenthesised scale labels (toolkit v7.1.3); both are moot in v9 (N1). The toolkit ships as one bundle that restores by copy and hash check. *The "(000s)" stop hit three tickers in a row and cost about 50 minutes on AGX; restoring by transcription cost about 15 minutes.*

**What v8 did not change** (carried into v9 except where v9 says otherwise). Everything in v7.1 not named above, including:
- the tail term p·L, the clamp, AT CAP, the Rule-4 minimum and Helena's floor;
- the share-count rule (F1), the redaction lists (F2), the versioned toolkit and replay gate (F3), and acquisition matching (F4);
- masking, rescaling, the identification probe and the memory test (removed in v9, N1);
- MARKET_INPUTS;
- 4 + 4 runs;
- the trimmed mean, the interval and the ledger rules;
- the template system and the Stage-0.5 diff;
- the critic and verifier stages, apart from S3's timing and the text changes listed in the change table below;
- Stage 7 (optional);
- FRAMEWORK. Where FRAMEWORK refers to ten investors, to Victor, Max or entry prices, to tier margins, or to a schedule for every fair value, the Stage-2 instructions govern (Appendix B, "Precedence").

**Season comparability (v8).** v8 changes the margin arithmetic (G1), the roster (G2) and the run instructions (G2, S1, S2).
- Roll-up rows carry `mechanism_version` "v8-grad".
- The arithmetic part is replayed: the reference execution recomputed under v8 arithmetic is recorded in the toolkit manifest as "ADBE @ v8 (replay)". Its step-tier line reproduces the v7.1 replay exactly.
- Every v8 Decision Card also shows the step-tier BUY, so each v8 figure can be read against the v7.1 rule on the same runs.
- The roster and run-instruction parts cannot be replayed. v8 headlines are not directly comparable with earlier ones.
- The pooled memory test spans v7, v7.1 and v8 rows: masking and rescaling are unchanged.

**What v7.1 changed (carried into v8 and v9).** Five edits on top of v7 (F1–F5):
1. **F1 — One share-count rule.**
   - Runs build value on company totals and convert to per share once, with the latest dated diluted count.
   - The count that divides the cash flow (`denominator_count_m`) must equal the per-share count. The script normalises any run where they differ, and logs it.
   - A new ledger row shows the period-weighted alternative.
   - *ADBE v7: the two dossiers' runs split 395M against 406M, worth about $7 per share, while the old share-count row read $0.*
2. **F2 — Redaction by fixed lists, checked across dossiers.**
   - The two-operation test is replaced by a redact list (stated prices and multiples, and the dollar side of the company's own equity transactions) and a keep list (every share count, and every other financial line).
   - One redaction screener reads every dossier. Tag screening stays one per dossier.
   - The toolkit rejects any redaction that names no list item or touches a share count, and writes a class table across dossiers.
   - *ADBE v7: the same rule led one screener to remove dossier A's whole share-count history and the other to keep dossier B's.*
3. **F3 — A versioned toolkit with a replay gate.**
   - The spec owner ships every script in `toolkit/<version>/`. The orchestrator never writes or edits a script during an execution.
   - A new toolkit version must reproduce the stored reference execution (ADBE v7, published BUY 237.87) in compatibility mode before first use.
   - Screener outputs are machine-readable, so the toolkit applies them with no orchestrator transcription and no per-ticker code.
   - The orchestrator handles packs, runs, critiques and verifications by script, not by reading them.
   - *ADBE v7: the 89KB arithmetic script and the Stage-1c checks were written by hand for one ticker, and the orchestrator was 30% of the cost.*
4. **F4 — Two-sided acquisition matching.**
   - Every seat declares whether its growth includes acquired growth and whether its cash flows deduct normalised acquisition spend. The two must match.
   - Every seat reports its fair value under the other matched treatment, and two ledger rows show the effect.
   - Dossiers carry five years of acquisition cash and the organic/acquired growth split.
   - *ADBE v7: 6 of 8 critiques found seats crediting acquired growth without its cost, and one run deducted the cost against organic-only growth.*
5. **F5 — No cliff in the margin arithmetic.**
   - A seat whose base(tier) + p·L exceeds 0.60 stays in the headline at the 0.60 cap (AT CAP) instead of dropping out. NO BUY remains only for a FRAMEWORK uninvestability rule.
   - L is measured against the seat's fair value at the macro base, before its own rate add-ons.
   - *ADBE v7 MECHANISM findings m4 #11 and w6 #12: a seat crossing the cap would have raised its run's headline by about 10%, and a +450bp rate add-on lowered its own tail term.*

**What v7 changed (carried into v7.1, v8 and v9; E3's masking, rescaling and memory test removed in v9).** Five major edits, each with the consequential changes it forces:
1. **E1 — One tail term replaces the asymmetry/gate machinery.**
   - Each seat's margin is `required = clamp(base(tier) + p·L, 0.10, 0.60)`. Here p and L come from the seat's own break branch, after Helena's floor.
   - R, ED/EU, the committee-median anchor, median-R inheritance, the 15% gate and the upside valve are deleted.
   - Every seat reports a tree and derives its break probability in three steps. Helena alone sets the floor.
2. **E2 — Numbers move only through the frozen arithmetic, by script.**
   - Critics and verifiers receive the rules the run followed, and those rules take precedence over FRAMEWORK's tier table.
   - Verifiers return field-level patches.
   - One hash-registered script computes Stages 3, 5 and 5b.
   - A fix that would change the formula is CONFIRMED-unquantified (MECHANISM).
3. **E3 — Price-memory control in every execution.**
   - Every run gets a masked pack, rescaled by two secret factors.
   - A scale-dependence test and an identification probe check for memory.
   - Critics lose web access, orchestrator-only files sit in a clean room, and Stage 7 becomes optional.
4. **E4 — Dated conventions and a season market-inputs sheet.**
   - Runs declare the valuation date, the per-share count date and the balance-sheet date.
   - One MARKET_INPUTS file gives the macro base.
   - Scripts report a convention sensitivity and a rate lever.
   - An INDUCED label marks agreement that a template dictated, and dossiers carry no methodology recommendations.
5. **E5 — What is published, and how precise it is.**
   - No scorers and no coefficient.
   - The point estimate is a trimmed mean, published with a labelled 80% confidence interval from run noise and a sensitivity ledger.
   - A script-built Decision Card opens the analysis.
   - Four runs per dossier by default.

v7 replaces the v5 margin mechanism with one tail term per seat (E1). Both items deferred to v7 in v6, the asymmetry anchor and the graded gate, are resolved by removal (see "Resolved from the v6 deferred list").

**What v7 did not change** (carried over from v6.3):
- Rule O-1 (blindness), extended by the clean room (E3);
- Rule O-2 (the orchestrator holds no valuation opinion), with one carve-out, the season MARKET_INPUTS file (E4);
- the template system: every text a subagent receives has a template, and a script diffs it;
- the Stage-1 two-operation redaction rule (replaced in v7.1 by F2);
- per-run Phase-0 frames and weights;
- the committee: ten investors, with Victor and Max segregated as IRR seats (Rule 6);
- the shortened council;
- verification routes (a)–(d′), with route (d)'s scope now stated (E2);
- FRAMEWORK, except the E1 and E4 edits listed in the v6.3 → v7 revision history.

**Attribution.** v7 is five edits at once. A v7 result read against v6 numbers cannot be attributed to any single edit. On the first v7 ticker, two bridges make the largest effects visible:
- the **v6-rule bridge headline** (E1): the v6 margin arithmetic recomputed by script from the same trees;
- the **bridge runs** (E3): one run per dossier on an unmasked, unscaled pack.

Stage 7 is optional under v7.

**Background: what v6 changed (carried into v7).** v6 is about **who makes the valuation judgments**.

In v5, the orchestrator wrote a ticker-specific pre-registration. It fixed:
- the denominator;
- the committee weights;
- the floor/gate reading;
- the guidance stance;
- the "candidate axis".

In practice it also argued which way the live judgments should go. It then handed that frame to every Stage-2 run. Every run inherited the same frame, so the frame's effect on the number was invisible to the drift floor.

The one comparison available is the two ADBE executions, at $316.15 and $221.16. Between them, the orchestrator, the run model and the redactions all changed at once, so frame effects could not be separated from anything else. What the comparison does show:
- The $95 gap was ~1.7× the average same-dossier drift.
- It split roughly half fair value, half margin.
- The fair-value half came almost entirely from **adjustments to owner cash flow** (acquisitions, deferred-revenue float, tax), not from the multiple.

v6 moves every valuation judgment into the runs. The orchestrator keeps only blinding, integrity controls and arithmetic. v7 keeps that design.

```
VARIABLES — set these once. Everything below refers to them. NOTHING ELSE about the company may be set by the orchestrator.
  TICKER       = <SET>
  UNIT         = <SET>   # reporting unit only, e.g. "USD per Class A share". A unit, never a basis-period, share-count or denominator choice.
  FRAMEWORK    = toolkit/v10/FRAMEWORK_v10.md   (shipped in the toolkit bundle, SHA-256 in its manifest; copied verbatim to dossier/FRAMEWORK_stage.md and given to EVERY subagent, see Stage 1; v10, T5)
  DOSSIERS     = [ A, A, A, A, B, B, B, B ]   # each dossier 4× by default; 3× is the minimum and must be logged as a deviation
  MODEL        = <SET>   # model ID for the orchestrator and every subagent; one model per execution unless running a deliberate model comparison
  USER_MANDATE = <NONE | verbatim user text>   # see "User mandates" below; the ONLY company-specific framing permitted, and only if the user supplied it
  MASK_LABEL   = "the Company"   # fixed; fills ⟨TICKER⟩ in every template text a Stage-2, Stage-4 or Stage-4b subagent receives. v9: packs are not masked and name the company; the label only keeps those templates identical across tickers. Never changed per ticker.
  MASK_UNIT    = "<ISO currency code> per share"   # e.g. "USD per share"; the reporting currency only, never a share class or company wording; fills ⟨UNIT⟩ in every template text a Stage-2, 4 or 4b subagent receives.
  AS_OF        = <SET>   # date of the season market-inputs sheet used: the latest AS_OF on or before the earliest pack as-of date
  MARKET_INPUTS = market/MARKET_INPUTS_<AS_OF>_<currency>.md   # season file (Rule O-2, "Season market inputs"); byte-identical for every ticker with the same AS_OF and currency; v9 and v10 use a file on the v9 Appendix-J template (N4)
  TOOLKIT      = toolkit/v10   # versioned scripts and FRAMEWORK_v10.md shipped by the spec owner (F3, T5); every file's SHA-256 is in toolkit/v10/TOOLKIT_MANIFEST.md; never written or edited during an execution
  VALIDATION   = <NONE | the v9 published data folder this execution re-values>   # v10, T6; set only for the pre-registered validation re-runs; the SHA-256 of that folder's DATA_MANIFEST.md fills ⟨BASELINE⟩ in Appendix G (a hash, so the pre-registration stays ticker-free); the path is recorded in ORCHESTRATOR_LOG
```

---

## The two rules that govern everything

**Rule O-1 — Blindness (inherited from v4; v7 adds the clean room).**
- Each stage must be genuinely blind to the stages after it.
- Pass artifacts between stages as FILES ONLY. Never summarise, characterise or preview one stage's output in the next stage's prompt.
- Never tell a subagent what you expect, or what a previous run concluded.
- Parallel subagents at the same stage must not see each other's work or be told how many of them exist. Use opaque output filenames, and keep the token → run map in a manifest only you hold.
- Bar every subagent from any project or knowledge-base search tool.
- **Clean room.** The harness cannot remove file-system tools from a subagent, so the barriers are physical, not instructions.
  - Every subagent works in its own directory. The directory holds copies of exactly its input files, an empty scratch folder and its output path.
  - No subagent's directory receives any file other than its declared inputs. Outputs are copied out by script as each subagent returns, the subagent's directory is then deleted with its scratch folder archived into the orchestrator-only tree, and the orchestrator routes an output by path without reading it.
  - **Timing (v8, S3).** A run's verifier may start as soon as its critique has returned. A run's critic may start as soon as that run has returned only where every subagent has its own file system. On a shared file system (standing deviation P-2), critics start only after every run has returned and every run's directory has been deleted, so no run can read a critique; the remaining exposure (a running critic could read a sibling run's verification or redlog) is logged under P-2. Stages 3, 5 and 5b wait for every run and every verification.
  - Orchestrator-only files are never readable by a subagent. They are:
    - the raw dossiers;
    - screener outputs, including the share-count tag lists;
    - the manifest (tokens, dossiers and packs);
    - files from prior tickers, including every published per-run data folder (G5);
    - the season roll-up and the outcome-ledger files (G4);
    - the Stage-3/5 configuration and outputs, and `statistics.md`, until Stage 6 is published (they map tokens to dossiers and results);
    - any spec copy that carries an execution note.
  - Keep them outside the subagents' file system. If the harness shares one file system, keep them encrypted at rest from the start of Stage 1 until Stage 5b ends: `openssl enc -aes-256-cbc -pbkdf2`, with a passphrase drawn with `secrets` and held only in the orchestrator's context.
  - At each launch, the orchestrator saves a listing of the tree that subagents can read to `final/cleanroom_<stage>_<token>.txt`.

**Rule O-2 — The orchestrator holds no valuation opinion.** The orchestrator may not decide, suggest, rank, pre-register or frame any of the following for the company:
- the denominator, basis period, share count, or any adjustment to the denominator;
- the macro base (other than supplying the season MARKET_INPUTS file below), growth or terminal assumptions, the debt path or the systematic risk class;
- the business-type classification, the committee weights or the peer set;
- which floor exists, or whether it bounds a loss;
- guidance credibility;
- the moat, the tier, break probabilities, or which risks the seats price and where;
- which judgments are "live", which way they lean, or which dossier difference is likely to matter.

These all belong to each run's Phase-0 moderator. Rule O-2 is Rule 7 applied to the orchestrator itself.

**Template conventions are not orchestrator opinions.** The valuation-date default, the share-count rule (F1), the acquisition matching rule and its default normalisation (the window total ÷ its years, F4), the alternative-denominator rule (v9, N2: the same definition as the declared denominator, differing only in its period or in the margin applied to the basis-period revenue, in either direction), the macro-base rate rule (v10, T1: every seat discounts at the macro base) and the debt rule (v10, T2: cash flow to equity, with debt counted once) are fixed in Appendix B, identical for every company, and labelled INDUCED by the Stage-3 induced-field check wherever runs agree on them. They decide how a choice is expressed and kept consistent, not which level is right.

**The ticker-swap test (how O-2 is enforced).** Every text the orchestrator gives a subagent must remain true and unchanged if TICKER were replaced by any other company. This covers:
- the Stage-2 instructions (Appendix B);
- the critic and verifier prompts (Appendices E and F);
- the critic checklist (Appendix C);
- the pre-registration (Appendix G);
- **the launch prompt used to start every subagent, and the redaction-screener, tag-screener, auditor and Stage-6 writer instructions (Appendix H);**
- the MARKET_INPUTS file (Appendix J), which is checked by hash, not by template diff (Stage 0.5).

**Every text any subagent receives from the orchestrator has a template in this spec.** There is no free-text channel: not the files, and not the short prompt that launches the subagent.

Only these slots may differ between tickers:
- TICKER;
- UNIT;
- opaque dossier filenames;
- each run's redaction list, `redlog_<run>.md` (locations and replacement texts only; Stage 1), which is shown only to that run's verifier (Stage 4b), never to runs or critics;
- the USER_MANDATE block, if the user supplied one;
- in the pre-registration only: the run count, the replicate structure, the model ID, the timestamp, the toolkit manifest's SHA-256 and, in a validation execution (v10, T6), the baseline data manifest's SHA-256;
- file paths in launch prompts;
- the MARKET_INPUTS file, which differs only by AS_OF and currency and is identical for every ticker that shares them.

**Fixed labels (v9).** In Appendices B, E and F, in any other template text a run, critic or verifier receives, and in every launch prompt for Stages 2, 4 and 4b, ⟨TICKER⟩ is filled with MASK_LABEL, ⟨UNIT⟩ is filled with MASK_UNIT, and no path contains the ticker. Those texts are therefore identical across tickers, apart from opaque file paths and the reporting currency (in MASK_UNIT and MARKET_INPUTS). Under v9 the packs are not masked (N1): they name the company, so the labels hide nothing; they keep the templates ticker-free, which is what the ticker-swap test and the Stage-0.5 diff check. UNIT itself is used only in texts no Stage-2, 4 or 4b subagent receives.

The Stage-0.5 diff and neutrality audit check this. The orchestrator does not certify its own texts.

**User mandates.** The user may impose a framing, e.g. "value it as a melting ice cube" or "use a 10% hurdle". O-2 binds the orchestrator, not the user. So:
- **Verbatim.** The orchestrator copies the user's framing verbatim into USER_MANDATE. It does not paraphrase, extend or interpret it.
- **Placement.** The text appears in a clearly labelled `USER MANDATE (supplied by the user, not the pipeline)` block. The block is placed identically in the Stage-2 instructions, the critic prompt and the verifier prompt.
- **Scope.** A mandate may override FRAMEWORK *valuation defaults*. It may **never** override:
  - Rule O-1 (blindness);
  - the no-market-data clause and the pack-only rule (Appendix B, Inputs);
  - the web restrictions of any stage;
  - the Stage-1 redactions.

  If a mandate would require any of these (e.g. "sanity-check against the current price"), the orchestrator **asks the user before Stage 0**. It does not start the pipeline until the mandate is revised or withdrawn.

  **If the user is not present** (a scheduled or unattended execution), the orchestrator **does not start**. It logs the conflict in ORCHESTRATOR_LOG, notifies the user, and stops. It never runs with the conflicting part dropped or reinterpreted.
- **Audit.** The block is exempt from the ticker-swap test. The Stage-0.5 auditor checks only that it matches the user's words exactly.
- **Confirmation route.** A run that ignores the mandate can be CONFIRMED under verification route (d′) (see Stage 4b).
- **Reporting.** Stage 6 states that the published figure is **conditional on the mandate**.
- **Default.** If USER_MANDATE = NONE, no such block exists anywhere.

**Season market inputs (the one pipeline-supplied valuation input).** A market observable is not a company judgment, but when each dossier builder picks its own, the choice varies by dossier and becomes a frame axis. (On DECK v6 the two packs gave 5.00% and 4.75%, a −$2 to −$5 per run PACK-GAP raised by 3 of 3 pack-B critics.) So:
- **Built once per AS_OF and currency, never per ticker.** It is built by the user, or with the user's approval by a season script that reads the named series. It is stored in durable storage outside every ticker folder as `market/MARKET_INPUTS_<AS_OF>_<currency>.md`, and it is instantiated from Appendix J. No orchestrator edits it.
- **Contents.** Only the Appendix-J fields: AS_OF, the 10-year government yield in that currency with its series and observation date, and one equity risk premium with its source, date and convention, the risk-free rate the source measured it against, and the premium rebased to the file's risk-free rate (v9, N4). Nothing else.
- **Why it passes the ticker-swap test.** It is byte-identical for every ticker valued with the same AS_OF and currency. Stage 0.5 proves this by hash (Step 1).
- **Which file.** The orchestrator uses the file whose AS_OF is the latest on or before the earliest pack as-of date. If that gap exceeds 31 days, or no file exists, the orchestrator asks the user before Stage 0. If the user is not present, it logs, notifies and stops, as for a conflicting mandate.
- **v9 files (N4).** A v9 or v10 execution uses only files on the v9 Appendix-J template: under "Which file", files on an earlier template are ignored. No two season files share an AS_OF and currency (check (ii) of Stage 0.5 refuses a reuse). If no v9 file qualifies, the orchestrator asks the user for a new v9 file before Stage 0 (or, unattended, logs, notifies and stops).
- **Who receives it.** Every Stage-2 run, critic and verifier. In Appendix B it governs over any macro figure in ⟨PACK⟩.
- **Attribution runs.** It is never supplied to runs whose purpose is comparison with a v5 or v6 execution. Those runs keep the v6 macro rule (Stage 7, "First application").

---

## Folder layout
`./TICKER/` contains `dossier/`, `runs/`, `critiques/` and `final/`. It is orchestrator-only (Rule O-1, clean room). Every path shown to a Stage-2, 4 or 4b subagent sits under an opaque root (`./<root>/`, drawn with `secrets`) that holds only the clean-room working directories. The orchestrator copies outputs from there into `./TICKER/` by script.
- Every artifact is written to disk and mirrored to durable storage as each stage completes, except two groups. The raw dossiers, the screener outputs, `REDACTION_LOG.md` and the manifest carry redacted market data or the token map: they are mirrored only after Stage 6 is published, when no subagent of the execution is active. The Stage-3/5 configuration and outputs and `statistics.md` are mirrored at the same point. Where the raw dossiers already sit in storage that subagents' tools can reach (for example a project knowledge base), the orchestrator logs it under P-2.
- `final/ORCHESTRATOR_LOG.md` records every act the orchestrator performed that was not purely mechanical, with the rule that authorised it. Under v6 this log should be nearly empty; its length is itself a finding.
- `final/SPEC_FLAGS.md` records neutrality-audit flags that land on spec-template text (see Stage 0.5). These are issues for the spec owner, not for this execution.
- `./toolkit/<version>/` (durable storage, shared by every ticker of the spec version) holds the shipped scripts, their TOOLKIT_MANIFEST and the reference execution. The execution copies the scripts read-only into `./TICKER/orch/` and checks every SHA-256 against the manifest. The reference execution is orchestrator-only (Rule O-1, files from prior tickers): no subagent receives it.

## Standing deviation P-1 — dossiers already in the orchestrator's context
When dossiers arrive as pasted text or attachments, the orchestrator has necessarily read them, and this cannot be undone. Treat it as a standing deviation, not something to try to avoid:
- the orchestrator writes each dossier to file **verbatim**;
- it performs **no content screen of its own** (the screeners do, in Stage 1);
- it logs P-1 in ORCHESTRATOR_LOG.

Its knowledge of the dossiers is harmless only because O-2 and the templates give it nowhere to put an opinion.

## Standing deviation P-2 — a shared file system (v8)
When the harness runs every subagent as one user on one file system (as on DECK, GSL and AGX), the clean-room barriers are partly instructional: a subagent could list sibling directories, and every subagent has the tools the harness gives it. Treat this as a standing deviation:
- the orchestrator logs P-2 in ORCHESTRATOR_LOG, with the harness facts;
- orchestrator-only files are sealed at rest or kept outside the subagents' root (Rule O-1);
- each subagent's directory is deleted when its output is collected;
- S3 pipelining is limited as Rule O-1 states (critics wait for every run).

## The toolkit and the orchestrator's context (v7.1, F3)
**Scripts come only from the toolkit.**
- Every script the pipeline runs is shipped by the spec owner in `toolkit/<version>/`:
  - the frozen arithmetic script;
  - the Stage-1 and Stage-1c script;
  - the template extractor and diff;
  - the clean-room builder;
  - the sealed store;
  - the checks script (toolkit, script and MARKET_INPUTS hashes, the v9 ERP arithmetic of the season file, and from v10 the staged FRAMEWORK copy's hash);
  - the configuration builder for Stages 3 and 5 (including ⟨CARD_THIN⟩);
  - the roll-up writer;
  - the extractor that serves Stage 6 (including the v9 MECHANISM list);
  - the data publisher and outcome-ledger writer (v8, G4 and G5);
  - the bridge writer (v10, T6: `bridge.py`, which writes `OUTCOME_BRIDGE.md` rows and, for a validation execution, the pre-registered comparison);
  - and, from v10, FRAMEWORK itself (`FRAMEWORK_v10.md`, T5), which is not a script but ships, and is hash-checked, with them.
- The orchestrator may run these scripts and plain file operations (copy, move, delete, list, hash; v8 adds move and delete for collecting and removing clean rooms). It writes no code.
- The orchestrator never writes, patches or extends a script during an execution.
- A toolkit defect found during an execution stops it before the affected stage. The orchestrator logs the defect and notifies the spec owner, and the fix becomes a new toolkit version (Stage 5b, "Replay gate").
- If no toolkit exists for the spec version, the execution does not start.
- **Restore (v8, S4).** The toolkit is kept in durable storage as one bundle (`toolkit/<version>/BUNDLE.tar.gz.b64`) next to its manifest. Restoring it is a copy, a decode and `checks.py toolkit`. Nothing is transcribed, by the orchestrator or by a subagent.

**No transcription.** The screeners write machine-readable outputs (Appendix H). The toolkit validates them and applies them as written. The orchestrator copies no span, number or label by hand.

**The orchestrator does not read the work it routes.**
- During Stages 1–5b it handles dossiers, screener outputs, packs, run files, critiques and verifications by path, through toolkit scripts.
- It reads only:
  - the JSON a subagent returns;
  - the scripts' summaries, checks and tables;
  - the documents it writes in Stage 6.
- Stage-6 synthesis draws on the runs' Phase-6 sections through the toolkit extractor, not on whole run files.
- Standing deviation P-1 still applies to pasted dossiers.

**Checkpoints.** After Stage 1c and after Stage 4b, the orchestrator writes `orch/state.json`: paths, tokens, hashes and the sealed-store location. It never writes the passphrase there in plaintext. It may compact its context and resume from that file.

## Stage 0 — Pre-registration (orchestrator, before anything runs)
Write `final/PREREGISTRATION.md` by instantiating **Appendix G verbatim**. The only slots are the run count, the replicate structure, the model ID, the timestamp, the toolkit manifest's SHA-256 (Stage 5b), in a validation execution the baseline data manifest's SHA-256 (⟨BASELINE⟩), and (if any) the USER_MANDATE text. It **may not be modified after Stage 2 begins**, and it is **not shown to any Stage-2 run**.

Before writing it, the orchestrator runs the toolkit self-test (`toolkit_selftest.py`: every script's self-test and the replay gate). It records the output in `final/script_selftest.txt` and the toolkit manifest's SHA-256 in the pre-registration. A failed self-test stops the execution: the orchestrator logs it and notifies the spec owner, and only a new toolkit version that passes the replay gate may be used.

Because it is a template, the Stage-0.5 diff proves nothing was added to it. For reference, **Appendix G contains ONLY ticker-generic material:**
- the run count and replicate structure;
- the v8 margin constants:
  - the quality premium π(score), piecewise-linear through (52.5, 0.40), (67.5, 0.325), (82.5, 0.225) and (95, 0.125), and flat outside them;
  - `required = clamp(π(score) + p·L, 0.10, 0.60)`, where p and L come from the seat's own break branch after Helena's floor, and L is measured against the seat's fair value at the macro base;
  - AT CAP (required 0.60, seat kept in the headline) if `π(score) + p·L` > 0.60 before clamping; NO BUY only under a FRAMEWORK uninvestability rule;
  - no asymmetry, gate or valve;
  - the seven seated investors (v10, T4), and no entry prices;
  - every seat's discount rate equal to the macro base (v10, T1);
  - the margin-rule alternatives and their constants (Stage 3);
- the critic checklist (Appendix C, verbatim);
- the Stage-3 statistics, and the Stage-5 point-estimate, interval and sensitivity-ledger rules;
- the blinding design: the redaction lists, unmasked packs and the pack-only rule (Stages 1 and 1c, Appendix B);
- the Stage-4b verification standard (Appendix F, verbatim);
- the Stage-5b folding rules;
- the SHA-256 of the toolkit manifest, which lists the SHA-256 of every toolkit script and of FRAMEWORK_v10.md;
- in a validation execution (v10, T6), the SHA-256 of the baseline data manifest and the pre-registered comparison (Appendix G, validation block);
- the Stage-7 pass/fail rule, if Stage 7 is run;
- the USER_MANDATE text verbatim, if any.

**It may NOT contain:**
- a business-type treatment;
- a denominator resolution or an adjustment list;
- frozen weights;
- a floor or tail reading;
- a guidance stance;
- a list of live judgments;
- a candidate dossier axis;
- any expectation about the outcome.

If the orchestrator believes something about the company matters, that belief goes nowhere. The runs either find it or they don't, and whether they find it is part of what is being measured.

**Validation executions (v10, T6).** The first v10 executions re-value ICE, BBW and HCI, each with the baseline's model and MARKET_INPUTS file and VALIDATION set to the baseline's published data folder. They are ordinary v10 executions in every stage, with these differences:
- **Session.** A fresh session with no project or knowledge base attached that holds the baseline's documents; if the harness attaches one, the orchestrator logs it under P-2 (subagents are barred from project tools in every case).
- **Baseline custody.** The baseline data folder, and the toolkit's `replay/` folder (which holds the ICE v9 fixture), are orchestrator-only files from a prior execution (Rule O-1): kept outside the subagents' root or sealed from the start of Stage 1 until Stage 6 is published. The orchestrator does not open the baseline's results before then; `bridge.py compare` reads them after.
- **Packs.** Where the baseline's packs can be restored byte for byte (each SHA-256 equal to the baseline's `final/MANIFEST.md`), the redaction and tag screens of Stage 1 and Stage 1c are skipped and those packs are used, with the baseline's `redlog_<run>.md` files, each under a fresh opaque name and token (the new manifest maps them); this is logged as deviation V-1. Otherwise the baseline's raw dossiers go through Stage 1 again, and the new class table is compared with the baseline's `redaction_check.md` (logged). Stage 1's FRAMEWORK copy and hash check run in either case.
- **Pre-registration.** Appendix G's validation block is instantiated in Stage 0, with ⟨BASELINE⟩ the SHA-256 of the baseline's `DATA_MANIFEST.md`.
- **Output.** `final/VALIDATION.md` (`bridge.py compare`), published after Stage 6 as an addendum to `TICKER_valuation.md`; the roll-up rows carry VALIDATION in their VALIDATION column.

ICE is in-sample for v10: the debate that set v10's direction saw ICE's market price beside its v9 BUY (Known costs). Its VALIDATION rows, and any v9-against-v10 outcome comparison that includes ICE, are marked in-sample.

Before starting, the orchestrator states to the user what it needs (the baseline packs or raw dossiers, and the baseline data folder) and starts only with the user's confirmation; validation executions are never scheduled to run unattended.

## Stage 0.5 — Template diff and neutrality audit

**Step 1 — Mechanical diff (script, before any LLM review).**
- A script diffs each instantiated text against its source appendix:
  - STAGE2_INSTRUCTIONS against Appendix B;
  - the critic checklist against Appendix C;
  - the critic prompt against Appendix E;
  - the verifier prompt against Appendix F;
  - PREREGISTRATION against Appendix G;
  - every launch prompt, the redaction-screener, tag-screener and auditor instructions and the Stage-6 writer instructions against Appendix H;
  - the Stage-6 Decision Card against Appendix I, when it is generated. Its ⟨CARD_…⟩ slots are wildcards for this diff only, and the result is appended to the audit file.
- **Launch prompts are diffed as actually sent.** The orchestrator saves each launch prompt to `final/launch_prompts/<stage>_<token>.txt` at the moment it sends it, and the script diffs those saved copies. Launch prompts sent after Stage 0.5 (Stages 1–6) are diffed when sent, and results are appended to the audit file. A launch prompt that fails the diff is not sent.
- **Slot values are typed.** A path slot (⟨OUT⟩, ⟨OUT2⟩, ⟨SCRATCH⟩, ⟨RUN⟩, ⟨PACK⟩, ⟨CRITIQUE⟩, ⟨REDLOG⟩, each line of ⟨FILES⟩) must be a single path with no whitespace. ⟨N_RUNS⟩, ⟨SCRIPT_SHA⟩, ⟨BASELINE⟩ (v10), ⟨TIMESTAMP⟩, ⟨AS_OF⟩ and ⟨REPLICATES⟩ must match their formats. A ⟨CARD_…⟩ value must follow the Appendix-I slot rules and contain no line break. A value that fails its type is orchestrator-added text. The card and the headline sentence are diffed separately.
- Any difference outside the declared slots (⟨TICKER⟩, ⟨UNIT⟩, ⟨PACK⟩, ⟨RUN⟩, ⟨CRITIQUE⟩, ⟨REDLOG⟩, ⟨OUT⟩, ⟨OUT2⟩, ⟨SCRATCH⟩, ⟨FILES⟩, ⟨N_RUNS⟩, ⟨REPLICATES⟩, ⟨MODEL⟩, ⟨TIMESTAMP⟩, ⟨SCRIPT_SHA⟩, ⟨BASELINE⟩, ⟨AS_OF⟩, the ⟨CARD_…⟩ slots of Appendix I, the mandate block and, in Appendix G, the validation block when VALIDATION ≠ NONE) is **orchestrator-added text**. It is deleted before Step 2 (or before sending).
  - The diff also checks that ⟨TICKER⟩ equals MASK_LABEL, and ⟨UNIT⟩ equals MASK_UNIT (pattern "[A-Z]{3} per share"), in every Stage-2, 4 and 4b text.
  - The Appendix-J slots (⟨AS_OF⟩, ⟨CURRENCY⟩, ⟨RF⟩, ⟨SERIES⟩, ⟨RF_DATE⟩, ⟨ERP⟩, ⟨ERP_RAW⟩, ⟨ERP_RF⟩, ⟨ERP_RF_SERIES⟩, ⟨ERP_SOURCE⟩, ⟨ERP_DATE⟩, ⟨ERP_CONVENTION⟩) are filled once per season file, never per ticker. Per ticker, MARKET_INPUTS is checked by hash, below.
- The toolkit scripts are not templates. Every script's SHA-256 must equal its TOOLKIT_MANIFEST entry, and the manifest's SHA-256 must equal the pre-registered ⟨SCRIPT_SHA⟩. The diff script checks this before Stage 1, before Stage 3, before each verifier launch and before Stage 5b.
- **FRAMEWORK (v10, T5).** FRAMEWORK is not a template either: it is a toolkit file. `checks.py framework dossier/FRAMEWORK_stage.md` checks that the staged copy's SHA-256 equals the manifest's FRAMEWORK_v10.md entry, at Stage 1 and before every launch of a subagent that receives it. A mismatch stops the execution before that launch.
- The diff output is saved in `final/NEUTRALITY_AUDIT.md`.
- **MARKET_INPUTS.** The script computes the SHA-256 of the staged MARKET_INPUTS and compares it with (i) the season file in durable storage and (ii) every SHA-256 already recorded in `SEASON_FRAME_ROLLUP.md` for the same AS_OF and currency. Any mismatch stops the execution before Stage 1. The hash is written to `final/NEUTRALITY_AUDIT.md`. Under v9 the script also checks the file (N4): ⟨ERP⟩ = ⟨ERP_RAW⟩ + ⟨ERP_RF⟩ − ⟨RF⟩ to within 0.005 percentage points, with the printed equation repeating those figures; ⟨ERP⟩ within 2–8%; the source premium's risk-free series ⟨ERP_RF_SERIES⟩ equal to the file's ⟨SERIES⟩ (the builder states the series; the script checks that the two agree); and ⟨ERP_DATE⟩ at most 31 days before ⟨RF_DATE⟩. The script first runs before Stage 0 (`checks.py market`) and again at this step; a file that fails, or one on the v8 template, stops the execution.

**Step 2 — Neutrality audit (one independent subagent).**
- **What the auditor receives:** the instantiated PREREGISTRATION, STAGE2_INSTRUCTIONS, critic prompt, verifier prompt, the Appendix-H redaction-screener, tag-screener and writer instructions, one example launch prompt per stage, all after Step 1, and (v10) `FRAMEWORK_v10.md`, which is spec-owner text outside the template diff: its flags go to `final/SPEC_FLAGS.md` like any spec-template flag.
- Since every text is now a template, the auditor's real job is narrower: **check the slot values** (e.g. that UNIT is a unit and not a basis choice, that a file path doesn't carry a descriptive name), **check the mandate**, and **flag any generic bias in template text** for the spec owner. The pre-registration's run count, replicate structure, model ID, timestamp, toolkit manifest SHA-256 and (v10) baseline data manifest SHA-256 are per-execution slots by design: the auditor does not flag them under (a), still checks them under (b), and the Step-1 script types them (v9, N7).
- **Masking:** every ticker slot is masked. TICKER, UNIT and pack names appear as ⟨TICKER⟩, ⟨UNIT⟩ and ⟨PACK⟩, and the auditor is **not told the company**.
- **The mandate block, if any,** is shown unmasked, together with the user's original message, for a verbatim comparison.
- **The auditor receives no dossiers.**

**What it flags.** Any sentence that:
- (a) would change or become false for a different company; or
- (b) states or implies a level, direction, probability, floor, denominator, adjustment, weight, tier, or "what matters" for the company.

**How flags are handled:**
- **Slot values.** A flagged slot value is replaced with a neutral value (e.g. a descriptive path renamed to an opaque one; a UNIT restated as a pure unit). The auditor re-checks until nothing is flagged.
- **Spec-template text** (anything that survived Step 1, i.e. verbatim appendix text, including Appendix G and H):
  - The orchestrator does **not** delete it; deleting it per ticker could break the mechanics.
  - The flag is logged to `final/SPEC_FLAGS.md` for the spec owner, and the execution proceeds unchanged.
  - A template is identical for every ticker, so it cannot introduce ticker-specific framing. At worst it carries a generic bias, which the spec owner fixes once.
- **USER_MANDATE.** The only possible flag is a mismatch with the user's words. It is fixed by re-copying the text verbatim.

## Stage 1 — Inputs and screens

**Redaction is a fixed list (v7.1, F2).** The redaction screener redacts what is on the redact list and nothing on the keep list. It makes no arithmetic judgment.
- **Redact list** (TICKER only):
  - **R-1. Market values.** Any stated TICKER share price, price range, average purchase or sale price per share, market capitalisation, enterprise value, trading multiple, dividend or earnings yield, or analyst price target; and (v9) any stated price per share of the company's own equity awards or instruments: grant-date fair value per share, exercise or strike price, ESPP purchase price, conversion price.
  - **R-2. The dollar side of the company's own equity transactions.** The dollar amount of any transaction in TICKER's own shares, in any period. This covers:
    - share repurchases: cash spent, accrued or authorised, and any remaining authorisation in dollars;
    - treasury stock at cost;
    - proceeds from share issuance, ESPP purchases and option exercises;
    - the stock component of acquisition or merger consideration;
    - exchange offers and block sales.
  - **R-3. Ratios built from R-1 or R-2 figures**, such as a repurchase yield or a buyback amount per share.
- **Keep list** (never redacted):
  - every share count, of any kind and period (outstanding, weighted-average basic and diluted, repurchased, issued, granted, options and RSUs outstanding);
  - every accounting per-share figure (EPS, book value, dividends per share; not a price per share of an award or instrument, which is R-1);
  - cash paid for acquisitions;
  - every other income-statement, cash-flow and balance-sheet line.
- **Why a list.** A count alone does not invert to a price; dollars spent on the company's own shares do.
  - Routes that need an assumption are not redacted. For example, free cash flow ÷ the fall in the share count assumes all free cash went to buybacks at one price, and ignores dilution.
  - The redaction screener logs such routes as soft routes, and the Stage-2 no-market-data clause bars acting on them.
  - *On ADBE v7, the two-operation test led one screener to remove dossier A's share-count history as a "crude price proxy" and the other to keep dossier B's. All four dossier-A critiques then listed the missing dated share count as a pack gap, and the share-count split between the two dossiers' runs was worth about $7 per share.*
- Keep the qualitative fact, e.g. "repurchases continued; amounts redacted".
- When in doubt, keep the figure and log it as a soft route.
- Peer prices and multiples in the dossier are left alone. The lists cover TICKER only.

**Redaction check (toolkit, before anything is applied).**
- Every redaction entry must name its list item (R-1, R-2 or R-3). An entry that names none is not applied, and is logged.
- An entry whose span contains a figure the tag screener tagged SHARES is a keep-list violation. It is not applied, and is logged. A figure is located with number boundaries, so "100" does not match inside "1,100".
- The same keep-list check applies to methodology-note spans: a note that would remove a SHARES-tagged figure is not applied.
- For each dossier and each list item, the redaction screener states "redacted" or "not present".
- Stage 2 does not start, and the redaction screener is relaunched with the same template, if any of these holds:
  - an entry names no list item, names an unknown dossier, or quotes a span not found on its line;
  - an entry or a note fails the keep-list check;
  - a status is missing, or is neither "redacted" nor "not present";
  - an item is marked "redacted" with no accepted entry, or "not present" with entries.
- **Order.** The redaction screener and the tag screeners run in parallel, on the raw dossiers. Tag line numbers refer to the raw dossier. No redaction is applied before the check passes.
- The check writes `final/redaction_check.md`: for each dossier, the number of entries under R-1, R-2 and R-3 and each item's status, the soft routes, and every rejected entry with its reason. It never contains a redacted span; spans stay in the orchestrator-only REDACTION_LOG. Stage 6 reports it.

**Who applies it.** Two kinds of screening subagent, neither of them the orchestrator. Each is launched with its Appendix-H launch prompt and receives its Appendix-H instructions and the Stage-1 FRAMEWORK copy.
- **One redaction screener for all dossiers.**
  - It receives every dossier and writes one JSON object: the redactions (each with its list item, dossier, line, exact span and replacement), the per-dossier status of each list item, the soft routes and the methodology notes.
  - Reading every dossier at once is what keeps the treatment consistent across them.
- **One tag screener per dossier.** It writes the data-thinness list for its dossier as text, and every share-count figure in it, tagged SHARES, as one JSON object (Appendix H). Under v9 that list serves only the redaction check's keep-list test (N1), and the check fails closed: a list that is missing or malformed, a SHARES span that is empty or not found on its line, or any share-count line without a SHARES tag stops Stage 1, and the tag screener is relaunched. A share-count line names shares ("shares", "share count") and carries a count-like number, in either order ("5 million shares", "diluted shares: FY2021 49,802,993"): a number with thousands separators, a scale word or at least four digits (or any number, where the share label carries a count unit such as "(m)") that is not a currency amount (no currency symbol or ISO code before it, no ISO code after it, and, on a line whose label states a currency unit such as "(US$ mn)", not unless the number sits next to "shares"), a percentage or a year. Independent of the tags, the check also refuses any redaction or note span that holds a count-like number on a share-count line. A line the tag screener lists, with a reason, as naming shares without stating a share count is exempt from both, and the list is logged in the Stage-1 report.
- Both outputs are orchestrator-only. The toolkit writes `dossier/REDACTION_LOG.md` from them.
- For verifiers, the toolkit derives a per-run `redlog_<run>.md`. It lists each redaction's location and replacement text only. It never contains the redacted figure or the arithmetic path. *(On DECK v6, verifiers received the redacted repurchase dollar figure together with its two-operation path to a per-share price.)*
- The toolkit applies the redactions that pass the redaction check, exactly as listed.
- **Methodology notes.** The redaction screener also lists every sentence that recommends a valuation method or convention, and (v9, N7) every sentence about the request or instructions the dossier was written under, the pipeline, the valuation framework or method document, or files its author could not find (Appendix H, redaction screener, step 2). The toolkit replaces each listed span with "[methodology note removed]", exactly as logged, in the same pass as the redactions. Each removal appears in the verifier's redaction list like any redaction. *(On DECK v6, pack A's "Recommendations" §3 told the runs to "use weighted-average diluted shares … throughout". All six runs did so, and three verifiers cited that sentence to refute the finding: t3 F1, y1 #3, y2 F3.)*

**Data-thinness gate (unchanged from v4).** Each tag screener logs, in `dossier/DATA_THINNESS_LOG.md`, which denominator-critical metrics rest on a single period.
- The log is **not shown to Stage 2**.
- It is used only in Stage 6, to label decisive inputs "thin-data".

**FRAMEWORK copy (v10, T5).** The orchestrator copies `toolkit/v10/FRAMEWORK_v10.md` byte for byte to `dossier/FRAMEWORK_stage.md` and runs `checks.py framework` on the copy (Stage 0.5). FRAMEWORK_v10 already carries the ticker-neutral Rule-10 example of Appendix D, so nothing is replaced, and no edit of any kind is permitted. **Every subagent at every stage receives this copy:** runs, critics, verifiers, screeners and the auditor. The project document "Valuation Framework" is not used by a v10 execution.

**Dossier names.** Dossiers are handed to runs under opaque names (`pack_xx.md`).

## Stage 1c — Packs (script, one pack per run)

This stage runs after the redactions are applied. **v9 (N1): each run's pack is its redacted dossier**: the raw dossier after the Stage-1 redactions and methodology-note removals, with the company's name and every figure unchanged. There are no secret factors, no masking, no rescaling, and no completeness, masking or consistency check. The toolkit writes one copy per run under an opaque name (`pack_xx.md`) and records each run's token, dossier and pack in the manifest, with k = j = 1, so the frozen script's back-scaling is the identity (Stage 3). The orchestrator makes no content judgment.

**Hand-off.**
- Run i receives its own pack under an opaque name (`pack_xx.md`).
- Run i's critic and verifier receive the same pack, and the verifier receives `redlog_<run>.md`.
- The manifest and the share-count tag lists are orchestrator-only until Stage 6 is published. They are then listed in `final/MANIFEST.md`.

**Why masking and rescaling were removed.** They never achieved blindness: every identification probe of the season named the company. The scale-dependence test never flagged. The Stage-1c checks were the season's most frequent stop (see "What v9 changes", N1). The pack-only rule (Appendix B, Inputs), the no-market-data clause and the redaction lists are the guard. The v7–v8 design (factor draws, the transform, the three checks, the bridge runs and the probe) is recorded in spec v8, and the toolkit keeps it behind `"masking": true` so that earlier executions replay; no v9 execution uses it.

## Stage 1d — Identification probe (removed in v9)

There is no identification probe (N1). Runs may recognise the company, and work under the pack-only rule (Appendix B, Inputs). The heading is kept so that stage numbers stay stable across versions.

## Stage 2 — Valuation fan-out (one subagent per DOSSIERS entry, PARALLEL, web OFF)

**What each run receives:**
- FRAMEWORK (the Stage-1 copy);
- `STAGE2_INSTRUCTIONS.md`, which is Appendix B **verbatim**, with only TICKER, UNIT, the pack filename and (if any) the USER_MANDATE block filled in;
- its pack (Stage 1c: its redacted dossier, unmasked and unscaled), under an opaque name;
- MARKET_INPUTS (Rule O-2, "Season market inputs"), byte-identical to the season file.

**It receives nothing else:** no PREREGISTRATION, no run count, no dossier count, no redaction log, no thinness log.

**What each run does:**
- **Phase 0:** makes and declares every frame choice itself, **including every adjustment to the denominator** and its alternative denominator (N2).
- **Council:** runs the shortened council (Phase 0 → 1 → 1.5 → 4 → 6) with the seven seated investors (v10, T4), every seat at the macro base (T1), on cash flow to equity (T2).
- **Mechanics:** builds the committee in one script (S1), shows base-branch schedules and states every other value as its input changes (S2), and checks every branch and tree before writing (N3).
- **Output:** ends with the Appendix-B MACHINE SUMMARY, which includes the `frame` block and (v10, T3) the risk register.

**What comes back:** only the file path and the JSON. The orchestrator records token → pack → dossier and the model ID in `runs/MANIFEST.md`, which is orchestrator-only until Stage 6 is published.

## Stage 3 — Deterministic statistics (orchestrator, by script)

**Back-scaling (replays of masked executions only).** A v9 execution has k = j = 1 for every run, so its run output is already in real units. The script keeps the v7–v8 back-scaling so that masked executions replay: there, every per-share quantity from run i is multiplied by kᵢ (seat fair values, tree branch values, floors, BUYs, denominators, the headline, and every figure recomputed from verifier patches in Stage 5b), share counts are divided by kᵢ·jᵢ for display, and every statistic is in back-scaled units.

**Parsing and recomputation.**
- The frozen arithmetic script (Stage 5b) parses every MACHINE SUMMARY. Every number in Stages 3, 5 and 5b comes from that one script. Its seat function is the per-seat recompute below, and nothing is computed by hand.
- It recomputes each run's `headline_buy` as the weighted mean of that run's seated investors, using **that run's own Phase-0 weights**.
- It also computes a uniform-weight headline per run, as a sensitivity.
- **Seat recompute from trees.** For every seat, the script reads the `tree` and, on the tree as reported (before Helena's floor), checks five things:
  - branch names are unique, with exactly one `base` and one `break`;
  - the probabilities sum to 1 (±0.005);
  - the base branch value equals `fair_value` within 0.1% (or 0.01 ⟨UNIT⟩, whichever is larger);
  - the base branch is the tree's median, i.e. P(V ≥ base) ≥ 0.5 and P(V ≤ base) ≥ 0.5;
  - the break branch is the lowest-valued branch.

  The script computes the quality premium π(`quality_score`) (G1), derives the tier from the score with FRAMEWORK's tier table as a label, and logs any mismatch with `quality_tier` as a C7 violation. A seat with no numeric score takes π at its reported tier's midpoint score (67.5 for Average, and so on), logged as a C7 violation. It then sets every branch value to max(value, Helena's `floor_per_share_or_null`, if not null) and recomputes, using the Appendix-B arithmetic:
  - `break_p`;
  - `break_loss` = 1 − break value ÷ `fair_value_macro_base`, floored at 0 on every path (F5). If that field is missing, the script estimates it from `fair_value` and `fair_value_rf_plus_50bp`, log-linearly in the rate, and logs a C7 violation (also when the seat's rate equals the macro base). For a seat with no valid tree in a v7 summary (replay only), the reported own-FV `break_loss` is restated on the macro-base fair value as 1 − (1 − L) × `fair_value` ÷ `fair_value_macro_base`;
  - `tail_term` = `break_p` × `break_loss`;
  - `required_margin`, `at_cap`, `no_buy` and `buy`.

  A reported `no_buy` is honoured when it names a FRAMEWORK rule in `no_buy_reason_or_null`, or when a verifier's patch sets it; under v10, where the only rule is two or more FAILs among Walter's gates, a reported `no_buy` is honoured only for Walter with two or more FAIL gates (or by a verifier's patch), and any other is logged (C7) and the seat kept. A reported `no_buy` with no reason on a seat above 0.60 is treated as AT CAP and logged as a C7 violation; with no reason on a seat at or below 0.60 it is honoured and the missing reason is logged.

  The script's values are canonical. Any mismatch with the run's reported fields is corrected and logged.
- **Denominator count (F1).** Before any seat is recomputed, the script compares `denominator_count_m` with `per_share_count_m`.
  - If they differ by more than 0.1%, it rescales every per-share value of every seat on its operating part: v′ = (v − `balance_sheet_add_per_share`) × `denominator_count_m` ÷ `per_share_count_m` + `balance_sheet_add_per_share`.
  - This covers fair values, tree values, `fair_value_rf_plus_50bp`, `fair_value_macro_base`, `fair_value_other_acquisition_basis`, `fair_value_alternative_denominator` (v9), IRR entry prices (replay of v7 summaries only), and, as a flow with no balance-sheet add, each `forecast_5y` cash flow per share (v8). The frame's per-share flow fields (gross, declared and alternative denominators, adjustments and normalised acquisition spend) are multiplied by `denominator_count_m` ÷ `per_share_count_m`. Helena's floor is not rescaled. A missing `denominator_count_m` is logged as a C8 violation.
  - The script logs the correction as a C1 violation. The rescaled figures are canonical.
- **Acquisition matching (F4).** The script tabulates each seat's `growth_basis` and `acq_spend_deducted`, and counts mismatched seats per run (organic with spend deducted; including acquisitions without spend deducted). A mismatch is reported, never corrected by the script; the critic and verifier treat it as a STAGE2_INSTRUCTIONS violation.
  - **Zero spend (v9, N5).** When a run's `acq_cash_by_year` is empty or sums to 0 (the pack shows no acquisition cash) and its `acq_spend_normalised_per_share` is 0, the deduction is 0 on either basis, so every pair counts as matched and none is counted as a mismatch. This is logged. A run that excludes a deal from non-zero acquisition cash is still checked, and the critic checks any shares issued as acquisition consideration (Appendix B).
- **A seat with no tree, or a tree that fails a check,** is recomputed from its reported `break_p` and `break_loss`. It is never imputed from another seat, and it is logged as a C7 violation.
- **Seats outside the roster (G2, T4).** A seat named Victor or Max in a v8 or later MACHINE SUMMARY, a seat named Simon in a v10 MACHINE SUMMARY, or one flagged `irr_entry` (a field of v7 summaries) is logged as a C5 violation and kept out of every statistic. Patches to it are dropped with a note. (Replayed v7 summaries keep their v7 IRR segregation, which has the same effect.)
- **Quality score checks (G1).** A score outside 0–100 is logged as a C7 violation. The reported `quality_premium` is compared with π(score) (tolerance 0.00005) and corrected and logged if it differs.
- **Modal tier (v9, N6).** `quality_tier_modal` must be one of the four tier names. Anything else is logged as a C8 violation. It moves no number.
- **v10 checks (T1–T4; logged, never corrected; they move no number).** The verifier, not the script, patches what they find (Appendix F).
  - **Rate (T1, C2).** The macro base is MARKET_INPUTS' risk-free rate plus its rebased ERP, as recorded in the configuration (the run's own `macro_base` only where the configuration has none). A seat whose `discount_rate` is missing or differs from it by more than 0.005 percentage points, or whose `fair_value_macro_base` differs from its `fair_value` by more than 0.1% (or 0.01 ⟨UNIT⟩, whichever is larger), is logged and counted as off the macro base; a run whose own `macro_base`, `risk_free` or `erp` differs from MARKET_INPUTS is logged, and every seat discounting at that wrong base is counted off it.
  - **Debt (T2, C1).** A run that reports a non-zero `debt_deducted_per_share` (a debt, preferred, minority or lease claim deducted from cash flow to equity) is logged as a C1 violation, the debt double count; one that reports no `debt_deducted_per_share` or no `net_claims_per_share` is logged (C8). A negative `balance_sheet_add_per_share` is noted for the critic (it may be a legitimate non-claim liability). The script cannot see whether the flows are after interest; the critic checks that against the pack.
  - **Risk register (T3, C6).** Every `risks` entry must name a seated investor and a channel from the closed list (`base_cash_flows`, `break_branch`, `quality_score`, `fv_mapping`, `non_break_branch`, `not_priced`), carry a numeric `size` in its channel's unit (or, for `not_priced`, a reason), and use `fv_mapping` only for Walter or Alexander. The same risk (compared case-insensitively, after whitespace is collapsed) entered for one seat in more than one channel is logged as a double count. A seat with no entry is logged. A missing register is one C6 violation per run.
  - **Seat-mapping table (T4).** `statistics.md` tabulates, per run, Walter's six components, four gates, score and multiplier and Alexander's score and adjustment.
  - **Walter's grade (T4, C5).** Walter's `management_grade` must hold six components, each an integer from −2 to +2; its `score` must be their sum and its `multiplier` 1 + 0.015 × score (to within 0.0005); a gate at CAUTION or FAIL must cap its component (trust → trust and guidance; incentive alignment → incentive alignment; board governance → board governance; capital-structure distress → capital allocation) at −1 or −2. A Walter seat with two or more FAILs that is not NO BUY is logged. Alexander's `earnings_quality` must hold a score from 0 to 100 and the FRAMEWORK mapping (+10% above 80, 0% from 60 to 80, −15% below 60), logged if not.
- Any mismatch is corrected and logged.

**Same computations as v5:**
- range, median, mean, SD and CoV;
- tier distribution (labels).

**Run noise (the statistic every interval and ledger row is measured against).** All figures are run headlines (back-scaled, in a replay of a masked execution).
- `s_w` = pooled within-dossier SD of the run headlines = sqrt( Σ_d Σ_i (H_di − H̄_d)² ÷ (N − D) ), with df = N − D. N is the number of runs and D the number of dossiers.
- Report `s_w`, its df, and a 90% chi-square interval for σ_w: `s_w·sqrt(df ÷ χ²₀.₉₅,df)` to `s_w·sqrt(df ÷ χ²₀.₀₅,df)`, where χ²₀.₉₅,df and χ²₀.₀₅,df are the 95th and 5th percentiles of the χ² distribution with df degrees of freedom.
- Compute the same statistic on ln(weighted FV of headline seats) and on ln(headline ÷ weighted FV). Report the share of within-dossier log variance due to fair value, to margin, and to their covariance.
- **Drift floor** (display only): the mean absolute pairwise gap between same-dossier replicates, pooled across dossiers, with the full within-dossier distribution. It sets no band. Stage 7 still uses it.

**Dossier contrast** (replaces the axis ratio). For two dossiers:
- `t = (H̄_A − H̄_B) ÷ ( s_w · sqrt(1/n_A + 1/n_B) )`, with df = N − D. Report t, its two-sided p, and the two camp means.
- With two dossiers, the between-dossier variance has 1 df and is not estimated. State this.

**Frame decomposition.** Covers every field in the `frame` block and the `helena_floor` block.
- **Categorical fields** (e.g. denominator type, gross source, basis period, guidance stance, Helena's floor type; v10: debt path and systematic risk class): tabulate the values across runs, and the mean headline under each value.
- **Continuous fields** (e.g. risk-free, ERP, declared denominator per share, **Σ adjustments per share**, normalised acquisition spend per share, median base FV, Helena's floor per share, weighted mean tail term; v10: the net claims and the debt deducted per share): report their values and their rank correlation with the headline.
- **Acquisition declarations (F4):** per run, the count of seats in each `growth_basis` × `acq_spend_deducted` cell, the mismatches, and the `recent_acquisitions` each run declared.
- **Adjustment ledger:**
  - tabulate every `denominator_adjustments` item across runs: the item, how many runs took it, and the mean and range of its $/share;
  - report the gross (pre-adjustment) denominator separately from the declared one;
  - an adjustment every run took is convergence; an adjustment only some runs took is a frame axis.
- **Break-probability elasticity table.** For each run, report the headline recomputed with every headline seat's `break_p` moved −5pp and +5pp, using the Appendix-B arithmetic:
  - the moved probability is taken from, or added to, the base branch;
  - `break_loss` is held;
  - on the −5pp side, `break_p` is floored at 0.10, the Rule-4 minimum.
  - report how many headline seats were already at 0.10 and so did not move on the −5pp side.

  Report each swing in the reporting unit and as a multiple of the run-noise statistic `s_w`, and supply this row to the Stage-5 sensitivity ledger. State with the table: *"The tail term is the break branch's expected loss. It is risk-neutral: a 10% chance of a total loss costs 10pp of margin, no more. Any further aversion to ruin enters only through the quality premium."*
- **Break-probability histogram.** Pool the headline seats' `break_p`. Report the share at exactly 0.10 and the share within 1pp of any multiple of 0.05.
- **Tree tail cost (descriptive only).** For each seat, report `1 − EV/FV` over its whole tree, together with its non-break downside and upside components. These figures never enter a margin. They show how much of the quality premium the tree's own downside accounts for.
- **v6-rule bridge (first v7 ticker only).** By script, from the same trees, recompute each run's headline under the v6 Appendix-B arithmetic:
  - M = the median `fair_value` of all ten seats (replay of v7 summaries only), recomputed by the script (the run's `committee_median_fv` is only checked against it);
  - ED = Σ p·max(0, M − V) and EU = Σ p·max(0, V − M) over the seat's own tree (after Helena's floor); R = ED/EU (3.0 if EU = 0); asym = clamp(0.10 × (R − 1), −0.10, +0.15);
  - the gate fires if `break_p` ≥ 0.15 and `break_loss` ≥ 0.40 (loss after Helena's floor); the valve is not evaluated;
  - neither fires: required = clamp(base(tier) + asym, 0.10, 0.60); gate fires: required = clamp(max(0.40, base(one tier below) + asym), 0.10, 0.60), where one tier below Below Average is Below Average;
  - if base(…) + asym exceeds 0.60 before clamping, the seat is NO BUY; the headline is the run's own-weight mean over non-IRR, non-NO-BUY seats.

  Label the result "v6-rule bridge (own trees, no inheritance)". It is reported, never published as the BUY. The self-test (Stage 5b) adds one bridge case: a High Quality seat with p = 0.15, L = 0.60 and asym = +0.15 gives required = 0.475.
- **Log-decompose each same-dossier pair's gap** into FV and margin shares. Then decompose the FV share further into denominator and multiple.
- **Convention sensitivity (script; back-scaled units in a replay of a masked execution).** For each run, recompute every headline seat, holding its reported required margin fixed:
  1. **Valuation date.** Roll operating value (`fair_value` − `balance_sheet_add_per_share`) from `valuation_date` to `pack_as_of_date` at the seat's own discount rate, with Δt in years (Δt = 0 if the dates are equal). Leave the balance-sheet amount un-rolled.
  2. **Share-count date.** Multiply every per-share value by `per_share_count_m ÷ latest_share_count_m`.
  3. **Both.**
  4. **Denominator count (F1).** Divide the cash flow by `period_weighted_count_m` instead of the per-share count: operating value × `per_share_count_m` ÷ `period_weighted_count_m`. A run whose pack gives no period-weighted count keeps its figure, and this is logged. The runs whose `per_share_count_basis` is "period" are listed beside this row.

  Report each run's headline under 1–4, and the committee figure under each. These rows are descriptive and go into the Stage-5 sensitivity ledger.
- **Acquisition rows (F4, script).** Recompute each headline seat twice, holding its required margin fixed:
  - with every seat on the organic basis: a seat already organic keeps its fair value, and a seat including acquisitions takes `fair_value_other_acquisition_basis`;
  - with every seat on the including-acquisitions basis, the other way round.

  Report both headlines per run and for the committee, as ledger rows. A seat with no `fair_value_other_acquisition_basis` keeps its fair value, and this is logged. For a mismatched seat, `fair_value_other_acquisition_basis` is its value under the matched treatment of its own growth basis, and both rows use it; this is logged. Under v9, a run with zero acquisition spend in that sense keeps every seat's fair value in both rows, which then equal its headline (N5; logged).
- **Alternative-denominator row (v9, N2, script).** Recompute each headline seat on its `fair_value_alternative_denominator`, holding its required margin fixed (the seat's tree and tail term are taken to move in proportion to its fair value), and report the headline per run and for the committee, as a ledger row. A seat with no `fair_value_alternative_denominator` keeps its fair value, logged as a C8 violation; a seat whose alternative fair value is zero or negative is NO BUY in this row, its weight dropped, logged.
  - The alternative is the run's own (Appendix B, Phase 0: the same definition as the declared denominator, differing only in its period or in the margin applied to the basis-period revenue), so the row shows how far the BUY rests on the starting point the runs chose. It does not reduce run noise.
  - Runs choose in either direction, so opposite choices net out in the committee row. Over the runs retained for the BUY, the script also reports how many chose an alternative above the declared denominator, below it, or none, the headline seats valued, and the mean absolute per-run change. With no seat valued the row reads n/a on the card and is never the largest sensitivity.
  - The script logs, and never corrects (moving no number): an `alternative_denominator_basis` outside period, margin or none (C8); "none" without `alternative_denominator_per_share` = `declared_denominator_per_share` and every seat's alternative fair value equal to its fair value (C1); an alternative ÷ declared ratio outside 0.5–2.0 or of opposite sign (listed in Stage 6); and a seat whose (alternative fair value − `balance_sheet_add_per_share`) ÷ (fair value − `balance_sheet_add_per_share`) differs by more than 1% from that ratio, other than a seat that reports its fair value unchanged or deducts a non-zero acquisition spend (whose deduction is not scaled, so the check does not apply) (C4).
  - Each run's basis, ratio, direction and row are tabulated in `statistics.md`.
- **Debt row (v10, T2, script).** Recompute each headline seat with its run's `net_claims_per_share` subtracted from its fair value and from every branch value (the v9 count, deducting net debt from cash flow that is already to equity), its required margin held fixed. Report the headline per run and for the committee, as a ledger row labelled "Debt: net claims deducted again (the v9 count)". Its distance from the headline is the size of the T2 correction.
  - A run that reports no `net_claims_per_share`, or reports 0, keeps its headline in this row (logged). A seat whose value falls to zero or below is NO BUY in this row, its weight dropped, logged. A net-cash run (negative net claims) moves up: v9 would have added its cash to flows that already carry its interest income.
  - The row is exact for the claims as reported; it does not re-derive the flows. With no run measured it reads n/a on the card. It is never ⟨CARD_BIGROW⟩: it restates the error v10 removes, not a judgment v10 runs make.
- **Rate lever (script).** Recompute each headline seat's BUY from `fair_value_rf_plus_50bp` with the pre-registered margin arithmetic. Each seat's required margin is held fixed, so the row is a pure rate effect. Report `headline_buy_rf_plus_50bp` per run and for the committee, as a ledger row. Under v9's ERP convention (N4) a change in the risk-free rate alone would leave the macro base unchanged; this row is a +50bp change in every seat's discount rate, whatever its cause. Under v10 every seat's rate is the macro base (T1), so it is a +50bp change in the macro base. The run's own figure, if it gives one, is checked against the script's; a difference above 0.05 ⟨UNIT⟩ is logged.
- **Margin-rule alternatives (script, v8 G3).** For each run, recompute the headline under three other rules, on the same headline seats, weights and floored trees:
  - **step tiers:** the v7.1 rule, `clamp(base(tier) + p·L, 0.10, 0.60)` with base(tier) 12.5% / 22.5% / 32.5% / 40%, and the v7.1 AT-CAP and NO-BUY decision made with base(tier);
  - **EV rule ("tuned Victor"):** BUY = 0.670 × the probability-weighted mean of the seat's floored tree;
  - **expectile rule ("tuned Max"):** BUY = the price P at which Σ p·max(V − P, 0) = 7.75 × Σ p·max(P − V, 0) over the seat's floored tree (the 1/8.75 expectile).

  A fourth rule, **EV × (1 − π(score))**, is computed the same way for the outcome ledger only (G4); it is never shown on the card.
  - A seat with no valid tree is left out of the tree-based rules and its weight dropped; this is logged, and the count is shown on the card.
  - A run with no seat eligible for a rule is left out of that rule's trimmed point (logged). If fewer than 3 runs remain, the rule is reported n/a.
  - For the published BUY and for each rule, the script reports the implied **expected upside ÷ expected downside** at that BUY: on the mixture of the run's eligible headline seats' floored trees, each weighted by its Phase-0 weight, evaluated at the run's headline under that rule; the median over the runs the point rule retains.
  - The constants are pre-registered (Appendix G). They were set once, in the v8 debate and in sample, at the v7.1 step rule's average strictness on AGX and ADBE, and are never re-tuned per ticker; changing them needs a new spec version.
  - Report each rule's headline per run and its trimmed point, beside the quality-premium headline, the seat-weighted premium and step base, and the number of headline seats within 3 points of a tier cut-off (60, 75, 90).
  - These are policy alternatives: they are not sensitivity-ledger rows, they enter no interval, and they are never averaged with the headline or with each other.
- **Channel monitor (v10, T6; descriptive).** Over the runs the point rule retains, and per run, the script reports: the seats off the macro base (T1 check); the seat-weighted means of terminal growth, five-year forecast growth (the compound annual growth of `cash_flow_total` from the first to the fifth `forecast_5y` period, where both are positive), quality score, `break_p` and tail term; Walter's mean `management_grade` multiplier and score; the counts of runs with debt deducted and of `systematic_risk_class` values; the risk register's entries by channel (count, summed size in the channel's unit, and the summed BUY effect in ⟨UNIT⟩ the script derives: base cash flows size × (1 − required); break branch −size ÷ 100 × fair value; quality score fair value × (π(score − size) − π(score)); fair-value mapping size ÷ 100 × fair value × (1 − required); non-break branch 0, its expected-value effect shown separately); and the debt row's change in BUY. It moves no number. The validation comparison (Appendix G) reads it; on other executions it is the season's record of where value is priced.
- **Base-branch forecasts and break horizons (v8 G4).** Each seat's `forecast_5y` (period end, months, cash flow as a company total and per share) is tabulated per seat (in a replay of a masked execution, back-scaled: totals ÷ j, per-share figures × k) with its `forecast_definition` and its break `horizon_years`, for the outcome ledger. A seat with fewer than five complete periods, or no horizon, is logged. None of these enters a statistic.
- **Induced-field check (script).** For every frame field on which all runs agree, the script looks the field up in the table below and in the Stage-1 methodology-note log. It labels the field **INDUCED** if a text every run received fixes or defaults its value, and **UNANIMOUS** otherwise. Only UNANIMOUS fields may be reported as independent convergence.

  | Field | Inducing text, if the value matches it |
  |---|---|
  | `risk_free`, `erp` | MARKET_INPUTS |
  | every seat's `discount_rate` = `macro_base`, and `fair_value_macro_base` = `fair_value` | Appendix B rate rule (v10, T1) |
  | `debt_deducted_per_share` = 0; `lease_treatment` | Appendix B debt rule (v10, T2) |
  | `valuation_date` = `pack_as_of_date` | Appendix B default |
  | `denominator_count_m` = `per_share_count_m` | Appendix B share-count rule (F1) |
  | `per_share_count_m`, `per_share_count_date` (the latest dated diluted count) | Appendix B share-count rule (F1) |
  | every seat's `growth_basis` and `acq_spend_deducted` matched | Appendix B acquisition rule (F4) |
  | `acq_spend_window` of up to five years | Appendix B acquisition rule (F4) |
  | `alternative_denominator_type` equal to each run's `denominator_type` | Appendix B alternative-denominator rule (v9, N2) |
  | an SBC adjustment in `denominator_adjustments` | FRAMEWORK Phase 0.A (SBC is a cost) |
  | `guidance_stance` = skeptical | FRAMEWORK Overview default |
  | any field whose value a removed methodology note recommended | the pack (Stage-1 log) |

**Scale-dependence test (closed in v9).** v7–v8 executions regressed ln(back-scaled blind headline) on the secret factors ln k and ln j, to detect a pull toward a remembered per-share level or total value. v9 packs are not rescaled (N1), so the test has nothing to regress on and is not run. Its last pooled result over the season's 40 masked rows (v7, v7.1 and v8) stands as the season's record: β̂ₖ +0.0038, β̂ⱼ +0.0417, joint permutation p 0.64; it never flagged on any ticker. The test, its stated size and power, and its limits are recorded in spec v8, and the toolkit runs it in `--spec v8` mode, so masked executions replay.

With eight runs (the default), the frame decomposition, adjustment ledger, elasticity table, histogram, tree tail cost, log-decomposition and convention rows are **descriptive, not inferential**, and must be labelled that way. The only inferential statistic is the dossier contrast (the scale-dependence test is closed in v9), a pre-registered test reported with its df and p-value and applied as Appendix G states. The purpose of the descriptive tables is to make visible which run-level choices moved the number, where the v5 frame hid them.

**Season roll-up.** After Stage 6 is published (so that rows record published, final results; they also carry the critics' checklist results), append this ticker's frame blocks to the season-level file `SEASON_FRAME_ROLLUP.md` (durable storage, outside the ticker folder), one row per run. Each row carries:
- the ticker, token, dossier and model;
- the business type the run declared;
- every frame field;
- AS_OF, the MARKET_INPUTS currency and its SHA-256;
- the critic's checklist result for the run (C1–C8, met / not met);
- the headline;
- **`log_rel_headline` = ln(headline ÷ median headline of this ticker's runs)**;
- **`mechanism_version`**: "v5-margin" for rows from v5 or v6 executions, "v7-tail" for v7 rows, "v7.1-tail" for v7.1 rows, "v8-grad" for v8 rows, "v9" for v9 rows, "v10" for v10 rows. Existing rows are back-filled "v5-margin";
- (v10, T6) `debt_path` and `systematic_risk_class` for the run, and a VALIDATION column ("VALIDATION" for a validation execution's rows, empty otherwise), as three columns after the probe cell; earlier rows read "n/a" there by definition. Because the header gains columns, v10 rows are appended under their own header, in a new table headed "v10 rows" in the same file (`rollup.py` writes it); the first 35 columns are unchanged, so pooled analysis reads both tables as one. The ticker cell is the ticker alone, so the ticker fixed effect is not split;
- under v7.1 and v8: whether the run's denominator count was normalised (and the ratio), its acquisition mismatches, and its AT-CAP seats; under v8 and v9 the weights cover the eight seated investors, under v10 the seven;
- `ln_k`, `ln_j` and the Stage-1d probe result (IDENTIFIED / NOT IDENTIFIED) for the run's dossier: v7–v8 rows only. v9 rows read "n/a" in these three cells (N1), and keep the header so the season table stays one table. N2's per-run figures are not in the roll-up; they are in `statistics.md` and the published per-run data (G5).
  - Headlines in v7–v8 rows are back-scaled.
  - k and j are written to the roll-up only after this ticker's Stage 6 is published.
  - First-ticker bridge runs get rows marked BRIDGE (k = j = 1). They are excluded from the `log_rel_headline` median and from every pooled test.

**Rules for pooled analysis:**
- Pooled analysis uses `log_rel_headline` only, never dollar headlines. Dollars are not comparable across tickers.
- Treat ticker as a fixed effect.
- Label pooled frame effects as **associations**. Frame choices are confounded with business type (for example, tail terms may run larger on asset-light names).
- Never pool margin-related frame effects across `mechanism_version` values. Analyse each version separately, or include version as a fixed effect. v8-grad, v9 and v10 rows share their margin arithmetic; pooling them with version as a fixed effect is intended. VALIDATION rows follow "Season comparability (v10)".
- The roll-up is the only place frame effects accumulate enough observations to be tested at all.
- The roll-up is never shown to any subagent of any later ticker.
- **Pooled scale-dependence test (closed in v9).** v7–v8 executions re-fitted the scale-dependence regression over every masked row of the season after each ticker. It closes at its 40-row result (β̂ₖ +0.0038, β̂ⱼ +0.0417, permutation p 0.64; no season flag). v9 rows have no k or j and enter no pooled memory test; nor do rows marked D-3 (unmasked), like BRIDGE rows. A masked execution of an earlier version, replayed or completed later, still runs it in its own mode.

Write `final/statistics.md`.

## Stage 4 — Critique fan-out (one subagent per run, PARALLEL, web OFF)

**Timing (v8, S3; Rule O-1).** A critic is launched only after its run's MACHINE SUMMARY parses (`extract.py summary`). Where subagents have isolated file systems, it is launched as soon as its run has returned. On a shared file system (P-2), critics are launched after every run has returned and every run's directory has been deleted. Critics never wait for Stage 3.

**What each critic receives:**
- FRAMEWORK (the Stage-1 copy);
- the one run file;
- that run's pack;
- that run's instantiated `STAGE2_INSTRUCTIONS.md`, the rules the run followed, including the margin arithmetic;
- the critic checklist: Appendix C, verbatim, as `CHECKLIST.md`;
- MARKET_INPUTS, the macro file the run was told to use;
- the critic prompt: Appendix E, verbatim, instantiated.

**It receives no PREREGISTRATION.**

**Tagging.** Every finding carries two tags:
- **SPECIFIC** or **TRANSFERABLE**;
- one of **ARITHMETIC / PACK-CONTRADICTION / FRAME-INCONSISTENCY / RULE-VIOLATION / FRAME-JUDGMENT / PACK-GAP / MECHANISM**.

**PACK-GAP** marks a finding that rests on a fact the pack did not contain. The critic names the missing item by its kind and period; it does not look it up, and it states no remembered value for it. Example: the pack states no figure for a cost the run had to assume.
- PACK-GAP findings never move a number.
- Stage 6 reports their recurrence.
- The season roll-up feeds them to whoever builds dossiers.

**MECHANISM** marks a finding about the pre-registered arithmetic itself, not about the run's use of it. Examples: the form of the tail term, the quality-premium map, the clamp bounds, the margin-rule alternatives, the roster, the headline formula, and (v10) the macro-base rate rule, Walter's multiplier constant or the 1% threshold of the risk register.
- MECHANISM findings never move a number.
- The orchestrator copies every MECHANISM finding, with the verifier's ruling, to `final/SPEC_FLAGS.md`.

Write `critiques/critique_<token>.md`.

## Stage 4b — Finding verification (one subagent per critique, PARALLEL, web OFF)

**Timing (v8, S3).** Each verifier is launched as soon as its critique has returned and been copied out.

**What each verifier receives:**
- one critique;
- its target run;
- that run's pack;
- that run's `redlog_<run>.md` (Stage 1: locations and replacement texts only);
- FRAMEWORK (the Stage-1 copy);
- that run's instantiated `STAGE2_INSTRUCTIONS.md`;
- MARKET_INPUTS;
- a read-only copy of the frozen arithmetic script, `frozen_arith.py` (hash-checked at launch);
- the verifier prompt and verification standard: Appendix F, verbatim.

**It receives no PREREGISTRATION beyond that standard.**

**Verification standard (frozen, ticker-generic).** A finding is **CONFIRMED** only if one of the following holds:
- **(a)** The verifier reproduces the critic's arithmetic, not the run's.
- **(b)** The run contradicts a figure in its own pack.
- **(c)** The run contradicts **its own declared frame**. For example, it:
  - declares one denominator but uses another for a seat;
  - declares a basis period but mixes periods;
  - lists an adjustment in `denominator_adjustments` but does not apply it, or applies one it did not list.
- **(d)** The run violates an explicit rule. Only these texts count as rules for route (d):
  - FRAMEWORK Rules 1–10;
  - the Phase-0.A requirements (such as SBC being a cost);
  - the Phase-0.B list of what the moderator does NOT establish;
  - the Overview's "No market data" paragraph, and its rule that investors use only the provided research;
  - the explicit scoring, gate or mapping rules in a seat's description under THE COMMITTEE;
  - every requirement of the run's STAGE2_INSTRUCTIONS: the Phase-0 declarations, the margin arithmetic, Mechanics and Output.

  FRAMEWORK's principles, examples and descriptive prose (Overview beyond the two items above, Core Principles prose, the Cross-Investor Consistency Checks, "What good looks like") are not rules for route (d). A finding that rests only on them is FRAME-JUDGMENT.
- **(d′)** The run ignores or contradicts the USER_MANDATE, if one exists.

**Everything else is REFUTED as a mover.** That includes:
- every FRAME-JUDGMENT finding;
- every PACK-GAP finding;
- any different level of a defensible input;
- anything asserted but not demonstrated.

A FRAME-JUDGMENT finding may still be recorded as CONFIRMED-unquantified, but only if the critic shows that the run failed to *declare* or *justify* a choice. The verifier never judges *which* choice was right.

**Precedence.** The margin arithmetic in STAGE2_INSTRUCTIONS is pre-registered. Where it differs from FRAMEWORK's margin table or text, the STAGE2_INSTRUCTIONS arithmetic governs. A required margin produced by that arithmetic is never a violation, even when it lies outside a FRAMEWORK band. The same holds for its roster (seven seated investors under v10, no entry prices) over any other roster in FRAMEWORK, for its rate rule (v10, T1: every seat at the macro base), and for its schedule rule (v8, S2) over Rule 5. Under v10 FRAMEWORK_v10 is edited to agree with STAGE2_INSTRUCTIONS (T5), so this precedence should not be needed; it stays as the tie-break: a branch value, extra fair value or other reported DCF value stated as complete input changes from a shown base-branch schedule, under the run's stated mechanics, meets Rule 5. A value that cannot be reproduced from its line is CONFIRMED-unquantified under (d); it is patched only if the critic shows that the run's own stated inputs and mechanics give a different value.

**Quantified means patched.** A CONFIRMED finding is QUANTIFIED only if its fix is written as field-level patches (`changed_inputs`) from the closed list in Appendix F, and the frozen arithmetic script accepts them. The number that moves is always the script's. A verifier's own dollar figure is recorded for comparison and is never folded.

**Remembered facts (v9).** A finding that the run used a figure or fact from outside its pack and MARKET_INPUTS is QUANTIFIED only if the pack contains the figure it displaced (for example the latest reported value the run replaced with a later one) and the patch restores that pack figure, everything else unchanged. Otherwise it is CONFIRMED-unquantified. A verifier never replaces it with a value it chooses or remembers.

**MECHANISM.** A fix that cannot be written as patches from that list is never QUANTIFIED. So is a set of patches whose only purpose is to reproduce a different formula. It is ruled CONFIRMED-unquantified, marked MECHANISM, and copied to `final/SPEC_FLAGS.md`.

**Off-base rates (v10, T1).** A seat whose discount rate is not the macro base breaks a STAGE2_INSTRUCTIONS requirement (route (d)). The finding is QUANTIFIED by the patch set `frozen_arith.py rebase ⟨RUN⟩ <Investor>` prints: `fair_value` set to `fair_value_macro_base`, every non-break branch value multiplied by `fair_value_macro_base` ÷ `fair_value`, the break value held (a break set by a floor or a distress multiple does not move with the rate), and `fair_value_macro_base` unchanged; the script scales the companion fields, `fair_value_rf_plus_50bp` included, by the same ratio. The scaling is an approximation (the non-break branches and the +50bp value need not move in proportion), and the fold log labels it. Where the run reports no `fair_value_macro_base`, or reports it equal to the off-base `fair_value`, the finding is CONFIRMED-unquantified.

**Debt double count (v10, T2).** A run that deducts a debt, preferred, minority or lease claim from cash flow to equity breaks a STAGE2_INSTRUCTIONS requirement. When the run reports the claims deducted (`debt_deducted_per_share`), the finding is QUANTIFIED by the patch set `frozen_arith.py undebt ⟨RUN⟩` prints: the deduction added back to every seat's fair value, `fair_value_macro_base`, every tree value and the companion fair values, and to `balance_sheet_add_per_share`. A finding that the flows themselves are not to equity (for example before interest) is CONFIRMED-unquantified unless the critic derives fair-value and tree patches from the run's own stated inputs.

Write `critiques/verification_<token>.md`.

## Stage 5 — Published estimate, interval and sensitivity ledger (orchestrator, by the frozen script)

There are no scorers and no coefficient. The C1–C8 criteria survive only as the unscored critic checklist (Appendix C). The checklist weights nothing, and its results go to the season roll-up. Every figure below is computed by the frozen arithmetic script, from the run headlines (back-scaled, in a replay of a masked execution), and never by hand.

**Point-estimate rule.**
- If N ≥ 6: the **trimmed mean**. Drop the single highest and the single lowest run headline, and average the rest with equal weight.
- If N < 6: the equal-weighted mean.
- Applied to blind headlines, this gives the **BLIND INTERMEDIATE**. Applied to the Stage-5b adjusted headlines, it gives the **published BUY**.
- Committee fair value is the equal-weighted mean of the weighted FV of headline seats over the same runs the point rule retains for the BUY: blind FVs for the blind intermediate, and FVs after the Stage-5b patches for the published figure.
- Also reported, descriptive only: the equal-weighted mean; the median; and each run's leave-one-out point estimate, which names the run with the most influence.

**Interval.**
- Half-width = `t₀.₉₀,df · s ÷ √N`, where s is the Stage-3 pooled within-dossier SD formula applied to the same headlines as the point: blind for the blind intermediate, adjusted for the published BUY. df = N − D.
- It is published with this label, verbatim, in `TICKER_valuation.md` and on the Decision Card (the headline sentence uses the short form fixed in Appendix I): *"80% confidence interval for this pipeline's expected BUY on these packs, with this model and this orchestration. A fresh execution's figure is expected within a range √2 wider. Neither range covers the items in the sensitivity ledger."*
- The √2-wider **replication range** is reported next to it.
- No rule widens either range. Outliers show in the leave-one-out table and in the ledger.

**Sensitivity ledger (not in the interval).** One row per item. Each row gives the change in the published BUY, in ⟨UNIT⟩ and in s_w units. The frozen script computes every row on the Stage-5b patched MACHINE SUMMARIES: it applies the counterfactual to every run, recomputes each run's headline with the pre-registered arithmetic, and re-applies the point-estimate rule, including the trim. The blind versions of the same rows are reported in `statistics.md`.

| Row | Source |
|---|---|
| Break probability −5pp / +5pp on every headline seat | Stage-3 elasticity table |
| Valuation date rolled to the pack date; share-count date; both | Stage-3 convention sensitivity |
| Denominator on the period-weighted count instead of the per-share count | Stage-3 convention sensitivity (F1) |
| Acquisitions: every seat on the organic basis; every seat including acquisitions | Stage-3 acquisition rows (F4) |
| Alternative denominator: every seat on its run's alternative denominator | Stage-3 alternative-denominator row (v9, N2) |
| Debt: net claims deducted again (the v9 count) | Stage-3 debt row (v10, T2) |
| Risk-free +50bp | Stage-3 rate lever |
| Published figure without the single finding whose removal moves it most | Stage-5b script |
| Dossier contrast: t, p and camp means | Stage 3 |
| Point rule: equal mean and median against the published figure | this stage |

**Margin-rule alternatives (v8, G3).** `TICKER_valuation.md` also reports the Stage-3 alternatives recomputed on the Stage-5b patched summaries: each as the trimmed mean of the runs' own-weight headlines under that rule, with its change against the published BUY, its blind point and its implied upside ÷ downside, beside the published BUY's own ratio. They are policy alternatives, not sensitivity-ledger rows: they are not in the interval, never averaged, and never candidates for the card's largest sensitivity.

Also listed, as **unmeasured**:
- dossier-builder variance (1 df with two dossiers);
- orchestrator variance, unless Stage 7 was run;
- model and harness effects.

Write `final/TICKER_valuation.md`, with every figure at full precision.

## Stage 5b — Critique-adjusted headline (orchestrator, by the frozen arithmetic script)
The folding rules:
1. Per-run application only.
2. Only CONFIRMED findings with patches that the script accepts move a number. Free-form dollar deltas never do.
3. Seats outside the roster (G2) stay out of every statistic, so a patch to one changes nothing that is published. (In replayed v7 summaries, a patch to an IRR seat changes only that seat's reference figures.)
4. For each run, the script applies the verifier's `joint_changed_inputs` to the run's MACHINE SUMMARY. It then recomputes every seat and the headline with the pre-registered arithmetic, and re-averages with the Stage-5 point-estimate rule.
5. Publish both numbers, and headline the adjusted one.
6. The Stage-5 uncertainty statement is recomputed on the adjusted headlines.

Independent recurrence across runs is the strength signal. Findings are never shared across runs.

**The frozen arithmetic script (`frozen_arith.py`).**
- **One script, ticker-generic.** The spec owner ships it in the toolkit (F3). It implements the Appendix-B arithmetic, the Stage-3 per-seat recompute and statistics, the Stage-5 estimate and this fold.
  - The orchestrator never writes or edits it. If no toolkit for the spec version exists, the execution does not start.
  - The same file serves every ticker of the toolkit version, so its SHA-256 must repeat across tickers.
  - The script contains no ticker-specific constant.
  - It runs in its own spec mode (`v10`) by default, and in four compatibility modes: `--spec v9` (v9 executions and their replays), `--spec v8` (masked v8 executions, with the memory test), `--spec v7.1` (the step-tier rule; also used for back-tests) and `--spec v7` (the replay gate). The v10 mode differs from the v9 mode only in the roster (seven seats), the logged v10 checks, the debt row, its card slot and the channel monitor; the seat, margin and BUY arithmetic is the same function.
- **Self-test (Stage 0), all must pass:**
  1. it reproduces every figure of the Appendix-A worked example, including the AT-CAP case;
  2. it rejects a patch whose path is not on the Appendix-F list;
  3. it rejects a patch whose `from` value does not match the summary;
  4. it rejects a patch set after which a tree fails the Stage-3 tree checks;
  5. it reproduces the v6-rule bridge case in Stage 3 (required = 0.475);
  6. it reproduces the AT-CAP and macro-base-L cases of Appendix A, floors L at 0, and logs an estimated `fair_value_macro_base`;
  7. it normalises a run whose `denominator_count_m` differs from `per_share_count_m`, reproduces the hand-computed result, and rejects a count patch;
  8. it counts acquisition mismatches on a constructed run with one mismatch of each kind, and reproduces hand-computed acquisition rows and convention row 4;
  9. it rejects a fair-value patch without a `fair_value_macro_base` patch, scales `fair_value_other_acquisition_basis` as a companion, and honours a verifier's NO-BUY patch on a seat above the cap;
  10. under v8, it reproduces the quality-premium map at its anchors, between them and outside them, and takes each tier's midpoint for a seat with no numeric score;
  11. under v8, it reproduces the Appendix-A margin-rule alternatives as literals (step tiers 34.25; EV rule 30.753; expectile rule 66.15 ÷ 2.0125 = 32.870, with an implied ratio of exactly 7.75 there; EV × (1 − π) 34.808), uses the probability-weighted mean, and checks the pre-registered constants;
  12. under v8, it computes an eight-seat run whose headline, premium, tail, fair value, lines and counts equal those of the same run with Victor and Max present; drops patches to them; rejects a score patch outside 0–100; leaves a seat with no valid tree, and a run with no eligible seat, out of the tree rules;
  13. under v8, the step line repeats the v7.1 F5 decision; a tree patch to a seat whose tree is null is applied; forecasts follow the F1 normalisation;
  14. it passes in all five modes (v10, v9, v8, v7.1, v7); the toolkit's own hashes match its manifest; the data publisher's copy of the reference execution replays to the same published BUY; the v8 replay reproduces the stored `replay_v8.json`; the v9 replay reproduces the stored `replay_v9.json`; and the v10 replay reproduces the stored `replay_v10.json`;
  15. under v9, it reproduces the alternative-denominator row of a constructed six-run case against an independent hand computation in Stage 3 and Stage 5 (`replay/V9_N2/`: F1 normalisation, AT CAP, NO BUY, zero weight, a missing field, a non-positive alternative, patched runs); keeps a seat without the field at its fair value (logged); scales the field with a fair-value patch and rejects it patched alone unless set equal to the seat's fair value; logs the N2 checks (basis, "none", ratio, per-seat scaling); counts no mismatch, and returns both acquisition rows equal to the headline, at zero acquisition spend, but still counts a run that excluded non-zero acquisition cash; logs a modal tier that is not a tier name; reads the mechanism flag strictly; and runs no memory test and prints no memory line;
  16. under v10, on a constructed seven-seat run: keeps a seat named Simon out of every statistic (logged C5); logs a seat off the macro base (by rate against MARKET_INPUTS, by a wrong run macro base, and by `fair_value_macro_base`), and moves no number for any; prints the `rebase` patch set (break value held) and accepts it, reproducing the Appendix-A rebase case (BUY 33.417) and the hand headline; labels a folded rebase finding approximate; reproduces the Appendix-A Walter case (multiplier 1.06; BUY 35.422) and logs a wrong multiplier, an uncapped gate and two FAILs without NO BUY; honours a NO BUY only for Walter with two FAILs; logs a run with debt deducted and prints the `undebt` patch set, which restores the undeducted headline; reproduces the Appendix-A debt row (FV 40; BUY 26.733) and keeps an unmeasured run's headline in it; logs an unknown register channel, a missing size, a `fv_mapping` entry for a seat without a mapping, a risk in two channels for one seat and a seat with no entry, and accepts `non_break_branch` entries; reproduces the channel monitor's means and the register's BUY effects; adds the induced-field row for the rate rule;
  17. `bridge.py` reproduces, on the stored ICE v9 per-run data (`replay/ICE_v9/`), the published BUY and its hand-computed macro-base and without-Simon rows (60.042 and 60.376 against 44.952), writes a row with every column of the Appendix-K header, computes the Appendix-G comparison of those runs against the same runs recomputed in v10 mode, matching a hand computation, and refuses a baseline folder that fails its manifest or ⟨BASELINE⟩.

  The numbers above name cases, not the script's test numbers; the self-test output names each case.

  The toolkit's other self-tests cover the rest: the Stage-1 redaction check (no list item; SHARES overlap, with a digit-boundary negative control; a note over a share count; non-USD amounts), the v9 Stage-1 path (the pack is the redacted dossier with k = j = 1, and a redaction over a share count is still refused), the season file's ERP arithmetic, the staged FRAMEWORK's hash (v10), the clean-room builder and the template diff's slot typing.
- **Patch validation (v7.1 and v8).** Under v8 the checks apply to seated investors; a patch to a seat outside the roster is dropped with a note (G2), and the rest of the finding is applied. A patch is accepted only if:
  - its path is on the Appendix-F closed list;
  - its `from` equals the current value;
  - every patched seat passes the Stage-3 tree checks after all of that finding's patches are applied;
  - every patched weight lies in 0–2.0, and (v8) every patched quality score in 0–100;
  - from v7.1: a `fair_value` patch on a seat that reports `fair_value_macro_base` comes with a `fair_value_macro_base` patch; an acquisition-declaration patch comes with an explicit `fair_value_other_acquisition_basis` patch; a companion patch comes with a fair-value, tree or acquisition-declaration patch (`fair_value_rf_plus_50bp` and, under v9, `fair_value_alternative_denominator` with a fair-value or tree patch to the same seat; under v9 the alternative may also be patched alone, only to set it equal to the seat's current fair value, when a finding is CONFIRMED that the run's alternative breaks the Phase-0 definition); and no share count is patched.
- **Companion fields.** A seat whose `fair_value` is patched without a patch to its `fair_value_rf_plus_50bp` (under v9 also its `fair_value_alternative_denominator`) has that field set by the script to its reported value × (patched `fair_value` ÷ reported `fair_value`), and the adjustment is logged. From v7.1 the same holds for `fair_value_other_acquisition_basis`, unless the same finding patches an acquisition declaration. `fair_value_macro_base` is never scaled by the script, because a fix to a rate (or, under v10, the rebase of an off-base seat) leaves it unchanged; the verifier patches it whenever a fix changes it.
- **Rejected patches.** If a finding's patches are rejected, the finding is logged CONFIRMED-unquantified (PATCH-INVALID), with the script's reason.
- **Joint fold.** For each run the script applies `joint_changed_inputs`.
  - If that list fails validation, the script applies the union of the findings whose own patch lists are valid and touch disjoint paths.
  - Findings with overlapping paths are then logged unquantified.
- **Knock-ons.** Knock-on effects are whatever the arithmetic implies, and only that: AT-CAP status at the 0.60 bound, FRAMEWORK NO-BUY status, Helena's floor applied to every seat's break branch, the denominator-count normalisation, and the weights.
- **Patch units.** Patches are applied in the run's own units. Any back-scaling of per-share figures happens after the fold.
- **Outputs, per run:**
  - the blind headline;
  - each finding's standalone delta (its patches alone);
  - the joint delta;
  - the adjusted headline;
  - the verifier's own figures;
  - a log line wherever the verifier's joint figure differs from the script's by more than 0.1% of the run's blind headline, both in the run's own units (scaled, in a replay of a masked execution).
- **Output for the Stage-5 sensitivity statement:** the point estimate recomputed without the single finding whose removal moves it most (its standalone delta taken out of its run's fold).
- **Hash checks.** A hash mismatch at any check is a deviation. Stages 3, 5 and 5b are then re-run with the pre-registered script before anything is published.

**Replay gate (F3).**
- **The reference execution.** The toolkit stores one reference execution, ADBE v7:
  - the MACHINE SUMMARIES of its 8 masked and 2 bridge runs;
  - its 8 verifications;
  - its k and j;
  - its Stage-3 and Stage-5 configuration and published figures.

  It is orchestrator-only.
- **New versions.** Any change to any toolkit script makes a new toolkit version. Before its first use:
  1. the self-test passes;
  2. in compatibility mode (`--spec v7`), the toolkit reproduces the reference's blind intermediate, published BUY, interval ends and committee fair value to within 0.005 ⟨UNIT⟩, every ledger row in ⟨UNIT⟩ to within 0.01 ⟨UNIT⟩, and the dossier contrast t and p and β̂ₖ and β̂ⱼ to within 1e-4. The expected values are pinned: `replay/ADBE_v7/expected_v7.json` must have SHA-256 `908de67b922f0be1346864d3126fd538c352b05c4e8a4e2f80d4145c946c96b6`, and no toolkit version may change that file;
  3. in its own mode, it records the reference replay ("ADBE @ <version> (replay)") in TOOLKIT_MANIFEST, with every approximation it needed stated. From v8 on, the stored own-mode replay (`replay/ADBE_v7/replay_v8.json`, hash in the manifest) is part of the gate: a later toolkit under the same spec version must reproduce it within 0.005 ⟨UNIT⟩. Toolkit v9 records `replay_v9.json` and also reproduces `replay_v8.json` in `--spec v8` mode, so the v8 arithmetic stays pinned. Toolkit v10 records `replay_v10.json` (the reference in v10 mode: Simon out of the roster, every other seat as reported) and reproduces `replay_v9.json` and `replay_v8.json` in their modes.
  4. every Stage-3/5 output records the spec mode it was computed in; Stage 5 refuses a Stage-3 output from another mode, and a `--spec` that contradicts the configuration's `spec_version` is an error.
- **Failure.** A version that fails any step is not used.

## Stage 6 — Final summary (v4 sections, plus the v6 and v7 additions)
The v4 `TICKER_analysis.md` and `TICKER_process.md` carry over, with these additions. The v4 commissioned "How the company makes money" section is written by one subagent that receives only the redacted dossiers (after the Stage-1 redactions and methodology-note removals; under v9 these are the packs) and the Appendix-H writer instructions; it is written after Stage 5b, and web is OFF.

**Decision Card (opens `TICKER_analysis.md`).**
- The frozen script generates it by filling the Appendix-I template from `statistics.md` and `TICKER_valuation.md`. The orchestrator writes no text into it.
- It is diffed against Appendix I (Stage 0.5, Step 1).
- **Rounding.** Published FV, BUY and range ends are rounded to a whole ⟨UNIT⟩ when the BUY is 20 or more, and to 0.1 below that. Range ends round outward. Unrounded values stay in `TICKER_valuation.md`.
- The card is followed by the **headline sentence**, also generated by script from its Appendix-I template. It names:
  - the rounded BUY;
  - the interval with its label;
  - the committee fair value;
  - the largest ledger row, with its size: the row with the largest absolute change in BUY in ⟨UNIT⟩, among the rows expressed as a change in BUY (break probability ±5pp, convention sensitivity including the denominator count, the acquisition rows, the alternative-denominator row (v9), risk-free +50bp, without the most influential finding, equal mean and median). The margin-rule alternatives and (v10) the debt row are never candidates.
- **v8.** The card's item 5 shows the margin-rule alternatives, the implied upside ÷ downside at each BUY, the seats left out of the tree rules and the number of headline seats within 3 points of a tier cut-off. Item 2 names the quality premium.
- **v9.** Item 6 adds the alternative-denominator lever (N2). Item 8 has no memory-control line and no first-v7-ticker bridge line, and the headline sentence has no memory flag (N1).
- **v10.** Item 6 adds the debt lever (T2). Item 8 adds the seats off the macro base, the runs with debt deducted, the risk-class counts and Walter's mean multiplier (T1, T2, T4).

**New section: "Frame choices the committees made."** It draws on the Stage-3 frame decomposition, adjustment ledger, break-probability elasticity table and histogram, convention sensitivity, rate lever and induced-field check, and (first v7 ticker) the v6-rule bridge, and covers:
- which choices varied across runs;
- which of them moved the headline, and by roughly how much;
- which choices every run made the same way, each labelled by the Stage-3 induced-field check as INDUCED (a text every run received fixed or defaulted it) or UNANIMOUS;
- the convention-sensitivity and rate-lever rows, with the dates each run used.

Only UNANIMOUS convergence counts as conviction. INDUCED agreement is reported with the text that induced it, and says nothing about independent judgment. Variation counts as honest uncertainty. The orchestrator reports all three and endorses none.

Under v7.1 the section also reports:
- how many runs had their denominator count normalised (F1), and by how much;
- the acquisition-matching table and its mismatches, with the two acquisition rows (F4);
- the seats AT CAP (F5);
- the redaction class table (F2).

Under v8 it also reports the seat-weighted quality premium against the step base per run, and the margin-rule alternatives, labelled as policy. Under v10 it also reports each run's debt path, interest-income and lease treatment, net claims and any debt deducted, and the debt row (T2); its systematic risk class (descriptive; it moves no number); the seats off the macro base and how their findings were folded (T1); the risk register by channel, with every logged double count (T3); Walter's grades, gates and multipliers and Alexander's scores and mappings, from the Stage-3 table of seat mappings (T4); and the channel monitor (T6). Under v9 it also reports each run's `alternative_denominator_basis`, its alternative ÷ declared ratio and direction and its own alternative-denominator row (from `statistics.md`), lists every run whose ratio lies outside 0.5–2.0, and states that the committee row nets opposite choices and holds each seat's margin. Before attributing dispersion to any frame choice, the section quotes the Stage-3 split of the fair-value share into denominator and multiple.

**New section: "What the packs lacked."** It lists PACK-GAP findings, with their recurrence count across critiques and the critics' hypothetical sensitivity, labelled as such (never a remembered value). It is reported, not booked.

**Blinding status (v9).** `TICKER_process.md` states that the packs were the redacted dossiers, unmasked and unscaled; that runs, critics and verifiers worked under the pack-only rule; and that price memory was not measured (N1).

**If USER_MANDATE ≠ NONE,** the headline sentence and the card's status line state that the figure is conditional on the mandate.

**Stage-6 checklist (v9, N7).** Before the Stage-6 documents are published, the orchestrator runs `extract.py mechanism` on every verification and confirms that every MECHANISM finding it lists (a critic's MECHANISM tag or a verifier's `"mechanism": true`) is in `final/SPEC_FLAGS.md` with the verifier's ruling and its `spec_change_or_null` sentence, copied from the extractor's output, not transcribed (Stage 4). *On MELI v8 they were copied only after publication.*

**Per-run data (v8, G5).** After the Stage-6 documents are published, the orchestrator runs `publish.py data` on the Stage-3/5 configuration.
- It writes to durable file storage, under `TICKER/<spec version>/data/`: every run's MACHINE SUMMARY as returned, every verification's JSON, the configuration with each run's k and j (1 under v9) and its spec mode, and the Stage-3 and Stage-5 outputs, with a `DATA_MANIFEST.md` of hashes (about 0.5 MB per ticker; AGX about 540 KB). Where durable storage is a size-capped knowledge base, the data folder goes to file storage outside it and only `DATA_MANIFEST.md`, with the folder's location, is kept there.
- The script replays Stages 3 and 5 from the copy, in the recorded mode, and records MATCH or MISMATCH. A mismatch is logged and the spec owner notified.
- The data are files from a prior ticker (Rule O-1): no subagent of any later ticker receives them.

**Outcome bridge (v10, T6).** After the data are published and replay MATCH, the orchestrator runs `bridge.py row` on the published data folder and appends its row to the season file `OUTCOME_BRIDGE.md` (durable storage, outside every ticker folder; orchestrator-only; Appendix K). In a validation execution it then runs `bridge.py compare` on the baseline and the new data folder and writes the result, the pre-registered comparison of Appendix G, to `final/VALIDATION.md`, published as an addendum to `TICKER_valuation.md`.

**Outcome ledger (v8, G4).** Then the orchestrator runs `publish.py ledger` and appends its row to the season file `OUTCOME_LEDGER_EXECUTIONS.md` (durable storage, outside every ticker folder; orchestrator-only; Appendix K).
- The row records the published BUY and interval, the committee fair value, the margin terms, the BUY and implied upside ÷ downside under each margin rule (including the ledger-only EV × (1 − π) rule), the mean quality score, the seats near a tier cut-off, the seats without a valid tree, the mean break probability and horizon, and the data path. It holds no market data.
- Outcomes are recorded only in `OUTCOME_OBSERVATIONS.md`, by the ledger-update procedure in Appendix K, never by an execution. No execution opens that file, because no execution may see market data.

## Stage 7 — Orchestration replicate (OPTIONAL; run only with an explicitly confirmed budget)
Under v7 this stage is optional:
- The text channel it was meant to test is closed by the Stage-0.5 mechanical diff, which passed 38/38 texts on ADBE and 19/19 plus every launch prompt on DECK, with negative controls.
- Under v7–v8 the Stage-3 scale-dependence test covered the uncontrolled channel, model memory, on every ticker. Under v9 that channel is not measured (N1).
- Stage 7 was never run in v6, at a cost of ~56 subagents and 8–10M tokens.

If it is run, Stage 6 says so. If it is not, Stage 6 states "orchestration replicate: not run".

Two independent orchestrators each execute Stages 0–5b on the same dossiers, blind to each other, with the same MODEL. Compare their published headlines.

*The pair counts, the simulated coverage and power, and the ADBE first-application budget below were computed for the v6 design (three runs per dossier, with scorers). They are kept as the v6 design record. If Stage 7 is run under v7, restate them for the v7 design before starting.*

**How to run it.** Use two **separate sessions**, started from the same dossier files and this spec.
- One session cannot orchestrate twice blind: by the second execution it has seen the first.
- Neither session may read the other's folder until both have published.

**Pass/fail rule (pre-registered).** The two published headlines should differ by no more than the pooled drift floor.

**Which pairs.** The pooled drift floor uses **only pairs from the same orchestrator AND the same dossier**. With three runs per dossier that is 3 pairs × 2 dossiers × 2 orchestrators = 12 pairs. Cross-orchestrator pairs are **excluded**: they contain the leak being tested, so including them inflates the threshold and cuts the test's power.

Why the threshold means roughly a 92% noise band:
- Each orchestrator averages n = 6 runs split evenly across the same dossiers. So the difference between the two means has SD ≈ σ√(2/6) ≈ 0.58σ.
- The drift floor is ≈ 1.13σ in expectation, where σ is the single-run SD within a dossier.
- 1.13σ ÷ 0.58σ ≈ 1.95 SDs, which would be ~95% if the drift floor were known exactly.
- It is estimated from only 12 pairs, so it is noisy. In simulation (200,000 trials, normal run noise) the false-alarm rate with no leak is **~8%**, i.e. a **~92%** band.

A gap above the band means orchestrator influence is still leaking. Trace it with the two ORCHESTRATOR_LOGs, NEUTRALITY_AUDITs and Stage-0.5 diffs.

**Power (same simulation, within-orchestrator pairs only).**

| True orchestrator leak | Probability the test flags it |
|---|---|
| none | ~8% (false alarm) |
| 1 drift floor | ~50% |
| 1.5 drift floors | ~81% |
| 2 drift floors | ~96% |

If cross-orchestrator pairs were wrongly pooled, power at a one-floor leak falls to ~36%.

The test cannot detect leaks much smaller than the drift floor. v6's drift floor will likely be wider than v5's, which lowers power in dollar terms. **Report the realised drift floor in dollars next to the pass/fail result, so the reader knows what size of leak was ruled out.**

**First application: re-run ADBE under v6 on the same two original dossiers.**
- **Do not add a macro rate or anything else to the dossiers, and do not supply MARKET_INPUTS or the v7 date conventions to these runs.** The point is comparability with the v5 executions.
- **Baseline:** the v5 execution that ran faithfully to v5 (tokens f6, n1, t8 and b3; published $221.16), with **MODEL set to that execution's model**. That execution's session was configured for `claude-opus-5-5`; the harness can fall back to a different serving model, so record the **serving** model per stage wherever the harness exposes it, and log where it does not.
- **Redaction check:** the v6 screeners apply the mechanical rule independently. Compare their dossier-B redactions with the v5 baseline's three hand redactions (repurchase cash series, treasury-stock row, authorization remaining-capacity figures). Log any difference; if they differ, the v5 and v6 sides did not see identical inputs, and the comparison says so.
- **Do not use the 4.8 execution ($316.15) as the attribution baseline.** It deviated from v5 itself:
  - no FRAMEWORK file was staged;
  - its runs saw the pre-registration;
  - the orchestrator scored the runs.

  Report it only as context.
- **The v5 side is a single orchestration.** A v6-vs-v5 difference is read against the pooled v6 drift floor and treated as **indicative**, because v5's own orchestrator noise is unmeasured.
- **Budget:** 2 orchestrators × (6 runs + 6 critiques + 6 verifications + 6 scorers + 2 screeners + 1 auditor + 1 writer) ≈ 56 subagents. At the v5 ADBE execution's usage (~120–250k tokens per subagent), that is on the order of **8–10M tokens**. Confirm the budget before starting.

A cheaper, weaker variant is one orchestrator and six runs, read against the v5 baseline. It measures the v6 drift floor, but cannot isolate orchestrator leakage.

## Artefacts
- Do not delete intermediate files.
- Mirror everything to durable storage, subject to the timing in Folder layout.
- Reproduce this specification as `final/spec_v10.md`, with VARIABLES instantiated and an execution note listing:
  - every ORCHESTRATOR_LOG entry;
  - every SPEC_FLAGS entry;
  - every Stage-0.5 diff deletion;
  - every deviation, including P-1.
- List every artefact in `final/MANIFEST.md`, with the configured model ID for every stage and the serving model where the harness exposes it.
  - After Stage 6 is published, add the manifest (tokens, dossiers and packs) and the share-count tag lists.
  - Keep the clean-room listings (`final/cleanroom_<stage>_<token>.txt`).
- Keep every launch prompt as sent (`final/launch_prompts/`) and its diff result.
- Keep the toolkit version used (its TOOLKIT_MANIFEST and every script as run), `final/script_selftest.txt`, every hash check, `final/redaction_check.md`, and the Stage-5b fold log (accepted and rejected patches, standalone and joint deltas, verifier-versus-script differences).
- Keep the MARKET_INPUTS copy used, with its SHA-256.
- Append to `SEASON_FRAME_ROLLUP.md` (Stage 3).
- Publish the per-run data and append the outcome-ledger row (Stage 6, G4 and G5) and the outcome-bridge row (Stage 6, T6); in a validation execution, publish `final/VALIDATION.md`.

---

## What changed from v9 to v10, and why

| Change | Reason |
|---|---|
| **T1. Every seat at the macro base.** No add-ons or credits; `fair_value_macro_base` = `fair_value`; the ERP-departure route closed; an off-base seat is a route-(d) violation patched by `frozen_arith.py rebase` (labelled an approximation); a descriptive `systematic_risk_class`; generic haircuts banned; the v8 "separate channel" sentence deleted. | 142 of 144 checkable seat rates sat above the average stock's expected return (ICE v9 62 of 64, median +150bp; ADBE v7 80 of 80, median +75bp). Add-ons were asserted, one-directional in practice, and could price one risk three times. On ICE, worth about +$15 of BUY with margins held. |
| **T2. Debt counted once, on cash flow to equity.** Every run values cash flow to common equity, after interest, preferred dividends, minority distributions, lease payments and the net borrowing its debt path implies; no claim deducted; operating balances in the flow; `net_claims_per_share` reported; C1 0.0 for a claim deducted from equity flows; `frozen_arith.py undebt`; a debt ledger row and card lever. The debated three-basis rule was replaced in review (P2) by the spec owner's decision. | All eight ICE v9 runs deducted net debt from flows already after interest: +$20.7 to +$23.7 of BUY on the runs' own flows. The macro base is an equity return, so the flow must be the equity's. An open flag since v7.1; ADBE v7 and TPR v8 critics had raised it. |
| **T3. A sized risk register.** Each risk and upside driver × seat in one channel (base cash flows, break branch, quality score, a fixed fair-value mapping, a non-break branch, or not priced), with a signed size; every item behind a non-break branch above 1% of fair value, either side, must be registered (not priced); generic haircuts banned in cash flows and scores; script checks for channel, size and double entries, and a derived BUY effect per channel. The debated one-way 1% rule was replaced in review (spec owner's decision on P3 and I1). | Within each ICE run, larger add-ons came with lower growth, scores and terminal growth and higher break probabilities (Spearman −0.34 to −0.46). The double-count check worked on labels. Without sizes, closing the rate channel would move value between channels unseen. |
| **T4. Seven seats.** Simon merged into Walter (four gates, two FAILs → NO BUY); Walter's grade symmetric and bounded (six components −2..+2; multiplier 1 + 0.015 × score, 0.82–1.18; gates cap components); preferred stock in the bridge; the mapped-dimension rule for Walter and Alexander; Graham's rate credits and Claire's rate channel removed. | With a shared rate Simon's DCF repeats other seats'. His gates and uninvestability rule survive in Walter; symmetry stops his one-way penalty returning as a one-way multiplier. About an eighth less seat work per run. |
| **T5. FRAMEWORK_v10, edited, versioned and hashed in the toolkit.** | Every subagent read a FRAMEWORK that contradicted Appendix B; route (d) would have enforced Rule 2 and Simon's gates against it; no record of which FRAMEWORK a run used. |
| **T6. What the season measures.** Stage-3 channel monitor; `OUTCOME_BRIDGE.md` by `bridge.py`; Appendix K test 5 (signed bias, stratified) and test 3 by spec; roll-up `debt_path`, `systematic_risk_class` and a VALIDATION column; validation re-runs of ICE, BBW and HCI, pre-registered. | v10 changes the run instructions, so it cannot be replayed. The bridge gives the arithmetic part; the validation runs and the monitor show how much of it the new runs realise and where any pessimism moved. |
| **Debate, not adopted.** A two-sided systematic rate term (±50bp); recalibrating π; a beyond-year-10 rate fade; making Alexander's mapping symmetric. | See Open flags. |
| **Review before release.** Three independent reviewers; every finding addressed. | `claude/SPEC_v10_REVIEW_RECORD.md`. |
| **Consequential.** Preamble and VARIABLES (FRAMEWORK, TOOLKIT, VALIDATION); Rule O-2 (template conventions; slots); toolkit section; Stage 0 list; Stage 0.5 (FRAMEWORK hash, ⟨BASELINE⟩); Stage 1 (FRAMEWORK copy); Stage 2; Stage 3 (v10 checks, roster, debt row, rate lever, channel monitor, induced row, frame fields, roll-up); Stages 4 and 4b (MECHANISM examples, precedence, off-base and debt findings); Stage 5 ledger; Stage 5b (modes, self-tests 16–17, replay); Stage 6 (card, frame section, bridge); Artefacts; Open flags; Known costs; Appendices A, B, C, D, E, F, G, H, I and K. | Forced by T1–T6. |

## What changed from v8 to v9, and why

| Change | Reason |
|---|---|
| **N1. No masking or rescaling; a pack-only rule.** Packs are the redacted dossiers, with names and real figures. Stage 1c no longer masks, rescales or checks completeness, masking or consistency; Stage 1d and the scale-dependence test (per ticker and pooled) are removed, and v9 executions have k = j = 1. The tag screener lists only thinness and share counts. Runs may recognise the company and use only the facts and reported figures in the pack and MARKET_INPUTS, their own assumptions being judgments (decision C: every remembered fact, not only market data, is barred). | Every probe of the season named the company (90–97% stated confidence where recorded). The pooled memory test never flagged (40 rows: β̂ₖ +0.0038, β̂ⱼ +0.0417, p 0.64). The Stage-1c checks were the season's most frequent stop: four toolkit point releases, and on MELI three failed completeness attempts per tag screener, then deviation D-3. |
| **N2. A defined alternative denominator, valued, with a ledger row.** Same definition as the declared denominator, differing only in its period or the margin applied to the basis-period revenue, in either direction, chosen by the run (decision A, option 2); `fair_value_alternative_denominator` per seat; a Stage-3 ledger row and a card lever. | MELI: five denominators across eight runs, headlines $293–$1,984, 87% of within-dossier log variance from fair value, run noise $564 against a $497 BUY. The v8 "leading alternative" was never valued, and the runs' own choices ranged from $29 to $230 on non-comparable definitions. |
| **N3. Runs check branches and trees before writing.** | MELI: 5 of 8 critics found branches that could not be rebuilt (C4); one run's trees failed the median check, so its seats left the tree-based rules. |
| **N4. ERP rebased to the file's risk-free rate** (decision B). Appendix J gains the source's own risk-free basis and its series; ERP used = source ERP + source risk-free − file risk-free; the checks script verifies the arithmetic. | The 2026-09-10 file paired a 4.09% ERP measured against 4.75% with a 4.95% risk-free rate (macro base 9.04% instead of 8.84%). Five of eight MELI critics raised it. |
| **N5. Zero acquisition spend counts as matched.** | MELI's card showed 8 mismatches that moved nothing. |
| **N6. Toolkit robustness:** thinness parser, modal-tier check, verifier command. | MELI: an empty thin-data line, a prose modal tier, a blocked `patch` command. |
| **N7. Housekeeping:** auditor slots, dossier guideline, MECHANISM checklist. | Flagged on every ticker; MELI and TPR dossiers; MELI's SPEC_FLAGS. |
| **Review before release** (decision D). Three independent reviewers (49 findings: 1 blocker, 18 major, 30 minor) and a closing check, whose 12 further findings (2 major, 10 minor) and the 3 of its re-check (1 major, 2 minor) were also fixed; every finding fixed or answered. | `claude/SPEC_v9_REVIEW_RECORD.md`. |
| **Consequential.** Preamble and VARIABLES (MASK_LABEL, MASK_UNIT, TOOLKIT, MARKET_INPUTS); Rule O-1 (orchestrator-only list), Rule O-2 (template conventions; fixed labels; mandate scope; season inputs); folder layout; toolkit section; Stage 0 list; Stage 0.5 (diff list, ERP check, auditor); Stage 1 (tag screener, redlog); Stages 1c and 1d; Stage 2; Stage 3 (back-scaling, F1 list, N5, N6, the new row, the memory test closed, roll-up); Stages 4 and 4b; Stage 5 ledger; Stage 5b (modes, self-tests 14–15, companion field, replay); Stage 6 (writer, card, frame section, blinding status, checklist); Stage 7; Artefacts; Open flags; dossier guideline; Known costs; Appendices B, C, E, F, G, H, I and J. | Forced by N1–N7. |

## What changed from v7.1 to v8, and why

| Change | Reason |
|---|---|
| **G1. A continuous quality premium.** `required = clamp(π(score) + p·L, 0.10, 0.60)`, with π piecewise-linear through (52.5, 0.40), (67.5, 0.325), (82.5, 0.225), (95, 0.125). The tier is a label. The term is renamed: a premium for estimation error and risk aversion, not the price of the bear branches. | On AGX and ADBE the tier step drove 64–79% of each investor's run-to-run margin variance, and a one-point score change at a cut-off moved a margin by 7.5–10pp. The trees showed the base was 4.5–5.2× the probability-weighted bear loss, so the v7.1 label was wrong. Both debate-2 advocates and the judge converged on the continuous map; v8 adopts it without the in-sample levelling constant they sketched. |
| **G2. Eight seats.** Victor and Max are not seated; no seat produces an entry price. | Their entry prices never entered the BUY and their fair values repeated the committee's (pricing them under the committee rule moved the BUY about 1%). Each cost about a fifth of every run's per-seat work. |
| **G3. Margin-rule alternatives, never averaged.** Step tiers, tuned Victor (0.670 × tree EV) and tuned Max (the 1/8.75 expectile) on the Decision Card and in the valuation file. | Debate 1: averaging the untuned profiles only loosened the margin. Debate 2: tuned to equal strictness, averaging was an expected loss (chance of beating the committee 25–35%). Showing the set makes the policy choice visible: on ADBE the margin rule moves the BUY by more than the interval's half-width. |
| **G4. An outcome ledger** with pre-registered tests (Appendix K). | Without outcomes, accuracy between margin rules cannot be decided. Both judges asked for it. |
| **G5. Per-run data published and replayable.** | Only ADBE's per-run data survived; GSL and DECK could not be back-tested under any proposed change. |
| **S1. One committee script per run; output written in one pass.** | AGX run-time review: one-script runs took 16–29 tool calls and 25–37 minutes; runs split across many scripts 42–64 calls and 44–88 minutes, with no better critique results. |
| **S2. A mechanics block, base and break schedules, complete input-change lines for every other value.** | Year-by-year schedule tables were 9–28% of each AGX run's output, about half for non-base values. The mechanics block and the 0.5% reproduction test keep every value checkable without the run's script. |
| **S3. Per-run pipelining.** Critic → verifier always; run → critic only with isolated file systems. | Verifiers waited for the slowest critique. On a shared file system, letting critics start early would let running runs read critiques (Rule O-1). |
| **S4. UNSCALED rule for unit labels; one-bundle restore.** | The "(000s)" completeness stop hit DECK, GSL and AGX; restore by transcription cost about 15 minutes and 1.2M tokens on AGX. |
| **Review before release.** Three reviewers (an arithmetic and code reviewer, an integrity auditor and a practitioner) raised 32 findings (1 blocker, 13 major, 18 minor); all are addressed, one (generic-uncertainty add-ons) by stating the v7.1 status quo rather than the proposed ban. A closing reviewer re-ran the reproductions, confirmed the fixes and raised eight small items, also fixed. Among them: the manifest and bundle regenerated and hash-checked in the self-test; S3 restricted on shared file systems; the ledger split so no execution opens market data; complete S2 lines with a mechanics block; `forecast_5y` redefined (period end, company total, definition); a break horizon; the ledger tests re-specified with a loss; implied upside ÷ downside ratios; the EV × (1 − π) challenger recorded; crash and edge-case fixes in the script. | `claude/SPEC_v8_DEBATE_RECORD.md`. |
| **Consequential.** Appendix A (v8 example and the alternatives); Appendix B (roster, Precedence, Margin, Mechanics, MACHINE SUMMARY); C4, C5, C7; Appendices E and F (precedence, task, patch list, MECHANISM examples); Appendix G (constants, statistics, folding); Appendix H (tag screener); Appendix I (item 2, new item 5, renumbering, slots); Appendix K added; Rule O-1 (pipelining); the toolkit section (publisher, restore); Stage 0 list; Stage 1c check 1; Stage 2; Stage 3 (premium, roster, alternatives, forecasts, roll-up); Stages 4 and 4b (timing, MECHANISM, precedence); Stage 5 (alternatives); Stage 5b (self-test, modes); Stage 6 (card, data, ledger); Artefacts; Known costs; Open flags. | Forced by G1–G5 and S1–S4. |

## What changed from v7 to v7.1, and why

| Change | Reason |
|---|---|
| **F1. One share-count rule.** Value is built on company totals and converted to per share once, with the latest dated diluted count. `denominator_count_m` must equal `per_share_count_m`, and the script normalises any run where they differ. A new ledger row shows the period-weighted alternative. | On ADBE v7, Appendix B allowed "a period-weighted count … for the flow denominator". Dossier-B runs divided owner cash flow by the 406M twelve-month average while converting value per share on 395M. That was worth about $7 of the $17 gap between the dossiers. The ledger's share-count row read $0, because it tested only the per-share step. |
| **F2. Redaction by fixed lists, checked across dossiers.** A redact list (market values, and the dollar side of the company's own equity transactions) and a keep list (every share count, and every other financial line). One redaction screener reads every dossier. The toolkit rejects entries that name no list item or touch a share count. | The two-operation test contradicted its own "keep the share count" clause. On ADBE v7 one screener removed dossier A's share-count history and the other kept dossier B's. All four dossier-A critiques listed the missing dated count as a pack gap. |
| **F3. A versioned toolkit with a replay gate; a lean orchestrator.** The spec owner ships every script, and the orchestrator never writes one. A new version must reproduce ADBE v7 in compatibility mode before first use. Screener outputs are machine-readable. The orchestrator routes work by script and checkpoints its context. | Two tickers valued by two hand-written 89KB scripts is an unregistered method change. ADBE v7's Stage-1c consistency check was hand-coded to that dossier's line numbers. The orchestrator was 30% of the execution's cost, with a context of 550–780k tokens for most of it. |
| **F4. Two-sided acquisition matching.** Every seat declares `growth_basis` and `acq_spend_deducted`, which must match. Every seat reports `fair_value_other_acquisition_basis`. Two ledger rows (every seat organic; every seat including acquisitions). Dossiers carry acquisition cash and the organic/acquired split. | FCF excludes acquisition spend, so growth that includes bought growth is credited free unless the cost is charged. 6 of 8 ADBE v7 critiques found it, with folded corrections of −$2.45, −$2.82, −$1.53 and −$0.96. Run d8 made the reverse error. On a serial acquirer this would be the largest error in the valuation. |
| **F5. No cliff in the margin arithmetic.** A seat above 0.60 before clamping is AT CAP (required 0.60) and stays in the headline. NO BUY applies only under a FRAMEWORK uninvestability rule. L is measured against `fair_value_macro_base`. | Confirmed MECHANISM findings on ADBE v7: dropping a seat that crosses 0.60 raised its run's headline by about 10% (m4 #11), so more risk gave a higher price. A seat's own rate add-on shrank its tail term (w6 #12: Simon's L 0.67 against 0.72–0.77). |
| **Consequential.** Appendix B (Phase-0 share-count and acquisition bullets, the Margin, Acquisitions and Mechanics blocks, and the MACHINE SUMMARY); Appendix A (AT-CAP and macro-base-L cases); C1 and C7; the Appendix F patch list and MECHANISM examples; Appendix G constants and lists; Appendix H (redaction and tag screeners, JSON outputs, launch prompts); Appendix I (three lever lines and one status line); Stage 0/0.5 (toolkit manifest hash); Stage 1/1c/1d (redaction check, consistency triples); Stage 3 (normalisation, acquisition tabulation and rows, convention row 4, induced row, roll-up fields); the Stage-5 ledger; the Stage-5b self-test and replay gate; Stage 6; Artefacts; the dossier guideline; Known costs. | Forced by F1–F5. |

## What changed from v6.3 to v7, and why

| Change | Reason |
|---|---|
| **E1. One tail term replaces the asymmetry/gate machinery.** `required = clamp(base(tier) + p·L, 0.10, 0.60)` from each seat's own tree; R, ED/EU, the median anchor, median-R inheritance, the 15% gate and the valve are deleted; break probability is derived in three steps; Helena alone sets the floor; Stage 3 recomputes every seat from its tree and reports an elasticity table. | On DECK v6 the margin mechanism, not the valuations, drove the number. Pack-A fair values agreed within 1.1% while BUYs spread $9.43. Asymmetry added about 10.7pp of margin. Moving break probabilities across 15% swung each run $11–$16 (ADBE: $37–$51). Excluded IRR seats set seven of eight headline margins in three runs. |
| **E2. Numbers move only through the frozen arithmetic, by script.** Critics and verifiers get STAGE2_INSTRUCTIONS; precedence over FRAMEWORK's tier table; route (d) scope stated; verifiers return field-level patches; one hash-registered script computes Stages 3, 5 and 5b; formula-changing fixes are MECHANISM. | On DECK one verifier's out-of-mechanism fix (−$5.31 on f6) moved the published figure from ≈$76.48 to $75.29 and reversed the sign of Stage 5b. Three verifiers gave three rulings on the same margin question, with $12.41 at stake. |
| **E3. Price-memory control in every execution.** Masked packs rescaled by secret k and j; back-scaling; a scale-dependence test; an identification probe; critics web OFF; a clean room; Stage 7 optional. | Price-blindness covered inputs only. Runs are models that may remember the price, and DECK runs demonstrably used remembered non-price facts. Stage 7 was REQUIRED and never run. Verifiers received redacted repurchase figures with their path to a price. |
| **E4. Dated conventions and a season market-inputs sheet.** Valuation, per-share count and balance-sheet dates; MARKET_INPUTS for the macro base (O-2 carve-out); convention sensitivity and rate lever; INDUCED labels; methodology notes removed from dossiers. | Every DECK run valued as of fiscal year-end on a period-average share count against a point-in-time cash balance, worth about +$5.7 to +$7.4 once corrected. A rubric line and a pack recommendation induced it, and Stage 6 called it independent. The two DECK packs quoted different risk-free rates. |
| **E5. What is published, and how precise it is.** No scorers or coefficient; trimmed-mean point; an 80% confidence interval from pooled run noise, labelled; a sensitivity ledger; a script-built Decision Card; 4 + 4 runs. | The coefficient moved the DECK figure by $0.02–$0.07. Inverse-dispersion equals the median by identity. The band rules could not fire. The band never said what it covered, while effects outside it were several times wider. |
| **Consequential.** Appendix A replaced; Appendix C becomes an unscored critic checklist; Appendices I (Decision Card) and J (MARKET_INPUTS) added; the scorer launch prompt deleted; new slots ⟨OUT2⟩, ⟨SCRIPT_SHA⟩, ⟨AS_OF⟩, ⟨CARD_…⟩ and the Appendix-J season slots; the MACHINE SUMMARY gains trees, dates, macro and rate-lever fields and loses the gate/asymmetry fields; the season roll-up gains `mechanism_version`, `ln_k`, `ln_j`, the probe result and the MARKET_INPUTS hash. | Forced by E1–E5 (see Revision history, v6.3 → v7). |

## What changed from v5 to v6, and why (history)

| Change | Reason |
|---|---|
| **1. Rule O-2: the orchestrator holds no valuation opinion.** Denominator, adjustments, basis, weights, floor, guidance stance, moat framing and "live judgments" move to each run's Phase 0. | In v5 these were fixed once and shared by every run. Their effect on the number could not show up in the drift floor. |
| **2. PREREGISTRATION is ticker-generic and never shown to Stage 2.** | The v5 LEN and ADBE-4.8 executions showed the full ticker-specific pre-registration to runs, so the frame travelled with it. |
| **3. Every text a subagent receives is a fixed template: Stage-2 instructions, rubric, critic and verifier prompts, pre-registration, launch prompts, screener and writer instructions (Appendices B, C, E, F, G, H). A script diffs each instantiated text — launch prompts as actually sent — against its template; a Stage-0.5 auditor blind to the company checks slot values and the mandate.** | An orchestrator cannot reliably audit its own framing. A template leaves no room to add any, and a diff proves none was added. Any untemplated text, even a one-line launch prompt, is a channel. |
| **4. Redaction becomes a mechanical two-operation rule, applied by screening subagents. It includes share-for-dollar pairings, and the dollar leg is always the one redacted.** | The two v5 ADBE executions reached opposite redaction decisions on the same repurchase figures. |
| **5. Weights are set per run.** The headline uses each run's own weights, with a uniform-weight sensitivity. | The FRAMEWORK gives weights to the moderator. Freezing them across runs was an orchestrator judgment. |
| **6. MACHINE SUMMARY adds a `frame` block (including `gross_source` and `denominator_adjustments`) and per-seat `break_p` and `break_loss`.** Stage 3 adds frame decomposition, an adjustment ledger and a knife-edge table. Stage 6 adds a frame-choices section. | Once frame choices vary by run, they have to be declared in a fixed vocabulary so their effect can be measured. On ADBE the decisive frame variable was the adjustment set, not the denominator type, and the largest BUY driver was the 15% gate threshold. |
| **7. Verification route (c): a run is judged against its own declared frame.** Route (d′) covers user mandates. FRAME-JUDGMENT and PACK-GAP findings never move numbers. | With no frozen treatment, "contradicts the frozen treatment" no longer exists as a confirmation route. A run's internal consistency replaces it. |
| **8. Coefficient gains C8 (frame declaration).** No criterion may reward or penalise *which* frame a run chose. Scorers get the pack but not the critique layer. | Scoring must not smuggle an orchestrator frame back in, must be able to check pack-dependent criteria, and should stay independent of the critique layer. |
| **9. Three replicates per dossier by default.** | More free choices per run means more run-level variance. Two replicates give a very noisy drift floor. |
| **10. Model ID recorded for every stage. One model per execution.** | The ADBE v5 comparison could not separate orchestrator effects from run-model effects. |
| **11. Rule-3 reading of "rate + gate" stated in the rubric (C6).** | In v5 ADBE, the scorer and the verifier read the same pattern differently. A generic rubric must be unambiguous. |
| **12. USER_MANDATE slot, which can never override blinding, the no-market-data clause, web limits or redactions.** | O-2 binds the orchestrator, not the user. A user framing (e.g. STLA's) needs a verbatim, audited, clearly labelled channel, and one that cannot be used to breach integrity controls. |
| **13. Frame-outlier band rule.** | Free frames make a consistent-but-unusual outlier possible. The band must show it. |
| **14. Stage 7 required for the first v6 ticker,** with the model held fixed, run as two separate sessions, with a pre-registered pass/fail band (within-orchestrator pairs only) and simulated coverage and power. | Without it, v6's effect cannot be separated from the model or from the other changes in the family. |
| **15. Every subagent receives the Rule-10-neutralised FRAMEWORK copy.** | The original example is shaped like one of the season's tickers, and it reached critics with web access in the draft. |

## Resolved from the v6 deferred list (v7 edit E1)
- **The asymmetry anchor.** Resolved by removal. There is no R, ED/EU or committee-median anchor. On DECK v6 the own-FV anchor alone saturated at +11 to +15pp on every seat, and made the committee *more* conservative.
- **A graded durability gate.** Resolved by removal. The break branch enters the margin continuously, as p·L, so there is no threshold to grade. The DECK v6 knife-edge swing ($11.03–$16.10 per run, 1.9–2.7× the drift floor) and the ADBE swing ($37–$51) were the evidence.

## Open flags carried forward (considered for v7, v7.1, v8, v9 or v10, not selected)
**From the v10 debate:**
- **A two-sided systematic rate term (±50bp)** for financial leverage, operating leverage and cyclicality. Not adopted: no run can measure beta without prices; the thresholds would be uncalibrated and set with one ticker's market gap in view (Rule 7); and two-sided wording (Graham's credits) already went unused. Gated on Appendix K test 5, stratified by `systematic_risk_class`.
- **Recalibrating π** after the add-ons go. Not adopted: every margin rule scales with the seat's own tree, so relative strictness is unchanged, and re-tuning to hold BUYs would re-hide the bias. Appendix K test 1 decides.
- **Fading the discount rate toward a long-run normal beyond year 10** (real yield 2.87% → 1.5% on ICE, about +$8 of BUY). Not adopted: a "normal" rate is a macro forecast, and it would be a third simultaneous change.
- **Making Alexander's mapping symmetric** (+10% / 0 / −15%). Not debated.
- **π is blind to duration and beta.** With one rate for every seat, a long-duration or highly cyclical business gets no rate difference; only its forecast, break branch and quality score carry it (Known costs).
- **Validation on other tickers** (SPGI, TPR). Not selected: the debate's ballot offered ICE, SPGI and TPR or ICE, BBW and HCI; all three debaters chose the second, because BBW (cyclical, lease-heavy) and HCI (an insurer) test the debt rule on two more kinds of balance sheet, and TPR's baseline is v8. SPGI also has a v9 baseline and remains a candidate for a fourth run.

**Resolved in v10:** named events and generic uncertainty as rate add-ons (T1, T3); debt and interest treatment (T2); a FRAMEWORK edit (T5); the Simon–Walter merge (T4); Claire's moat in more than one channel (T3, T4).

**From the v9 change list:**
- **Option 1 for the alternative denominator:** the declared denominator recomputed at the prior five fiscal years' average margin. Not adopted: a pipeline-imposed convention, which the induced-field check would label INDUCED, and which builds in a recovery on a deliberate-trough company.
- **Annotating the ERP instead of rebasing it.** Not adopted: rebasing puts the premium on the basis it is added to; annotating would only have kept the macro base comparable with earlier rows.
- **Widening or replacing the trimmed mean** after MELI's $564 run noise. Not adopted: the interval reported the noise honestly. N2 reports one part of it; the larger MELI source (the forecast path and terminal growth relative to the macro base) is open.
- **Terminal growth relative to the macro base** (MELI v8 0d #1, MECHANISM): whether to cap terminal growth against the macro base.
- **Caps inside branch rules stated as numbers** (MELI v8 68 #3, MECHANISM).
- **The alternative computed by script from the frame fields** ((fair value − balance-sheet add) × alternative ÷ declared + balance-sheet add), dropping the seat field. Not adopted: seats whose value does not start from the denominator need their own figure; the script instead logs any seat whose figure departs from that scaling.
- **Frame fields for the alternative's gross line and adjustments**, so the definition could be checked mechanically. Not adopted: critics check it from Phase 0, and a confirmed breach is patched to "none".
- **A sealed record of the model's remembered price**, to report how often run fair values sit near it. Not designed; under v9 price memory is unmeasured.
- **Re-running MELI under v9.** Not done: its packs already match v9's (its run instructions were v8's). Worth doing only if a clean v9 row is wanted for the outcome ledger.
- **Measuring price memory without masking.** No design was proposed. Under v9 price memory is unmeasured (Known costs).
- **The v7.1 and v8 open flags** (named events as rate add-ons, debt and interest treatment, generic-uncertainty add-ons, a FRAMEWORK edit) stayed open in v9; all four are resolved in v10.

**From the v8 debates and review:**
- **Critics receive the run's committee script** (about −30 to −40 minutes on Stage 4). Not selected: a critic that leans on the run's script can miss a bug inside it.
- **Committee + tuned Victor at equal weights.** Judged about neutral (chance of beating the committee 35–50%, low confidence). Recorded in the ledger through the card line instead.
- **One EV-based rule, BUY = EV × (1 − premium(score)).** Sign of the effect unknown. A ledger challenger.
- **Sizing the premium against measured fair-value error.** The anchors are the v7.1 tier constants. Appendix K's pre-registered tests decide any change.
- **A levelling constant for the premium map** (−0.73pp, fitted in sample on AGX and ADBE). Not adopted.
- **Generic-uncertainty rate add-ons and the premium (Rule 3).** Under G1's wording, a rate add-on for generic forecast uncertainty or volatility may price what the premium prices (AGX a8 #19, about +$1.62; GSL w7 F15). v8 keeps the v7.1 status quo and states it in Appendix B and C6: such an add-on is a separate channel, and only an add-on naming the break event double-counts the tail term. Whether to ban such add-ons was next in line for a ruling. *Resolved in v10 (T1): no add-ons.*
- **A FRAMEWORK edit for v8.** FRAMEWORK still describes ten investors, Rule 6's entry prices, Phase 4's IRR sub-table and "Max's bear values". Appendix B's Precedence governs; editing FRAMEWORK itself would remove the standing contradiction. *Resolved in v10 (T5).*

**From the v7.1 debate** (Borda points out of 21, from three ballots of seven):
- **Named events as rate add-ons (6 points; next in line).** On ADBE v7, 7 of 8 critiques found leadership succession priced one-sided, as a rate add-on, against Rule 9. Proposed: named, datable events only as two-sided tree branches, with rate add-ons only for diffuse uncertainty. *Resolved in v10: no rate add-ons (T1); every risk in one sized channel (T3).*
- **Dossier variance in the interval (5 points; vetoed by the Engineer as four dossiers mid-season).**
  - On ADBE v7 the dossier contrast ($17) exceeded run noise ($8). With two dossiers it has 1 df and is not measured.
  - The Methodologist's fallback, which was not adopted: a season-pooled between-dossier variance, estimated from each ticker's two dossier means with ticker fixed effects, published beside the run-noise interval.
- **Memory test by re-randomisation (1 point).** It is needed before any cut below 4 runs per dossier. A plain permutation across all runs is not a valid null, because Stage 1c balances k and j within each dossier. Re-drawing under the Stage-1c rules is. *Moot from v9 (N1).*
- **Debt and interest treatment (1 point).** State whether flows are unlevered with net debt subtracted once, or levered without a second debt deduction. Three dossier-B critiques raised a double count. *Resolved in v10 (T2).*
- **Not on any final ballot:** derived quality scores; a continuous tier margin (left out of F5, and opposed by the Practitioner as adding false precision; adopted in v8 as G1); the patch-stage variance diagnostic (on ADBE v7, Stage-5b patching raised s from 6.60 to 8.41); the remaining auditor flags on FRAMEWORK and template text; Appendix I inline conditionals; the writer's length; a definition of "decisive inputs"; recording the serving model from session records; sealed-store isolation as the standard method.
- **Rejected:** a pre-registered adaptive run count. Stopping on the observed same-dossier gap biases the noise estimate downward, so the interval under-covers (Methodologist veto, conceded by its proposer).

**From v7.** v7 contained exactly five major edits. These issues were debated and not selected; the flags stay open for the spec owner.
- **Moat priced in more than one channel (Claire, Rule 3).** Confirmed in 5 of 6 DECK runs. A fixed seat channel map was proposed and not selected. *Addressed in v10: one non-rate channel for Claire (T4), checked by the risk register (T3).*
- **Neutrality-auditor flags on FRAMEWORK text** (DECK F1–F15, ADBE L1–L19). The same sentences were flagged on both tickers. Only F13 (Helena's floor) and F14 (Alexander's margin routing) are partly addressed, by E1's FRAMEWORK edits.
- **Redaction by operation count (O6).** Resolved in v7.1 by F2 (redaction by transaction class). Treasury-stock and authorisation dollars are now on the redact list; roll-forward routes remain soft and stay in the packs.
- **Housekeeping** (template defects that did not win a slot):
  - O2/O3: resolved in v7.1 by F2 (the thinness log is the tag screener's ⟨OUT⟩);
  - O4: ⟨FILES⟩ rendering;
  - O11: masking of bare tokens for the auditor;
  - O12: resolved in v7.1 by F2 (the replacement span is in the redaction screener's JSON);
  - P1/L18: C1's "SBC excluded" against the checklist's scope rule;
  - P2/L19: C3's widened guidance exception;
  - L1/L2: the units-line examples.

  Resolved by the five edits: O1 (⟨UNIT⟩ now appears in Appendices B and E), O7 (no coefficient), O8 (E1), O9 and O10 (E2). O14 is addressed, not eliminated, by E3: masking reduces memory use and the scale-dependence test measures what remains, but anchoring on a remembered ratio or multiple is invisible to it (v7–v8; under v9, O14 is unmeasured: N1).
- **Tier cliffs.** Resolved in v8 by G1.
- **Replay audit.** An independent replay subagent was proposed and not selected. E2's self-test and hash checks cover part of it.
- **Roster.** Cutting Max, merging Simon into Walter, and one Victor-owned tail tree were proposed in v7 and not selected. v8 unseats Victor and Max (G2); v10 merges Simon into Walter (T4).

## Dossier-construction guideline (outside the pipeline; applies to whoever builds dossiers)
- **Macro inputs come from MARKET_INPUTS, not from dossiers** (Rule O-2, "Season market inputs").
  - Why: on ADBE, all four v5 critiques independently found each run's inferred risk-free rate 50–100bp low (≈ −$9 to −$27 per run). On DECK v6, the two dossiers carried different rates.
  - A dossier may still quote macro figures. Where they differ from MARKET_INPUTS, MARKET_INPUTS governs (Appendix B).
- **No methodology recommendations.** A dossier describes the company. It never tells the valuer which method, denominator, share count or share-count convention, rate, growth, adjustment, peer or figure to use. Any such sentence is removed at Stage 1 (redaction screener, step 2).
- **Dates.**
  - State the dossier's as-of date.
  - Give every dated shares-outstanding figure available, with its date, including the latest one on or before the as-of date. A share count alone does not invert to a price, and the Stage-1 rule keeps share counts.
  - Give the date of every balance sheet.
  - Give the latest period-end diluted share count and the dilutive securities outstanding (options, RSUs), where reported.
- **Acquisitions (F4).**
  - Give the cash paid for acquisitions in each year, for at least five years, naming the deals.
  - Give the organic and acquired parts of revenue (or ARR) growth where the company discloses them, or say that they are not disclosed.
- **Country context (v9).** For each main operating country, give recent and long-run nominal GDP growth and inflation, the policy rate and the reporting-currency exchange-rate history, with sources. Under the pack-only rule runs cannot use remembered macro figures, and FRAMEWORK rules such as terminal growth against nominal GDP need them.
- **No statement about the pipeline (v9, N7).** A dossier says nothing about the pipeline, the valuation framework or method document, or files its builder could not find. *Both MELI and both TPR dossiers said the method document could not be found, which was not true. The redaction screener removes such sentences (step 2).*
- **Do NOT retrofit any of this into the ADBE dossiers** used for the Stage-7 attribution test.
- PACK-GAP recurrences in `SEASON_FRAME_ROLLUP.md` are the running list of what dossiers should add next.

## Known costs of v10, v9, v8, v7.1 and v7
*v6 costs that still apply are kept. Later costs name their edit.*
- **One rate for every business (v10, T1).** π, the tail term and the forecast must now carry every company-specific risk, and nothing carries market-wide risk: a leveraged cyclical and a defensive business are discounted alike. `systematic_risk_class` records the difference; Appendix K test 5 says whether a term is needed. π is blind to duration and beta.
- **Pessimism may move rather than go (v10, T1, T3).** Seats may cut growth, scores or terminal growth, or raise break probabilities, where they used to add to the rate. The register's sizes and the channel monitor make this visible; nothing prevents it. The validation runs measure it once (T6).
- **An approximate patch (v10, T1).** The rebase patch scales every non-break branch by one ratio and holds the break value; the non-break branches need not move in proportion. It is labelled. The debt row is exact for the claims as reported, but it does not re-derive the flows.
- **One basis for every business (v10, T2).** Cash flow to equity needs a debt path: a run that holds debt constant, or grows it with the business, makes a financing assumption that an unlevered valuation would not. It is stated and checked, and the debt row shows the size of the debt treatment. Which balances are operating items is the run's call, declared and checked for consistency only.
- **A longer MACHINE SUMMARY (v10, T2, T3, T4).** Five frame fields, the risk register, Walter's grade and Alexander's mapping. Registers of 20–40 entries per run are expected.
- **Fewer independent views (v10, T4).** Seven seats; Simon's trust-adjusted DCF no longer exists as a cross-check.
- **Comparability (v10).** v10 headlines differ from v9's by rate, debt treatment, roster and instructions at once. `OUTCOME_BRIDGE.md` bridges the arithmetic part; the rest is attributed only by the validation runs, on three tickers.
- **Validation cost (v10, T6).** Three extra executions (about 29 subagents each) that add no new ticker to the season.
- **The direction was set with one price in view (v10).** The conversation and debate that chose v10's direction saw ICE's market price beside its v9 BUY. The case for T1 rests on no price (142 of 144 seat rates above the average stock's expected return), and the spec states none; but every adopted change raises ICE's BUY, so ICE is in-sample for any v9-against-v10 comparison of outcomes (Stage 0, Appendix K).
- **The register matches by label (v10, T3).** The script can catch a risk entered twice only under the same name; the same risk under two names is left to critics (C6). Register sizes are the runs' own statements; the BUY effects the monitor derives from them are approximations (a score effect uses π's slope at the seat's score).
- **The rebase scales the +50bp value (v10, T1).** A rebased seat's `fair_value_rf_plus_50bp` moves by the same ratio as its fair value, which understates its rate sensitivity; the rate lever is slightly biased for rebased seats.
- **Price memory is unmeasured (v9, N1).** Runs see the company's name and may remember its price, multiples or later events. The pack-only rule, the no-market-data clause and the redaction lists are the only guard: instructions and redaction, not measurement. An anchor on a remembered price cannot be told apart from valuation skill in the outcome ledger; under v9 it is effectively undetectable. *MELI v8, with masking off, showed no sign of a pull toward the price (review record); one ticker, not a test.*
- **Remembered facts leave no trace (v9, N1, decision C).** A critic can flag a figure or event the pack does not contain, but a run that silently leans on a remembered fact cannot be detected. The rule bars it; nothing measures it.
- **One more value per seat (v9, N2).** Every seat reports `fair_value_alternative_denominator` as one more input-change line.
- **A lever that may dominate (v9, N2).** On a company at a trough margin the alternative-denominator row may be the largest sensitivity. It is reported beside the interval, never in it.
- **A different macro base (v9, N4).** Rebasing the ERP moves the macro base by the source's risk-free rate minus the file's, in either direction: −20bp at 2026-09-10 figures, which would raise v9 headlines against v8's on the same inputs.
- **More checking inside each run (v9, N3).** Runs rebuild every branch and check every tree before writing: a few more script lines and re-runs, in exchange for fewer C4 and C7 findings.
- **Fewer independent views (v8, G2).** The headline always used eight seats, but Victor's and Max's own trees no longer exist as cross-checks. Their methods now run only on the other seats' trees.
- **A continuous premium is not a calibrated one (G1).** The anchors are the old tier constants. G1 removes the cliffs; it does not show that the premium's level is right. The outcome ledger is the test.
- **Three more numbers on the card (G3).** Policy alternatives can be misread as a range. The card labels them, never averages them, and keeps them out of the largest-sensitivity slot.
- **Less printed arithmetic (S1, S2).** Non-base values are stated as input changes. Critics re-derive them from those lines, not from printed schedules.
- **Comparability.** v8 headlines differ from v7.1 by roster and premium. The step-tier line bridges the premium part only.
- **Storage (G5).** Per-run data add about 0.5 MB per ticker (AGX about 540 KB). A capped knowledge base cannot hold a season of them; the data go to file storage and the knowledge base keeps the manifests.
- **Shared-file-system exposure (S3).** On a shared file system a running critic could read a sibling run's verification or redlog. Only instruction stops it; it is logged under P-2. Full pipelining needs isolated file systems.
- **Market data in season storage (G4).** Outcome observations bring prices into durable storage. Their custody (a separate file, outside the executions' storage or sealed, never opened by an execution) is a new integrity duty.
- **A FRAMEWORK that contradicts the instructions (G2, S2; resolved in v10, T5).** Through v9 every subagent read a FRAMEWORK that still described ten investors, entry prices and a schedule for every fair value; Appendix B's Precedence governed. FRAMEWORK_v10 is edited to agree.
- **A shared valuation function (S1).** One function can narrow how differently seats model the business. The Phase-6 groupthink check and the cross-seat fair-value dispersion show whether it does.
- **Disclosure (S2).** Each run writes a mechanics block, break-branch schedules and complete input-change lines, about 30–60 extra lines, in exchange for the non-base schedules it drops.
- **Wider published bands.** Frame variance that v5 hid inside a single shared draw now appears in run noise. This is intended, but the headline will look less precise. Under v7 the interval covers run noise only. The ledger beside it is usually wider. (E5)
- **Fewer confirmed critique findings,** because the "frozen treatment" confirmation route is gone.
- **Only FV and BUY are comparable across runs.** Denominators, tail terms and seat-level figures no longer share a frame. Cross-run comparisons of intermediates are descriptive only.
- **Compute (v7).** A default execution uses: (E5)
  - 8 runs, 8 critiques and 8 verifications;
  - 2 screeners (3 under v7.1: one redaction screener and two tag screeners), 1 auditor, 2 identification probes and 1 writer.

  That is about 30 subagents (31 under v7.1 and v8; 29 under v9 and v10, which have no probes), against 28 on DECK v6. Under v8 and v9 each run values eight seats, not ten; under v10, seven. There are no scorers. At DECK's usage (88–234k tokens per subagent) that is roughly 5–5.5M tokens, plus two bridge runs on the first v7 ticker. Stage 7, if run, doubles the execution.
- **No process-quality weight.** Scorers and the coefficient are gone, so a sloppy but internally consistent run counts fully in the trimmed mean. On DECK the coefficient moved the figure by $0.02–$0.07. Critique findings still correct the number through Stage 5b, and the checklist is recorded. (E5)
- **Runs can now pick a poor frame.**
  - FRAMEWORK rules, verification routes (c) and (d), and checklist items C1/C8 catch *inconsistent* or *rule-breaking* frames.
  - A consistent but unusual frame stands. It shows up as run noise, in the leave-one-out table, and (if trimmed) outside the point estimate.
- **Runs may miss issues a v5 frame would have raised,** e.g. treating acquisitions as a recurring cost. Under v6, whether runs raise such issues unprompted is part of what is measured, and the adjustment ledger shows it.
- **The margin level changes, and tail pricing is risk-neutral.** (E1)
  - At fixed DECK v6 inputs the BUY rises about 8%, and effective margins fall from about 37% to about 31%.
  - The tail term is the break branch's expected loss. Any further aversion to ruin enters only through the quality tier.
  - Every seat now builds a tree of at least four branches: more asserted numbers, though only the break branch reaches the margin.
- **One script carries every number.** (E2)
  - Verifiers emit patch JSON and must run a script.
  - Some fixes become unquantified.
  - The script is a single point of failure. The Stage-0 self-test and the SHA-256 checks are its guard. The script must be maintained with each spec version.
- **A shared market input is a shared frame.** (E4)
  - MARKET_INPUTS removes the risk-free rate from run-to-run dispersion, so its effect can no longer appear in run noise.
  - The rate-lever row (`headline_buy_rf_plus_50bp`) reports that effect instead, and the induced-field check labels it INDUCED.
  - Through v9 the ERP was a convention that runs could depart from, with a reason; v10 closes that route (T1).
- **Default dates are a template convention.** The valuation-date default and the dated share-count rule pass the ticker-swap test, but they move DECK-like BUYs up by roughly 5–10% against v6 (DECK: +$5.7 to +$7.4 mean across runs). v6 and v7 headlines are therefore not comparable without the convention rows. (E4)
- **Stage 7 has limited power.** It detects orchestrator leaks of roughly one drift floor or more (50% at one floor, ~81% at 1.5), not smaller ones, and has a ~8% false-alarm rate.
- **Stage 7 is expensive.** Roughly 56 subagents and 8–10M tokens for the first ticker. It is optional under v7. (E3)
- **Share-count convention is a template rule (v7.1, F1).** Runs no longer choose it, so it cannot appear as run noise or as a frame axis. The induced-field check labels the agreement INDUCED.
- **More fields per seat (v7.1, F4, F5).** Two extra fair values per seat (`fair_value_macro_base` and `fair_value_other_acquisition_basis`) and two declarations. Run output grows somewhat.
- **Margins can rise (v7.1, F5).** Against v7:
  - seats with positive rate add-ons get a larger L, and a lower BUY;
  - seats with negative add-ons (a fair value above the macro-base fair value) get a smaller L, and a higher BUY;
  - AT-CAP seats stay in the average instead of leaving it, which lowers the headline.

  The toolkit's ADBE replay shows the size.
- **Weaker redaction (v7.1, F2).** Crude price proxies that need an assumption now stay in the packs. The no-market-data clause and the memory test were the guard; under v9, the no-market-data clause and the pack-only rule are.
- **Slower method changes (v7.1, F3).** Any script fix needs a new toolkit version and a passing replay before use.
- **Screener count (v7.1, F2).** One redaction screener plus one tag screener per dossier: three screeners at two dossiers.
- **Masking and rescaling (v7; removed in v9, N1).** (E3)
  - **Cost.** Two probe subagents and three scripts per ticker, plus two bridge runs on the first v7 ticker.
  - **Tagging errors reach every run at once.** The completeness, masking and consistency checks, the probe's inconsistency list and the first-ticker bridge are the guard.
  - **Critics lose web fact-checks** of company figures.
  - **Size-dependent judgments.** Scaling company dollar totals can shift judgments that legitimately depend on absolute size, such as size relative to peers. Such shifts appear as βⱼ ≠ 0 and are labelled SCALE-DEPENDENCE, not memory.
  - **Comparability.** v7 packs differ from v6 packs, so v6-to-v7 comparisons are indicative only.

---

## Appendix A — Worked v8 margin example (hypothetical company; not given to any subagent)
A hypothetical seat. Figures are in currency units per share.
- Base-case FV = 50.00. Quality score 80, so the tier label is High Quality. The quality premium (G1) is π(80) = 0.325 + (80 − 67.5) ÷ 15 × (0.225 − 0.325) = 0.24167. (Under the v7.1 step tiers it was 0.225.) The seat's discount rate carries no add-ons, so `fair_value_macro_base` = 50.00.
- Tree:

  | Branch | p | Value |
  |---|---|---|
  | bull | 0.20 | 60 |
  | base | 0.45 | 50 |
  | bear | 0.20 | 42 |
  | break | 0.15 | 20 |

  The base branch is the median: P(V ≥ 50) = 0.65 and P(V ≤ 50) = 0.80.
- Helena's floor = 12. It is below 20, so the break value stays 20.
- L = 1 − 20/`fair_value_macro_base` = 1 − 20/50 = 0.60. p·L = 0.15 × 0.60 = 0.090.
- required = clamp(0.24167 + 0.090, 0.10, 0.60) = 0.33167. BUY = 50 × (1 − 0.33167) = 33.417.
- **With a floor of 28:** the break value becomes 28, L = 0.44, p·L = 0.066, required = 0.30767, BUY = 34.617.
- **Bull and bear branches** do not enter the margin. The quality premium is not the price of the bear branch: here the bear branch's expected loss is 0.20 × 8 ÷ 50 = 3.2pp, against a premium of 24.2pp.
- **With a +200bp seat add-on (v7.1, F5):** suppose the seat's own add-on lowers its FV to 45, while its `fair_value_macro_base` stays 50 and the break value stays 20. The tree's base branch is then 45.
  - L = 1 − 20/50 = 0.60, as before. Under v7 it would have been 1 − 20/45 = 0.556: the add-on lowered the tail term.
  - required = 0.33167; BUY = 45 × 0.66833 = 30.075.
- **A score of 52.5 or below (π = 0.40) with p = 0.25 and L = 0.90:** p·L = 0.225, and 0.40 + 0.225 = 0.625 > 0.60, so the seat is AT CAP (v7.1, F5).
  - required = 0.60, and BUY = FV × 0.40.
  - It stays in the headline with its weight. Under v7 it was NO BUY and dropped out.
- **Margin-rule alternatives (G3), same seat, floor 12:**
  - step tiers: required = 0.225 + 0.090 = 0.315, BUY = 34.25;
  - EV rule ("tuned Victor"): 0.670 × EV, where EV = 0.20 × 60 + 0.45 × 50 + 0.20 × 42 + 0.15 × 20 = 45.9, so BUY = 30.753;
  - expectile rule ("tuned Max"): the P with 0.20(60 − P) + 0.45(50 − P) + 0.20(42 − P) = 7.75 × 0.15(P − 20), i.e. 42.9 − 0.85P = 1.1625P − 23.25, so P = 66.15 ÷ 2.0125 = 32.870, where the implied upside ÷ downside is exactly 7.75;
  - EV × (1 − π), ledger only: 45.9 × (1 − 0.24167) = 34.808.
- **v10: the add-on case rebased (T1).** Under v10 the +200bp add-on above is a route-(d) violation. The `rebase` patch sets FV to `fair_value_macro_base` = 50, multiplies every non-break branch by 50 ÷ 45 (bull 60, base 50, bear 42) and holds the break value at 20: L = 1 − 20/50 = 0.60, required = 0.33167, BUY = 50 × 0.66833 = 33.417, the value of the seat valued at the macro base from the start. The approximation the label names is in the non-break branches, which need not move in proportion.
- **v10: Walter's grade (T4).** The same seat is Walter's, with a balance-sheet add of 0. Components +2, +1, 0, +1, 0, 0: score +4, multiplier 1 + 0.015 × 4 = 1.06, applied to every branch's operating value: bull 63.6, base 53, bear 44.52, break 21.2. `fair_value` = `fair_value_macro_base` = 53; L = 1 − 21.2/53 = 0.60, unchanged by the multiplier; required = 0.33167; BUY = 53 × 0.66833 = 35.422.
- **v10: the debt row (T2).** A seat with FV 50 on cash flow to equity, required 0.33167 and a run whose `net_claims_per_share` is 10. In the debt row every value falls by 10: FV 40 and BUY = 40 × 0.66833 = 26.733, against 33.417 published. The 6.683 between them is the v9 double count T2 removes.

## Appendix B — STAGE2_INSTRUCTIONS template (use verbatim; fill only ⟨TICKER⟩, ⟨UNIT⟩, ⟨PACK⟩ and, if any, the mandate block)

> You are one investment committee valuing ⟨TICKER⟩. Follow FRAMEWORK exactly, running the shortened council: Phase 0 → 1 → 1.5 → 4 → 6, with seven seated investors: Marcus, Sophie, Claire, Graham, Walter, Helena and Alexander.
>
> ⟨IF USER_MANDATE ≠ NONE:⟩ **USER MANDATE (supplied by the user, not the pipeline).** "⟨verbatim text⟩" Apply it. Where it conflicts with a FRAMEWORK valuation default, the mandate governs; say where it does. The mandate never overrides the Inputs and No-market-data rules below.
>
> **Inputs.** Read FRAMEWORK, ⟨PACK⟩ and MARKET_INPUTS, and nothing else.
> - Do not use web, search, or project or knowledge-base tools.
> - Use only the facts and reported figures in ⟨PACK⟩ and MARKET_INPUTS, and the rules and constants in FRAMEWORK and these instructions. Your assumptions (growth, margins, probabilities, branch and terminal values, the debt path, the risks you price and their sizes) are your own judgments: state each as an assumption and justify it from ⟨PACK⟩, never from a fact you remember. If something you want is not there, say so and proceed without it.
> - Some figures may have been redacted. Treat a redaction as missing data.
> - In these instructions ⟨TICKER⟩ means the company ⟨PACK⟩ describes. ⟨PACK⟩ names it, and you may recognise it. That changes nothing: do not use any remembered price, market value, multiple or analyst target, or any other remembered observation about the company, its peers, its industry or its countries that ⟨PACK⟩ does not contain (for example a figure, a market share, a regulatory change, a macro data point, or an event after ⟨PACK⟩'s as-of date). Cite ⟨PACK⟩ for every fact a seat input rests on; a premise without a citation is an assumption and is labelled as one. Value the company from ⟨PACK⟩ and MARKET_INPUTS alone.
>
> **No market data.** You are given no market price, market capitalisation, enterprise value or multiple for ⟨TICKER⟩, and you must not use one you remember. Do not derive or estimate one, including by combining figures in ⟨PACK⟩. Your BUY is built bottom-up.
>
> **Precedence.** FRAMEWORK and these instructions are written to agree. If you find a difference, these instructions govern: the committee is the seven seated investors, no seat produces an entry price, every seat discounts at the macro base, and the margin is the one below. A seat whose framework uses a required return or hurdle sets it equal to the macro base, converts it to a fair value and applies the margin below. FRAMEWORK's Downside check compares Helena's floor with every seat's break-branch value; the Floor rule below applies it. Rule 5 is met as stated under Mechanics.
>
> **Phase 0 is yours.** Nothing about this company has been decided for you. The only pipeline-supplied inputs are MARKET_INPUTS, the default valuation date and the share-count, acquisition, alternative-denominator, rate and debt rules below, and all are identical for every company. As moderator, choose, state and justify each of the following:
> - the declared denominator (Rule 1) and its basis period.
>   - Build value on company totals, and convert it to per share once, with the per-share count below.
>   - `denominator_count_m`, the count you divide the company-total denominator by to state it per share, must equal that per-share count.
>   - Do not add buyback accretion to per-share growth. Project company totals.
>   - Also report the period-weighted diluted count for the basis period (`period_weighted_count_m`), if ⟨PACK⟩ gives one, for reference only;
> - the valuation date. It is ⟨PACK⟩'s as-of date unless you justify another. State how the cash flows in your schedules are timed relative to it;
> - the share count used to convert value to per share, with its date.
>   - Use the latest diluted count in ⟨PACK⟩ on or before the valuation date: a reported diluted count, or a basic count plus the dilutive securities ⟨PACK⟩ reports. If ⟨PACK⟩ gives only weighted-average counts, use the one for the shortest latest period it reports (for example the latest quarter, not a fiscal year), dated at that period's end, and set `per_share_count_basis` to "period" (otherwise "point").
>   - If that count is not dated at the valuation date or at the date of the balance-sheet amounts you add to or subtract from value, state the headline at the other end of the bracket.
>   - Also report the latest dated diluted share count in ⟨PACK⟩ and its date (`latest_share_count_m`, on the same diluted basis);
> - the date of every balance-sheet amount you add to or subtract from value, and their total per share;
> - cash flow to equity, with debt counted once. Every seat values the cash flow to common equity: after interest (net of any interest income you keep in the flow), preferred dividends, distributions to minority interests, lease payments, and the net borrowing or repayment your debt path implies.
>   - Deduct no debt, preferred, minority or lease claim from value: the flow has already paid them. Report `debt_deducted_per_share` = 0. Add a balance-sheet asset (for example surplus cash or investments) only if its income is not already in the cash flow.
>   - Operating balances (balances held for customers or required to operate the business) are operating items: their flows stay in the cash flow, and they are neither added to nor deducted from value.
>   - State the debt path your flows assume (for example held constant, repaid on schedule, growing with the business) and its source in ⟨PACK⟩, how interest income is treated, and that lease payments stay in the flow. If your gross source is before interest (for example EBITDA or operating income), deduct after-tax interest at a stated rate as a listed `denominator_adjustments` item.
>   - Report `net_claims_per_share`: debt + preferred stock + minority interests − cash, per share, from the balance sheet at the balance-sheet date (negative for net cash). It is reported for a ledger row only and is never deducted;
> - the systematic risk class (`systematic_risk_class`): defensive, average or cyclical, with one line of reason from ⟨PACK⟩ (how revenue and cash flow moved in the downturns ⟨PACK⟩ covers; operating and financial leverage). It is descriptive only: it moves no number, and no seat prices it;
> - the pack line or lines your denominator starts from (the gross source);
> - every adjustment you make between that gross figure and the declared denominator (what, $ per share, and why), or an explicit statement that you make none;
> - acquisitions:
>   - the company's cash paid for acquisitions in each year in ⟨PACK⟩, for up to the last five years;
>   - your normalised annual acquisition spend: by default the total ÷ the number of years, per share, with the ⟨PACK⟩ lines and the window. You may exclude or reweight a deal within the window if you state why;
>   - shares issued as acquisition consideration, if ⟨PACK⟩ reports any: they are part of the acquisitions' cost. Either include them in the per-share count or state the dilution;
>   - any acquisition closed within the basis period, with the number of months it contributes to the base.
>
>   If ⟨PACK⟩ gives no acquisition cash, write "no acquisition cash in ⟨PACK⟩" and use 0;
> - the alternative denominator: the one you judge the most reasonable alternative to the declared denominator.
>   - It has the same definition as the declared denominator: the same gross line or lines and the same kinds of adjustment, each re-measured for the alternative (state each amount). A one-off item removed from the basis period is not carried into a period or margin it does not belong to. `alternative_denominator_type` repeats `denominator_type`.
>   - It differs only in the period it is measured over (longer, shorter or different) or in the margin applied to the basis-period revenue (higher or lower than the declared denominator's; state and justify it from ⟨PACK⟩). Set `alternative_denominator_basis` to "margin" whenever the margin differs, otherwise "period".
>   - State what differs and why, its value per share, and whether your seats' base paths already assume a move toward it. Every seat values it (`fair_value_alternative_denominator`, Mechanics).
>   - If the declared denominator is zero or negative, or the alternative would differ from it in sign, use "none". Where the denominator nets out investment that scales with growth (for example loan-book growth or working capital inside operating cash flow), prefer a period alternative; a margin alternative states the growth rate its investment line assumes, which equals the base branch's.
>   - If you judge no alternative reasonable, say why and set `alternative_denominator_basis` to "none", `alternative_denominator_per_share` equal to `declared_denominator_per_share`, and every seat's `fair_value_alternative_denominator` equal to its `fair_value` (no input-change line);
> - the macro base. Take the risk-free rate from MARKET_INPUTS and the ERP from MARKET_INPUTS (its first figure, the rebased premium; the source's own figure is shown for the record and is not an alternative). Their sum is the macro base, and it is every seat's discount rate (Margin). Where ⟨PACK⟩ carries a different macro figure, MARKET_INPUTS governs;
> - the business-type classification;
> - the framework weights (0–2.0 per seated investor);
> - the peer set, drawn only from peers in ⟨PACK⟩, if any;
> - the optionality screen;
> - your reading of management's guidance credibility, citing ⟨PACK⟩.
>
> **Margin.** For each investor:
> - **Discount rate.** Every seat discounts at the macro base, with no add-on and no credit for any risk: `discount_rate` = `macro_base`. `fair_value_macro_base` is the seat's base-case value recomputed with its discount rate set to the macro base and everything else unchanged; a seat that follows this rule reports it equal to `fair_value`, and a seat that used any other rate reports its value at the macro base here, never a copy of its own fair value. A seat whose framework builds a required return (for example Graham's or Marcus's) shows it equal to the macro base. Risks are priced in the channels of the risk register below, never in the rate.
> - **Tree.** Build your own probability tree on your own base case, with probabilities summing to 1. It has at least four branches:
>   - a base branch, whose value is your base-case fair value (the tree's median);
>   - at least one upside branch;
>   - at least one non-break downside branch;
>   - the break branch (Rule 4), which is the lowest-valued branch.
>
>   Show how every branch value is derived. An upside branch must be identifiable and cite ⟨PACK⟩. Give every branch a name that is unique within your tree (for example `bear_1`, `bear_2`). Exactly one branch is named `base` and exactly one `break`.
> - **Break probability, derived in three steps:**
>   1. the break mechanism, in one sentence;
>   2. a reference frequency with its ⟨PACK⟩ citation (how often comparable franchises, segments or products named in ⟨PACK⟩ have broken over a stated period), or the words "no reference in ⟨PACK⟩". State the reference frequency and your break probability over the same horizon, in years (`horizon_years`);
>   3. your adjustment from that reference, in pp, with its reason.
>
>   A seat at the 10% minimum states why the break is no likelier than that.
> - **Floor.** Only Helena computes the committee floor. She works in ⟨UNIT⟩, from ⟨PACK⟩ balance-sheet lines, counting only assets that are real and collectible, net of all liabilities, or she reports none. Every branch value below Helena's floor is raised to it (this changes the margin only through the break branch). No other seat claims a floor.
> - **Tail term.** `p` = your break-branch probability. `L` = 1 − (break-branch value after Helena's floor) ÷ `fair_value_macro_base`, floored at 0. `fair_value_macro_base` is defined under Discount rate. `tail_term = p × L`.
> - **Required margin.** `required = clamp(π(score) + tail_term, 0.10, 0.60)`. π is the quality premium. It is 0.40 at a quality score of 52.5 or below and 0.125 at 95 or above; in between, it is linear between the neighbouring points (52.5, 0.40), (67.5, 0.325), (82.5, 0.225) and (95, 0.125). For example, π(80) = 0.325 + (80 − 67.5) ÷ 15 × (0.225 − 0.325) = 0.24167. Report π to four decimals as `quality_premium`. State in one line what your quality score is built from. Also state the tier your score falls in under FRAMEWORK's tier table, as a label (Rule 8). If Rule 8 moves a seat's tier, re-derive that seat's score and state the old and new score with the reason; a move with no re-derivation sets the score to the new tier's nearest edge (60, 75 or 90 moving up; 59.9, 74.9 or 89.9 moving down).
>   - If `π(score) + tail_term` exceeds 0.60 before clamping, the seat is AT CAP: required = 0.60. It stays in the headline with its weight. Report `at_cap` = true.
>   - `BUY = fair_value × (1 − required)`.
>   - A seat is NO BUY only under a FRAMEWORK uninvestability rule (for example, two FAILs among Walter's gates). Name the rule in `no_buy_reason_or_null`. A NO-BUY seat has no BUY; it is excluded from the headline and its weight is dropped.
> - **What each part prices.** The tail term prices the break branch, once. The quality premium is a margin for estimation error and risk aversion, graded by business quality, on top of the tree's expected loss; it is not derived from any branch. Upside branches and non-break downside branches are reported in the tree but never netted into the margin, because they largely offset around the base. No committee statistic and no other seat's tree enters your margin.
> - **Risk register (Rule 3).** Each seat lists every risk it considers, and every upside driver behind a branch above its base, once, in one channel, with a signed size (the change the item makes to that channel's quantity):
>   - `base_cash_flows`: an expected drag (or lift) on the base path (probability × impact), sized as the change in the seat's fair value in ⟨UNIT⟩ (negative for a drag). A base-case haircut must name such a drag; a haircut for generic uncertainty or volatility is not allowed. FRAMEWORK's guidance default (management a bit too optimistic) is entered here, by name and size, where you apply it;
>   - `break_branch`: the item is the break mechanism or part of it, sized as its part of the seat's tail term, in pp of p·L (positive: it adds to the tail);
>   - `quality_score`: a named quality dimension, with its evidence in ⟨PACK⟩, sized as the points it moves the quality score (negative for a cut). A cut for generic uncertainty, with no named dimension, is a generic haircut and is not allowed;
>   - `fv_mapping`: only Walter's management grade and Alexander's earnings-quality adjustment, sized as the % change in fair value the mapping makes;
>   - `non_break_branch`: the item is carried by a non-break branch of the tree (a downside or an upside branch), sized as its effect on the tree's expected value in ⟨UNIT⟩ (branch probability × its value against the base; negative for a downside). These branches are reported and never reach the margin, by design, because downside and upside largely offset around the base;
>   - `not_priced`, with a reason (for example: immaterial, or already in the reported figures).
>
>   Every item behind a non-break branch whose expected-value effect exceeds 1% of the seat's fair value, downside or upside, must be in the register (as `non_break_branch`, or in a channel above if you price it there); leaving it out is a violation. Nothing is moved into the margin by this rule. The same item in two channels for one seat is a double count; the break event's own risk belongs to `break_branch` only. Market-wide exposure (financial leverage, operating leverage, cyclicality) is entered only through its effect on this company's cash flows, break branch or a named quality dimension, never as a premium of its own.
> - **Seat mappings (FRAMEWORK, THE COMMITTEE).**
>   - **Walter's grade.** Six components, each an integer from −2 to +2 and each derived from ⟨PACK⟩ and 0 where ⟨PACK⟩ is silent: capital allocation; trust and guidance; incentive alignment; insider transactions; board governance; five-year operating returns (ROIC or ROE, from ⟨PACK⟩) against the sector, never stock returns. Four gates, each PASS, CAUTION or FAIL by FRAMEWORK's criteria (PASS where ⟨PACK⟩ shows none of them): trust; incentive alignment; board governance; capital-structure distress. A CAUTION caps the matching component at −1 and a FAIL at −2 (trust → trust and guidance; incentive alignment → incentive alignment; board governance → board governance; capital-structure distress → capital allocation). Score = the sum (−12 to +12); multiplier = 1 + 0.015 × score (0.82 to 1.18). Two or more FAILs make Walter's seat NO BUY (name the rule); no other NO BUY exists. Preferred stock is a claim the cash flow to equity pays (Phase 0); it enters the grade only as evidence of distress under the capital-structure gate's criteria, never as such.
>   - **Alexander's earnings quality.** The FRAMEWORK score (0–100) and its mapping: above 80, +10%; 60 to 80, 0%; below 60, −15%.
>   - **Applying a mapping.** The seat values each branch's operating value (before the balance-sheet amount) with the shared function, multiplies it by its mapping (Walter: the multiplier; Alexander: 1 + the adjustment), then adds the balance-sheet amount. Every branch, `fair_value_macro_base`, `fair_value_rf_plus_50bp`, `fair_value_other_acquisition_basis` and `fair_value_alternative_denominator` carry the same mapping.
>   - **Mapped dimensions.** Walter's quality score leaves out management, governance and the operating-returns record, and Alexander's leaves out earnings quality, including the goodwill share of assets: their mappings price those dimensions.
>
> **Acquisitions.** For each investor:
> - `growth_basis`: "organic" if its growth inputs exclude growth bought through acquisitions, "including_acquisitions" otherwise;
> - `acq_spend_deducted`: true if its cash flows deduct the Phase-0 normalised acquisition spend;
> - the two must match: organic growth with no deduction, or growth including acquisitions with the deduction. If ⟨PACK⟩ gives no organic/acquired split, say so and state how you separated them;
> - `fair_value_other_acquisition_basis`: the seat's fair value under the other matched treatment, everything else unchanged. If the seat is mismatched, report instead its value under the matched treatment of its own growth basis;
> - if ⟨PACK⟩ gives no acquisition cash and reports no shares issued as acquisition consideration (normalised spend 0), use "organic" with no deduction for every seat. Any pair then counts as matched, because the deduction is 0 either way, and `fair_value_other_acquisition_basis` is the seat's value with acquired growth included, which equals `fair_value` when ⟨PACK⟩ shows no acquired growth.
>
> **Mechanics.**
> - **One committee script.** Do all arithmetic in Python, in one script in your scratch folder: one shared valuation function (helpers it calls are fine), and one table holding every seat's inputs and each branch's input changes. A seat's own method (a closed form, a grade or a quality adjustment) is an input or a step inside that function, not a separate script. Run it, check the output against this block, and fix and re-run until every check passes. Before the output is written, the script itself also checks every seat's tree. It prints each input-change line from the code, listing every input of that branch (or extra fair value) whose value differs from the base branch's, and rebuilds the value by calling the valuation function on the base inputs updated with exactly the printed changes; the result must match within 0.5%. It then checks: branch names unique, with exactly one `base` and one `break`; probabilities summing to 1 within 0.005; the base branch equal to `fair_value` within 0.1%; the base branch the tree's median (P(V ≥ base) ≥ 0.5 and P(V ≤ base) ≥ 0.5); and the break branch the lowest-valued branch. If a check fails, fix the branch values or the tree's shape and re-run; do not change `break_p` only to pass a check. Write your output file in one pass from the script's printed tables. Do not split the work into one script or file per seat, per step or per section.
> - **Schedules (Rule 5).** State your valuation function's mechanics once, as formulas: how each year's cash flow is built from the seat inputs; timing and discounting, including any stub period; the terminal method and formula; the per-share conversion and balance-sheet add; and any seat adjustment applied after the function. Show the year-by-year schedule of every seat's base branch and break branch. A break value not computed by the function is shown as its formula, with every input and its ⟨PACK⟩ citation. For every other branch, for `fair_value_rf_plus_50bp`, `fair_value_other_acquisition_basis` and `fair_value_alternative_denominator`, and for every other value a seat reports from its DCF (for example a rate or growth sensitivity), give one line listing every input that differs from the base branch with its full value (a path as all its year values; the discount rate; terminal growth and any other terminal parameter; any change of terminal method; the starting cash flow or margin; the acquisition deduction per share), then the resulting value. The line must reproduce the value with the stated mechanics to within 0.5%; such a line meets Rule 5.
> - Every seat reports its tree as specified under Margin. The break branch is ≥10% (Rule 4). Report each seat's `break_p`, `break_loss` (after Helena's floor), its three-step derivation, and `tail_term`.
> - Every seat's discount rate is the macro base (Margin).
> - For every seat, also report its fair value recomputed with its discount rate +50bp and everything else unchanged (`fair_value_rf_plus_50bp`), its `fair_value_macro_base` (defined under Margin) and `fair_value_other_acquisition_basis` (Acquisitions), and `fair_value_alternative_denominator`: its base-branch fair value with every forecast cash flow before any acquisition-spend deduction multiplied by alternative ÷ declared (the Phase-0 alternative over the declared denominator; for a path built as revenue × margin, every year's margin, including any steps, multiplied by that ratio), and every growth rate, discount rate and terminal parameter of the base branch held as stated. Change no other input. A seat whose value does not start from the denominator (for example an asset-based value) reports its `fair_value` unchanged and says so.
> - For every seat, report the first five forecast periods of its base branch (`forecast_5y`): for each, `period_end` (YYYY-MM-DD), `months`, and the cash flow the schedule discounts, as a company total in ⟨PACK⟩'s currency unit (`cash_flow_total`) and per share at the per-share count (`cash_flow_per_share`), before any acquisition-spend deduction and before the net borrowing or repayment in your debt path (state that amount in `forecast_definition`). Also report `forecast_definition`: the ⟨PACK⟩ lines and adjustments that turn reported figures into that cash flow, so it can be recomputed from a later annual report. A closed-form seat reports the cash flows its formula implies.
> - `headline_buy` = Σ(wᵢ·buyᵢ)/Σwᵢ over the seven seated investors, using YOUR Phase-0 weights. An AT-CAP seat is included at required = 0.60. A NO-BUY seat (FRAMEWORK uninvestability only) is excluded and its weight dropped.
>
> **Output.** Write your full analysis, with your Phase-6 summary under the heading `## PHASE 6`, ending with `## MACHINE SUMMARY` containing valid JSON:
> ```
> {"ticker","unit",
>  "frame":{"denominator_type","gross_source","basis_period","denominator_count_m","period_weighted_count_m",
>           "pack_as_of_date","valuation_date","per_share_count_m","per_share_count_date","per_share_count_basis":"point|period",
>           "latest_share_count_m","latest_share_count_date","balance_sheet_date","balance_sheet_add_per_share",
>           "gross_denominator_per_share","denominator_adjustments":[{"item","per_share","reason"}],
>           "declared_denominator_per_share",
>           "acq_cash_by_year":[{"year","amount"}],"acq_spend_normalised_per_share","acq_spend_window","recent_acquisitions":[{"name","close_date","months_in_basis_period"}],
>           "alternative_denominator_type","alternative_denominator_basis":"period|margin|none","alternative_denominator_per_share",
>           "debt_deducted_per_share","net_claims_per_share","debt_path","interest_income_treatment","lease_treatment",
>           "systematic_risk_class":"defensive|average|cyclical","systematic_risk_reason",
>           "risk_free","erp","macro_base","market_inputs_as_of",
>           "business_type","guidance_stance":"credit|neutral|skeptical",
>           "weights":{investor:weight,...},
>           "peers_used":[...]},
>  "helena_floor":{"floor_type","floor_per_share_or_null","pack_lines":[...]},
>  "investors":[{"investor","fair_value","quality_score","quality_tier","discount_rate","fair_value_rf_plus_50bp","fair_value_macro_base","terminal_growth",
>                "growth_basis":"organic|including_acquisitions","acq_spend_deducted":true/false,"fair_value_other_acquisition_basis",
>                "fair_value_alternative_denominator",
>                "tree":[{"branch":"base|break|<unique name>","p","value"}],
>                "break_p","break_loss","break_derivation":{"mechanism","reference","adjustment_pp","horizon_years"},
>                "tail_term","quality_premium","required_margin","buy","at_cap":true/false,"no_buy":true/false,"no_buy_reason_or_null",
>                "forecast_definition","forecast_5y":[{"period_end","months","cash_flow_total","cash_flow_per_share"}],
>                "management_grade":{"components":{"capital_allocation","trust_guidance","incentive_alignment","insider_transactions","board_governance","returns_vs_sector"},
>                                    "gates":{"trust","incentive_alignment","board_governance","capital_structure"},"score","multiplier"},
>                "earnings_quality":{"score","adjustment"}}],
>  "risks":[{"risk","seat","channel":"base_cash_flows|break_branch|quality_score|fv_mapping|non_break_branch|not_priced","size","reason_or_null"}],
>  "committee_median_fv","quality_tier_modal":"Exceptional|High Quality|Average|Below Average","headline_buy"}
> ```
> - Use decimals for margins, the quality premium, tree probabilities, `break_p`, `break_loss` and `tail_term` (0.325). Tree values, fair values, floors and every `…_per_share` field (including `cash_flow_per_share`) are in ⟨UNIT⟩. `acq_cash_by_year` amounts and `cash_flow_total` are company totals in the pack's currency unit. `months_in_basis_period` is a number of months.
> - Use percents for rates and growth (9.5).
> - `management_grade` is Walter's only and `earnings_quality` Alexander's only; other seats omit them. Gates are "PASS", "CAUTION" or "FAIL"; `adjustment` is a decimal (0.10, 0, −0.15).
> - In `risks`, `seat` is an investor's name; `size` is in ⟨UNIT⟩ for `base_cash_flows` and `non_break_branch`, pp of p·L for `break_branch`, score points for `quality_score` and percent of fair value for `fv_mapping` (signed as each channel states), and null for `not_priced`, which gives `reason_or_null`. List each seat's items separately, even when seats share one, and name a shared item the same way for every seat.
> - `debt_deducted_per_share` and `net_claims_per_share` are in ⟨UNIT⟩; `debt_deducted_per_share` is 0 under these instructions; `net_claims_per_share` is signed (net cash negative).
> - Give dates as YYYY-MM-DD. Share counts are in millions. `balance_sheet_add_per_share` is in ⟨UNIT⟩ and signed: non-operating assets whose income is not in the cash flow, less any non-claim liability the flow does not pay (for example an unfunded pension); never a debt, preferred, minority or lease claim.
> - `gross_denominator_per_share` + Σ `denominator_adjustments.per_share` must equal `declared_denominator_per_share`.
>
> Return only the file path and the JSON.

## Appendix C — Critic checklist (ticker-generic; unscored)

**Scope rule.** Each criterion is judged only from the presence, consistency and quality of derivations. **No criterion may reward or penalise *which* frame choice a run made, or the size or direction of its BUY.** The critic applies this checklist with FRAMEWORK, the run file, the run's pack and STAGE2_INSTRUCTIONS.

**How to read it.**
- "1.0 if" means **met**.
- Each deduction ("−0.x for each …") names one kind of **miss**.
- "0.5" and "0.0" name misses of increasing severity.
- No number is computed from the checklist, and it weights nothing.
- For each of C1–C8, report "met" or "not met", with every miss listed and its location in the run.

- **C1 — Denominator discipline (Rule 1).**
  - **1.0:** all of the following hold:
    - one denominator is declared in Phase 0 and used for every FV and for the comparable check;
    - its gross source is named and matches the pack;
    - value is built on company totals and converted to per share once, with the latest dated diluted count (dated at the valuation date or at the date of the balance-sheet amounts added to value, or with a stated bracket; a shortest-latest-period count is acceptable when declared with `per_share_count_basis` "period"); `denominator_count_m` equals that count; each balance-sheet amount is dated; a period-weighted count appears only as history or reference;
    - the Phase-0 acquisition spend is stated with its pack lines (or "no acquisition cash in pack"), and every seat's `growth_basis` and `acq_spend_deducted` match;
    - every adjustment is listed with $/share and a reason, and the listed adjustments reconcile gross to declared;
    - SBC is treated as a cost (FRAMEWORK Phase 0.A);
    - the cash flow is to equity and debt is counted once: no debt, preferred, minority or lease claim deducted from value; no asset added whose income is in the flow; operating balances kept in the flow; the debt path, interest income and leases stated; `net_claims_per_share` reported;
    - the alternative denominator is shown on the same definition as the declared one, differing only in its period or the margin applied to the basis-period revenue, with what differs and why, and every seat values it as STAGE2_INSTRUCTIONS defines; or "none" with a reason;
    - any peers are converted to the declared basis.
  - **0.5:** one of those elements is missing.
  - **0.0:** any of: two denominators for one FV; mixed periods within the denominator; a denominator count that differs from the per-share count; an undated per-share count or balance-sheet amount; SBC excluded as a cost; a gross source that does not match the pack; adjustments that do not reconcile; a seat whose growth includes acquisitions with no acquisition spend deducted, or the reverse; cash flows after interest (levered) with debt also deducted, or any other count of debt twice.
  - A margin measured over stated periods and applied to basis-period revenue is a normalised margin, not mixed periods.
- **C2 — One rate (Rule 2).**
  - 1.0 if every seat's discount rate equals the macro base (MARKET_INPUTS' risk-free rate plus its rebased ERP), and every seat's `fair_value_macro_base` equals its `fair_value`.
  - −0.2 for each seat whose rate is not the macro base, including a credit below it; a required return or hurdle set above or below the macro base counts the same.
- **C3 — Real tail and two-sided events (Rules 4, 9).**
  - 1.0 if every tree has a break branch of ≥10%, and every event that can resolve negatively is modelled with both tails.
  - Guidance is treated per the FRAMEWORK default (a bit too optimistic), unless the run *shows from the pack* a documented history of beats or sandbagging.
  - −0.25 for each violation.
- **C4 — Visible schedules (Rule 5, as STAGE2_INSTRUCTIONS states it).**
  - 1.0 if the mechanics are stated; every base-branch and break-branch value shows a year-by-year schedule, an explicit closed-form derivation or (break only) its formula with cited inputs; and every other branch value, extra fair value and reported DCF value shows its input changes, complete enough to reproduce it with the stated mechanics to within 0.5%.
  - −0.2 for each unsupported value. A value that cannot be reproduced from its line is unsupported.
- **C5 — Roster, seat mappings and comparability (Rule 6).**
  - 1.0 if the committee is the seven seated investors; every seat's BUY is its fair value × (1 − required); Walter's grade has six components from −2 to +2 (0 where the pack is silent), each gate follows its FRAMEWORK criteria and caps its component, its multiplier is 1 + 0.015 × score, two or more FAILs make his seat NO BUY, and preferred stock as such is not in it; Alexander's adjustment follows the FRAMEWORK mapping; and each mapping is applied to every branch's operating value.
  - −0.2 for each mapping violation.
  - 0.5 if a seat outside the roster is reported but kept out of the headline.
  - 0.0 if an entry price or a seat outside the roster enters the headline.
- **C6 — One-channel pricing and tier gate (Rules 3, 8).**
  - 1.0 if all of the following hold:
    - the risk × investor matrix is present, and the MACHINE SUMMARY's `risks` register lists, for every seat, every risk the seat's analysis prices or discusses and every upside driver behind a branch above its base, each with one channel and a signed size (or "not priced" with a reason);
    - no risk is priced in two channels for one seat (a double count), including through the rate;
    - nothing is left out: an item behind a non-break branch (downside or upside) whose expected-value effect exceeds 1% of the seat's fair value and that is not in the register is a miss (registering it is enough; it need not be priced);
    - no generic haircut: every base-case haircut names a specific expected drag, and every quality-score cut names a quality dimension;
    - the mapped-dimension rule holds: Walter's quality score leaves out management, governance and the operating-returns record, and Alexander's leaves out earnings quality (including the goodwill share of assets);
    - Rule 8 is resolved;
    - the committee floor is set by Helena alone, computed from pack balance-sheet lines net of liabilities (or reported as none);
    - no other seat claims a floor.
  - −0.2 for each violation.
  - **Rule-3 reading (v10):**
    - The pricing channels are the base-case cash flows, the break branch (tail term), the quality score (quality premium) and a seat's fixed fair-value mapping; a non-break branch is a registered location, not a pricing channel. The discount rate is not a channel.
    - A cash-flow haircut or score cut that names the break event itself, combined with the tail term on that same event, is a double count.
    - An item sized in the register at a size its seat's numbers do not show (for example a base-path drag on a path that the analysis does not lower) is a miss.
    - Register entries are matched by meaning, not by label: the same risk under two names in two channels for one seat is a double count.
- **C7 — Tree and tail discipline (v7).**
  - 1.0 if, for every seat, all of the following hold:
    - a tree of at least four branches is shown, with derived branch values;
    - the base branch equals the seat's FV and is the tree's median;
    - the break branch is the lowest-valued branch, and branch names are unique;
    - the tier label matches the quality score, the score's basis is stated (and re-derived after any Rule-8 move), and the quality premium is π(score) as STAGE2_INSTRUCTIONS defines it;
    - `break_p` states its horizon in years;
    - `break_p` has the three-step derivation (mechanism; pack-cited reference or "no reference in pack"; adjustment);
    - `break_loss` applies Helena's floor;
    - the margin is shown as π(score) + p·L with the exact arithmetic, with L measured against `fair_value_macro_base`, and a seat over 0.60 shown AT CAP, not dropped;
    - no upside or non-break branch is netted into the margin.
  - −0.15 for each violation. A seat with no tree is one violation.
- **C8 — Frame declaration.**
  - 1.0 if every field of the `frame` block is filled, including `gross_source` and `denominator_adjustments` (an empty list is valid if stated), each choice is justified in Phase 0 with pack citations, and every seat reports `forecast_definition` and five complete `forecast_5y` periods.
  - −0.1 for each missing or unjustified field.
  - Justification quality is judged; the choice itself is not.

## Appendix D — Ticker-neutral Rule-10 example (built into FRAMEWORK_v10; through v9 it replaced the FRAMEWORK original in the Stage-1 copy)
> Example: "Regional same-store sales growth falls below 0% for two consecutive quarters → cut near-term growth to 2% → BUY moves down ≥15%."

*(Illustrative only. It names no KPI tied to any specific company, and states no discount rate and no dollar BUY. From v10 it is FRAMEWORK_v10's own Rule-10 example, and Stage 1 copies FRAMEWORK unchanged (T5).)*

## Appendix E — Critic prompt template (use verbatim; fill only ⟨TICKER⟩, ⟨UNIT⟩, ⟨RUN⟩, ⟨PACK⟩, ⟨OUT⟩, ⟨SCRATCH⟩ and, if any, the mandate block)

> You are an independent critic of ONE valuation of ⟨TICKER⟩. Read ⟨RUN⟩, ⟨PACK⟩, STAGE2_INSTRUCTIONS, CHECKLIST, MARKET_INPUTS and FRAMEWORK in full, and nothing else on this machine. Do not use project or knowledge-base tools. STAGE2_INSTRUCTIONS contains the rules the run was required to follow. Its margin arithmetic is pre-registered and governs over FRAMEWORK's margin table: a margin produced by that arithmetic is not an error, even outside a FRAMEWORK band. Its margin governs over FRAMEWORK's margin text too, and its roster (seven seated investors, no entry prices), its rate rule (every seat at the macro base) and its schedule rule (Mechanics) likewise govern over FRAMEWORK, which is written to agree with them.
>
> ⟨IF USER_MANDATE ≠ NONE:⟩ **USER MANDATE (supplied by the user, not the pipeline).** "⟨verbatim text⟩" The run was required to apply it.
>
> **Task.**
> - Re-derive in Python, using the STAGE2_INSTRUCTIONS arithmetic and the run's stated mechanics, every base-branch and break-branch schedule, every other value from its stated input changes, and every tree, break derivation, tail term, margin and the headline. Put your scripts in ⟨SCRATCH⟩.
> - If a value cannot be reproduced from its line, report RULE-VIOLATION (Rule 5 as STAGE2_INSTRUCTIONS states it), with the inputs you tried. Propose a patch only if the run's own stated inputs and mechanics give a different value.
> - Check every pack figure the run uses against ⟨PACK⟩, including its gross source, and every macro figure against MARKET_INPUTS.
> - Check that the run's `denominator_adjustments` reconcile gross to declared, and that every seat uses the declared frame.
> - Check `denominator_count_m` against `per_share_count_m`. The script normalises any difference itself, so report one as a finding with no fix. Check each seat's `growth_basis`, `acq_spend_deducted` and `fair_value_other_acquisition_basis` against STAGE2_INSTRUCTIONS. Where ⟨PACK⟩ gives no acquisition cash and reports no shares issued as acquisition consideration, no pair is a mismatch.
> - Check the alternative denominator against STAGE2_INSTRUCTIONS (the same definition as the declared one, differing only in its period or the margin applied to the basis-period revenue; or "none" with a reason), and every seat's `fair_value_alternative_denominator` line.
> - Check that every seat's discount rate is the macro base. Report any seat whose rate is not, with its rate and its `fair_value_macro_base`, as RULE-VIOLATION (STAGE2_INSTRUCTIONS, Margin).
> - Check the debt treatment: whether the starting cash flow is after interest, against ⟨PACK⟩ (a pre-interest source needs a listed after-tax interest item); that no debt, preferred, minority or lease claim is deducted from value and no asset is added whose income is in the flow; the debt path; and `net_claims_per_share` against the balance sheet. A claim deducted from cash flow to equity is RULE-VIOLATION (STAGE2_INSTRUCTIONS, Phase 0).
> - Check the risk register against the analysis: every risk each seat prices or discusses is in it, once, in one channel, at a size its numbers show; every item behind a non-break branch, downside or upside, above 1% of the seat's fair value is in the register (registering is enough); no base-case haircut is generic; Walter's and Alexander's quality scores leave out their mapped dimensions. Check Walter's grade, gates and multiplier and Alexander's mapping, and that each is applied to every branch.
> - List each factual premise behind a growth, margin, break or register input that carries no ⟨PACK⟩ citation, and check it against ⟨PACK⟩.
>
> **Web and memory.** Do not use the web. In these instructions ⟨TICKER⟩ means the company ⟨PACK⟩ describes; ⟨PACK⟩ names it, and you may recognise it. Do not state or infer its share price, market capitalisation, enterprise value, trading multiples or analyst targets. Judge the run against ⟨PACK⟩ and MARKET_INPUTS only: a fact you remember that ⟨PACK⟩ does not contain is not evidence.
> - If a finding needs such a fact, tag it PACK-GAP and name the missing item by its kind and period (for example "segment revenue, latest quarter"). Do not state, estimate or use any value you remember for it; quantify a PACK-GAP, if at all, only as a stated hypothetical range.
> - If the run presents as fact a specific observation about the company, its peers, its industry or its countries that neither ⟨PACK⟩ nor MARKET_INPUTS contains (a reported or historical figure, a price or multiple, an event after ⟨PACK⟩'s as-of date), report RULE-VIOLATION (STAGE2_INSTRUCTIONS, Inputs), quoting the run.
> - A stated and justified assumption is not such a fact: a disagreement with its level is FRAME-JUDGMENT. Rules and constants from FRAMEWORK or STAGE2_INSTRUCTIONS are not such facts.
>
> **Findings.** Number them, ranked by materiality. For each finding, give:
> - **Tag 1:** SPECIFIC or TRANSFERABLE.
> - **Tag 2**, one of:
>   - ARITHMETIC;
>   - PACK-CONTRADICTION (the run versus its own pack);
>   - FRAME-INCONSISTENCY (the run versus its own declared frame);
>   - RULE-VIOLATION (an explicit rule as listed for verification route (d), including any STAGE2_INSTRUCTIONS requirement, or the user mandate);
>   - FRAME-JUDGMENT (you would have chosen differently);
>   - PACK-GAP (rests on a fact the pack did not contain);
>   - MECHANISM (about the pre-registered arithmetic itself, not about the run's use of it).
> - **The evidence**, quoting the run and the pack.
> - **The concrete fix**, where quantifiable:
>   - stated as changes to named MACHINE SUMMARY inputs (a seat's `fair_value`, `fair_value_macro_base`, tree branch probabilities or values, quality score, acquisition declarations with `fair_value_other_acquisition_basis`, the run's weights, Helena's floor, or a framework NO BUY);
>   - with the resulting change to the run's headline in ⟨UNIT⟩ under the STAGE2_INSTRUCTIONS arithmetic.
>
>   A fix that needs a different formula is MECHANISM.
>
> **Scope.** Do not compare the run with any other valuation, and do not argue for a target number.
>
> **Close** with a "What to keep" section and a net verdict: stands, up or down, and roughly how much.
>
> **Checklist.** Apply CHECKLIST to the run. End your file with a JSON block `{"C1".."C8": {"met": true/false, "misses": [...]}}`. The checklist is recorded only; it moves no number.
>
> Write to ⟨OUT⟩. Reply with only the path and a one-line list: finding number, both tags, and the $ delta or "unquantified".

## Appendix F — Verifier prompt template and verification standard (use verbatim; fill only ⟨TICKER⟩, ⟨CRITIQUE⟩, ⟨RUN⟩, ⟨PACK⟩, ⟨REDLOG⟩, ⟨OUT⟩, ⟨SCRATCH⟩ and, if any, the mandate block)

> You are an independent verifier. Read ⟨CRITIQUE⟩, ⟨RUN⟩, ⟨PACK⟩, ⟨REDLOG⟩, STAGE2_INSTRUCTIONS, MARKET_INPUTS and FRAMEWORK, and nothing else. You may run, but not modify, `frozen_arith.py`. Put any files you write in ⟨SCRATCH⟩.
> - STAGE2_INSTRUCTIONS contains the rules the run was required to follow, including the pre-registered margin arithmetic.
> - ⟨REDLOG⟩ lists the redactions applied to the pack. A redacted figure is missing data, not a run error.
> - Do not use the web, or project or knowledge-base tools.
> - Never state or infer ⟨TICKER⟩'s price, market capitalisation, enterprise value or multiples.
> - ⟨TICKER⟩ means the company ⟨PACK⟩ describes; ⟨PACK⟩ names it, and you may recognise it. A fact you remember that ⟨PACK⟩ does not contain is not evidence: rule only on ⟨CRITIQUE⟩, ⟨RUN⟩, ⟨PACK⟩, ⟨REDLOG⟩, STAGE2_INSTRUCTIONS, MARKET_INPUTS and FRAMEWORK. A stated and justified assumption in the run is a judgment, not a fact: a finding that only disputes its level is FRAME-JUDGMENT.
>
> ⟨IF USER_MANDATE ≠ NONE:⟩ **USER MANDATE (supplied by the user, not the pipeline).** "⟨verbatim text⟩"
>
> For EVERY finding, rule CONFIRMED, REFUTED or UNVERIFIABLE in one or two sentences, under this standard. A finding is **CONFIRMED** only if:
> - **(a)** you reproduce the critic's arithmetic (not the run's) in Python. A value that cannot be reproduced from an incomplete input-change line is CONFIRMED-unquantified under (d); patch it only if the critic shows that the run's own stated inputs and mechanics give a different value; or
> - **(b)** the run contradicts a figure in its own pack; or
> - **(c)** the run contradicts its own declared frame, for example:
>   - it declares one denominator but uses another for a seat;
>   - it mixes basis periods;
>   - it names a gross source that does not match the pack;
>   - it lists an adjustment it does not apply, or applies one it did not list; or
> - **(d)** the run violates an explicit rule. Only these count:
>   - FRAMEWORK Rules 1–10;
>   - Phase 0.A;
>   - the Phase-0.B list of what the moderator does NOT establish;
>   - the Overview's "No market data" paragraph and its rule that investors use only the provided research;
>   - the explicit scoring, gate or mapping rules in a seat's description;
>   - any requirement of STAGE2_INSTRUCTIONS.
>
>   FRAMEWORK's principles, examples and other prose are not rules for (d). A finding that rests only on them is FRAME-JUDGMENT. Or:
> - **(d′)** the run ignores or contradicts the user mandate, if one exists.
>
> **Everything else is REFUTED as a mover.** That includes:
> - every FRAME-JUDGMENT and PACK-GAP finding;
> - any different level of a defensible input;
> - anything asserted but not demonstrated.
>
> A web fact cannot make a web-barred run wrong. You may record a FRAME-JUDGMENT finding as CONFIRMED-unquantified only if the run failed to *declare* or *justify* the choice. Never judge *which* choice was right.
>
> **Precedence.** The STAGE2_INSTRUCTIONS margin arithmetic is pre-registered and governs over FRAMEWORK's margin text. A required margin produced by that arithmetic is never a violation, even outside a FRAMEWORK band. Its roster (seven seated investors, no entry prices), its rate rule (every seat at the macro base) and its schedule rule (Mechanics) govern over FRAMEWORK, which is written to agree with them.
>
> Keep the critic's tags. For each CONFIRMED finding, state whether it is QUANTIFIED or UNQUANTIFIED.
>
> **QUANTIFIED means patched.** A finding is QUANTIFIED only if you write its fix as `changed_inputs`: patches to the run's MACHINE SUMMARY, each `{"path","from","to"}`, where `from` is the run's current value. Only these paths are allowed:
> - `investors.<Investor>.fair_value`
> - `investors.<Investor>.tree.<branch>.p` and `investors.<Investor>.tree.<branch>.value` (`to` = null removes a branch; a new branch name adds one and needs both)
> - `investors.<Investor>.quality_score` (the script derives the quality premium and the tier label from it; a `quality_tier` patch must match the patched score)
> - `investors.<Investor>.no_buy`: only for a FRAMEWORK uninvestability rule, such as two FAILs among Walter's gates. The 0.60 cap (AT CAP) is applied by the script and is never a patch.
> - `investors.<Investor>.fair_value_macro_base` (it sets the seat's L; patch it whenever a fix changes the seat's fair value at the macro base)
> - `frame.weights.<Investor>`
> - `helena_floor.floor_per_share_or_null`
> - `investors.<Investor>.break_p` and `investors.<Investor>.break_loss`: only for a seat with no valid tree.
> - `investors.<Investor>.growth_basis` and `investors.<Investor>.acq_spend_deducted`: only together with an explicit `investors.<Investor>.fair_value_other_acquisition_basis` patch and the fair-value and tree patches the change implies.
> - Companion paths, which move no margin: `investors.<Investor>.fair_value_rf_plus_50bp`, `investors.<Investor>.fair_value_other_acquisition_basis`, `investors.<Investor>.fair_value_alternative_denominator`, `frame.valuation_date`, `frame.per_share_count_date`, `frame.balance_sheet_add_per_share`. Patch them only as part of a fix that also patches the fair values and trees it changes, so that the sensitivity rows stay consistent with the fold.
> - `investors.<Investor>.fair_value_alternative_denominator` alone: only to set it equal to the seat's current `fair_value`, for every seat of the run that reports it, in one finding, when a finding is CONFIRMED under (d) that the run's alternative breaks the Phase-0 definition in STAGE2_INSTRUCTIONS (the script rejects a set that leaves any seat's value different from its fair value). The run's row then equals its headline, and the card counts the run as none.
>
> **Share counts are never patched.** The script normalises any run whose `denominator_count_m` differs from `per_share_count_m` (spec Stage 3). A finding about that difference is CONFIRMED-unquantified, because the script has already corrected it: do not patch fair values for it. A finding that the per-share count itself is wrong is quantified, if at all, by patching every affected seat's fair values and trees, with the counts left as reported.
>
> **Patch `fair_value_macro_base` with every fair-value patch.** Whenever you patch a seat's `fair_value`, also patch its `fair_value_macro_base`, with `to` equal to `from` if your fix leaves it unchanged (the rebase of an off-base rate does; a cash-flow or growth fix does not). The script rejects a fair-value patch without it, for any seat whose MACHINE SUMMARY reports the field.
>
> **Off-base rates.** Every seat must discount at the macro base. If a finding that a seat's rate is not the macro base is CONFIRMED under (d), run `python3 frozen_arith.py rebase ⟨RUN⟩ <Investor>` and use the patches it prints as that finding's `changed_inputs` (fair value set to `fair_value_macro_base`, every non-break branch scaled by the same ratio, the break value held; an approximation the script labels). If the seat reports no `fair_value_macro_base`, or reports it equal to the off-base fair value, the finding is CONFIRMED-unquantified.
>
> **Debt counted twice.** A CONFIRMED finding that a run deducted a debt, preferred, minority or lease claim from its cash flow to equity is QUANTIFIED by the patches `python3 frozen_arith.py undebt ⟨RUN⟩` prints (the run's `debt_deducted_per_share` added back to every seat's fair value, `fair_value_macro_base`, tree values and companion fair values, and to `balance_sheet_add_per_share`). A finding that the flows are not to equity (for example before interest, with no listed interest item) is QUANTIFIED only by fair-value, `fair_value_macro_base` and tree patches the critic derives from the run's own stated inputs; otherwise it is CONFIRMED-unquantified.
>
> **Risk-register findings.** A double count is QUANTIFIED by removing the second channel's stated size where it is a patchable input: a `quality_score` entry by a score patch of minus its size; a `base_cash_flows` entry by fair-value, `fair_value_macro_base` and tree patches of minus its size. A generic haircut is QUANTIFIED the same way if the run states its size; otherwise CONFIRMED-unquantified. An item left out of the register, a size the run's numbers do not show, and a breach of the mapped-dimension rule are CONFIRMED-unquantified: never supply a size the run did not state.
>
> A change to a discount rate, growth rate, schedule or adjustment is quantified by recomputing that seat's fair value and tree values and patching those. Every other MACHINE SUMMARY field is derived by the script, and a patch to it is invalid.
>
> **Remembered facts.** A finding that the run used a figure or fact from outside ⟨PACK⟩ and MARKET_INPUTS is QUANTIFIED only if ⟨PACK⟩ contains the figure it displaced (for example the latest reported value the run replaced with a later one) and the patch restores that ⟨PACK⟩ figure, everything else unchanged. Otherwise it is CONFIRMED-unquantified. Never replace it with a value you choose or remember.
>
> **Run the script.** Write your JSON block (below) to a file in ⟨SCRATCH⟩ and run `python3 frozen_arith.py verify ⟨RUN⟩ <that file>`. It checks every patch, recomputes every seat and the headline with the pre-registered arithmetic, and prints each finding's standalone delta, the joint delta and the adjusted headline. (To check one finding alone, run `verify` on a file holding only that finding.) Copy its figures into your JSON. The orchestrator re-runs it, and only the script's figures are folded.
>
> **MECHANISM.** A fix that cannot be written as patches on this list is never QUANTIFIED. So is a set of patches whose only purpose is to reproduce a different formula. Examples:
> - a different form of the tail term;
> - another quality-premium map, other clamp bounds or the 0.60 cap;
> - another headline formula;
> - moving the Rule-4 minimum;
> - seating Victor, Max or Simon, or averaging in an entry price or a margin-rule alternative;
> - a discount rate other than the macro base for any seat, Walter's multiplier constant, or the risk register's 1% threshold.
>
> Rule such a finding CONFIRMED-unquantified, set `"mechanism": true` (a JSON boolean), and give in `spec_change_or_null` one sentence on what the spec owner would have to change.
>
> **Joint fixes.** If several QUANTIFIED findings touch the same seat, give `joint_changed_inputs`: one consistent patch list that applies them all together.
>
> Write to ⟨OUT⟩, ending with a JSON block:
> `{"rulings":[{"finding","ruling","quantified":true/false,"mechanism":true/false,"spec_change_or_null","tag1","tag2","changed_inputs":[{"path","from","to"}],"script_delta"}],"joint_changed_inputs":[{"path","from","to"}],"script_joint_delta","script_adjusted_headline"}`
>
> Reply with only the path and that JSON.

## Appendix G — PREREGISTRATION template (use verbatim; fill only ⟨N_RUNS⟩, ⟨REPLICATES⟩, ⟨MODEL⟩, ⟨TIMESTAMP⟩, ⟨SCRIPT_SHA⟩, in a validation execution ⟨BASELINE⟩, and, if any, the mandate block)

> # PRE-REGISTRATION
> Timestamp: ⟨TIMESTAMP⟩. Model: ⟨MODEL⟩. Toolkit manifest SHA-256: ⟨SCRIPT_SHA⟩ (the manifest lists the SHA-256 of every toolkit script and of FRAMEWORK_v10.md). Frozen before Stage 2; not shown to any Stage-2 run.
>
> **Structure.** ⟨N_RUNS⟩ valuation runs; replicate structure ⟨REPLICATES⟩ (dossier → number of runs).
>
> ⟨IF USER_MANDATE ≠ NONE:⟩ **USER MANDATE (supplied by the user, not the pipeline).** "⟨verbatim text⟩"
>
> **Margin constants (v8; unchanged in v9 and v10).** Quality premium π(score), piecewise-linear through (52.5, 0.40), (67.5, 0.325), (82.5, 0.225) and (95, 0.125), and flat outside them; the tier is a label. required = clamp(π(score) + p·L, 0.10, 0.60), with p and L from the seat's own break branch after Helena's floor, and L measured against the seat's fair value at the macro base. Seven seated investors (Marcus, Sophie, Claire, Graham, Walter, Helena, Alexander); no entry prices. Every seat's discount rate is the macro base (risk-free + rebased ERP from MARKET_INPUTS); a seat off it is a STAGE2_INSTRUCTIONS violation, patched by the rebase patch. Every run values cash flow to equity, with no debt, preferred, minority or lease claim deducted. Walter's grade multiplier is 1 + 0.015 × score (score −12 to +12) and Alexander's mapping +10% / 0% / −15%, each applied to every branch's operating value. A seat above 0.60 before clamping is AT CAP (required 0.60) and stays in the headline; NO BUY only under a FRAMEWORK uninvestability rule. The cash-flow denominator count equals the per-share count; the script normalises any run where it does not. No asymmetry, gate or valve. Upside and non-break branches are reported, not netted. The Stage-3 script recomputes every seat from its tree. Exact arithmetic as in the Stage-2 instructions (spec Appendix B).
>
> **Margin-rule alternatives (policy; never averaged; not sensitivity-ledger rows).** On the same headline seats, weights and floored trees: step tiers (base(tier) 12.5% / 22.5% / 32.5% / 40% + p·L, clamped, with the v7.1 AT-CAP and NO-BUY decision); the EV rule (0.670 × the tree's probability-weighted mean); the expectile rule (the 1/8.75 expectile of the tree: expected upside = 7.75 × expected downside); and, for the outcome ledger only, EV × (1 − π). A seat with no valid tree is left out of the tree-based rules; a run with no eligible seat is left out of that rule's point, which is n/a below 3 runs. Each rule's implied expected upside ÷ downside on the pooled trees is reported. Constants fixed in spec v8.
>
> **Stage-3 statistics.** All on the run headlines (k = j = 1 under v9; back-scaled only in replays of masked executions). Per-run headline recomputed on each run's own weights, with a uniform-weight sensitivity; range, median, mean, SD, CoV; tier distribution (labels); margin-rule alternatives and seats within 3 points of a tier cut-off; run noise s_w = pooled within-dossier SD of headlines with df = N − D and a 90% χ² interval for σ_w, and the same on ln FV and on the log margin term, with variance shares; drift floor (display only); dossier contrast t with df = N − D; per-seat recompute from trees; frame decomposition, adjustment ledger, break-probability elasticity table (±5pp), break-probability histogram and descriptive tree tail cost, labelled descriptive; convention sensitivity including the denominator count, acquisition-matching tabulation (zero acquisition spend counts as matched) and acquisition rows, the alternative-denominator row, the debt row (net claims deducted again, the v9 count), rate lever (+50bp) and induced-field check; the logged v10 checks (rate, debt, risk register, seat mappings) and the descriptive channel monitor; v6-rule bridge headline on the first v7 ticker.
>
> **Stage-5 estimate, interval and ledger.**
> - **Point.** Trimmed mean of run headlines (drop the single highest and lowest) if N ≥ 6; otherwise the equal-weighted mean. The blind intermediate uses blind headlines; the published BUY uses adjusted headlines. Equal mean, median and leave-one-out estimates are descriptive.
> - **Interval.** Point ± t₀.₉₀,df · s ÷ √N, where s is the pooled within-dossier SD of the headlines the point uses, labelled "80% confidence interval for this pipeline's expected BUY on these packs, with this model and this orchestration". The replication range is √2 wider. No rule widens either range.
> - **Ledger (not in the interval).** Break probability ±5pp; convention sensitivity, including the denominator count; acquisitions (every seat organic; every seat including acquisitions); every seat on its run's alternative denominator; debt: net claims deducted again (the v9 count); risk-free +50bp; the figure without its most influential finding; dossier contrast; equal mean and median. Each row is in the reporting unit and in s_w units. Unmeasured sources are listed.
> - No scorers, coefficient, scheme-spread rule or frame-outlier rule.
>
> **Critic checklist.** Spec Appendix C, verbatim (attached). Unscored; it weights nothing.
>
> **Stage-4b verification standard.** Spec Appendix F, verbatim (attached).
>
> **Stage-5b folding rules.** Per-run only. Only CONFIRMED findings whose `changed_inputs` the frozen script accepts move a number, and only by the script's recompute; free-form dollar deltas never do. A fix that would change the pre-registered arithmetic is CONFIRMED-unquantified (MECHANISM) and goes to SPEC_FLAGS. Seats outside the roster stay out of every statistic. Re-average with the Stage-5 point-estimate rule. Publish both numbers, and headline the adjusted one. The Stage-5 uncertainty statement is recomputed on the adjusted headlines. The frozen arithmetic script in the toolkit above computes Stages 3, 5 and 5b.
>
> ⟨IF STAGE 7:⟩ **Stage-7 rule (optional stage).** The two orchestrations' published headlines pass if they differ by no more than the pooled drift floor computed from same-orchestrator, same-dossier pairs only (≈92% noise band; power ≈50% at a one-floor leak, ≈81% at 1.5 floors).
>
> **Blinding (v9).** Every run's pack is its redacted dossier (the Stage-1 redaction lists applied and methodology notes removed), unmasked and unscaled. Runs, critics and verifiers use no remembered fact: only the facts and reported figures in the pack and MARKET_INPUTS, with the runs' assumptions stated and justified as judgments. Price memory is not measured.
>
> ⟨IF VALIDATION ≠ NONE:⟩ **Validation (v10).** This execution re-values, under spec v10, the packs of an earlier v9 execution whose published data manifest has SHA-256 ⟨BASELINE⟩, with the same model and MARKET_INPUTS file. Its outputs are labelled VALIDATION. The comparison below is computed by `bridge.py compare` after Stage 6, which first checks the baseline folder against its manifest and ⟨BASELINE⟩ and reproduces the baseline's published BUY to within 0.005; it is published as `final/VALIDATION.md`, changes no published figure, and uses no market price.
> - **Bridge change** Δ_B = the baseline's BUY with every seat on its `fair_value_macro_base` and its required margin held, and the seat named Simon left out with its weight dropped, minus the baseline's published BUY (both by the Stage-5 point rule on the baseline's patched summaries).
> - **Realised change** Δ_R = this execution's debt-row BUY (every run's net claims deducted again, the v9 count), minus the baseline's published BUY. The debt row puts back the error T2 removes, so Δ_R and Δ_B both exclude the debt correction.
> - **Realised share** R = Δ_R ÷ Δ_B, with an 80% interval from run noise (the two executions' interval half-widths combined in quadrature; Δ_B treated as fixed), and the **unexplained share** 1 − R. If |Δ_B| is below twice that combined half-width, both read n/a. R is not a measure of migration alone: besides any move of pessimism between channels, Δ_R contains Walter's new grade, the mapped-dimension rule, the register, the closed ERP route and run noise. After the three validation executions, the spec owner also reports their precision-weighted mean R.
> - **Channels.** For each of committee fair value (on the debt-row seats in this execution, so both sides carry the v9 debt count), seat-weighted terminal growth, five-year forecast growth, quality score, `break_p` and tail term: the mean over each execution's retained runs, with the baseline's seat named Simon left out, the difference, and Welch's t on the run means (descriptive). Also: the seats off the macro base in this execution (expected 0) and the T2 correction (published BUY − debt-row BUY).
> - If the baseline folder fails its manifest, ⟨BASELINE⟩ or the published-BUY check, the bridge and channel lines read n/a and only the published BUYs and fair values are compared; the orchestrator logs it.
>
> This document contains no statement about the company.

## Appendix H — Launch prompts, screener and auditor instructions, and Stage-6 writer instructions (use verbatim; fill only the slots shown)

**Launch prompts.** Every subagent is started with exactly one of these. ⟨FILES⟩ is a list of file paths, each on its own line; paths use opaque names (`pack_xx.md`, `run_<token>.md`). Nothing else may be added: no description of the company, no expectation, no summary of another stage.

- **Redaction screener:** "Read ⟨FILES⟩ in full and follow the redaction-screener instructions in them exactly. Read nothing else. Write your output to ⟨OUT⟩. Reply with only the output path."
- **Tag screener:** "Read ⟨FILES⟩ in full and follow the tag-screener instructions in them exactly. Read nothing else. Write your outputs to ⟨OUT⟩ and ⟨OUT2⟩. Reply with only the output paths."
- **Neutrality auditor:** "Read ⟨FILES⟩ in full and follow the auditor instructions in them exactly. Read nothing else. Write your output to ⟨OUT⟩. Reply with only the output path."
- **Stage-2 run:** "Read ⟨FILES⟩ in full and follow STAGE2_INSTRUCTIONS.md exactly. Read nothing else. Write your output to ⟨OUT⟩; put any scratch scripts in ⟨SCRATCH⟩."
- **Critic:** "Read ⟨FILES⟩ in full and follow the critic instructions in them exactly. Read nothing else on this machine, and do not use the web. Write your output to ⟨OUT⟩; put any scratch scripts in ⟨SCRATCH⟩."
- **Verifier:** "Read ⟨FILES⟩ in full and follow the verifier instructions in them exactly. Read nothing else. Write your output to ⟨OUT⟩; put any scratch files in ⟨SCRATCH⟩."
- **Stage-6 writer:** "Read ⟨FILES⟩ in full and follow the writer instructions in them exactly. Read nothing else. Write your output to ⟨OUT⟩. Reply with only the output path."

The instructions and inputs each launch prompt points to are passed as files in ⟨FILES⟩: Appendices B, C (as `CHECKLIST.md`), E and F; the redaction-screener, tag-screener, auditor and writer instructions below; MARKET_INPUTS; and, for verifiers, `frozen_arith.py`.

**Redaction-screener instructions (Stage 1).**
> You screen EVERY dossier listed in ⟨FILES⟩, together. Read FRAMEWORK and those dossiers and nothing else. No web, no project or knowledge-base tools. Do not state or estimate the company's share price, market capitalisation or enterprise value.
>
> 1. **Redaction.** Apply these lists to the company only, never to peers.
>    - **R-1.** Any stated share price, price range, average purchase or sale price per share, market capitalisation, enterprise value, trading multiple, dividend or earnings yield, or analyst price target for the company; and any stated price per share of the company's own equity awards or instruments (grant-date fair value per share, exercise or strike price, ESPP purchase price, conversion price).
>    - **R-2.** The dollar amount of any transaction in the company's own shares, in any period: share repurchases (cash spent, accrued or authorised, and any remaining authorisation in dollars), treasury stock at cost, proceeds from share issuance, ESPP purchases and option exercises, the stock component of acquisition or merger consideration, exchange offers and block sales.
>    - **R-3.** Any ratio built from R-1 or R-2 figures, such as a repurchase yield or a buyback amount per share.
>
>    Never list any of these:
>    - a share count of any kind or period;
>    - an accounting per-share figure (EPS, book value, dividends per share; a price per share of an award or instrument is R-1);
>    - cash paid for acquisitions;
>    - any other income-statement, cash-flow or balance-sheet line.
>
>    If you are unsure, do not list the figure; list it under soft routes instead.
>
>    For each redaction, give:
>    - the list item;
>    - the dossier;
>    - the line number;
>    - the exact text to redact;
>    - a short qualitative replacement (e.g. "repurchases continued; amounts redacted").
>
>    For each dossier and each of R-1, R-2 and R-3, state "redacted" or "not present". Then list, separately, any route by which a price could be estimated only with an assumption (soft routes), with the figures it uses. Soft routes are not redacted.
> 2. **Methodology notes.** List every sentence that recommends or prescribes how to value the company: a valuation method, denominator, share count or share-count convention, discount rate, growth rate, adjustment, peer, or which figure to use. Give the dossier, the line number and the exact text span. Do not list sentences that only describe what the company reports. Also list, the same way, every sentence about the request or instructions the dossier was written under, the valuation pipeline, framework or method document, or files its author could not find.
>
> Write one JSON object to ⟨OUT⟩, and nothing else: `{"redactions":[{"item","dossier","line","span","replacement"}],"class_status":[{"dossier","item","status":"redacted|not present"}],"soft_routes":[{"dossier","route","figures"}],"methodology_notes":[{"dossier","line","span"}]}`. Name each dossier by its file name. Make no other comment on the company.

**Tag-screener instructions (Stage 1).**
> You screen ONE dossier. Read FRAMEWORK and ⟨PACK⟩ and nothing else. No web, no project or knowledge-base tools. Do not state or estimate the company's share price, market capitalisation or enterprise value.
>
> 1. **Data thinness.** List which denominator-critical metrics rest on a single period or a single source. Start each entry with the metric's name in bold, exactly one of: **Cash flow**, **Capex**, **SBC**, **Share count**, **Tax**, **Acquisitions**, **Growth indicators**.
> 2. **Share counts.** List every figure in ⟨PACK⟩ that is a count of the company's shares (outstanding, weighted-average basic or diluted, repurchased, issued, granted, authorised, options and RSUs outstanding; any period; any split basis), with its line number and the exact text span. Do not list amounts per share, currency amounts or peers' figures. Separately, list every line that mentions shares and carries numbers but states no count of the company's shares (for example a currency amount spent on repurchases, or a peer's figure), with its line number and a one-line reason.
>
> Write list 1 to ⟨OUT⟩ as text. Write list 2 to ⟨OUT2⟩ as one JSON object, and nothing else: `{"tags":[{"line","span","tag":"SHARES"}],"not_share_counts":[{"line","reason"}]}`. Make no other comment on the company.

**Neutrality-auditor instructions (Stage 0.5).**
> You receive texts in which the company name, unit and file names are masked. You are not told the company. For each sentence, flag it if (a) it would change or become false for a different company, or (b) it states or implies a level, direction, probability, floor, denominator, adjustment, weight, tier or "what matters" for the company. Check every slot value the same way. If a USER MANDATE block and the user's original message are supplied, check only that the block matches the message word for word. The run count, replicate structure, model ID, timestamp, toolkit manifest SHA-256 and any baseline data manifest SHA-256 in a pre-registration are per-execution slots by design: check only that each reads as a count, a dossier → runs list, a model ID, a timestamp or a SHA-256, and do not flag them under (a). Write each flag with its location and reason to ⟨OUT⟩.

**Stage-6 writer instructions.**
> Read the dossiers in ⟨FILES⟩ and nothing else. No web, no project or knowledge-base tools. Write a section titled "How the company makes money", about 300–500 words, that DESCRIBES and does not judge the business: what it sells and to whom, how revenue is earned, how any recurring-revenue metrics work, where costs go, how cash is generated and where it goes, and the balance-sheet shape. Use only facts and figures in the dossiers, with their periods; add nothing you remember about the company. Omit any figure the dossiers mark as redacted. No opinions, forecasts, valuation, price, or evaluative adjectives.

---

## Appendix I — Decision Card and headline sentence (generated by the frozen script; diffed; fill only the ⟨CARD_…⟩ slots and ⟨TICKER⟩, ⟨UNIT⟩, ⟨AS_OF⟩)

> **DECISION CARD — ⟨TICKER⟩ (⟨UNIT⟩), as of ⟨AS_OF⟩**
>
> 1. **Fair value (the estimate):** ⟨CARD_FV⟩. Run range ⟨CARD_FV_LO⟩–⟨CARD_FV_HI⟩.
> 2. **Required margin (the policy):** effective ⟨CARD_M⟩ = quality premium ⟨CARD_BASE⟩ + tail term p·L ⟨CARD_TAIL⟩ + weighting residual ⟨CARD_RESID⟩. Each term is the seat-weighted mean within runs, averaged with equal weight over the runs retained for ⟨CARD_BUY⟩; ⟨CARD_RESID⟩ is ⟨CARD_M⟩ minus the two terms.
> 3. **BUY: ⟨CARD_BUY⟩.** 80% confidence interval for this pipeline's expected BUY on these packs, with this model and this orchestration: ⟨CARD_LO⟩–⟨CARD_HI⟩. A fresh execution's figure is expected within ⟨CARD_REP_LO⟩–⟨CARD_REP_HI⟩. Neither range covers the levers in item 6 or the margin rules in item 5.
> 4. **BUY at one quality premium for every seat, with no tail term** (policy alternatives, not the committee's figure): 12.5% ⟨CARD_B1⟩; 22.5% ⟨CARD_B2⟩; 32.5% ⟨CARD_B3⟩; 40% ⟨CARD_B4⟩. Modal tier: ⟨CARD_TIER⟩ (⟨CARD_TIER_N⟩ of ⟨CARD_SEATS⟩ headline seats).
> 5. **Other margin rules on the same seats and trees** (policy alternatives, not estimates and not a confidence range; never averaged; constants fixed in the spec at the v7.1 step rule's average strictness on two earlier tickers): step tiers ⟨CARD_R1⟩; EV rule, tuned Victor (0.67 × tree expected value) ⟨CARD_R2⟩; expectile rule, tuned Max (expected upside 7.75 × expected downside) ⟨CARD_R3⟩. Expected upside ÷ expected downside at each BUY, on the committee's pooled trees: published ⟨CARD_K0⟩; step tiers ⟨CARD_K1⟩; EV rule ⟨CARD_K2⟩; expectile rule ⟨CARD_K3⟩. Seats left out of the tree rules: ⟨CARD_NOTREE⟩. Seats within 3 points of a tier cut-off: ⟨CARD_NEAR⟩ of ⟨CARD_SEATS⟩.
> 6. **Levers** (change in BUY, ⟨UNIT⟩ / run-noise SDs):
>    - break probability −5pp ⟨CARD_L1⟩, +5pp ⟨CARD_L2⟩;
>    - valuation date rolled to pack date ⟨CARD_L3⟩;
>    - share-count date ⟨CARD_L4⟩;
>    - both ⟨CARD_L5⟩;
>    - denominator on the period-weighted count ⟨CARD_L8⟩;
>    - acquisitions: every seat organic ⟨CARD_L9⟩, every seat including acquisitions ⟨CARD_L10⟩;
>    - every seat on its run's alternative denominator ⟨CARD_L11⟩ (runs with the alternative above the declared denominator ⟨CARD_ALT_UP⟩, below ⟨CARD_ALT_DN⟩, none ⟨CARD_ALT_NONE⟩; seats valued ⟨CARD_ALT_K⟩ of ⟨CARD_SEATS⟩; each seat's margin held);
>    - debt: net claims deducted again, the v9 count (each seat's margin held) ⟨CARD_L12⟩;
>    - risk-free +50bp ⟨CARD_L6⟩;
>    - without the most influential finding ⟨CARD_L7⟩;
>    - dossier contrast t = ⟨CARD_T⟩ (df ⟨CARD_DF⟩).
> 7. **Reproducibility:** run-noise SD ⟨CARD_SW⟩ (df ⟨CARD_DF⟩; 90% range ⟨CARD_SW_LO⟩–⟨CARD_SW_HI⟩). Within-dossier noise is ⟨CARD_FV_NOISE⟩ of the mean on fair value and ⟨CARD_BUY_NOISE⟩ on BUY. Two published BUYs from fresh executions of these packs that differ by less than ⟨CARD_SW⟩ are within run noise (about a 90% band); single runs differ by more than ⟨CARD_SW⟩ about half the time.
> 8. **Status:**
>    - runs ⟨CARD_RUNS⟩;
>    - valuation date(s) ⟨CARD_VDATE⟩; per-share count date(s) ⟨CARD_SDATE⟩;
>    - MARKET_INPUTS ⟨CARD_MI⟩;
>    - orchestration replicate ⟨CARD_S7⟩;
>    - mandate ⟨CARD_MANDATE⟩;
>    - seats at the 0.60 cap ⟨CARD_CAP⟩; acquisition-matching mismatches ⟨CARD_ACQ⟩ (undeclared ⟨CARD_ACQ_U⟩); denominator counts normalised ⟨CARD_DENOM⟩;
>    - seats off the macro base ⟨CARD_OFFBASE⟩ (fair value still off it after the fold ⟨CARD_OFFBASE_FOLD⟩); runs with debt deducted ⟨CARD_DEBTDED⟩; systematic risk class (descriptive): defensive ⟨CARD_SRC_D⟩, average ⟨CARD_SRC_A⟩, cyclical ⟨CARD_SRC_C⟩ runs; Walter's mean multiplier ⟨CARD_WMULT⟩;
>    - thin-data decisive inputs ⟨CARD_THIN⟩.

**Headline sentence.**

> Published BUY ⟨CARD_BUY⟩ ⟨UNIT⟩ (80% confidence interval for this pipeline's expected BUY on these packs: ⟨CARD_LO⟩–⟨CARD_HI⟩); committee fair value ⟨CARD_FV⟩; largest sensitivity not in the interval: ⟨CARD_BIGROW⟩, ⟨CARD_BIGSIZE⟩ ⟨UNIT⟩.⟨IF CARD_MANDATE ≠ NONE:⟩ The figure is conditional on the user mandate.

Slot rules:
- Every ⟨CARD_…⟩ value is one of the following:
  - a number, a date or a hash;
  - a fixed status word: run / not run; NONE / conditional; or n/a;
  - for ⟨CARD_THIN⟩ and ⟨CARD_BIGROW⟩, metric or row names copied verbatim from `DATA_THINNESS_LOG.md` or the ledger. ⟨CARD_THIN⟩ lists, in the tag-screener vocabulary's order, every denominator metric (Cash flow, Capex, SBC, Share count, Tax, Acquisitions) that any dossier's thinness list names, each followed by the dossiers that name it, e.g. "Share count (A, B); Tax (B)"; the configuration builder sets it.
- ⟨CARD_MI⟩ is the MARKET_INPUTS AS_OF, currency and SHA-256.
- ⟨CARD_BIGROW⟩ is the ledger row with the largest absolute change in BUY in ⟨UNIT⟩ among the rows expressed as a change in BUY (break probability ±5pp, convention sensitivity including the denominator count, the acquisition rows, the alternative-denominator row (v9), risk-free +50bp, without the most influential finding, equal mean and median; never the debt row); ⟨CARD_BIGSIZE⟩ is that change.
- ⟨CARD_L12⟩ is the debt row (v10, T2), written like every lever, or n/a when no run retained for ⟨CARD_BUY⟩ reports a non-zero `net_claims_per_share`. It is never ⟨CARD_BIGROW⟩: it restates the error v10 removes.
- ⟨CARD_OFFBASE⟩ counts the headline seats of the blind summaries that the Stage-3 rate check logs (rate not the macro base, or `fair_value_macro_base` not equal to `fair_value`), and ⟨CARD_OFFBASE_FOLD⟩ those still off after the Stage-5b fold (their `fair_value` differs from `fair_value_macro_base`, or their rate is off and the fold left their fair value unpatched), both over the runs retained for ⟨CARD_BUY⟩; ⟨CARD_DEBTDED⟩ counts those runs whose blind summary reports a non-zero `debt_deducted_per_share`; ⟨CARD_SRC_D⟩, ⟨CARD_SRC_A⟩ and ⟨CARD_SRC_C⟩ count those runs by declared value (a run with another value is counted in none, and logged); ⟨CARD_WMULT⟩ is the mean of Walter's multiplier over those runs (1 + 0.015 × the sum of his components where they are valid, else as reported) to three decimals, or n/a.
- ⟨CARD_CAP⟩, ⟨CARD_ACQ⟩, ⟨CARD_ACQ_U⟩ and ⟨CARD_DENOM⟩ are counts of seats, seats, seats and runs over the runs retained for ⟨CARD_BUY⟩.
- ⟨CARD_R1⟩, ⟨CARD_R2⟩ and ⟨CARD_R3⟩ are the trimmed points of the step-tier, EV-rule and expectile-rule headlines on the Stage-5b patched summaries (Stage 5), rounded as the BUY, or n/a.
- ⟨CARD_K0⟩–⟨CARD_K3⟩ are the implied expected upside ÷ expected downside (Stage 3) at the published BUY and at each rule's BUY, written "x.x:1", or n/a.
- ⟨CARD_NOTREE⟩ counts the headline seats without a valid tree, and ⟨CARD_NEAR⟩ the headline seats whose quality score lies within 3 points of 60, 75 or 90, over the runs retained for ⟨CARD_BUY⟩. ⟨CARD_BASE⟩ is the seat-weighted quality premium.
- ⟨CARD_L11⟩ is the alternative-denominator row (v9, N2), written like every lever, or n/a when no headline seat of the runs retained for ⟨CARD_BUY⟩ reports `fair_value_alternative_denominator`; an n/a row is never ⟨CARD_BIGROW⟩. ⟨CARD_ALT_UP⟩, ⟨CARD_ALT_DN⟩ and ⟨CARD_ALT_NONE⟩ count those runs whose alternative lies above, below or equal to the declared denominator ("none" included, as are runs whose every seat's alternative fair value equals its fair value and runs that report no alternative); ⟨CARD_ALT_K⟩ counts their headline seats that report the field.
- Cards of v7–v8 executions also carry the memory-control and bridge lines, with their status words; spec v8 states them. Cards of v9 executions have no item-6 debt lever and no v10 status line (spec v9).
- Rounding follows Stage 6.

## Appendix J — MARKET_INPUTS template (season file; fill only the slots shown; never per ticker)

> # MARKET INPUTS
> AS_OF: ⟨AS_OF⟩. Currency: ⟨CURRENCY⟩.
>
> - **Risk-free rate:** ⟨RF⟩% — 10-year government bond yield in ⟨CURRENCY⟩, series ⟨SERIES⟩, observed at the close of ⟨RF_DATE⟩ (the last trading day on or before AS_OF).
> - **Equity risk premium:** ⟨ERP⟩% — the source's implied premium of ⟨ERP_RAW⟩% (source ⟨ERP_SOURCE⟩, dated ⟨ERP_DATE⟩, convention ⟨ERP_CONVENTION⟩ as the source states it), computed against a ⟨CURRENCY⟩ 10-year government yield (series ⟨ERP_RF_SERIES⟩) of ⟨ERP_RF⟩% on that date, rebased to this file's risk-free rate: ⟨ERP_RAW⟩ + ⟨ERP_RF⟩ − ⟨RF⟩ = ⟨ERP⟩. The risk-free rate plus this premium equals ⟨ERP_RAW⟩ + ⟨ERP_RF⟩, the source's implied market return.
>
> This file is identical for every company valued with this AS_OF and currency. It contains no statement about any company.

*The slots are filled once per season file. For every ticker the file is used byte for byte (Stage 0.5, Step 1). ⟨ERP⟩ is computed, not chosen: the checks script recomputes it from ⟨ERP_RAW⟩, ⟨ERP_RF⟩ and ⟨RF⟩ (v9, N4). Where the source states its premium on the same risk-free rate as the file, ⟨ERP_RF⟩ equals ⟨RF⟩ and ⟨ERP⟩ equals ⟨ERP_RAW⟩. The source must be an implied (forward-looking) premium computed against the 10-year government yield in ⟨CURRENCY⟩ (⟨ERP_RF_SERIES⟩ is the same series as ⟨SERIES⟩), dated no more than 31 days before ⟨RF_DATE⟩. A historical or survey premium, a premium measured in another currency, or one whose source sets its own pairing with the risk-free rate is not rebased: the builder asks the spec owner before filling the file. The checks script also stops a file whose ⟨ERP⟩ lies outside 2–8%.*


## Appendix K — Outcome ledger (season files, v8 G4 and v10 T6; no slots)

The ledger is two files in durable storage, outside every ticker folder, with a third, the bridge file, from v10. All three are orchestrator-only (Rule O-1) and never shown to any subagent.

**`OUTCOME_LEDGER_EXECUTIONS.md`.** One row per execution, appended at Stage 6 by `publish.py ledger` and never edited afterwards. It holds no market data. Its header is fixed:

| ticker | execution date | spec | toolkit manifest SHA-256 | AS_OF | pack as-of date(s) | valuation date(s) | published BUY | 80% interval | committee FV | effective margin | quality premium (w) | tail term (w) | step tiers | EV rule (tuned Victor) | expectile rule (tuned Max) | EV × (1 − π) | implied upside ÷ downside (published / step / EV rule / expectile rule / EV × (1 − π)) | mean quality score | seats within 3 points of a cut-off | seats without a valid tree | mean break_p | mean break horizon (years) | data |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

**`OUTCOME_OBSERVATIONS.md`.** Written only by the ledger-update procedure below; one row per execution per observation date. It is kept outside the storage the executions use (or sealed there), and no execution ever opens it. Its header is fixed:

| ticker | execution date | observation date | horizon (years) | split-adjusted close | price source | first close at or below each BUY (published / step / EV rule / expectile rule / EV × (1 − π); dates) | horizon value V* | realised cash flow, company total, per matched forecast period (`period_end`; value; definition used) | break event observed (per pre-registered definition) | notes |
|---|---|---|---|---|---|---|---|---|---|---|

**`OUTCOME_BRIDGE.md` (v10, T6).** One row per execution whose per-run data folder exists and replays, written by `bridge.py row` from that folder (G5) and never edited afterwards. It holds no market data. The spec owner may back-fill rows for earlier executions with `bridge.py row` on their data folders; a back-filled row says so in its notes. Its header is fixed:

| ticker | execution date | spec | data manifest SHA-256 | published BUY (recomputed) | BUY, every seat on its macro-base fair value | BUY, macro base, without Simon | debt row (v10 only) | seats off the macro base | Walter's mean multiplier (v10 only) | notes |
|---|---|---|---|---|---|---|---|---|---|---|

Every BUY is the Stage-5 point on the patched summaries, with each seat's required margin held (as with the rebase patch, the break value is not moved); "without Simon" drops his seat and weight. A seat that reports no `fair_value_macro_base` keeps its fair value (counted in notes). For a v10 row the macro-base columns equal the published BUY up to seats still off the base. The published column must equal the execution's published BUY to within 0.005 ⟨UNIT⟩, or the row is not written and the mismatch is logged.

**Ledger-update procedure (outside every execution).**
- It is run by the spec owner, or by a scheduled task the spec owner sets up; never by an execution's orchestrator or subagents, and never while an execution is in progress in the same storage, because it handles market prices.
- Observation dates: 1, 3 and 5 years after each execution, with an optional reading at 6 months.
- Prices come from a named public source, with the date. Closes are split-adjusted, and every BUY is adjusted by later split factors. A takeover ends the series at the deal price; a delisting in distress records −100%.
- **V\*** at a horizon is the split-adjusted total-return value at the horizon, discounted to the execution date at the MARKET_INPUTS macro base the execution used.
- Realised cash flows come from the company's filed annual reports, computed with each seat's own `forecast_definition` as fixed at publication. Each forecast period is matched by `period_end` to the filed fiscal year whose end lies within ±3 months; other periods are dropped. Company totals are compared, which removes share-count drift.
- **Break event (objective).** A seat's break is recorded as having occurred if, within its stated `horizon_years`, the realised company-total cash flow falls below its base-year figure **and** the split-adjusted close falls to or below the seat's break-branch value (back-scaled, for a masked execution).

**Base-year cash flow.** The seat's cash flow, under its `forecast_definition`, for the last fiscal year ending on or before the execution's valuation date, computed from the pack's figures at publication and recorded with the observation.

**One row set per ticker.** A ticker valued more than once (a VALIDATION execution) enters each pre-registered test once: by its first execution, with a sensitivity that uses the VALIDATION execution instead. Executions marked in-sample (Stage 0, ICE) are reported with and without those rows.

**Pre-registered tests.** Nobody computes a test statistic before the trigger: 30 distinct tickers with a 1-year observation; then again at 3 and 5 years. Results go to the spec owner as a note; any spec change follows only through a new spec version.
1. **Forecast error by quality.** Per matched period, e = |realised − forecast| ÷ max(|forecast|, |base-year cash flow|).
   - Primary (sizes π): between tickers, the ticker-mean quality score against the ticker-median e, OLS with an HC3 confidence interval.
   - Secondary: within ticker, each seat's e on its score, with ticker fixed effects and errors clustered by ticker.
   - Both are reported. A change to π needs the primary.
2. **Tree shape.** Within a tier label, does a seat's tree dispersion (downside semideviation ÷ FV) predict its e (same model as test 1, secondary)? If it does, the tree-based rules carry information the premium ignores.
3. **Margin rules (expectile calibration).** For each rule r (published, step tiers, EV rule, expectile rule, EV × (1 − π)), with its implied ratio K_r recorded at publication: at each horizon, using relative deviations d = V* ÷ B_r − 1 so that tickers of different price levels are comparable, the realised ratio Σ(d)+ ÷ Σ(−d)+ over executions, against the median K_r. A rule is calibrated when the two agree. The fill share, the return from the fill and the overpay rate are reported as descriptive only. Any choice between rules names the overpay:underpay ratio it assumes. From v10 the test is also reported by spec version (v7 to v9, whose rates carried add-ons, against v10).
4. **Break calibration.** Stated `break_p` against the objective break event within the stated horizon: a Brier score and a reliability table, by horizon bucket.
5. **Signed forecast bias (v10).** Per matched period, b = (realised − forecast) ÷ max(|forecast|, |base-year cash flow|), averaged per execution over its seats and periods. Does the committee under- or over-forecast cash flow? The ticker-level mean of b is tested against 0 (t with an HC3 interval), and reported stratified by spec version and by `systematic_risk_class` (from the roll-up; "n/a" for earlier rows, which form their own stratum). A systematic rate term (Open flags) is considered only if the cyclical and defensive strata differ in V* ÷ BUY beyond what their b explains.

*This appendix has no slots. All three headers are fixed; `publish.py` writes the first exactly, and `bridge.py` the third.*

---

## Revision history

### v6 → v6.1 (2026-09-29)
| # | Edit | Why |
|---|---|---|
| 1 | Added `gross_denominator_per_share` and `denominator_adjustments` to the frame block. The Phase-0 instruction requires every adjustment to be listed. Stage 3 adds an adjustment ledger and splits the FV share into denominator vs multiple. C1/C8 require reconciliation. Verification route (c) covers unlisted or unapplied adjustments. | The FV half of the v5 ADBE gap came from owner-cash-flow adjustments (acquisitions, float and tax: $3.59/share on dossier B). A denominator-type field cannot see these. |
| 2 | Added Appendix E (critic template) and Appendix F (verifier template and standard). | v6 said these were fixed templates, but only B and C existed. |
| 3 | Changed "one change" to "one family of changes". Stage 7 made REQUIRED for the first v6 ticker, with the model held fixed. The macro-rate guideline is barred from the ADBE attribution dossiers. | v6 changes several things at once. |
| 4 | Added the USER_MANDATE slot and verification route (d′). | O-2 binds the orchestrator, not the user. |
| 5 | The auditor sees masked texts. Flags on spec-template text go to `SPEC_FLAGS.md` instead of being deleted. | Keeps the auditor's own priors out, and avoids breaking the mechanics per ticker. |
| 6 | Added the frame-outlier band rule. | Free frames let a consistent outlier pull the weighted mean. |
| 7 | Scorers no longer receive verification files. | Keeps scoring independent. |
| 8 | Redaction extended to share-for-dollar pairings; routes of three or more operations are logged, not redacted. | Closes stock-settled edge cases while keeping the line bright. |
| 9 | Pasted dossiers became standing deviation P-1. | When dossiers are pasted, the orchestrator has already read them. |
| 10 | The macro base became a dossier-construction guideline. Added the PACK-GAP tag and the "What the packs lacked" section. | It is a dossier requirement, not a pipeline mechanism. |
| 11 | Added `SEASON_FRAME_ROLLUP.md`. | Six runs per ticker give descriptive results only. |

### v6.1 → v6.2 (2026-09-29)
| # | Edit | Why |
|---|---|---|
| 1 | A mandate may override FRAMEWORK valuation defaults only, never O-1, the no-market-data clause, web limits or redactions. The orchestrator asks the user before Stage 0 if a mandate would. | In v6.1, "the mandate governs" had no limit, so a mandate could have breached integrity controls. |
| 2 | Every subagent (runs, critics, verifiers, scorers, screeners, auditor) receives the Rule-10-neutralised FRAMEWORK copy. The original never leaves the orchestrator. | In v6.1 only Stage 2 got the neutral copy. The original example is ticker-shaped and would reach critics who have web access. |
| 3 | Scorers receive the run's pack and FRAMEWORK. The rationale for withholding critique files is restated as independence, not double-counting. | C1, C6 and C8 check pack-derived items, which a scorer cannot do without the pack. Withholding verification files never prevented a scorer finding the same defect. |
| 4 | Per-seat `break_p` and `break_loss` added to the MACHINE SUMMARY and C7. Stage 3 adds a gate knife-edge table. | The 15% threshold was ADBE's largest BUY driver, and gate booleans alone cannot measure it. |
| 5 | The season roll-up uses `log_rel_headline` with ticker fixed effects and records business type. Pooled effects are labelled associations. | Dollar headlines cannot be pooled across tickers, and frame choices are confounded with business type. |
| 6 | Stage 7 runs as two separate sessions, with a pre-registered pass/fail band (≈95% noise band for n = 6) and a stated power. The baseline is the faithful v5 execution ($221.16) with its model, not the 4.8 execution. The v5 side is marked as n = 1 and indicative. | One session cannot orchestrate twice blind. The 4.8 execution deviated from v5 itself. The threshold needed a stated meaning. |
| 7 | Share-for-dollar pairings: always redact the dollar leg. | "Whichever is not denominator-critical" was a screener judgment. |
| 8 | Stage 0.5 starts with a mechanical diff of instantiated texts against their appendices. The auditor reviews PREREGISTRATION and the diffed texts. | A script can prove that nothing was added outside the slots. An LLM review can only suggest it. |
| 9 | Minor: `gross_source` field; trimmed defined for n = 6; the frame-outlier rule's overlap with the v5 decision rule stated; units convention extended to `break_p` and `break_loss`. | Removes ambiguity. |

### v6.2 → v6.3 (2026-09-29)
| # | Edit | Why |
|---|---|---|
| 1 | Launch prompts, screener instructions and Stage-6 writer instructions templated (Appendix H). Launch prompts are saved as sent and diffed before sending. | The one-line prompt that starts each subagent was untemplated, orchestrator-written text reaching every subagent. It was the easiest remaining channel for framing. |
| 2 | PREREGISTRATION templated (Appendix G) and diffed. The auditor's job narrows to slot values, the mandate, and generic template bias. | Its required contents were already fully generic. As free text, it was the one input the diff could not cover. |
| 3 | Stage-7 drift floor uses same-orchestrator, same-dossier pairs only. | Cross-orchestrator pairs contain the leak being tested; pooling them cut power at a one-floor leak from ~50% to ~36% in simulation. |
| 4 | Stage-7 band restated as ≈92% (simulated false-alarm ~8%), with a simulated power table. The realised drift floor in dollars is reported next to the result. | The drift floor is estimated from 12 pairs, so the nominal 95% is optimistic. The reader needs the leak size ruled out in dollars. |
| 5 | Exact margin formulas for neither/gate/valve added to Appendix B and used by the Stage-3 knife-edge table. | "Floor 40% plus tier capped" admitted more than one reading, and the knife-edge recompute must match the runs' arithmetic. |
| 6 | Unattended executions with a conflicting mandate do not start: log, notify, stop. | "Ask the user" is impossible when no one is present. |
| 7 | Stage 7: record the serving model where exposed; check that v6 screener redactions match the v5 baseline's; budget stated (~56 subagents, ~8–10M tokens). | The configured model can differ from the serving model; the v5/v6 comparison requires identical inputs; the cost should be known before starting. |

### v6.3 → v7 (2026-09-30)
Five major edits, chosen by vote after the DECK v6 and ADBE v6 executions, and the consequential changes they force.

| # | Edit | Why |
|---|---|---|
| E1 | **One tail term replaces the asymmetry/gate machinery.** Appendix B margin block, Mechanics and MACHINE SUMMARY (trees, `break_derivation`, `tail_term`, `helena_floor`); Stage-3 per-seat recompute, elasticity table, histogram, tree tail cost and v6-rule bridge; Appendix A replaced; C6 and C7; Appendix G constants; FRAMEWORK tier-margin text, Rule 3, Phase 1.C, Helena, Alexander and the Downside check. | The margin mechanism dominated the DECK and ADBE numbers: median-anchored R exploded (up to 306.7), segregated IRR seats set headline margins, and the 15% cliff swung runs by $11–$16 (DECK) and $37–$51 (ADBE). |
| E2 | **Numbers move only through the frozen arithmetic, by script.** STAGE2_INSTRUCTIONS given to critics and verifiers; route (d) scope; precedence; MECHANISM tag; closed patch list; `frozen_arith.py` with self-test and pre-registered SHA-256; Stage 5b rewritten; Appendices E, F and G. | O9 and O10: checkers lacked the margin rules, and an out-of-mechanism fold (−$5.31) moved the DECK figure and reversed the sign of Stage 5b. |
| E3 | **Price-memory control in every execution.** Stages 1c and 1d; MASK_LABEL; clean room; back-scaling; scale-dependence test and pooled season test; critics web OFF; per-run redlog without figures; Stage 7 optional; Appendices B, E, G and H. | O14: price-blindness covered inputs only. Stage 7 was never run. |
| E4 | **Dated conventions and a season market-inputs sheet.** O-2 carve-out and Appendix J; Phase-0 date, share-count and macro bullets; frame fields; rate lever; convention sensitivity; induced-field check and INDUCED label; C1 wording; methodology notes removed at Stage 1; dossier guideline; FRAMEWORK Phase 0.A. | All six DECK critics flagged the shared valuation-date and share-count conventions (≈ +$5.7 to +$7.4), which a rubric line and a pack recommendation induced. The two DECK packs quoted different risk-free rates. |
| E5 | **What is published, and how precise it is.** Scorers, coefficient, scheme zoo and band rules removed; trimmed-mean point; run noise s_w, χ² interval and dossier contrast; labelled 80% interval with replication range; sensitivity ledger; Decision Card (Appendix I); Appendix C as a critic checklist; 4 + 4 runs. | The coefficient moved DECK by $0.02–$0.07. Inverse-dispersion equals the median. DISAGREE and frame-outlier rules could not fire. The band never stated what it covered. |
| C1 | Consequential: preamble rewritten ("What v7 changes", "What v7 does NOT change", attribution), with the v6 background kept. | Five edits change the spec's scope statement. |
| C2 | Consequential: Stage-0.5 slot list gains ⟨OUT2⟩, ⟨SCRIPT_SHA⟩, ⟨AS_OF⟩, the ⟨CARD_…⟩ slots and the Appendix-J season slots. The diff also checks MASK_LABEL, the script hash and the MARKET_INPUTS hash. | Every slot used in a template must be declared. |
| C3 | Consequential: Appendix H loses the scorer prompt and gains the probe prompt and instructions; the screener gains steps 3 and 4 and ⟨OUT2⟩; the verifier prompt gains ⟨SCRATCH⟩; Appendix E gains ⟨UNIT⟩ in its fill list. | E2, E3, E4 and E5 inputs and outputs. |
| C4 | Consequential: the season roll-up gains `mechanism_version`, `ln_k`, `ln_j`, the probe result, AS_OF and the MARKET_INPUTS hash. | Pooled analysis must not mix mechanisms, and needs the memory-control and market-input columns. |
| C5 | Consequential: "Deferred to v7" is replaced by "Resolved from the v6 deferred list" and "Open flags carried forward"; "Known costs" is rewritten for v7; a v6.3 → v7 "What changed" table is added, and the v5 → v6 table is kept as history. | Consistency. |
| C6 | Consequential: the Stage-7 v6 design record (pair counts, power, ADBE budget) is marked as computed for the v6 design; Stage-6 heading; `final/spec_v7.md`; artefacts keep the script, the self-test, the fold log and the MARKET_INPUTS copy. | Stage 7 is optional and the replicate default is 4 + 4. |
| C7 | Round-4 review fixes (see `FIX_LOG.md`): MASK_UNIT and its Stage-0.5 check; the full v6-rule bridge formulas and a self-test case; IRR entry prices never overwritten; tree checks (unique names, tolerance, before flooring; every branch floored); tier derived from the quality score; ledger rows and committee FV computed after the fold; E4 companion patch paths; the per-ticker memory test requires 4 runs per dossier; the rate lever holds L fixed; card and label wording. | Reviewers P1, P2, P4 and P5 found gaps where the five edits meet. |

### v7 → v7.1 (2026-09-30)
Five edits, chosen by a three-debater Borda vote after the ADBE v7 execution (`claude/SPEC_v7.1_DEBATE_RECORD.md`). Each was on all three final ballots.

| # | Edit | Why |
|---|---|---|
| F1 | **One share-count rule.** Appendix B Phase-0 denominator and share-count bullets; `denominator_count_m` and `period_weighted_count_m` replace `share_count_m`; Stage-3 normalisation and convention row 4; induced-field row; C1; ledger and Card. | ADBE v7: a $7 split from 395M against 406M that the old ledger row reported as $0. |
| F2 | **Redaction by fixed lists, checked across dossiers.** Stage-1 redaction rule and redaction check; a redaction screener for all dossiers plus tag screeners per dossier (Appendix H); `final/redaction_check.md`. | ADBE v7: one rule, opposite calls; dossier A lost its share-count history. |
| F3 | **Versioned toolkit, replay gate, lean orchestrator.** VARIABLES `TOOLKIT`; a new section on the toolkit and the orchestrator's context; Stage 0/0.5 manifest hash; Stage-5b script text, self-test 6–9 and replay gate; machine-readable screener outputs; Artefacts. | Two tickers on two hand-written scripts; Stage-1c checks hand-coded to one dossier; orchestrator 30% of cost. |
| F4 | **Two-sided acquisition matching.** Appendix B Phase-0 acquisitions bullet and Acquisitions block; MACHINE SUMMARY fields; Stage-3 tabulation and acquisition rows; C1; ledger and Card; dossier guideline. | ADBE v7: 6 of 8 critiques; folded corrections of up to −$2.82 per finding; the reverse error in d8. |
| F5 | **No cliff in the margin arithmetic.** AT CAP in place of NO BUY at the 0.60 bound; L against `fair_value_macro_base`; Appendix A cases; Appendix B Margin and Mechanics; Stage-3 recompute; C7; Appendix F patch list; Appendix G constants; Card status. | ADBE v7 MECHANISM findings m4 #11 (about +10% headline jump at the cap) and w6 #12 (add-ons shrank L). |
| C1 | Consequential: preamble ("What v7.1 changes", "What v7.1 does NOT change", season comparability); the v7 sections are kept as history. | Scope statement. |
| C2 | Consequential: Open flags gain the v7.1 debate's unselected items and the rejected adaptive run count; O6 marked resolved by F2. | Record of what was considered. |
| C3 | Consequential: Known costs gain six v7.1 items. | Each edit has a price. |
| C4 | Independent review before release (35 findings, all addressed): count paths removed from the patch list and normalisation stated to critics and verifiers; `no_buy_reason_or_null`; explicit `fair_value_macro_base` patches; patchable acquisition declarations; induced rows for F1 and F4; `per_share_count_basis`; typed slot values in the diff; digit-boundary and note checks in the redaction check; currency-generic completeness; Appendix-H texts audited; checks, configuration and roll-up scripts shipped; pinned replay expectations; wording fixes. | A blocker (a share-count fix applied twice) and twelve major gaps. |

### v7.1 → v8 (2026-10-04)
Nine edits chosen after the AGX v7.1 execution: two four-agent debates on margin rules, a back-test on the season's executions and a run-time review (`claude/SPEC_v8_DEBATE_RECORD.md`).

| # | Edit | Why |
|---|---|---|
| G1 | **Continuous quality premium.** Appendix B Margin, MACHINE SUMMARY (`quality_premium`); Stage-3 recompute; Appendix A; C7; Appendix F patch note and MECHANISM; Appendix G; Card item 2. | Tier cliffs drove 64–79% of each investor's margin variance; the v7.1 label ("prices the bear branches") was contradicted by the trees. |
| G2 | **Eight seats.** Appendix B roster and Precedence; Mechanics; Stage 2; Stage-3 roster rule; C5; Appendices E, F and G; roll-up weights. | Victor's and Max's entry prices never entered the BUY and their fair values repeated the committee's; they cost about a fifth of each run's seat work. |
| G3 | **Margin-rule alternatives.** Stage 3; Stage 5; Card item 5 and slots; Appendix G; MECHANISM examples. | Debates 1 and 2: averaging was an expected loss; showing the set keeps the policy choice visible. |
| G4 | **Outcome ledger.** Appendix K; Stage 6; `forecast_5y`; `publish.py ledger`. | Margin-rule accuracy needs outcomes. |
| G5 | **Per-run data.** Stage 6; Artefacts; `publish.py data`. | GSL and DECK could not be back-tested. |
| S1 | **One committee script.** Appendix B Mechanics; Stage 2. | Tool calls, not tokens, set run time on AGX. |
| S2 | **Mechanics block, base and break schedules, complete input-change lines.** Appendix B Mechanics; C4; Appendices E and F; Stage 4b precedence. | Schedule tables were 9–28% of AGX run output, about half for non-base values. |
| S3 | **Per-run pipelining.** Rule O-1; Stages 4 and 4b. | Critics and verifiers waited for the slowest run. |
| S4 | **UNSCALED rule and bundle restore.** Appendix H tag screener; Stage 1c check 1; toolkit section. | The "(000s)" stop recurred on three tickers; transcription restore was slow. |
| R | **Review fixes before release** (32 findings, all addressed): Rule O-1 (pipelining by harness, per-launch listings, deletion on collection, k/j files and ledger/data orchestrator-only); S2 mechanics block and complete lines (B, C4, E, F, Stage 4b); `forecast_5y` and `forecast_definition`; `horizon_years`; Rule-8 score rule; Appendix K rewritten (two files, objective break event, tests with a loss); implied ratios and the EV × (1 − π) challenger; card item 5; roll-up after Stage 6; pooled-test cells by execution; script fixes (crash on a run with no eligible seat, roster patches, null trees, the step line's F5 decision, score range, `quality_premium` check, Σp-normalised EV, spec mode in outputs); self-tests and the v8 replay pinned; manifest, RESTORE and bundle. | `claude/SPEC_v8_DEBATE_RECORD.md`. |

### v8 → v9 (2026-10-06)
Seven edits drawn from the MELI v8 execution and the season's record (`claude/CHANGES_v9_simple.md`), with the spec owner's decisions on its four open questions (A: the run chooses the alternative denominator within a fixed definition; B: rebase the ERP; C: bar every fact the pack does not contain; D: one review round).

| # | Edit | Why |
|---|---|---|
| N1 | **No masking or rescaling; a pack-only rule.** Stage 1c writes the redacted dossier as each run's pack (k = j = 1); Stage 1d, the scale-dependence test (per ticker and pooled), the card's memory and bridge lines and the roll-up memory cells removed; the tag screener lists thinness and share counts only; Appendix B Inputs, Appendices E, F, G and H; Rule O-1 and O-2 text; VARIABLES. | Probes identified every company; the memory test never flagged; the Stage-1c checks were the most frequent stop. |
| N2 | **Alternative denominator.** Appendix B Phase 0, Mechanics and MACHINE SUMMARY (`alternative_denominator_basis`, `fair_value_alternative_denominator`); Stage-3 row; Stage-5 ledger; card lever ⟨CARD_L11⟩; C1; Appendices E, F and G; template conventions in Rule O-2. | MELI: five denominator definitions across eight runs, and the v8 alternative was never valued. |
| N3 | **Pre-write tree checks.** Appendix B Mechanics; Stage 2. | MELI: unrebuildable branches in 5 of 8 critiques; one run's seats out of the tree rules. |
| N4 | **ERP rebased.** Appendix J (⟨ERP_RAW⟩, ⟨ERP_RF⟩); Stage 0.5 check; season-inputs rules. | A 4.75%-basis ERP added to a 4.95% risk-free rate. |
| N5 | **Zero acquisition spend matched.** Stage 3; Appendix B Acquisitions; Appendix E. | Eight inert mismatches on MELI's card. |
| N6 | **Toolkit robustness.** Thinness parser; `quality_tier_modal`; verifier command (Appendix F). | Three MELI run-time problems. |
| N7 | **Housekeeping.** Auditor slots (Stage 0.5, Appendix H); dossier guideline; Stage-6 MECHANISM checklist (`extract.py mechanism`). | Recurring auditor flags; dossier statements about the pipeline; MELI's SPEC_FLAGS. |
| R | **Review fixes before release** (49 findings; all fixed or answered): the alternative's fair value defined mechanically (starting cash flow scaled, path held), its definition re-worded (any adjustment re-measured, either direction, no examples that point one way, "none" fully specified, sign and lender cases), script checks and card counts for it (direction, seats valued, n/a when unmeasured, non-positive values), its induced-field row, a patch to "none", and a pinned hand-computed fixture; the pack-only rule split into facts and assumptions, with remembered-fact patching and PACK-GAP limits; N5 keyed on the pack's acquisition cash; N3 made non-tautological; the ERP rebase limited to same-currency implied premiums with equation, range, currency and date checks; a fail-closed share-count list and a keep-list backstop; award prices on R-1; request statements removed from dossiers; mirroring timing for price-bearing files; comparability and Known-costs claims corrected, and no market price in the spec; Open flags for terminal growth and branch caps. The closing check's 12 further findings, and the 3 of its re-check (a share-count line stated in a currency unit, share tables in millions, a logged exemption list): card slot typing for n/a values, a share-count detector that reads both orders and ignores currency amounts in any format, the neutralising patch applied to every seat, the scaling check skipping seats that deduct acquisition spend, one definition of the alternative's value, the ERP source's series checked against the file's, one mirroring boundary, and wording residues. | `claude/SPEC_v9_REVIEW_RECORD.md`. |

### v9 → v10 (2026-10-14)
Six edits drawn from the ICE v9 execution, the season's record and a three-debater debate in which every ballot item was endorsed unanimously, with no veto (`claude/CHANGES_v10_simple.md`). The spec owner set the direction beforehand: no discount-rate add-ons; Simon merged into Walter; Walter's grade moves Walter's fair value only; FRAMEWORK hashed into the toolkit.

| # | Edit | Why |
|---|---|---|
| T1 | **Every seat at the macro base.** Appendix B Phase-0 macro bullet, Margin (discount rate, tail term, What each part prices), Mechanics, MACHINE SUMMARY (`erp_departure_reason_or_null` removed); Stage-3 rate check and induced row; C2; Appendices E and F (off-base finding; `frozen_arith.py rebase`; MECHANISM examples); Appendix A rebase case; Appendix G; card status. | 142 of 144 checkable seat rates above the average stock's expected return; add-ons asserted and in practice one-directional; one risk priced up to three times. |
| T2 | **Debt counted once, on cash flow to equity.** Appendix B Phase-0 debt bullet and frame fields; C1; Stage-3 debt check and debt row; Stage 4b and Appendix F (`undebt`); Stage-5 ledger; card lever ⟨CARD_L12⟩; Appendix A debt case; Appendix E. | ICE v9: net debt deducted from flows already after interest in all eight runs; open since v7.1. The three-basis rule of the debate was replaced in review by levered only (spec owner's decision on review finding P2). |
| T3 | **Sized risk register.** Appendix B risk register and `risks`; C6 and its Rule-3 reading; Stage-3 register check; Appendix E. | Add-ons co-moved with cuts in other channels (Spearman −0.34 to −0.46); the double-count check worked on labels. |
| T4 | **Seven seats.** Appendix B roster, seat mappings, Walter's and Alexander's fields; C5; Stage-3 roster and grade checks; Appendix A Walter case; Appendices F and G. | Simon's DCF repeats other seats at a shared rate; his gates survive in Walter; symmetry prevents a one-way multiplier. |
| T5 | **FRAMEWORK_v10 in the toolkit.** VARIABLES; Stage 0.5 and Stage 1 (copy and hash check); Appendix D; Precedence texts in B, E, F and Stage 4b; Known costs. | Every subagent read a contradicting FRAMEWORK; route (d) would have enforced it; no record of the version used. |
| T6 | **Season measurement.** Stage-3 channel monitor; `OUTCOME_BRIDGE.md` and `bridge.py`; Appendix K tests 3 and 5; roll-up columns; validation executions (Stage 0, Appendix G validation block, ⟨BASELINE⟩, `final/VALIDATION.md`). | The change cannot be replayed; the bridge, the validation runs and the monitor attribute it. |
| C | Consequential: preamble ("What v10 changes", "What v10 does NOT change", season comparability); the v9 and v8 sections kept as history; Rule O-2; toolkit section; Stage 0 list; Stage 5b modes, self-tests 16–17 and replay; Stage 6; Artefacts; Open flags (v10 debate items; four earlier flags resolved); Known costs. | Forced by T1–T6. |
| R | **Review fixes before release** (three reviewers; 55 findings: 4 blockers, 24 majors, 27 minors; `claude/SPEC_v10_REVIEW_RECORD.md`). Two overturn debated options, by the spec owner's decision: one debt basis, cash flow to equity (the three-basis rule let the basis move ICE's fair value by +$14 to +$49 and forced a double count on the financial basis), and a register that requires listing, not pricing, of items behind non-break branches, upside included (the 1% rule pushed value one way). Also: the rate checked against MARKET_INPUTS; `fair_value_macro_base` defined as a recomputation; the rebase holds the break value; `undebt`; register patch rules, signed sizes, BUY effects and the generic-haircut ban extended to scores; Walter's gates given criteria, preferred stock only as distress evidence, operating (not stock) returns, 0 where the pack is silent; NO BUY only for Walter's two FAILs; validation custody, fresh tokens, a hash-checked baseline, the unexplained share and its n/a rule; ICE marked in-sample; the debt row never the largest sensitivity; the rate induced row; a seat-mapping table; FRAMEWORK_v10 aligned word for word and audited at Stage 0.5. | `claude/SPEC_v10_REVIEW_RECORD.md`. |
