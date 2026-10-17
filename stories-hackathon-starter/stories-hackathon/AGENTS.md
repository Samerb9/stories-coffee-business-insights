# AGENTS.md — EECE490 Stories Coffee Hackathon

This file is the operating manual for any AI agent (Claude, Codex, Cursor, Copilot, etc.)
or human working in this repository. **Read it fully before writing any code or text.**
It contains: the brief decoded into requirements, hard rules, what we already know about
the data, the step-by-step plan, the specs for each candidate finding, and the final
quality gate.

If anything here conflicts with the hackathon brief, **the brief wins**. If anything here
conflicts with what the data shows when you rerun the scripts, **the data wins**; update
this file and say so in `docs/decision_log.md`.

---

## 0. TL;DR for an agent starting a session

1. Read sections 1–3 (the mission, the rules, the data).
2. Open `docs/decision_log.md` and `docs/assumptions.md` to see where the team left off.
3. Find your lane in section 11 (Person A or B), then the first unchecked phase in section 6, and continue from there.
4. Never ask the user a clarifying question about the brief. Decide, write the
   assumption down, keep going (rule R1).
5. Every number you put in prose must come from a script output in `outputs/`.
   Never type a number from memory or from this file into the README.

---

## 1. The mission (decoded from the brief)

**Audience:** Stories Coffee's CEO.
**What we must prove:** students at the start of their AI and data careers can produce
*useful business results*, meaning decisions and money, not dashboards.
**Data:** real Stories transaction data with replacement transaction IDs, delivered as is
(expect quality problems; finding them is part of the work).
**Competition:** Stories already has a data team that knows what each branch sells, and
it already has Claude and ChatGPT. Anything they could get from one prompt is worth
roughly zero.
**Graders:** AI agents that have already mined this dataset. They compare our work to
theirs. Original, valid, well-evidenced findings with clear business value rank highest.
A valid finding they missed can win. Technical complexity alone earns nothing.
**Deliverable:** one public GitHub repo URL per team, team member names clearly shown,
any format. *A one-paragraph conclusion with clear business value can beat extensive
visuals and code.* Evidence must be easy to inspect.

### 1.1 Requirement traceability (every sentence of the brief → where we satisfy it)

| ID  | Brief requirement | How we satisfy it | Where |
|-----|-------------------|-------------------|-------|
| B1  | Show the CEO useful business results | Lead with an executive paragraph: action + $ value + confidence | `README.md` §1 |
| B2  | Data has replacement IDs, delivered as is | Full data audit before analysis; document every cleaning choice | `docs/01_data_audit.md` |
| B3  | Basic sales summaries / "query my DB" earn no credit | Summaries appear only as context, never as findings; no chatbot | Rule R6 |
| B4  | Choose a business problem that matters | Explicit problem-selection scorecard | `docs/02_problem_selection.md` |
| B5  | Think deeply, challenge first explanation, consider other causes **and alternative decisions** | Each finding lists rival explanations and the test of each, plus the alternative actions considered | Finding template §7 |
| B6  | Chart/model is useful only if it supports a clear action | Every chart caption ends with "→ so Stories should…" | Rule R9 |
| B7  | Support conclusions with evidence | Every claim links to a table/figure and the script that made it | `outputs/`, `src/` |
| B8  | Check data quality | Data audit phase with pass/fail checks | Phase 1 |
| B9  | Test alternative explanations | Robustness/red-team phase | Phase 7 |
| B10 | Estimate business value, costs, tradeoffs | Value model per finding: benefit, cost to act, tradeoffs | Phase 5 |
| B11 | Explain which assumptions could change the action | Sensitivity table + "decision flips if…" line per finding | Phase 5 |
| B12 | If a model: compare with simple baseline | Seasonal-naive / mean baseline always reported beside the model | Phase 6 |
| B13 | If a model: test on unseen data | Time-based holdout (train ≤ Apr, validate May, test June) | Phase 6 |
| B14 | Explain weak areas, uncertainty, possible failures | "Limitations & how this could be wrong" per finding + README section | §7, README §8 |
| B15 | Identify missing information | Missing-data list (labour, rent, waste, supplier invoices, foot traffic…) | README §8 |
| B16 | A practical test Stories could run before wider use | A concrete pilot design per finding (who, where, how long, metric, success threshold) | §7, README §7 |
| B17 | Do not present correlation as proof of cause | Causal language only for designed comparisons (DiD); everything else says "associated with" | Rule R4 |
| B18 | Keep measured results separate from estimated benefits | Every number tagged `[MEASURED]`, `[ESTIMATED]` or `[ASSUMPTION]` | Rule R3 |
| B19 | Explain important choices and approaches rejected | Decision log + "Rejected approaches" section | `docs/decision_log.md`, README §9 |
| B20 | No questions allowed; make and state all assumptions | Assumptions register with ID, rationale, impact if wrong | `docs/assumptions.md` |
| B21 | Explain how important assumptions affect conclusions | Each assumption has a "decision impact" column (none / changes size / flips action) | `docs/assumptions.md` |
| B22 | Keep assumptions separate from observed facts | Separate sections and tags; never mix in one sentence without a tag | Rule R3 |
| B23 | One public repo URL; team names clear | Names on line 3 of README; repo set to public before submission | Phase 9 |
| B24 | Make evidence easy to inspect | Flat repo, one-command rerun, numbered docs, every number in `outputs/key_numbers.json` | §4, Phase 8 |
| B25 | Original findings rank higher | Prioritise non-obvious findings and deeper versions of obvious ones (decompositions, designed tests, break-evens, null results) | Phase 3 |
| B26 | Technical complexity alone earns no credit | Simplest method that answers the decision; complexity must justify itself vs a baseline | Rule R8 |

