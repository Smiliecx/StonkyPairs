**Published BUY (trimmed mean of adjusted headlines): 239.056662 USD per share.** Blind intermediate: 237.143312.

Interval: 234.501392 to 243.611932 (half-width 4.555270 = t(0.90,6) 1.439756 × s 8.948914 ÷ √8). *80% confidence interval for this pipeline's expected BUY on these packs, with this model and this orchestration. A fresh execution's figure is expected within a range √2 wider. Neither range covers the items in the sensitivity ledger.* Replication range: 232.614537 to 245.498787.

Blind intermediate interval: 232.989388 to 241.297236 (s 8.160461).

Committee fair value (equal-weighted mean of weighted FV of headline seats, retained runs): 396.066529 (blind: 396.094599).

Retained runs (published): u7, w6, g9, m4, f8, n7. Retained runs (blind): w6, g9, m4, g8, f8, n7.

Descriptive: equal-weighted mean 237.047737; median 238.738325.

| run | dossier | blind | adjusted | joint delta | weighted FV (blind) | weighted FV (adjusted) | fold mode |
|---|---|---|---|---|---|---|---|
| u7 | A | 249.5382 | 244.0683 | -5.4699 | 398.6371 | 389.6452 | joint_changed_inputs |
| w6 | A | 237.2544 | 244.2915 | +7.0371 | 391.9106 | 405.4145 | joint_changed_inputs |
| g9 | A | 237.3403 | 239.3902 | +2.0499 | 403.4197 | 406.8436 | joint_changed_inputs |
| m4 | A | 239.8127 | 238.0864 | -1.7263 | 403.6368 | 400.5453 | joint_changed_inputs |
| g8 | B | 241.4615 | 245.6482 | +4.1867 | 403.6498 | 410.8560 | joint_changed_inputs |
| f8 | B | 236.6668 | 236.6668 | +0.0000 | 389.5916 | 389.5916 | no patches applied |
| d8 | B | 218.4343 | 216.3938 | -2.0405 | 369.7071 | 366.6832 | joint_changed_inputs |
| n7 | B | 230.3242 | 231.8367 | +1.5125 | 384.3590 | 384.3590 | joint_changed_inputs |

**Leave-one-out point estimates** (descriptive):

| run left out | point | change |
|---|---|---|
| u7 | 238.0543 | -1.0023 |
| w6 | 238.0097 | -1.0470 |
| g9 | 238.9900 | -0.0667 |
| m4 | 239.2507 | +0.1940 |
| g8 | 238.0097 | -1.0470 |
| f8 | 239.5346 | +0.4780 |
| d8 | 240.5007 | +1.4440 |
| n7 | 240.5007 | +1.4440 |

Most influential run: d8.

**Sensitivity ledger (not in the interval).** Each row: change in the published BUY, USD per share and in s_w units (s_w = 8.9489, adjusted headlines).

| row | counterfactual point | change | change (s_w) | note |
|---|---|---|---|---|
| Break probability −5pp on every headline seat | 251.1724 | +12.1158 | +1.354 |  |
| Break probability +5pp on every headline seat | 224.1487 | -14.9079 | -1.666 |  |
| Valuation date rolled to the pack date | 239.0567 | +0.0000 | +0.000 |  |
| Share-count date | 239.0567 | +0.0000 | +0.000 |  |
| Valuation date and share-count date (both) | 239.0567 | +0.0000 | +0.000 |  |
| Denominator on the period-weighted count instead of the per-share count | 235.8549 | -3.2018 | -0.358 |  |
| Acquisitions: every seat on the organic basis | 239.0567 | +0.0000 | +0.000 |  |
| Acquisitions: every seat including acquisitions | 239.0567 | +0.0000 | +0.000 |  |
| Alternative denominator: every seat on its run's alternative denominator | n/a | n/a | n/a | no headline seat reports fair_value_alternative_denominator; mean absolute per-run change 0.0000; runs above / below / none 1 / 5 / 0 (retained); seats valued 0 of 48 |
| Risk-free +50bp | 222.4510 | -16.6056 | -1.856 |  |
| Published figure without the single finding whose removal moves it most | 238.3326 | -0.7241 | -0.081 | run w6, finding 1 |
| Point rule: equal-weighted mean | 237.0477 | -2.0089 | -0.224 |  |
| Point rule: median | 238.7383 | -0.3183 | -0.036 |  |
| Dossier contrast: t, p and camp means | — | t = +1.3943, df 6, p = 0.2127 | camp means A 241.4591; B 232.6364 | adjusted headlines |

**Margin-rule alternatives (policy; not ledger rows; not in the interval; never averaged).** Each is the trimmed mean of the runs' own-weight headlines under that rule, on the Stage-5b patched summaries; constants fixed in the spec.

| rule | point | change against the published BUY | change (s_w) | blind point | implied expected upside ÷ downside (median over retained runs) |
|---|---|---|---|---|---|
| Published BUY (quality premium + p·L) | 239.0567 | — | — | 237.1433 | 6.08 |
| Step tiers (SPEC v7.1 rule) | 238.9465 | −0.1102 | −0.012 | 237.5152 | 6.00 |
| EV rule, tuned Victor (0.67 × tree expected value) | 230.5261 | −8.5305 | −0.953 | 228.9649 | 6.76 |
| Expectile rule, tuned Max (expected upside 7.75 × expected downside) | 224.6839 | −14.3727 | −1.606 | 223.3898 | 7.30 |
| EV × (1 − quality premium) (ledger only) | 248.3631 | +9.3064 | +1.040 | 246.4502 | 5.28 |

Unmeasured: dossier-builder variance (1 df with two dossiers); orchestrator variance (Stage 7 not run); model and harness effects.