---

## 2. Hard rules (non-negotiable)

- **R1 — No clarifying questions about the brief.** When something is ambiguous (a column
  meaning, whether prices include VAT, what a branch is), pick the most reasonable
  reading, log it in `docs/assumptions.md` with an ID (`A#`), and continue.
- **R2 — Never modify raw data.** `data/raw/` is read-only. All cleaning happens in code
  and writes to `data/processed/`.
- **R3 — Tag every number.**
  - `[MEASURED]` = computed directly from the data (e.g. "Garden gross margin was 46.9% Jan–Jun 2026").
  - `[ESTIMATED]` = derived using one or more assumptions (e.g. "≈$32K/yr recoverable, A3, A4").
  - `[ASSUMPTION]` = something we chose to believe (always with its `A#`).
  Estimated benefits are never written as if they were measured results.
- **R4 — Causality discipline.** Use causal verbs ("caused", "drove", "increased because")
  only when backed by a designed comparison (difference-in-differences with a control,
  placebo tests). Otherwise write "is associated with", "coincides with", "is consistent with".
- **R5 — Every finding must end in an action.** Format: *who* does *what*, *where*, *by
  when*, expected value, and how we would know it worked.
- **R6 — No "summary as finding".** "Iced Latte is the top seller" or "Harbour has the
  most revenue" is context, not a finding. A finding changes a decision.
- **R7 — Reproducibility.** One command (`python -m src.run_all`) regenerates every table,
  figure and `outputs/key_numbers.json` from the raw CSV. Fixed random seeds (`SEED=490`).
- **R8 — Baseline before sophistication.** Any model is reported next to a naive baseline
  on a time-based holdout. If it doesn't clearly beat the baseline, say so and don't use it.
- **R9 — Charts serve decisions.** Each figure has a title that states the takeaway, labelled
  axes with units, a source line (script + date range), and a caption ending "→ action".
  No pie charts, no 3D, no charts that just restate totals.
- **R10 — Report uncertainty.** Confidence intervals (bootstrap or robust SE), sample sizes
  (n) next to every rate or lift, and a plain-language "how sure are we" line.
- **R11 — Numbers in prose come from `outputs/key_numbers.json`.** Scripts write every
  headline number there; the README quotes them. If you change code, rerun and re-sync
  the README. Never copy the preliminary numbers in §3.3 into the README directly.
- **R12 — Plain business English.** Write for a CEO: short sentences, dollars and
  percentages, no jargon without a one-line explanation. Technical detail goes in `docs/`.
- **R13 — Honesty over polish.** A null result (e.g. "the promotion did not pay back")
  or a data limitation (e.g. "customer IDs carry no behavioural signal") is a valid and
  valuable finding. Never stretch evidence to make a finding look bigger.
- **R14 — Don't leak private info.** No personal emails or phone numbers in the repo. Team
  names only.

---

## 3. The data

### 3.1 File

`data/raw/stories_transactions.csv`, about 5 MB, 51,177 rows (one row = one product line
in a transaction). See decision D1 in §8 about whether the raw file is committed.

### 3.2 Data dictionary (as understood; meanings are assumptions where noted)

| Column | Type | Meaning / notes |
|--------|------|-----------------|
| `Transaction ID` | str | Replacement ID (`SYN-#######`). One ID = one receipt; multiple rows per receipt. |
| `Date` | date | 2026-01-01 → 2026-06-30 (181 days). |
| `Time` | time | 07:00:00 → 23:59:56. Same for all lines in a transaction. |
| `Branch` | cat | `Harbour`, `Garden`, `Uptown`. |
| `Customer ID` | str / blank | `C#####`; blank = anonymous (~36% of lines). See trap T3. |
| `Order Type` | cat | `Dine-in` / `Takeaway`. |
| `Product` | cat | 45 products. |
| `Category` | cat | 9: Bakery, Hot Coffee, Matcha & Tea, Cold Coffee, Cold Drinks, Desserts, Sandwiches, Breakfast, Meals. |
| `Quantity` | int | 1 or 2. |
| `Unit Price (USD)` | float | List price before discount. A5: assumed to include VAT. |
| `Discount Rate` | float | 0, 0.10 or 0.15. |
| `Unit Cost (USD)` | float | Per-unit cost. A6: assumed to be COGS only (ingredients and packaging), not labour or rent. **Critical assumption for F1.** |
| `Line Revenue (USD)` | float | = Quantity × Unit Price × (1 − Discount). Verified exact on all rows. |
| `Line Gross Profit (USD)` | float | = Line Revenue − Quantity × Unit Cost. Verified exact on all rows. |

### 3.3 Preliminary facts from the first exploration

*Status: discovered in an exploratory pass. Phase 1–4 scripts must reproduce each one
before it is used. Numbers may shift slightly after deduplication.*

**Structure**
- 33,887 transactions, 3,494 distinct customer IDs, 45 products, 3 branches.
- Basket size: 54% single-line, 42% two lines, 5% three lines; never more than 3.
- No missing values except `Customer ID`. No negative or zero prices, quantities or margins.

**Data-quality items**
- 132 exact duplicate rows (all columns identical, same transaction), ≈$741 revenue.
  Genuine doubles are recorded as `Quantity = 2` (2,910 lines), so these look like double scans.
- IDs prefixed `SYN-`; many patterns are exact constant multipliers. The data appears
  generated or perturbed. A1 treats it as representative of Stories' business anyway.

**Prices and costs (the strongest money signal)**
- Each product has **one fixed price per branch**, unchanged for 6 months. Garden ≈ 4.8%
  below Harbour, Uptown ≈ 8.6% below Harbour, identical across all 45 products.
- **Garden's unit cost ≈ 1.43× Harbour's on every product** (range 1.426–1.439), every
  week, every category. Uptown ≈ 0.96× Harbour.
- Gross margin: Harbour 65.0%, Uptown 62.6%, **Garden 46.9%**.
- Margin bridge Harbour → Garden (18 pts): **cost −15.9 pts**, price −1.8 pts, mix −0.4 pts.
- Garden excess cost vs Harbour cost basis: ≈ $15.9K in 6 months; June run-rate ×12 ≈ $38.6K/yr.

**Promotions and discounts**
- **15% promo:** Harbour only, 9 SKUs (Brownie, Cheesecake Slice, Coffee Frappe, Cold Brew,
  Frozen Yoghurt Cup, Iced Americano, Iced Latte, Iced Mocha, Tiramisu Cup), two windows:
  Mar 12–19 and May 12–19. 100% of those SKU lines at Harbour in-window are discounted.
  Discount given ≈ $472.
  - DiD (log daily promo units, branch + date fixed effects, robust SE): lift ≈ +11%,
    95% CI ≈ [−6%, +28%].
  - Break-even lift at Harbour's 65.5% margin = 0.15 / (0.655 − 0.15) ≈ **+30%**. The upper CI is below break-even.
  - No halo on non-promo items (≈ +0.3%, CI ±9%).
- **10% discount:** ~5.6% of lines, flat across category, hour, branch, basket size and
  customer type. Untargeted; ≈ $1,707 given in 6 months. Purpose unknown (A9).

**Time patterns**
- Transactions grow ≈ +50% Jan → Jun, evenly across branches. No outlier days after
  controlling for weekday and trend (residual SD ≈ 7%).
- **Tuesday ≈ 1.66× other weekdays** (≈285 vs ≈171 tx/day), stable in every month, every
  hour, both order types, known and anonymous customers. Same basket size, no discounts.
  Saturday is the lowest day (≈129).
- Peak hour is 21:00; 44% of transactions happen at 19:00 or later. At 19:00 the mix
  flips: hot coffee share 18% → 11%, matcha 12% → 20%, cold coffee 13% → 17%, desserts
  7% → 11%. 07:00–10:00 is bakery and hot coffee.

**Branch mix**
- Category share index vs the 3-branch average: Garden desserts 1.28; Uptown sandwiches
  1.31; Harbour sandwiches 0.84, desserts 0.90. Everything else within ±5%.

**Baskets** (compute lift *within multi-item baskets only*; see trap T4)
- Cold Drinks × Sandwiches/Meals ≈ 1.9× lift (lunch pairing). Matcha & Tea × Bakery 1.23×.
- Pairs: Sparkling Water + Turkey & Cheese 2.55× (n=31), Strawberry Matcha + Cinnamon Roll
  1.66× (n=57), Vanilla Latte + Almond Croissant 1.66× (n=36), Iced Matcha + Pistachio
  Cookie 1.54× (n=69).
- Food attach rate among baskets with a drink: 41% overall; matcha 46%, hot coffee 41%,
  cold drinks 38%, **cold coffee 38%**.

**Customers: likely a null result**
- 94% of IDs visit more than one branch. Top-branch share 56.5% vs 56.0% under random
  assignment. Repeat-product share 17.3% vs 17.8% shuffled. Frequency H1 vs H2
  correlation −0.02; average ticket H1 vs H2 −0.03. Known and anonymous customers have
  identical baskets.
- Interpretation: IDs behave like random labels (possibly scrambled in anonymisation, A8).
  Customer-level analytics (RFM, CLV, churn, segmentation) would be fitting noise.

### 3.4 Known traps (read before analysing)

- **T1 Duplicates.** Drop the 132 exact duplicates for the main analysis. Rerun headline
  numbers with them kept as a sensitivity check.
- **T2 Cross-branch prices ≠ price elasticity.** Relative prices are identical within every
  branch and constant over time, so demand response cannot be estimated from this data.
  Branch volume differences are confounded with location and size.
- **T3 Customer IDs.** Test for signal before using them (F3). Don't build segments on noise.
- **T4 Basket lift bias.** With 54% single-item baskets, lift over all baskets is pushed
  below 1 for almost every pair. Use multi-item baskets, report n, and add bootstrap CIs.
- **T5 Promo windows contain different weekdays and sit on a growth trend.** Use date
  fixed effects and control branches, not raw before/after.
- **T6 Weekday composition.** Any period comparison must control for the Tuesday effect.
- **T7 Growth trend.** Annualising from January understates and from June overstates.
  Report both or use the full-period average, and say which.
- **T8 Synthetic-looking data.** Constant multipliers mean "statistically significant" is
  easy. Focus on size, value and decision relevance, not p-values.

---

## 4. Repository layout (target)

```
.
├── README.md                  # THE deliverable: names, 1-paragraph conclusion, findings, evidence links
├── AGENTS.md                  # this file
├── requirements.txt           # pandas, numpy, scipy, matplotlib, statsmodels (pin versions)
├── data/
│   ├── raw/                   # stories_transactions.csv (read-only; see D1)
│   └── processed/             # clean.parquet / clean.csv, transactions.csv (1 row per receipt)
├── src/
│   ├── config.py              # paths, SEED=490, promo windows, branch list
│   ├── load.py                # load + rename columns + types
│   ├── audit.py               # Phase 1 checks → outputs/tables/audit_*.csv
│   ├── clean.py               # dedup, derived fields → data/processed/
│   ├── f1_garden_cost.py      # F1
│   ├── f2_promo_eval.py       # F2
│   ├── f3_customer_signal.py  # F3
│   ├── f4_baskets.py          # F4
│   ├── f5_demand_timing.py    # F5 (+ optional forecast model)
│   ├── f6_discount_policy.py  # F6
│   ├── f7_uptown_pricing.py   # F7
│   ├── value_model.py         # Phase 5: value + sensitivity for all findings
│   ├── numbers.py             # helper: record(key, value, tag, source) → key_numbers.json
│   └── run_all.py             # runs everything in order
├── outputs/
│   ├── numbers/<module>.json  # each script writes its own file (no merge conflicts)
│   ├── key_numbers.json       # merged by run_all: every headline number, with tag + source script
│   ├── audit_report.md        # generated by src/audit.py
│   ├── tables/                # CSV evidence tables (small, human-readable)
│   └── figures/               # PNG charts (one per key claim, max ~8 total)
└── docs/
    ├── 01_data_audit.md
    ├── 02_problem_selection.md
    ├── 03_findings/           # one .md per finding using the §7 template
    ├── assumptions.md         # A# register
    ├── decision_log.md        # D# choices + rejected approaches
    └── pilot_designs.md       # test Stories can run before wider use
```

Keep the tree flat. A grader should reach any piece of evidence in at most two clicks from README.

---

## 5. Writing conventions

- **Tags:** `[MEASURED]`, `[ESTIMATED]`, `[ASSUMPTION A#]`. Put them right after the number.
- **Money:** USD, `$15.9K` style in prose, full precision in tables. Always say the period
  (e.g. "Jan–Jun 2026", "per year at June run-rate").
- **Rates:** always with n (e.g. "38% attach rate, n = 6,168 cold-coffee baskets").
- **Intervals:** "95% CI [a, b]".
- **Verbs:** see R4.
- **Finding titles** are full-sentence claims that include the action:
  "Garden pays 43% more per unit than Harbour for identical products; auditing its supply costs is worth ≈$30–39K/yr."

---

## 6. Step-by-step plan

Priority order if time is short: **Phase 0 → 1 → F1 → F2 → F3 → Phase 5 → Phase 8 → Phase 9.**
F4–F7 and the model in Phase 6 are add-ons. A tight README with three strong findings
beats a sprawling one with eight.

### Phase 0 — Setup (≈30 min)
- [ ] Create the repo structure in §4. Add `.gitignore` (data/raw per D1, `__pycache__`, `.ipynb_checkpoints`).
- [ ] `requirements.txt` with pinned versions; confirm `python -m src.run_all` runs end to end on an empty pipeline.
- [ ] `src/config.py`: paths, `SEED = 490`, branch list, promo windows (derived from data in Phase 1, not hard-coded guesses).
- [ ] `src/numbers.py`: `record(key, value, tag, source, note="")` appends to `outputs/key_numbers.json`.
- [ ] Put team member names in README line 3 now (placeholder until the team fills it).
- [ ] Create empty `docs/assumptions.md` and `docs/decision_log.md` and seed them from §8.

**Done when:** a fresh clone plus the raw CSV runs `python -m src.run_all` without errors.

### Phase 1 — Data audit (B2, B8) (≈1–1.5 h)
Write `src/audit.py`, which outputs `outputs/tables/audit_checks.csv` (check, result, pass/fail, rows affected) and `docs/01_data_audit.md`.
- [ ] Schema: column names, dtypes, row count, date and time range, unique counts.
- [ ] Missingness per column; anonymous share of lines and transactions by branch.
- [ ] Arithmetic integrity: revenue and GP recompute (tolerance $0.01).
- [ ] Transaction consistency: one date, time, branch, customer and order type per transaction ID.
- [ ] Duplicates: exact duplicate rows; same product repeated in a transaction; compare with `qty = 2`. Decide (D2) and record.
- [ ] Range checks: price, cost, discount values, cost < price, opening hours.
- [ ] Price and cost stability: per product × branch, std of price and cost over time (expect 0). Per product, the branch ratio.
- [ ] Discount census: which values, where, when (this is how the promo windows are discovered).
- [ ] Calendar coverage: every branch has every day; daily counts; residual outliers after weekday and trend.
- [ ] Synthetic-data signals: list them neutrally (prefix, constant multipliers) and state A1.
- [ ] Write the audit doc: what we checked, what we found, what we did, and what each issue means for the conclusions.

**Done when:** each check has a pass/fail result and a stated treatment, and `data/processed/clean.*` exists.

### Phase 2 — Broad exploration and hypothesis log (≈1–1.5 h)
Goal: generate many candidate findings cheaply, then kill most of them.
- [ ] Build `transactions.csv` (one row per receipt: branch, datetime, weekday, hour, customer, order type, lines, items, revenue, GP, any discount, has drink, has food, drink category).
- [ ] Explore across: branch × {margin, price, cost, mix}, time {month, week, weekday, hour}, discount {who, what, when}, baskets {size, pairs, attach}, customers {frequency, loyalty, persistence}, order type.
- [ ] For each pattern write one line in `docs/02_problem_selection.md`: *observation → possible business decision → rough $ size → would the graders' agents find it? → originality angle*.
- [ ] Explicitly test the three questions the team raised: (a) products sold together, (b) what recurring customers buy, (c) what cross-branch price differences mean. Record the answer to each, including "not answerable, and why".

**Done when:** at least 10 candidate hypotheses are logged with a rough value and a keep/kill decision.

### Phase 3 — Choose the problem(s) (B4, B25) (≈30 min)
Score each candidate 1–5 on:
1. **Business value ($)**: size of the money at stake.
2. **Actionability**: can Stories act within a month?
3. **Evidence strength**: designed comparison > robust pattern > correlation.
4. **Originality**: would a generic agent pass miss it, or miss the *depth* (decomposition, break-even, null test, pilot)?
5. **Effort**: can we finish it well in the time left?

Expected outcome (confirm with the scorecard; don't just accept it):
- **Headline:** F1 Garden cost gap (largest $, clear action).
- **Method showcase:** F2 promo evaluation (designed comparison, break-even, null result).
- **Data-quality credibility:** F3 customer-ID signal test (prevents a costly wrong analysis).
- **Supporting:** F4 baskets/attach, F5 Tuesday and evening operations, F6 discount policy, F7 Uptown price test.

Write the decision and the rejected candidates (with reasons) to `docs/decision_log.md`.

### Phase 4 — Deep analysis per finding (B5, B7, B9, B17)
For each chosen finding, follow its spec in §7 and produce:
- [ ] `src/fN_*.py` → `outputs/tables/fN_*.csv` + at most 2 figures + `record()` calls.
- [ ] `docs/03_findings/fN_*.md` using the finding template (§7.0).
- [ ] At least two rival explanations, each with the test run and its result.
- [ ] The alternative *decisions* considered (not just alternative causes) and why the recommended one wins.

### Phase 5 — Business value, costs, tradeoffs, sensitivity (B10, B11, B18, B21)
`src/value_model.py`:
- [ ] For each finding: benefit formula, inputs (tagged measured or assumed), cost to act, tradeoffs (e.g. supplier switch → quality risk; price rise → volume loss).
- [ ] Three scenarios: conservative, base, optimistic. Annualise two ways (full-period average and June run-rate) and say which is the headline.
- [ ] Sensitivity: vary each key assumption and report the value at which **the recommended action flips** (e.g. "if less than X% of Garden's cost gap is closable, the audit still pays because its cost is only ~$Y").
- [ ] Output `outputs/tables/value_summary.csv`: finding, measured basis, estimated value (low/base/high), key assumption, flip point.

### Phase 6 — Optional model (B12, B13, B26)
Only if it supports an action (staffing and prep for Tuesday and evening peaks, F5).
- [ ] Target: daily transactions per branch (and optionally an hourly profile).
- [ ] Split: train Jan–Apr, validate May, **test June** (never tune on June).
- [ ] Baselines: seasonal naive (same weekday last week), and a weekday-mean baseline.
- [ ] Model: log-linear trend + weekday + branch (interpretable). Anything fancier must beat this.
- [ ] Metrics: MAE and MAPE per branch on June, model vs baselines, in a table.
- [ ] Translate to action: e.g. staff-hours by branch × weekday × shift, using an explicit `[ASSUMPTION]` of transactions per staff-hour.
- [ ] If the model doesn't clearly beat the baseline, report that and recommend the baseline.

### Phase 7 — Robustness and red-team (B5, B9, B14)
For every headline number:
- [ ] Rerun with duplicates kept (T1). Rerun excluding the first and last weeks (partial weeks).
- [ ] Split-half stability: Jan–Mar vs Apr–Jun; does the finding hold in both?
- [ ] Placebo tests where a designed comparison is used (F2: fake promo windows at Harbour).
- [ ] Try to refute it: write the strongest argument *against* the finding, then test it or state why it can't be tested.
- [ ] Fresh-eyes review: a separate agent or person who hasn't seen the work reads only README + `docs/03_findings/` and lists the weakest claims. Fix or soften them.

### Phase 8 — Write-up (B1, B6, B19, B22, B24)
- [ ] `README.md` per the template in §9. The one-paragraph conclusion goes first and has to stand alone.
- [ ] Every number in the README appears in `outputs/key_numbers.json` (write a tiny check script).
- [ ] ≤ 8 figures total, each with a takeaway title and an action caption.
- [ ] `docs/pilot_designs.md`: one pilot per recommended action.
- [ ] Rejected approaches section filled in (§8.3).

### Phase 9 — Final QA and submission (B23)
- [ ] Run the final checklist in §10. Every box ticked.
- [ ] Fresh clone → `pip install -r requirements.txt` → `python -m src.run_all` → outputs identical.
- [ ] Repo set to **public**. Team names visible in README. Submit **one** URL for the team.

---

## 7. Finding specifications

### 7.0 Finding template (`docs/03_findings/fN_name.md`)

```
# FN — <claim + action in one sentence>
## Decision this informs
## What we measured            [MEASURED] facts only, with n and CI; link tables/figures
## Why we believe it           method; why this method; what it controls for
## Rival explanations tested   explanation → test → result → verdict
## Alternative decisions considered and why the recommendation wins
## Business value              formula; inputs tagged; low/base/high; annualisation basis
## Assumptions that could change the action   A# → what happens if wrong → flip point
## Weak areas & how this could be wrong
## Missing information that would sharpen it
## Pilot Stories can run before wider rollout  who/where/how long/metric/success threshold/stop rule
## Reproduce                   script name + output files
```

### F1 — Garden's unit costs are ~43% higher than Harbour's (headline)
**Decision:** should Stories audit and fix Garden's supply costs, and how much is it worth?
**Method**
1. Per product: Garden cost ÷ Harbour cost and ÷ Uptown cost; distribution across 45 products; weekly stability (26 weeks).
2. Margin bridge Harbour → Garden GM: sequentially swap mix, then price, then cost. Report each effect in GM points and dollars.
3. Excess cost dollars = Σ Garden qty × (Garden cost − Harbour cost), by category and top 10 SKUs (Pareto: where should the audit start?).
4. Interaction with branch mix: Garden over-indexes on desserts (index 1.28). Are high-cost-dollar categories also its over-indexed ones?

**Rival explanations to test or argue**
- Unit cost includes overheads (rent, labour) allocated differently at Garden (A6). *Test:* the ratio is the same constant for a $0.57 tea and an $8 salad bowl, which suggests a single multiplier such as supplier markup or allocation factor rather than ingredient differences. The data can't distinguish further. State it.
- Bigger portions or premium recipe at Garden. *Counter-evidence:* Garden prices are lower, not higher.
- Waste or shrink booked into unit cost. Can't test without waste logs (missing info).
- Data or anonymisation artefact. Acknowledge (A1).

**Alternative decisions:** raise Garden prices to Harbour level (closes only ~1.8 pts of 18); renegotiate Garden's suppliers; move Garden to Harbour's supplier or central purchasing; do nothing (show the cost of inaction).
**Value:** closable share s × excess cost. Scenarios s = 25% / 50% / 100%. Annualise on the full-period average (≈$32K/yr at 100%) and the June run-rate (≈$38.6K/yr at 100%). Cost to act: an audit (a few days of finance time, `[ASSUMPTION]`).
**Pilot:** 2-week invoice audit comparing Garden vs Harbour purchase prices for the top 10 excess-cost SKUs; switch 3–5 SKUs to Harbour's supplier for 4 weeks; success = Garden unit cost on those SKUs within 5% of Harbour's with no change in units sold.

### F2 — Harbour's 15% promotion did not pay for itself (method showcase)
**Decision:** should Stories repeat this promotion format?
**Method**
1. Identify windows and SKUs from the data (already: Mar 12–19, May 12–19; 9 SKUs).
2. Difference-in-differences on daily log units of promo SKUs: Harbour vs Garden and Uptown, with branch and date fixed effects (absorbs weekday and trend; T5, T6), robust SEs. Report the pooled estimate and each window separately.
3. Triple-difference variant: promo SKUs vs non-promo SKUs within each branch.
4. Halo checks: non-promo units, transactions per day, basket size at Harbour in-window.
5. Post-window dip (pull-forward): the 14 days after.
6. **Placebo:** rerun the DiD on many fake 8-day windows at Harbour outside the promo; show where the real estimate sits in the placebo distribution.
7. Break-even lift = d / (m − d) at Harbour's list-price GM on promo SKUs (≈ +30%).

**Rival explanations:** seasonality or weather (handled by date fixed effects and controls); spill-over to control branches (customers travel between branches, so there is a small downward bias, discussed); small sample (two 8-day windows: report the CI honestly).
**Value:** discount cost vs incremental GP at the point estimate and the CI bounds. Dollars are small, so frame the value as **a decision rule**: "only run discounts whose expected lift exceeds d/(m−d); always hold out a control branch".
**Pilot:** next promo, randomise which branch and which week gets it, keep one control branch, and pre-register break-even lift as the success threshold.

### F3 — Customer IDs carry no usable behavioural signal (data-quality credibility)
**Decision:** should Stories invest in loyalty or CRM analytics using its current customer IDs?
**Method:** permutation tests (≥1,000 shuffles, `SEED`), each with an empirical p-value:
1. Branch loyalty: observed top-branch share vs IDs randomly reassigned to transactions.
2. Product and category repeat: observed vs products shuffled across customers within the same time slot.
3. Frequency persistence: H1 vs H2 visit counts (Spearman) vs shuffled.
4. Ticket persistence: H1 vs H2 average ticket.
5. Known vs anonymous: baskets, ticket and discount rate compared.

**If the null holds:** customer-level work (RFM, CLV, churn, segmentation) goes in "rejected approaches" *with this evidence*. Recommendation: fix ID capture (loyalty app or phone number at POS) before any CRM spend. Value = avoided cost of a CRM or segmentation project built on noise (`[ASSUMPTION]` cost).
**If signal appears:** proceed with a simple segment analysis and report effect sizes vs the shuffled baseline.

### F4 — Pairings and the food attach gap (supporting)
**Decision:** which pairing prompts or bundles to test, and where.
**Method:** lift and conditional probability within multi-item baskets (T4); min n = 25; bootstrap 95% CI on lift; category-level drink × food crosstab with χ². Attach rate by drink category, branch, hour band, order type.
**Value (estimated):** e.g. raising cold-coffee food attach from 38% to matcha's 46% → extra food units × average food GP/unit (≈$1.7K per 6 months; small, so present it honestly). Any bundle discount must clear the same break-even logic as F2.
**Rival explanations:** time of day drives both (cold drinks and sandwiches are both lunch). Control by hour band. Co-purchase is association, not "promoting X causes Y" (R4).
**Pilot:** a barista prompt ("add a pastry?") for cold-coffee orders at one branch for 2 weeks vs another; metric = attach rate.

### F5 — Tuesday and evening demand (operations, supporting)
**Decision:** staffing and prep schedule by branch × weekday × hour.
**Method:** tx/day by weekday per branch (with CIs), stability by month; hour × category profile; peak-hour load (tx/hour at 21:00 by branch × weekday). Optional forecast model per Phase 6.
**Rival explanations (state them; the cause is not identifiable):** a recurring Tuesday event, a partner offer not recorded in the discount field, or a data artefact. Recommend Stories check with branch managers. Saturday is the weakest day, which is a candidate for a traffic-building test.
**Value:** needs a labour-cost assumption (not in the data). Give a formula and a sensitivity range, clearly `[ESTIMATED]`.
**Pilot:** shift one barista-shift from Saturday to Tuesday evening at Harbour for 4 weeks; metric = Tuesday 19:00–23:00 wait time or abandoned orders (data Stories would need to start collecting) and sales.

### F6 — The 10% discount is untargeted (supporting)
**Method:** discount incidence by every dimension (all flat ≈5.6%); basket size and ticket with vs without the discount; total dollars given.
**Interpretation:** without a reason code we can't tell whether it is a staff, loyalty or manager discount (A9). It shows no association with bigger baskets.
**Action:** add a discount reason code at POS; run a 4-week holdout where one branch stops the discount; metric = transactions and GP vs control branches.

### F7 — Uptown's price level is a testable opportunity, not a finding (supporting)
**Why it matters:** this answers the team's question about cross-branch price differences honestly.
**Fact:** Uptown prices are ≈8.6% below Harbour's on every SKU, and Garden's are ≈4.2% above Uptown's. Uptown's gross margin (62.6%) is close to Harbour's (65.0%).
**What we can't say:** anything about price sensitivity (T2).
**Value scenarios:** move Uptown to Garden's level → +$2.3K GP per 6 months if volume holds; break-even volume loss ≈6.3%. Move to Harbour's level → +$5.2K; break-even loss ≈13%.
**Pilot:** raise 10 SKUs at Uptown by 4% for 4 weeks; DiD on units vs the same SKUs at other branches and untouched Uptown SKUs; stop if units fall more than the break-even.

---

## 8. Registers to seed

### 8.1 Assumptions (`docs/assumptions.md`), seed list. Format: ID | assumption | why reasonable | impact if wrong (none / size / flips action)
- **A1** The data, though it looks generated or perturbed, reflects Stories' real business patterns. *Impact: flips everything if wrong; unavoidable.*
- **A2** Branch names are anonymised real branches with comparable opening hours (07:00–24:00).
- **A3** Garden's cost gap is at least partly closable (closable share is a scenario variable). *Impact: size.*
- **A4** Annualisation: headline uses the full-period average; June run-rate shown as the upper case. *Impact: size.*
- **A5** Prices are VAT-inclusive. *Impact: size of revenue figures only.*
- **A6** Unit cost = COGS (ingredients and packaging), not allocated overhead. *Impact: if wrong, F1 becomes an accounting-allocation question rather than a supplier question; the action changes from renegotiating to reviewing the allocation.*
- **A7** Promo SKUs and windows inferred from the 15% discount lines are the complete promotion.
- **A8** Customer IDs may have been scrambled in anonymisation; real IDs might carry signal. *Impact: F3's recommendation becomes "re-test on raw IDs".*
- **A9** The 10% discount's purpose is unknown; treated as discretionary.
- **A10** Duplicate rows are double-scans, not real sales. *Impact: negligible (≈$741).*
- **A11** No major external events (closures, holidays) affected specific days beyond what the weekday and trend controls absorb.
- **A12** Labour cost per staff-hour (for F5) is an external assumption; give a range.

### 8.2 Decision log (`docs/decision_log.md`), seed list
- **D1** Raw data in a public repo: the brief calls it "real transaction data". Default: **do not commit the raw CSV**; commit scripts and aggregated evidence tables, and explain in the README how to place the file. The graders already have the dataset. (Team may override; log it if so.)
- **D2** Drop exact duplicates in the main analysis; keep them in a sensitivity check.
- **D3** Basket lift computed on multi-item baskets only (T4).
- **D4** Promo evaluation via DiD with date fixed effects rather than raw before/after (T5).
- **D5** Interpretable models only; ML only if it beats the interpretable model on the June holdout.

### 8.3 Rejected approaches (README §9)
- Sales dashboards and top-product rankings: the brief says they earn no credit; Stories' data team already has them.
- "Chat with your database" / LLM query interface: explicitly excluded by the brief.
- RFM, CLV, churn or customer segmentation: customer IDs show no behavioural signal (F3).
- Price-elasticity estimation from cross-branch prices: no within-branch or over-time price variation (T2).
- Association rules on all baskets: biased by single-item baskets (T4).
- Deep-learning or complex forecasting: no evidence it beats an interpretable baseline (Phase 6). Complexity earns no credit.
- Causal claims about the Tuesday spike: cause not identifiable from the data.

---

## 9. README template (the deliverable)

```
# Stories Coffee — <one-line headline with $ value>
**Team:** <Name 1>, <Name 2>, <Name 3>, <Name 4>     (EECE490 Stories Coffee Hackathon)

## 1. Conclusion (read this if nothing else)
<One paragraph, ≤120 words: the action, the $ value [ESTIMATED] with its basis, the key
measured fact [MEASURED], confidence, and the first step Stories should take this month.>

## 2. Recommended actions
| # | Action | Owner | Value (low/base/high, per yr) | Confidence | First step / pilot |

## 3. Findings (one short section each: claim → evidence link → value → caveat)
## 4. Data quality: what we checked and what we fixed            → docs/01_data_audit.md
## 5. Facts vs assumptions vs estimates (table)                    → docs/assumptions.md
## 6. What would change our recommendation (flip points)
## 7. Tests Stories should run before wider rollout                → docs/pilot_designs.md
## 8. Limitations, uncertainty and missing information
## 9. Approaches we rejected and why
## 10. Reproduce: `pip install -r requirements.txt && python -m src.run_all`
```

---

## 10. Final checklist (graders' view; every box must be ticked)

**Business value**
- [ ] The first paragraph alone tells the CEO what to do, what it's worth, and how sure we are.
- [ ] Each finding changes a decision; none is a basic sales summary.
- [ ] Value estimates show low/base/high, cost to act, and tradeoffs.

**Evidence and rigour**
- [ ] Data-quality checks are documented, with treatments and their impact.
- [ ] Each finding has at least two rival explanations tested or argued.
- [ ] Correlation is never stated as cause; causal claims rest on DiD and placebo tests.
- [ ] Any model beats a baseline on held-out June data, or we say it doesn't.
- [ ] Sample sizes and CIs appear next to rates, lifts and effects.
- [ ] Results hold in split-half and with duplicates kept, or the difference is reported.

**Honesty**
- [ ] Every number is tagged `[MEASURED]` / `[ESTIMATED]` / `[ASSUMPTION A#]`.
- [ ] The assumptions register lists decision impact and flip points.
- [ ] Limitations, possible failures and missing information are stated plainly.
- [ ] Each recommended action has a practical pilot with a success threshold.
- [ ] Rejected approaches are listed with reasons.

**Originality**
- [ ] At least one finding goes beyond what a generic "analyse this CSV" agent pass would produce (margin bridge, break-even rule, placebo-tested DiD, null-signal test, pilot design).

**Inspectability and submission**
- [ ] Every README number exists in `outputs/key_numbers.json`.
- [ ] A fresh clone reproduces all outputs with one command.
- [ ] Any piece of evidence is reachable within two clicks of the README.
- [ ] Team names are on the README. The repo is public. One URL is submitted.

---

## 11. Team of 2: who owns what

Two people, two lanes, few shared files. The split balances the work. **Person A** owns
the money story (costs, pricing, value). **Person B** owns the testing story (promos,
customers, baskets, discounts).

| | Person A: money and operations | Person B: tests and behaviour |
|---|---|---|
| Findings | F1 Garden cost (headline), F7 Uptown pricing, F5 demand timing (+ optional model) | F2 promo DiD (showcase), F3 customer-ID null test, F4 baskets, F6 10% discount |
| Phase 5 | `src/value_model.py`, `outputs/tables/value_summary.csv` | Supplies value inputs for F2, F3, F4, F6 via `rec.record(...)` |
| Phase 7 | Red-teams **B's** findings | Red-teams **A's** findings |
| Phase 8 | README §1 conclusion, §2 actions, §3 F1/F5/F7, §6 flip points | README §3 F2/F3/F4/F6, §4 data quality, §5 facts vs assumptions, §8 limitations, §9 rejected |
| Docs | `docs/03_findings/f1_*, f5_*, f7_*` | `docs/03_findings/f2_*, f3_*, f4_*, f6_*`, `docs/01_data_audit.md` |

**Shared files (edit only at sync points or in small, separate commits):** `README.md`,
`AGENTS.md`, `docs/assumptions.md`, `docs/decision_log.md`, `docs/pilot_designs.md`,
`src/config.py`, `src/load.py`, `src/clean.py`. Append to the registers; never rewrite the
other person's rows. New assumption IDs: Person A uses `A13, A15, …` (odd), Person B uses
`A14, A16, …` (even), so IDs never collide.

**Git workflow**
- `main` must always run (`python -m src.run_all`). Work on `a/<topic>` or `b/<topic>` branches; open small PRs, and the other person merges.
- Never commit `data/raw/` (D1). `outputs/` *is* committed: rerun `run_all` on `main` after each merge so outputs match code.
- Each script writes only its own `outputs/numbers/<module>.json` and `outputs/tables/<module>_*`, so the two lanes can't conflict.

**Sync points (15 minutes each, both people)**
1. **Kickoff:** read AGENTS.md together, confirm the split, run the pipeline on both machines.
2. **After first results (~25% of time):** each person shows their headline number and its strongest rival explanation. Fill in the `docs/02_problem_selection.md` scores together and confirm headline vs supporting findings.
3. **Midpoint (~50%):** freeze scope. Anything not producing a decision-grade result by now gets cut and logged as rejected.
4. **Swap and red-team (~70%):** each person reviews the other's finding docs against the §7.0 template and the §10 checklist.
5. **Final (~90%):** README read aloud start to finish, `check_numbers`, fresh-clone test, repo set to public, submit.

**When an AI agent works in this repo:** tell it which person's lane it's in (e.g. "You are
working for Person B on F2; only edit `src/f2_promo_eval.py` and
`docs/03_findings/f2_promo_eval.md`"). Agents must not edit the other lane's files.

---

## 12. Commands

```bash
pip install -r requirements.txt
python -m src.run_all            # full pipeline → data/processed, outputs/, key_numbers.json
python -m src.audit              # Phase 1 only
python -m src.f2_promo_eval      # any single finding
python -m src.check_numbers      # verifies README numbers exist in key_numbers.json
```
