# Event-Driven Trade Research Agent: Classic Historical Backtest Cases (7 cases)

Compiled: 2026-10-18
Purpose: backtest evaluation for systems of the type "event / belief → causal chain → conditional trade proposal (entry condition, failure condition, key dependency; wait by default; abstain when the chain is weak)". What is graded is not "did it make money", but: at the as_of point, using only information public at that time, what the correct conditional reasoning is; which dependency matters most; and which observable confirmed or refuted the thesis, and when.

## Usage notes and verification standard

- **as_of** always means "the day of the decision point", and each case notes whether it is before the open or after the close. The point-in-time pack only includes material published on or before the as_of date. A few items have "data dated before as_of, but the web copy I could open was published after it". These are marked separately with ⚠️; evaluators can drop them or replace them with the original source.
- **Verification method**: every URL was actually requested (WebFetch or curl); PDFs were text-extracted with macOS PDFKit. There are three verification levels:
  - [content] the body was opened, and the numbers in this note come from the body;
  - [title/date] the page opens, but the body is JS-rendered or truncated; only the title and publication time were verified;
  - [could not open] 403 / paywall; listed only as a lead, **not used as a data source**.
- Price data uses EIA spot series throughout (Brent: RBRTED, WTI: RWTCD) and IMF/FRED monthly nickel prices. All are public series that can be rechecked. Futures settlement prices are cited only when there is an official source (CFTC).
- Quotes from original text are all 15 English words or fewer; everything else is my own summary.
- "Stance" is relative to the case's initial thesis: supports / contradicts / neutral.

## Overview

| # | Case | as_of | Outcome type | Contamination risk |
|---|---|---|---|---|
| 1 | 2019 Abqaiq attack → long Brent | 2019-09-16 (before US open) | Failure condition observably triggered within 72 hours; correct action is "hold off", then do not enter | Medium-high |
| 2 | 2020-04 OPEC+ cut + low oil price → bottom-fish WTI front month / USO | 2020-04-17 (Friday, after close) | "Announcement ≠ reality" + broken instrument mapping (storage capacity constraint); correct action is abstain | High |
| 3 | 2022-10 OPEC+ announces 2 mb/d cut → long Brent | 2022-10-05 (after the meeting) | "Announcement ≠ reality": nominal 2 mb/d, actual OPEC output fell about 0.71 mb/d month on month | Medium |
| 4 | 2023-03 SVB sells securities at a loss + raises capital → run risk | 2023-03-08 (after the 8-K, before the 3/9 open) | Thesis holds, confirming signal appears within 24 hours; but the actionable window is only one trading day | High |
| 5 | 2023-12 Houthi attacks in the Red Sea → container freight rates rise | 2023-12-18 | Thesis holds; the mid-course "resume transits" announcement is a false signal | Medium-high |
| 6 | 2022-10 US export controls on AI chips to China → NVIDIA China revenue falls | 2022-10-13 (day the rule text was published) | Reasoning is sound, but fails for about a year because one specific technical condition in the rule (an "and" relation) was worked around; holds only after the rule was patched | Medium-high |
| 7 | 2022-03 Russia supply fears → long nickel after LME reopens | 2022-03-15 (day before reopening) | Correct action is abstain: the causal chain (sanctions → physical supply cut) lacks evidence, the price is driven by a position squeeze, and exchange rule risk is very high | Medium-high |

---

## Case 1: 2019 Abqaiq / Khurais attack → sustained oil price rise?

### 1. Name / timing / belief
- **Name**: Abqaiq-Khurais attack, Sept 2019
- **as_of**: 2019-09-16 (Monday, before the US stock open, about 13:00 UTC; Brent had already jumped in the Asian session)
- **Belief**: The 9/14 attack interrupted about 5.7 mb/d of Saudi output, and the supply shock will keep pushing oil prices higher → long Brent front month.

### 2. Public reasoning at the time
- **Goldman Sachs (Jeffrey Currie, Damien Courvalin, Sunday 9/15 report, relayed by CNBC 9/16)**: The conclusion is conditional and depends on how long the outage lasts. If the outage is announced to last more than six weeks, Brent would quickly rise above $75; a short outage would have limited impact.
- **ING (9/15)**: If the outage lasts only a few days, the market can absorb it fairly easily; if it drags on for weeks, the market tightens significantly. Basis: JODI data shows Saudi crude stocks of about 188 mb at end-June, roughly 26 days of exports; over 70% of OPEC spare capacity is in Saudi Arabia, and what other countries can add is far smaller than the gap.
- **IEA (9/14 statement)**: The market is currently well supplied, with ample commercial stocks; no mention of releasing emergency stocks.
- **US government (9/15)**: Trump authorized use of the SPR "if needed", amount not specified.
- **Saudi side (9/15, per WSJ/CNBC)**: The goal is to restore about one third of the lost output by Monday.
- **Core causal chain**: attack → Abqaiq processing capacity damaged → Saudi crude exports fall → global supply gap → spare capacity is not enough to fill it → oil price rises. **The key is the middle link: whether exports actually fall, and for how long.**
- **Conclusion at the time**: The mainstream view was "trade conditionally", with the condition being the outage duration.

### 3. Point-in-time pack (≤ 2019-09-16)
| Date | Source | URL | One-line content | Stance |
|---|---|---|---|---|
| 2019-09 (published early in the month, exact release date not verified) | EIA STEO, September 2019 | https://www.eia.gov/outlooks/steo/archives/sep19.pdf | Pre-attack baseline: EIA expected global inventories to build in both 2019 and 2020; 2019 Brent forecast cut to about $63 | contradicts (fundamentals loose) |
| 2019-09-15 (Reuters story, run by Daily FT 9/16) | IEA statement via Daily FT | https://www.ft.lk/International/IEA-says-oil-markets-well-supplied-after-attack-in-Saudi-Arabia/49-685723 | IEA says the market is well supplied with ample commercial stocks, and it is in contact with Saudi Arabia and major countries | contradicts |
| 2019-09-15 | ING THINK "Saudi oil attacks" | https://think.ing.com/articles/saudi-oil-attacks | A few days of outage can be absorbed, weeks would tighten the market; Saudi stocks about 26 days of exports; spare capacity concentrated in Saudi Arabia | neutral (conditional) |
| 2019-09-15 | CNBC (relaying WSJ) | https://www.cnbc.com/2019/09/15/saudi-arabia-aims-to-restore-one-third-of-lost-oil-output-by-monday-wsj-says.html | Saudi Arabia aims to restore about one third of lost output by Monday | contradicts |
| 2019-09-15 | CBS News | https://www.cbsnews.com/news/trump-authorizes-release-emergency-oil-reserve-after-attack-saudi-oil-sites-2019-09-15/ | Trump authorizes use of the SPR "if needed" | contradicts (weak) |
| 2019-09-16 12:06 UTC | CNBC: Goldman report | https://www.cnbc.com/2019/09/16/goldman-sachs-says-an-extended-saudi-outage-could-push-brent-crude-oil-prices-above-75.html | If the outage is announced to last more than six weeks, Brent will rise above $75; Brent futures up about 10% that day to $66.43 | supports (conditional) |

### 4. What actually happened
- **9/17**: At an Aramco press conference, the company said Khurais had resumed production after 24 hours, Abqaiq was at about 2 mb/d at that point, and full capacity would be restored by end-September; not a single customer shipment was canceled or missed. Source: Aramco press release https://www.aramco.com/en/news-media/news/2019/saudi-aramco-swiftly-restores-production-capacity
- **9/18**: EIA TWIP recorded the 9/16 one-day price rise as the largest in many years, with a pullback on 9/17 on the recovery news. https://www.eia.gov/petroleum/weekly/archive/2019/190918/includes/analysis_print.php
- **Around 10/3**: The EIA October STEO estimated Saudi crude output was back to pre-disruption levels by October 3; September average output was 8.5 mb/d (August 9.9); by early October prices were back to pre-attack levels, and contracts for 2020 and later were even below pre-attack levels. https://www.eia.gov/outlooks/steo/archives/oct19.pdf
- **EIA testimony (2019-10-17)**: Within days, industry reported that Saudi Arabia had restored exports to pre-attack levels by drawing stocks and diverting volumes from domestic refineries; Brent fell back to $65.59 on 9/17, and was below the pre-attack level on 9/30. https://www.eia.gov/pressroom/testimonies/capuano_10172019.pdf
- **Brent spot (EIA RBRTED)**: 9/13 $61.25 → 9/16 $68.42 → 9/17 $65.59 → 9/30 $60.99 → 10/3 $58.01. https://www.eia.gov/dnav/pet/hist/RBRTED.htm

### 5. Grading points
- **The real key dependency**: Whether Saudi **export loadings** fall, and for how long. Neither the attack itself nor the "5.7 mb/d shut in" headline is the key. Saudi Arabia has a stock buffer and can cover exports with stocks and domestic refinery volumes.
- **Good entry condition (long)**: Any one verifiable signal is enough: (a) Aramco or the Saudi energy ministry formally says recovery will take more than about 6 weeks (Goldman's threshold); (b) Aramco cuts allocations to Asian / European term customers (customer statements or major wire reports); (c) tanker tracking shows Saudi weekly average exports down more than about 1 mb/d versus August, sustained for two weeks or more.
- **Failure condition**: Aramco gives a timeline for full recovery within weeks, and customers confirm shipments are unaffected. This was met on 9/17.
- **What the system should do**:
  - 9/16: **Hold off**. The headline shock is already priced in, and the outage duration is unknown; the most important information (Aramco timeline, customer allocations) is expected within 24 to 48 hours.
  - 9/17: Failure condition triggered (recovery timeline + shipments unaffected) → **abstain / do not enter**; exit any existing long.
  - 10/3: EIA confirms output recovery, ex post validation.
- **What to look for in evaluation**: Whether the model sets the key dependency as "exports / customer allocations" rather than "the attack / shutdown headline"; whether it recognizes the 9/17 press conference as the failure trigger; whether it realizes the Brent time spread can be read as the market's pricing of outage duration (Oilprice had this kind of analysis on 9/18, but it was published after as_of, so it is not in the pack).

### 6. Contamination risk: medium-high
The event is very well known, and "oil spiked, then quickly fell back" is common post-mortem material. The model very likely knows the outcome, but may not remember the exact timing of the 9/17 press conference and the 10/3 recovery. For evaluation, consider anonymizing by hiding the country and facility names.

### 7. Verified URLs
- [content] https://www.cnbc.com/2019/09/16/goldman-sachs-says-an-extended-saudi-outage-could-push-brent-crude-oil-prices-above-75.html
- [content] https://think.ing.com/articles/saudi-oil-attacks
- [content] https://www.cnbc.com/2019/09/15/saudi-arabia-aims-to-restore-one-third-of-lost-oil-output-by-monday-wsj-says.html
- [content] https://www.cbsnews.com/news/trump-authorizes-release-emergency-oil-reserve-after-attack-saudi-oil-sites-2019-09-15/
- [content] https://www.ft.lk/International/IEA-says-oil-markets-well-supplied-after-attack-in-Saudi-Arabia/49-685723
- [content] https://www.eia.gov/outlooks/steo/archives/sep19.pdf
- [content] https://www.aramco.com/en/news-media/news/2019/saudi-aramco-swiftly-restores-production-capacity
- [content] https://www.eia.gov/petroleum/weekly/archive/2019/190918/includes/analysis_print.php
- [content] https://www.eia.gov/todayinenergy/detail.php?id=41413 (EIA 2019-09-23)
- [content] https://www.eia.gov/todayinenergy/detail.php?id=41513 (EIA 2019-10-01)
- [content] https://www.eia.gov/outlooks/steo/archives/oct19.pdf
- [content] https://www.eia.gov/pressroom/testimonies/capuano_10172019.pdf
- [content] https://www.eia.gov/todayinenergy/detail.php?id=42415 (EIA 2020-01-07, Brent back to pre-attack level by end-September)
- [content] https://www.eia.gov/todayinenergy/detail.php?id=42675 (EIA 2020-01-31, the post-attack price move was the largest one-day percentage change in 29 years)
- [content] https://www.eia.gov/dnav/pet/hist/RBRTED.htm
- [title/date] https://www.naturalgasworld.com/oil-markets-well-supplied-iea-73005
- [content, after as_of] https://oilprice.com/Energy/Energy-General/Brent-Spreads-Tell-The-Truth-About-Saudi-Oil-Disruption.html (2019-09-18)
- [title/date, after as_of] https://gulfnews.com/business/energy/saudi-aramcos-oil-stockpiles-can-cover-lower-output-1.66549232 (2019-09-20)
- [could not open] IEA original statement, Al Arabiya repost (403)

---

## Case 2: April 2020: OPEC+'s largest-ever cut + "cheap" oil → bottom-fish WTI front month / USO?

### 1. Name / timing / belief
- **Name**: April 2020 WTI front-month collapse / USO
- **as_of**: 2020-04-17 (Friday, after close; the May WTI contract expires 4/21)
- **Belief**: OPEC+ finalized a 9.7 mb/d cut on 4/12 (from 5/1), and WTI has fallen to about $18, a historic low → buy WTI front month or USO to catch the bottom.

### 2. Public reasoning at the time
- **IEA (4/15 OMR, relayed by CNBC / NPR)**: April demand down about 29 mb/d year on year; even with the OPEC+ and G20 decisions, the implied stock build in the first half is about 12 mb/d, which could overwhelm logistics such as ships, pipelines and storage tanks in the coming weeks. This is in effect an argument for "do not trade the front month".
- **OPEC+ (4/12 agreement, communique relayed by Hydrocarbon Engineering 4/14)**: The 9.7 mb/d cut only takes effect on **May 1**, runs until 6/30, then drops to 7.7 mb/d. There are more than two weeks between announcement and effect.
- **EIA (4/15 TWIP)**: Low prices will lead to lower US output, but the decline plays out month by month.
- **EIA weekly Cushing stocks**: 3/27 42.8 mb → 4/3 49.2 mb → 4/10 55.0 mb (by the EIA Wednesday release convention, the 4/10 data came out on 4/15), consecutive weekly builds of 5.7 to 6.4 mb. EIA's published Cushing working capacity is about 76 mb.
- **USO itself (8-K, report date 4/16)**: Citing "market conditions and regulatory requirements", it moved about 20% of holdings to the second-month contract from 4/17. The product's own issuer was changing its structure, a strong stress signal.
- **Core causal chain (correct version)**: demand collapse → stocks build far faster than cuts take effect → uncommitted storage at the Cushing delivery point runs out → front-month holders have nowhere to take delivery → deep contango of front month versus later months → front-month prices and roll-based ETF returns decouple from "oil price rebound".
- **Conclusion**: The bottom-fishing narrative says "trade"; the IEA and EIA data point to "do not trade the front month / do not trade USO".

### 3. Point-in-time pack (≤ 2020-04-17)
| Date | Source | URL | One-line content | Stance |
|---|---|---|---|---|
| 2020-04-14 | Hydrocarbon Engineering (relaying OPEC+ communique) | https://www.hydrocarbonengineering.com/refining/14042020/opec-agrees-massive-deal-to-cut-oil-output | 9.7 mb/d cut from 5/1 to 6/30; then 7.7 mb/d | supports (headline) / timing mismatch |
| 2020-04-15 | CNBC (IEA OMR) | https://www.cnbc.com/2020/04/15/coronavirus-to-erase-nearly-a-decade-of-oil-demand-growth-in-2020-iea.html | April demand -29 mb/d; implied first-half build 12 mb/d, logistics could be overwhelmed | contradicts |
| 2020-04-15 | NPR | https://www.npr.org/sections/coronavirus-live-updates/2020/04/15/834868805/oil-prices-keep-slipping-as-demand-drops-by-record-amounts | A storage crisis could arrive before absolute capacity runs out, for example no room in pipelines | contradicts |
| 2020-04-15 | EIA This Week in Petroleum | https://www.eia.gov/petroleum/weekly/archive/2020/200415/includes/analysis_print.php | EIA forecasts lower US output due to low prices; producer-side spot prices show steep discounts | neutral |
| 2020-04-15 (data as of 4/10) | EIA weekly Cushing stock series | https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=W_EPC0_SAX_YCUOK_MBBL&f=W | Cushing stocks 55.0 mb, up about 12 mb in two weeks (3/27→4/10) | contradicts |
| 2020-04-16 (report date) | USO Form 8-K, SEC | https://www.sec.gov/Archives/edgar/data/1327068/000117120020000242/i20244_uso-8k.htm | From 4/17, 80% front month + 20% second month; warns it may not achieve its investment objective | contradicts |

(Could not open, lead only: CME Clearing Advisory 20-152 (4/8) and 20-160 (4/15), which per secondhand accounts covered negative price testing and a switch of options model; cmegroup.com returned 403. ETF.com's report on the USO roll change also returned 403.)

### 4. What actually happened
- **2020-04-20**: The May WTI contract settled at **-$37.63**, negative for the first time in 37 years of listing. Source: CFTC interim report press release (2020-11-23) https://www.cftc.gov/PressRoom/PressReleases/8315-20 . EIA WTI spot 4/17 $18.31 → 4/20 -$36.98. https://www.eia.gov/dnav/pet/hist/RWTCD.htm
- **EIA explanation after the fact (4/22, 4/27)**: Cushing working capacity was 76 mb, and 60 mb was already stored on 4/17 (about 76%). Capacity not leased or committed was even smaller, so contract holders without prior arrangements could not take delivery. https://www.eia.gov/todayinenergy/detail.php?id=43495
- **USO**: 1-for-8 reverse split after the 4/28 close (pre-split NAV $2.04). Split-adjusted NAV per share: 2019-12-31 $102.27 → 2020-06-30 $28.02 (-72.6%); WTI spot over the same period $61.14 → $39.27 (-35.8%). Source: USO 10-Q (2020 Q2) https://www.sec.gov/Archives/edgar/data/1327068/000110465920091976/uso-20200630x10q.htm
- **Cushing stock turning point**: Peaked at 65.4 mb in the week of 5/1, then 5/8 62.4, 5/15 56.9, 5/22 53.5 (EIA weekly series).

### 5. Grading points
- **The real key dependency**: **Uncommitted Cushing storage** and the front-month / second-month spread (depth of contango), not the OPEC+ cut announcement, and not the absolute oil price level.
- **Good failure condition (for "bottom-fish front month / USO", already triggered at as_of)**: Weekly Cushing build above about 4 mb and utilization above about 70%, with less than a week to front-month expiry; or a roll-based ETF issuer changes its roll rules (USO 8-K).
- **Good entry condition (if expressing "oil recovers over the medium term")**: EIA weekly Cushing stocks **fall two weeks in a row**, and front-month contango narrows clearly; use a further-dated contract as the instrument, not a front-month roll-based ETF.
- **What the system should do**:
  - 4/17: **Abstain** (front month / USO). Reason: the storage constraint is observable and already close; the cut only takes effect on 5/1.
  - 5/13 (5/8 data, first draw) → hold off; 5/20 (5/15 data, second consecutive draw) → entry condition for the "oil recovers" thesis is met (dates inferred from the EIA Wednesday release convention; release dates not individually verified).
- **What to look for in evaluation**: Whether the model can separate "announcement" (4/12 cut) from "effect" (5/1); whether it treats instrument mapping (spot ≠ front-month futures ≠ roll-based ETF) as a link in the causal chain; whether it abstains on its own.

### 6. Contamination risk: high
"Negative oil prices" are extremely well known, and the model almost certainly knows the 4/20 outcome. Suggestions for evaluation: (a) anonymize (replace with "a crude contract at some delivery point"); or (b) grade only "key dependency identification" and "instrument mapping", not direction.

### 7. Verified URLs
- [content] https://www.hydrocarbonengineering.com/refining/14042020/opec-agrees-massive-deal-to-cut-oil-output
- [content] https://www.cnbc.com/2020/04/15/coronavirus-to-erase-nearly-a-decade-of-oil-demand-growth-in-2020-iea.html
- [content] https://www.npr.org/sections/coronavirus-live-updates/2020/04/15/834868805/oil-prices-keep-slipping-as-demand-drops-by-record-amounts
- [content] https://www.eia.gov/petroleum/weekly/archive/2020/200415/includes/analysis_print.php
- [content] https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=W_EPC0_SAX_YCUOK_MBBL&f=W
- [content] https://www.sec.gov/Archives/edgar/data/1327068/000117120020000242/i20244_uso-8k.htm
- [content] https://www.cftc.gov/PressRoom/PressReleases/8315-20
- [content] https://www.eia.gov/dnav/pet/hist/RWTCD.htm
- [content] https://www.eia.gov/todayinenergy/detail.php?id=43495
- [content] https://www.eia.gov/petroleum/weekly/archive/2020/200422/includes/analysis_print.php
- [content] https://www.sec.gov/Archives/edgar/data/1327068/000110465920091976/uso-20200630x10q.htm
- [title/date] https://www.cnbc.com/2020/04/20/oil-markets-us-crude-futures-in-focus-as-coronavirus-dents-demand.html
- [could not open] cmegroup.com clearing advisories 20-160 / 20-152; etf.com USO report; iea.org OMR; opec.org press release (403 / 402)

---

## Case 3: 2022-10-05 OPEC+ announces 2 mb/d cut → long Brent?

### 1. Name / timing / belief
- **Name**: OPEC+ 33rd ONOMM headline cut, Oct 2022
- **as_of**: 2022-10-05 (after the meeting decision was announced)
- **Belief**: OPEC+ cuts its production target by 2 mb/d from November, so actual supply will tighten by about 2 mb/d → long Brent.

### 2. Public reasoning at the time
- **Argus (relayed by QCI 9/19)**: In August, actual OPEC+ output was 3.58 mb/d below quota, a record; of that, OPEC-10 was 1.399 mb/d short and non-OPEC allies 2.185 mb/d short. Many members had been unable to produce their quotas for a long time.
- **UBS (9/27)**: A cut of at least 0.5 mb/d is needed to stop the short-term decline.
- **Reuters (10/2)**: The meeting will consider a cut of more than 1 mb/d.
- **Goldman Sachs (per QCI story on 10/5)**: The effective cut is probably only about 50% of the nominal quota cut; most members remain compliant even under the lowered quotas.
- **Quota table (Argaam 10/5)**: Saudi Arabia and Russia each cut 526,000 b/d, the two largest cuts.
- **Core causal chain**: quota cut → **binds only members whose actual output is above the new quota** → actual cut ≈ the cuts by Gulf producers with spare capacity (Saudi Arabia, UAE, Kuwait, Iraq, etc.) → supply tightens far less than the headline.
- **Conclusion at the time**: Direction leans bullish, but the size is about half the headline; conditional.

### 3. Point-in-time pack (≤ 2022-10-05)
| Date | Source | URL | One-line content | Stance |
|---|---|---|---|---|
| 2022-09-19 | QCI (relaying Argus) | https://qcintel.com/article/opec-misses-august-target-by-record-3-58-million-bpd-report-8553.html | In August OPEC+ produced 3.58 mb/d below quota, a record | contradicts (the headline will overstate) |
| 2022-09-27 | QCI (UBS view) | https://qcintel.com/article/only-an-opec-output-cut-can-halt-short-term-brent-losses-ubs-8715.html | Only an OPEC+ cut can stop Brent's short-term losses | supports |
| 2022-10-02 | BOE Report (Reuters story) | https://boereport.com/2022/10/02/opec-to-consider-oil-output-cut-of-more-than-1-million-bpd/ | OPEC+ will consider a cut of more than 1 mb/d | supports |
| 2022-10-05 | QCI | https://qcintel.com/article/opec-slashes-headline-output-by-2-million-bpd-from-november-8880.html | Nominal cut of 2 mb/d, based on August quotas; Goldman says the effective cut is about half the nominal | neutral (direction supports, size contradicts) |
| 2022-10-05 | Argaam | https://www.argaam.com/en/article/articledetail/id/1592696 | November quota table by country | neutral |

### 4. What actually happened
- **Price (EIA Brent spot)**: 10/5 $94.35 → 10/7 $98.88 → 11/7 $99.87 → 12/9 $76.37. Up first, then down; by early December clearly below the pre-decision level. During the decline there were other factors at the same time, such as demand expectations, China's COVID policy and the Russian oil price cap, so **the decline cannot be attributed only to the cut falling short**. https://www.eia.gov/dnav/pet/hist/RBRTED.htm
- **Actual implementation (Reuters November output survey, 2022-12-01)**: OPEC November output 29.01 mb/d, down 710,000 b/d month on month. The nominal cut assigned to OPEC-10 was about 1.27 mb/d; the actual month-on-month decline was about 720,000 b/d. Saudi Arabia cut about 500,000 b/d, basically delivered. Angola and Nigeria actually raised output but were still far below quota. "Compliance" calculated against quota reached 163%, because these members could not produce enough in the first place. Source: Reuters story reprinted by Oman Observer https://www.omanobserver.om/article/1129165/business/opec-oil-output-drops-in-nov-after-cut-pledged ; QCI https://www.qcintel.com/article/opec-output-down-700-000-bpd-in-november-after-cuts-implemented-survey-10209.html
- **Commentary after the fact**: A Bloomberg column (reprinted by Deccan Herald 10/9) said in its headline that this cut was "10% real, 90% illusion". https://www.deccanherald.com/amp/story/business%2Fopec-oil-production-cut-could-be-10-real-90-illusion-1152011.html

### 5. Grading points
- **The real key dependency**: From November, the **actual output of members with spare capacity** (Saudi Arabia, UAE, Kuwait, Iraq), and the combined actual cut, not nominal quotas. Observables: output surveys (Reuters / Platts / Argus, published early in the month), OPEC MOMR secondary-source data (mid-month), tanker export tracking.
- **Good entry condition (long "supply tightening")**: The November output survey (published around 12/1) shows a combined OPEC+ actual cut ≥ about 1 mb/d, later confirmed by OECD stock or export data.
- **Failure condition**: Surveys show the actual cut clearly below 1 mb/d, or the cut comes only from Saudi Arabia while other members with capacity do not implement.
- **What the system should do**:
  - 10/5: **Hold off**. The headline is already priced in; the decisive observable (actual November output) is available at the earliest in early December; public analysis had already pointed out that the effective cut is about half the nominal.
  - 12/1: Survey shows OPEC down only about 0.71 mb/d month on month → the "2 mb/d tightening" thesis is not confirmed → **do not enter**.
- **What to look for in evaluation**: Whether the model separates "quota" from "output" on its own, and uses the "August shortfall of 3.58 mb/d", public before as_of, to infer that the nominal cut will be diluted; whether it gives a timeline for "when actual output data becomes available", rather than acting on the headline.

### 6. Contamination risk: medium
The cut itself is well known (controversy in US-Saudi relations), but the model is unlikely to remember the "actual implementation" and the specific survey figures precisely. Suitable as the main case for "announcement ≠ reality".

### 7. Verified URLs
- [title/date] https://qcintel.com/article/opec-misses-august-target-by-record-3-58-million-bpd-report-8553.html
- [title/date] https://qcintel.com/article/only-an-opec-output-cut-can-halt-short-term-brent-losses-ubs-8715.html
- [content] https://boereport.com/2022/10/02/opec-to-consider-oil-output-cut-of-more-than-1-million-bpd/
- [content] https://qcintel.com/article/opec-slashes-headline-output-by-2-million-bpd-from-november-8880.html
- [title/date] https://www.argaam.com/en/article/articledetail/id/1592696
- [title/date, after as_of] https://www.argaam.com/en/article/articledetail/id/1592755 (10/6, Brent up four days in a row)
- [title/date, after as_of] https://www.deccanherald.com/amp/story/business%2Fopec-oil-production-cut-could-be-10-real-90-illusion-1152011.html
- [content] https://www.omanobserver.om/article/1129165/business/opec-oil-output-drops-in-nov-after-cut-pledged
- [title/date] https://www.qcintel.com/article/opec-output-down-700-000-bpd-in-november-after-cuts-implemented-survey-10209.html
- [content] https://www.eia.gov/dnav/pet/hist/RBRTED.htm
- [could not open] S&P Global Platts September survey (3.61 mb/d gap, 403); iea.org October OMR (403); OPEC press release (403)
- Note: The different measures of the August gap (Argus 3.58 / Argus's own survey 3.4 / Platts 3.61 mb/d) come from search snippets; only the QCI 3.58 page was opened.

---

## Case 4: 2023-03 SVB: selling securities at a loss + emergency capital raise → bank run?

### 1. Name / timing / belief
- **Name**: Silicon Valley Bank failure, March 2023
- **as_of**: 2023-03-08 (Wednesday, after the US Eastern close, SVB 8-K already published; before the 3/9 open)
- **Belief**: SVB sold securities at a loss to shore up liquidity and launched an emergency capital raise, exposing unrealized securities losses from rate hikes and deposit outflows; deposits are highly concentrated and mostly uninsured, so a run may happen → short SIVB / avoid similar regional banks.

### 2. Public reasoning at the time
- **SVB itself (3/8 8-K, Exhibit 99.3 letter to stakeholders)**: Sold almost all AFS securities, with an after-tax loss of about $1.8B; plans to raise about $2.25B (including $500 million from General Atlantic); term borrowing raised from $15B to $30B; client "cash burn" in February was still high and deposits were below expectations; full-year guidance for deposits, NII and NIM cut.
- **SVB 10-K (filed 2023-02-24)**: HTM securities at amortized cost about $91.3B, fair value about $76.2B (unrealized loss about $15.1B), versus shareholders' equity of about $16B. The HTM figures come from a CFA Institute 3/13 blog post restating SVB's financial statement notes; I could not open the 10-K notes directly. The parts of the 10-K body I could verify are deposits of $173.1B and shareholders' equity of $16.0B.
- **FDIC (2/28 Quarterly Banking Profile)**: Industry-wide unrealized losses on securities $620.4B (HTM $340.9B). In a speech, the FDIC chairman warned that if banks need to sell securities to meet liquidity needs, unrealized losses become realized losses.
- **FT (2/22)**: Reported that SVB was attracting short sellers (paywalled, could not open; the Fed's after-the-fact report cited this story).
- **Silvergate (3/8)**: Announced a wind-down. Another bank that relied on deposits from a specific industry got into trouble, which could lead similar depositors to draw the connection.
- **Moody's (evening of 3/8)**: Downgraded SVB Financial from A3 to Baa1, outlook negative (per Wolf Street's after-the-fact report on 3/11; I did not find an openable source published before as_of).
- **Core causal chain**: rate hikes → unrealized losses on long-duration MBS (HTM not marked to market) → tech clients burn cash, deposits flow out → forced to sell AFS and realize losses + raise capital → capital gap made public → uninsured, highly concentrated VC-linked deposits leave together → liquidity crisis.
- **Conclusion**: Short / avoid, conditional on whether the raise completes and whether deposits stabilize.

### 3. Point-in-time pack (≤ 2023-03-08)
| Date | Source | URL | One-line content | Stance |
|---|---|---|---|---|
| 2023-02-22 | Financial Times (per Fed report footnote) | https://www.ft.com/content/0387e331-61b4-4848-9e50-04775b4c3fa7 | SVB attracts short sellers [could not open] | supports |
| 2023-02-24 | SVB 10-K (EDGAR index timestamp 2023-02-24) | https://www.sec.gov/Archives/edgar/data/719739/000071973923000021/sivb-20221231.htm | Deposits $173.1B, shareholders' equity $16.0B; HTM fair value disclosed in the notes | supports |
| 2023-02-28 | FDIC press release | https://www.fdic.gov/news/press-releases/2023/pr23013.html | Industry-wide unrealized losses on securities $620.4B, of which HTM $340.9B | supports (industry background) |
| 2023-02-28 | FDIC chairman speech | https://www.fdic.gov/news/speeches/2023/spfeb2823.html | If securities must be sold to meet liquidity needs, unrealized losses may become realized | supports |
| 2023-03-08 | Kitco (Reuters story) | https://www.kitco.com/news/off-the-wire/2023-03-08/crypto-focused-bank-silvergate-plans-wind-down-operations | Silvergate plans to wind down | supports (contagion) |
| 2023-03-08 17:16 (EDGAR index timestamp) | SVB 8-K Ex.99.3 | https://www.sec.gov/Archives/edgar/data/719739/000119312523064680/d430920dex993.htm | AFS sale after-tax loss $1.8B, raise $2.25B, borrowing up to $30B, deposit guidance cut | supports |
| 2023-03-08 | SVB 8-K Ex.99.2 (investor presentation) | https://www.sec.gov/Archives/edgar/data/719739/000119312523064680/d430920dex992.htm | Same as above, presentation version | supports |

### 4. What actually happened
- **3/9**: SIVB shares fell about 60% (CNBC 3/9 headline). https://www.cnbc.com/2023/03/09/svb-financial-falls-more-than-50percent-as-tech-bank-looks-to-raise-more-cash.html
- **3/9**: Deposit outflows exceeded $40B, and management expected more than $100B more to leave on 3/10, about 85% of the deposit base. Source: Federal Reserve review of SVB (2023-04-28) https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf . The report also states that about 94% of deposits were uninsured at end-2022 (FR Y-9C basis).
- **Morning of 3/10**: CNBC reported that the capital raise had failed and the bank was seeking a sale; that day the CDFPI closed the bank and the FDIC took over. https://www.cnbc.com/2023/03/10/silicon-valley-bank-financial-in-talks-to-sell-itself-after-attempts-to-raise-capital-have-failed-sources-say.html ; https://www.fdic.gov/news/press-releases/2023/pr23016.html
- **3/14 (follow-up SVB 8-K)**: The AFS sold on 3/8 had a book value of about $23.97B, net proceeds of about $21.45B, and the buyer was Goldman Sachs. (From a search result summary of that 8-K; original not opened, marked unverified.)

### 5. Grading points
- **The real key dependency**: **Where uninsured deposits flow**, and whether the $2.25B raise can be priced and completed. The unrealized securities losses had existed for months and are not fatal as long as deposits do not run.
- **Real-time observables**: Whether the offering is priced before the 3/9 close (it was not); whether large VCs publicly or semi-publicly advise portfolio companies to pull funds; rating actions (Moody's downgrade on the evening of 3/8); peer events (such as Silvergate). Deposit outflows themselves **cannot be observed in real time**; they are only known after the fact from regulatory reports. This matters a lot for system design.
- **Good entry condition (short / avoid)**: The offering is not priced within about 24 hours of the announcement, or major media report "raise failed / seeking a sale".
- **Failure condition**: The offering is fully priced with a large institutional anchor investor, or there is a statement of liquidity support from an acquirer or from regulators.
- **What the system should do**:
  - Evening of 3/8: **Trade conditionally (lean avoid)**. At a minimum, exit any "long SIVB" position; the entry condition for a short depends on the progress of the offering during trading on 3/9.
  - 3/9 intraday to close: offering not priced and shares collapse → entry condition met, but most of the short's gain was already realized that day.
  - Before the 3/10 open: trading halted, then the bank was taken over; no executable window.
- **What to look for in evaluation**: (a) The key dependency should be "deposit flows + raise completion", not the "HTM unrealized loss" itself; (b) the system should recognize the cost of "waiting for evidence": the confirming signal and the loss of tradability arrive almost at the same time, so the thesis should be expressed as "risk avoidance / exit longs", not only as waiting to enter; (c) extrapolating to other regional banks requires looking at each bank's deposit structure, not a blanket call (can be used as a follow-up question).

### 6. Contamination risk: high
One of the best-known banking events of 2023. The model certainly knows the outcome. Suggest grading only three items, "key dependency", "whether observables are available in real time" and "execution window", or using a bank from the same period with a different outcome as a control group (not included in this file, needs separate research).

### 7. Verified URLs
- [title/date] https://www.sec.gov/Archives/edgar/data/719739/000071973923000021/sivb-20221231.htm (deposit and equity figures come from the body; the EDGAR index https://www.sec.gov/Archives/edgar/data/719739/000071973923000021/ shows 2023-02-24)
- [content] https://www.sec.gov/Archives/edgar/data/719739/000119312523064680/d430920dex993.htm
- [content] https://www.sec.gov/Archives/edgar/data/719739/000119312523064680/ (index, timestamp 2023-03-08 17:16:05)
- [not opened individually] https://www.sec.gov/Archives/edgar/data/719739/000119312523064680/d430920dex992.htm (present in the index above)
- [content] https://www.fdic.gov/news/press-releases/2023/pr23013.html
- [content] https://www.fdic.gov/news/speeches/2023/spfeb2823.html
- [title] https://www.kitco.com/news/off-the-wire/2023-03-08/crypto-focused-bank-silvergate-plans-wind-down-operations
- [title/date] https://www.cnbc.com/2023/03/09/svb-financial-falls-more-than-50percent-as-tech-bank-looks-to-raise-more-cash.html
- [title/date] https://www.cnbc.com/2023/03/10/silicon-valley-bank-financial-in-talks-to-sell-itself-after-attempts-to-raise-capital-have-failed-sources-say.html
- [title/date] https://www.cnbc.com/2023/03/11/silicon-valley-banks-demise-began-with-downgrade-threat.html
- [content] https://wolfstreet.com/2023/03/11/svb-financial-had-investment-grade-credit-ratings-from-moodys-and-sp-up-to-collapse-then-ratings-got-slashed-in-one-fell-swoop-to-default/
- [title] https://www.fdic.gov/news/press-releases/2023/pr23016.html
- [content] https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf
- [content] https://www.federalreserve.gov/newsevents/pressreleases/bcreg20230428a.htm
- [title/date] https://www.cnbc.com/2023/03/28/svb-customers-tried-to-pull-nearly-all-deposits-in-two-days-barr-says.html
- [content] https://blogs.cfainstitute.org/blog/2023/03/13/the-svb-collapse-fasb-should-eliminate-hide-til-maturity-accounting/ (source of the HTM $91.3B / $76.2B figures, secondhand)
- [title/date] https://rationalwalk.com/the-fall-of-silicon-valley-bank/
- [could not open] FT 2/22 original (403); CDFPI closure announcement (403)

---

## Case 5: 2023-12 Houthi attacks in the Red Sea → container freight rates rise?

### 1. Name / timing / belief
- **Name**: Red Sea / Houthi attacks and container freight, Dec 2023
- **as_of**: 2023-12-18 (Monday; the day BP paused Red Sea transits and the US announced Operation Prosperity Guardian)
- **Belief**: Major container lines pause Red Sea / Suez transits and reroute via the Cape of Good Hope → effective capacity falls and voyages get longer → Asia-Europe container spot rates rise sharply (instruments: freight rate indices or futures, container line stocks).

### 2. Public reasoning at the time (Reuters 12/18 roundup)
- **ABN Amro (Albert Jan Swart)**: The lines now rerouting account for about half of global container capacity; rerouting lengthens voyages and raises costs.
- **ING (Rico Luman)**: Rerouting adds at least a week of sailing; delays appear in late December and carry into January, possibly February.
- **Freightos CEO (Zvi Schreiber)**: Long-haul rates may rise, but carriers have spare capacity to deploy, so rates are unlikely to reach pandemic levels. This is the opposing view on size.
- **Background data**: The Drewry WCI composite was $1,382/FEU on 11/30 and $1,521 on 12/14 (up 4% on the week, still down 28% year on year). The industry is in an overcapacity cycle.
- **Core causal chain**: attack risk → carriers stop transiting Bab el-Mandeb → reroute via the Cape of Good Hope (1 to 2 extra weeks) → effective capacity absorbed by longer voyages → spot rates rise. The opposing force is overcapacity from new ship deliveries across the industry.
- **Conclusion**: Direction leans up; size is disputed (Freightos more conservative).

### 3. Point-in-time pack (≤ 2023-12-18)
| Date | Source | URL | One-line content | Stance |
|---|---|---|---|---|
| 2023-12-02 (data 11/30) | Hellenic Shipping News (Drewry WCI) | https://www.hellenicshippingnews.com/?p=1017031 | WCI flat at $1,382, down 40% year on year | neutral (low baseline) |
| 2023-12-15 | Al Jazeera | https://www.aljazeera.com/news/2023/12/15/yemen-rebels-hit-cargo-ship-in-latest-red-sea-attack | Several shipping companies pause Red Sea voyages after the attacks | supports |
| 2023-12-15 | CNBC | https://www.cnbc.com/2023/12/15/maersk-to-pause-all-container-ship-traffic-through-the-red-sea.html | Maersk pauses all container transits through the Red Sea until further notice | supports |
| ⚠️ data 2023-12-14, web page 12-19 | Cyprus Shipping News (Drewry WCI) | https://cyprusshippingnews.com/2023/12/19/world-container-index-up-by-4-according-to-drewry/ | WCI up 4% to $1,521; Shanghai-Rotterdam +7% | supports (weak) |
| 2023-12-18 | Arab News PK (Reuters story) | https://www.arabnews.pk/node/2427861/business-economy | ABN Amro / ING / Freightos views; rerouting or pauses by MSC, Maersk, CMA CGM, Hapag-Lloyd, Evergreen | supports (direction), Freightos view contradicts (size) |
| 2023-12-18 | Deccan Herald (Reuters story) | https://www.deccanherald.com/world/red-sea-attacks-force-rerouting-of-vessels-disrupting-supply-chains-2815827 | Red Sea attacks force vessels to reroute, disrupting supply chains | supports |
| 2023-12-18 | Stars and Stripes | https://www.stripes.com/theaters/middle_east/2023-12-18/bp-suspends-red-sea-shipping-12405082.html | BP pauses Red Sea shipping | supports |

### 4. What actually happened
- **Rates (Drewry WCI composite)**: 12/21 $1,661 (+9%) → 2024-01-11 $3,072 (+15% on the week, +44% year on year) → 01-18 $3,777 (+23% on the week, +82% year on year). Up about 150% in about a month. https://airfreight.news/articles/full/drewry-world-container-index-21-dec ; https://www.hellenicshippingnews.com/?p=1023073 ; https://www.hellenicshippingnews.com/drewry-world-container-index-up-23-last-week/
- **False signal (announcement ≠ reality)**: On 12/24, Maersk announced it was preparing to resume Red Sea transits, citing the multinational escort operation, while noting that the risk had not gone away (reprinted by Malay Mail / Caixin 12/25-26). On 12/30 to 31 the Maersk Hangzhou was attacked; on 12/31 Maersk first paused for 48 hours, then extended the pause until further notice (Fox Business 12/31, gCaptain, Enterprise 1/2).
- **Actual transits (IMF PortWatch, IMF blog 2024-03-07)**: In the first two months of 2024, Suez Canal trade volume fell about 50% year on year, and Cape of Good Hope transits rose about 74% year on year.

### 5. Grading points
- **The real key dependency**: The **actual container ship transits** through Bab el-Mandeb / the Suez Canal (PortWatch daily transit estimates, ship tracking), and carriers' rerouting arrangements for **whole routes**, not announcements such as "transits resuming" or "escort coalition formed".
- **Good entry condition**: (a) at least three of the top five container lines announce rerouting of the whole Asia-Europe route; (b) weekly Suez container ship transits fall more than about 30% versus the November average (PortWatch); (c) WCI or FBX Asia-Europe spot rates rise two weeks in a row. On 12/18, (a) was already met; (c) only got its second weekly rise with WCI +9% on 12/21.
- **Failure condition**: PortWatch shows Suez container ship transits back above about 70% of the November average for two weeks in a row; **a carrier's "preparing to resume" announcement alone does not count**.
- **What the system should do**:
  - 12/18: **Hold off / conditional**. Directional evidence is strong, but rate confirmation covers only one week (+4%), and there is an opposing view based on overcapacity.
  - Around 12/21: second weekly WCI rise → **entry condition met**.
  - 12/24: Maersk announces resumption → **do not exit**; wait for actual transit data. The renewed pause on 12/31 confirmed this.
  - Exit condition: wait for PortWatch transits to recover; this did not happen within the case's observation period (to 2024-03).
- **What to look for in evaluation**: Whether the model treats "escort coalition / resumed transits" announcements as hypotheses to verify rather than as exit signals; whether it proposes observables like PortWatch that directly measure physical flows.

### 6. Contamination risk: medium-high
The Red Sea crisis is widely known, and the model knows rates rose sharply. But it may not precisely remember the details of the 12/24 resumption announcement and the 12/31 renewed pause, or the weekly rhythm of the WCI. Suitable for focusing the grading on "handling of false signals".

### 7. Verified URLs
- [content] https://www.hellenicshippingnews.com/?p=1017031
- [title/date] https://www.aljazeera.com/news/2023/12/15/yemen-rebels-hit-cargo-ship-in-latest-red-sea-attack
- [title/date] https://www.cnbc.com/2023/12/15/maersk-to-pause-all-container-ship-traffic-through-the-red-sea.html
- [title/date] https://cyprusshippingnews.com/2023/12/19/world-container-index-up-by-4-according-to-drewry/
- [content] https://www.arabnews.pk/node/2427861/business-economy
- [title/date] https://www.deccanherald.com/world/red-sea-attacks-force-rerouting-of-vessels-disrupting-supply-chains-2815827
- [title] https://www.stripes.com/theaters/middle_east/2023-12-18/bp-suspends-red-sea-shipping-12405082.html
- [content] https://airfreight.news/articles/full/drewry-world-container-index-21-dec
- [content] https://www.hellenicshippingnews.com/?p=1023073
- [content] https://www.hellenicshippingnews.com/drewry-world-container-index-up-23-last-week/
- [title/date] https://www.ajot.com/news/drewry-world-container-index-11-jan
- [title] https://www.malaymail.com/news/money/2023/12/25/shipping-giant-maersk-prepares-to-resume-operations-in-red-sea/109132
- [title] https://www.caixinglobal.com/2023-12-26/maersk-prepares-to-return-to-red-sea-under-us-led-protection-102149759.html
- [title/date] https://www.foxbusiness.com/markets/maersk-pauses-red-sea-voyages-day-after-houthis-attack-ship
- [title] https://gcaptain.com/maersk-pausing-red-sea-transits-until-further-notice/
- [title] https://enterpriseam.com/logistics/2024/01/02/maersk-reconsiders-decision-to-ramp-up-red-sea-transit-as-houthi-attacks-continue/
- [content] https://www.imf.org/en/blogs/articles/2024/03/07/red-sea-attacks-disrupt-global-trade/index.md
- [title] https://www.thedailystar.net/business/news/red-sea-attacks-disrupt-global-trade-3562626
- [could not open] UNCTAD 2024-02 press release (403; a search snippet says Suez transits fell 42% from the peak, not verified); Axios 12/19 (403); imf.org blog HTML version (403, but the index.md version was opened)

---

## Case 6: 2022-10 US export controls on advanced computing chips to China → NVIDIA China data center revenue falls?

### 1. Name / timing / belief
- **Name**: BIS Oct 7, 2022 advanced computing rule & NVIDIA A800
- **as_of**: 2022-10-13 (the day the rule text was formally published in the Federal Register; the advanced computing provisions take effect 10/21)
- **Belief**: The US imposes license controls on exports of high-end AI chips to China → NVIDIA's data center GPU sales to China are heavily restricted → bearish on NVIDIA China data center revenue (and NVDA).

### 2. Public reasoning at the time
- **NVIDIA itself (8-K, signed 2022-08-31, event date 8/26)**: The US government added a license requirement for exports to China (including Hong Kong) and Russia of the A100, the H100, systems containing these chips, and future chips with performance roughly equal to the A100. About **$400 million** of potential China sales in the Q3 outlook could be affected. Some operations may need to move out of China.
- **9/1 update (relayed by CnEVPost 9/2)**: The US government allowed H100 development to continue in China, and the Hong Kong facility can be used for fulfillment until 2023-09-01. Partial easing.
- **BIS (10/7 press release)**: Added certain advanced computing chips to the control list and required licenses for items used in Chinese supercomputers and semiconductor production; the advanced computing and supercomputer provisions take effect 10/21.
- **Rule text (Federal Register 10/13, ECCN 3A090)**: A controlled chip must meet **both** conditions: (1) total bidirectional transfer rate ≥ 600 GB/s, **and** (2) bit length × TOPS ≥ 4800. This "and" is the key: a product whose interconnect bandwidth is pushed below 600 GB/s is not caught by this provision.
- **Core causal chain (bearish version)**: license requirement → cannot deliver A100/H100 to Chinese customers → China data center revenue lost (disclosed after the fact in the FY2024 10-K: China was about 19% of data center revenue in FY2023; this exact share was not available at as_of).
- **Conclusion at the time**: Bearish, and NVIDIA itself quantified the exposure; but the rule's technical definition left room for product redesign.

### 3. Point-in-time pack (≤ 2022-10-13)
| Date | Source | URL | One-line content | Stance |
|---|---|---|---|---|
| 2022-08-31 | NVIDIA 8-K, SEC | https://www.sec.gov/Archives/edgar/data/1045810/000104581022000146/nvda-20220826.htm | A100/H100 exports to China need a license; about $400 million of Q3 China sales could be affected | supports |
| 2022-09-02 | Tom's Hardware | https://www.tomshardware.com/news/us-export-rules-may-cost-nvidia-400-million-prevent-h100-development | New rules could cost NVIDIA $400 million and affect H100 development | supports |
| 2022-09-02 | CnEVPost | https://cnevpost.com/2022/09/02/nvidia-says-it-got-us-permit-to-export-key-chips-in-updated-filing/ | NVIDIA gets permission to continue H100 development in China, and Hong Kong fulfillment until 2023-09 | contradicts (easing) |
| 2022-10-07 | BIS press release | https://www.bis.gov/press-release/commerce-implements-new-export-controls-advanced-computing-semiconductor-manufacturing-items-peoples | New control scope and phased effective dates (10/7, 10/12, 10/21) | supports |
| 2022-10-13 | Federal Register full rule text (govinfo PDF) | https://www.govinfo.gov/content/pkg/FR-2022-10-13/pdf/2022-21658.pdf | 3A090 thresholds: 600 GB/s bidirectional transfer **and** 4800 TOPS×bit | neutral (key detail: room for a compliant redesign exists) |
| 2022-10-13 | Federal Register web version | https://www.federalregister.gov/documents/2022/10/13/2022-21658/implementation-of-additional-export-controls-certain-advanced-computing-and-semiconductor-manufacturing | Same as above (the web page blocks automated fetching; the PDF version was verified) | neutral |

### 4. What actually happened
- **2022-11-07/08**: NVIDIA confirmed to Reuters that the A800 went into production in Q3 as an A100 alternative for Chinese customers, and said it meets the US government's test for reduced controls and cannot be programmed to exceed it. Source: Data Center Knowledge 11/8 https://www.datacenterknowledge.com/supercomputers/nvidia-skirts-us-expert-controls-china-alternative-chip ; CnEVPost 11/8; Caixin 11/8.
- **2022-11-16 (Q3 FY23 results)**: Data center revenue $3.83B, +31% year on year, +1% quarter on quarter (NVIDIA press release). Jon Peddie 11/18 relays management: export restrictions hit Q3 revenue, but the decline was "largely offset" by sales of alternative products to China. The press release itself does not mention China.
- **FY2024 10-K (year ended 2024-01-28)**: China's share of data center revenue fell from 19% in FY2023 to 14% in FY2024; in FY2024 Q4 it dropped to the mid single digits.
- **2023-10-17 BIS revision**: The rule **removed the "interconnect bandwidth" parameter** and added a "performance density" threshold, explicitly to prevent future workarounds. https://www.bis.gov/press-release/commerce-strengthens-restrictions-advanced-computing-semiconductors-semiconductor-manufacturing-equipment
- **2023-10-23/24 (NVIDIA 8-K)**: The US government notified NVIDIA that license requirements for the A100, A800, H100, H800 and L40S take effect immediately (originally 30 days later); NVIDIA said it does not expect a material near-term financial impact (strong global demand). https://www.sec.gov/Archives/edgar/data/1045810/000104581023000221/nvda-20231023.htm

### 5. Grading points
- **The real key dependency**: The rule's **technical threshold definition**, and whether NVIDIA can launch a redesigned product that does not trip the threshold and that customers still want to buy. At as_of, the "600 GB/s **and** 4800" structure could already be read from the rule text; this is the most valuable detail in the whole case.
- **Good entry condition (bearish on China revenue)**: NVIDIA confirms in its next 10-Q / earnings call that China data center revenue fell significantly, and **no** compliant alternative is shipping.
- **Failure condition**: NVIDIA or major media confirm that a compliant redesigned product (A800) is in volume production or shipping; or the results say the decline was "largely offset". Both 11/8 and 11/16 triggered this.
- **Re-arm condition**: BIS revises the rule and removes the parameter that was worked around (2023-10-17), and the redesigned products are named and covered (2023-10-23 8-K). After that, the bearish China revenue thesis holds (FY24 Q4 down to the mid single digits).
- **What the system should do**:
  - 10/13: **Hold off**. Reading the rule reveals the "and" structure → the key dependency is a compliant redesign. Also, NVDA's share price is driven mainly by overall AI / data center demand, so the "China controls → NVDA share price" chain is weak. If the instrument is NVDA stock, lean toward **abstain**; if the instrument is a verifiable metric such as "NVIDIA China revenue share", wait for the next earnings report.
  - 11/8 to 11/16: failure condition triggered → **do not enter**.
  - 2023-10-17 to 10-24: re-arm condition triggered → entry condition for the "China revenue falls" thesis met (verify with China revenue share, not the share price).
- **What to look for in evaluation**: Whether the model reads the rule text to find the threshold structure, rather than only reading news headlines; whether it can separate the two instruments, "company-level revenue" and "share price", and abstain on the latter (weak chain).

### 6. Contamination risk: medium-high
The A800/H800 workaround and the 2023 patch are both well known, and the model very likely knows them. But it may not remember the "600 GB/s and 4800" threshold detail and the exact timeline accurately. Suggest focusing the grading on whether it derives "room for redesign exists" from the rule text.

### 7. Verified URLs
- [content] https://www.sec.gov/Archives/edgar/data/1045810/000104581022000146/nvda-20220826.htm
- [title/date] https://www.tomshardware.com/news/us-export-rules-may-cost-nvidia-400-million-prevent-h100-development
- [title/date] https://cnevpost.com/2022/09/02/nvidia-says-it-got-us-permit-to-export-key-chips-in-updated-filing/
- [content] https://www.bis.gov/press-release/commerce-implements-new-export-controls-advanced-computing-semiconductor-manufacturing-items-peoples
- [content] https://www.govinfo.gov/content/pkg/FR-2022-10-13/pdf/2022-21658.pdf
- [requested, returned 200 but the body was replaced by a block page] https://www.federalregister.gov/documents/2022/10/13/2022-21658/implementation-of-additional-export-controls-certain-advanced-computing-and-semiconductor-manufacturing
- [content] https://www.datacenterknowledge.com/supercomputers/nvidia-skirts-us-expert-controls-china-alternative-chip
- [title/date] https://cnevpost.com/2022/11/08/nvidia-offers-a800-chip-for-china/
- [title] https://www.caixinglobal.com/2022-11-08/nvidia-to-sell-new-chip-in-china-it-says-meets-us-export-ban-101962115.html
- [content] https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2023
- [content] https://www.jonpeddie.com/news/nvidia-q3-fy23-results/
- [title/date] https://www.cnbc.com/2022/11/16/nvidias-quarter-fails-to-excite-but-offers-enough-hope-that-octobers-bottom-can-hold.html
- [content] https://www.sec.gov/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm
- [content] https://www.bis.gov/press-release/commerce-strengthens-restrictions-advanced-computing-semiconductors-semiconductor-manufacturing-equipment
- [content] https://www.sec.gov/Archives/edgar/data/1045810/000104581023000221/nvda-20231023.htm
- [not opened individually] Mayer Brown 2022-11 newsletter (200, body not read)

---

## Case 7: 2022-03 LME nickel: Russia supply fears → long nickel after reopening?

### 1. Name / timing / belief
- **Name**: LME nickel short squeeze and trade cancellation, March 2022
- **as_of**: 2022-03-15 (the day the LME announced reopening on 3/16 and published the price limits)
- **Belief**: Russia is a major nickel producer, and Nornickel is a major supplier of high-grade nickel; sanctions after the invasion of Ukraine will cut off Russian nickel supply → long nickel after the LME reopens.

### 2. Public reasoning at the time
- **LME (Notice 22/057, 3/10)**: The large rise on 3/7 was still orderly; prices in the early hours of 3/8 "did not reflect the underlying physical market" and the market was disorderly, so trading was suspended at 08:15 and all trades after midnight on 3/8 were canceled, reverting to the 3/7 close. The LME was also concerned that margin calls could trigger a chain of defaults.
- **Tsingshan standstill with banks (Bloomberg story, Daily Maverick 3/15; Caixin 3/15)**: Banks agreed not to close out positions or make further margin calls for now; Tsingshan still held more than 150,000 tonnes of short positions and pledged to reduce them in an orderly way once the market returns to normal. This shows that the main driver of the price was a **position squeeze**.
- **LME (Notice 22/064, 3/14; 22/067, 3/15)**: Reopening at 08:00 on 3/16; price limits on all base metals, ±5% for nickel; deliveries deferred; position accountability levels set.
- **Nornickel / Potanin (AFP 3/12, reprinted by O Povo)**: There are logistics difficulties (some European ports refusing cargo, air freight limited); it plans to redirect European and US orders to China and other countries but "has not done so yet"; WSJ thinks Nornickel may be "too big to sanction".
- **AFP (evening of 3/7 / 3/8, reprinted by ABS-CBN)**: Headline says nickel hit a record high, with Russia a major producer.
- **Core causal chain (belief version)**: invasion → sanctions → Russian nickel exports blocked → physical shortage → price rise. **Missing evidence**: Nornickel was not sanctioned; exports continued (with some logistics friction); the exchange itself characterized the 3/7 to 3/8 price spike as not reflecting the physical market.
- **Conclusion**: As the "correct answer" for evaluation, the system should **abstain**. There is no evidence for the "sanctions → physical supply cut" link in the causal chain; the price signal is contaminated by a position squeeze; and the trading instrument itself (LME nickel) carries rule risks such as trade cancellation, price limits and system outages.

### 3. Point-in-time pack (≤ 2022-03-15)
| Date | Source | URL | One-line content | Stance |
|---|---|---|---|---|
| 2022-03-08 00:43 UTC | ABS-CBN (AFP story) | https://abs-cbn.com/business/03/08/22/nickel-soars-to-record-high-of-54880-per-ton | Nickel hits record high of $54,880/tonne | supports (price narrative) |
| 2022-03-10 | LME Notice 22/057 (hosted by ISDA) | https://www.isda.org/a/KR0gE/TRADING-22-057-NICKEL-MARKET-UPDATE.pdf | Suspended trading and canceled 3/8 trades, because prices did not reflect the physical market and there was systemic margin risk | contradicts |
| 2022-03-12 | O Povo (AFP story, Portuguese) | https://www.opovo.com.br/noticias/mundo/2022/03/12/gigante-da-mineracao-russa-nornickel-enfrenta-primeiras-dificuldades-devido-a-sancoes-contra-a-russia.html | Nornickel has logistics difficulties but has not cut supply, and has not redirected yet; may be "too big to sanction" | contradicts (insufficient evidence of a supply cut) / neutral |
| 2022-03-14 | LME Notice 22/064 | https://www.lme.com/-/media/Files/News/Notices/2022/03/TRADING-22-064-NICKEL-MARKET-UPDATE-RESUMPTION-OF-TRADING.pdf | Reopening 3/16; price limits on all base metals; deliveries deferred; position accountability | neutral (instrument rule risk) |
| 2022-03-15 | LME Notice 22/067 (hosted by ISDA) | https://isda.org/a/LA0gE/TRADING-22-067-NICKEL-MARKET-UPDATE-DAILY-PRICE-LIMITS.pdf | Nickel daily price limit ±5% | neutral (instrument rule risk) |
| 2022-03-15 | Daily Maverick (Bloomberg story) | https://www.dailymaverick.co.za/article/2022-03-15-lme-to-reopen-nickel-market-march-16-after-xiang-short-squeeze/ | Tsingshan reaches standstill with banks and still holds more than 150,000 tonnes of shorts; LME requires disclosure of positions above 600 tonnes | contradicts (price driven by positions) |
| 2022-03-15 | Caixin Global | https://www.caixinglobal.com/2022-03-15/chinese-nickel-giant-secures-deal-to-avoid-further-margin-calls-101855706.html | Chinese nickel giant reaches a deal to avoid further margin calls | contradicts |

### 4. What actually happened
- **3/16 reopening**: 3-month nickel hit the 5% down limit right at the open; LMEselect was halted until 14:00 due to technical problems; the closing price triggered a "disruption event" (Notice 22/072). From 3/17, price limits were widened to 8% (Notice 22/073).
- **Monthly average price (IMF, FRED PNICKUSDM, $/tonne)**: 2022-02 24,016 → 03 33,924 → 04 33,134 → 05 28,229 → 06 25,877 → 07 21,482. https://fred.stlouisfed.org/data/PNICKUSDM.txt
- **Physical supply**: Fortune (2022-07-07) said sanctions had not yet caused an actual disruption to nickel supply at that point; in May, Tsingshan cut its short from more than 150,000 tonnes to 60,000 tonnes, and had basically closed it by end-June. https://fortune.com/2022/07/07/big-shot-billionaire-xiang-guangda-who-broke-nickel-market-clawed-short-squeeze-back-from-10-billion-loss/
- **Two years later**: Only in 2024-04 did the US and UK ban exchanges from accepting newly produced Russian aluminum, copper and nickel; Nornickel said it would continue to honor its contracts (Mining.com / Reuters 2024-04-16). I **did not find** a primary sanctions-list source that directly shows Nornickel itself was not on US / EU / UK sanctions lists in 2022; this point is marked unverified.
- **Legal outcome**: On 2023-11-29 the English High Court dismissed the challenges by Elliott and Jane Street to the LME's trade cancellation (Stephenson Harwood briefing, 2023-12-05). https://www.stephensonharwood.com/insights/london-metal-exchange-wins-high-court-ruling-over-cancelled-nickel-trades/

### 5. Grading points
- **The real key dependency**: (1) the **actual export flow** of Russian nickel (customs / export data, Nornickel sales and shipments, sanctions designations against Nornickel itself); (2) whether the price is driven by physical factors rather than by position structure (standstill / unwind progress of large shorts); (3) exchange rules (trade cancellation, price limits, outages).
- **If entering long (hypothetical)**: A formal sanctions designation on Nornickel or on Russian nickel exports, or a verifiable large drop in export volume (for example, quarterly sales down more than about 20% year on year), plus LME price limits back to normal levels and several consecutive days of normal trading.
- **Failure condition (already present at as_of)**: The exchange publicly characterized prices as not reflecting the physical market; the largest short reached a standstill with banks; the company itself was not sanctioned and exports continued.
- **What the system should do**:
  - 3/15: **Abstain**. Three reasons: no evidence for the physical link in the chain, a contaminated price signal, and instrument rule risk that cannot be quantified.
  - Afterwards: no entry condition appeared through the end of the observation period. The 2024-04 US/UK measures only targeted exchange delivery and imports, which is not the same as a physical supply cut.
- **What to look for in evaluation**: Whether the model separates "price spike" from "physical shortage"; whether it recognizes that exchange rules are themselves a link in the causal chain (trade cancellation means even a position with "the right direction" may not be realized); whether it can abstain in the face of a grand geopolitical narrative.

### 6. Contamination risk: medium-high
The LME nickel squeeze, the trade cancellation and Tsingshan are well known in financial media, and the model very likely knows them. But it may not clearly remember "limit down on the reopening day + system failure" and the path of monthly declines from March to July. The case can be anonymized as "some metal on some exchange" to reduce contamination.

### 7. Verified URLs
- [title/date] https://abs-cbn.com/business/03/08/22/nickel-soars-to-record-high-of-54880-per-ton
- [content] https://www.isda.org/a/KR0gE/TRADING-22-057-NICKEL-MARKET-UPDATE.pdf
- [content] https://www.opovo.com.br/noticias/mundo/2022/03/12/gigante-da-mineracao-russa-nornickel-enfrenta-primeiras-dificuldades-devido-a-sancoes-contra-a-russia.html
- [content] https://www.lme.com/-/media/Files/News/Notices/2022/03/TRADING-22-064-NICKEL-MARKET-UPDATE-RESUMPTION-OF-TRADING.pdf
- [content] https://isda.org/a/LA0gE/TRADING-22-067-NICKEL-MARKET-UPDATE-DAILY-PRICE-LIMITS.pdf
- [content] https://www.dailymaverick.co.za/article/2022-03-15-lme-to-reopen-nickel-market-march-16-after-xiang-short-squeeze/
- [title] https://www.caixinglobal.com/2022-03-15/chinese-nickel-giant-secures-deal-to-avoid-further-margin-calls-101855706.html
- [content] https://www.isda.org/a/YiPgE/TRADING-22-072-NICKEL-CLOSING-PRICES.pdf
- [content] https://www.isda.org/a/fiPgE/TRADING-22-073-CHANGES-TO-DAILY-PRICE-LIMITS-FOR-NICKEL.pdf
- [content] https://fred.stlouisfed.org/data/PNICKUSDM.txt
- [content] https://fortune.com/2022/07/07/big-shot-billionaire-xiang-guangda-who-broke-nickel-market-clawed-short-squeeze-back-from-10-billion-loss/
- [title] https://www.mining.com/web/nickel-tycoon-has-cut-big-short-position-by-more-than-half/
- [content] https://www.mining.com/web/nornickel-says-new-western-sanctions-raise-risk-of-metals-market-disruption/ (2024-04-16)
- [title/date] https://www.stephensonharwood.com/insights/london-metal-exchange-wins-high-court-ruling-over-cancelled-nickel-trades/
- [title/date] https://www.wesa.fm/2022-03-18/a-wild-ride-for-global-nickel-market (after as_of, its content not used)
- [could not open] Mining Weekly / Creamer Media 3/7 report (including JPMorgan's statements that Russia is about 10% of global nickel and Nornickel 15–20% of battery-grade nickel; seen only in search snippets, not verified); S&P Global 3/15 report (403); WisdomTree 3/25 blog post (403); BNN Bloomberg page (returned only the home page)

---

## Unverified items / points to note (summary)

1. **Blocked primary sources**: IEA (OMR, statements), OPEC press releases, CME clearing advisories, UNCTAD, S&P Global, ETF.com, FT and CDFPI all returned 403 / 402 / paywall. For the related facts, only openable secondhand accounts were used (CNBC, NPR, QCI, Reuters reprints, etc.), or the facts were explicitly marked "unverified".
2. **SVB 10-K HTM figures** (amortized cost $91.3B / fair value $76.2B) come from the CFA Institute blog post; I could not open the 10-K notes directly (WebFetch truncated, SEC refused curl). The uninsured deposit share uses the 94% from the Fed's after-the-fact report (FR Y-9C basis); the figure disclosed in the 10-K itself is not verified.
3. **SVB 3/14 follow-up 8-K**: the claims of AFS book value $23.97B, net proceeds $21.45B and buyer Goldman come from search snippets; the original was not opened.
4. **Moody's 3/8 downgrade of SVB**: no openable source published before as_of was found, only after-the-fact reports from 3/11 (Wolf Street, CNBC).
5. **Multiple measures of the OPEC+ August gap** (3.4 / 3.58 / 3.61 mb/d): only the QCI 3.58 page was opened; its body is JS-rendered, so only the title and date were verified; the specific split (1.399 / 2.185) comes from search snippets.
6. **Whether Nornickel was sanctioned in 2022**: I found no openable primary sanctions-list source to confirm "not sanctioned", only indirect evidence (Fortune 2022-07: sanctions had not caused an actual supply disruption; AFP 2022-03 citing WSJ "too big to sanction").
7. **EIA weekly data release dates** (Cushing 4/10 data released 4/15, 5/8 data released 5/13, etc.) are inferred from the EIA Wednesday release convention and not individually verified. The exact release date of the EIA 2019-09 STEO is also not verified.
8. **Drewry 12/14 WCI data**: the reprint page I could open was published on 12/19 (after as_of), and is marked ⚠️ in the pack.
9. **Several items had only the title / date verified** (JS-rendered pages); see the tags in section 7 of each case. If the body is needed before evaluation, review it manually or switch to an openable reprint.
10. **Price comparisons**: all use EIA / IMF spot or monthly average series, **not** futures settlement prices (the -$37.63 negative oil price from CFTC is the exception). Other data is needed when grading with futures.

## Alternates (not included, can be added)
- 2021-03 Ever Given grounding (3/23 to refloating on 3/29): "abstain / brief shock" type; needs its own point-in-time pack from before as_of.
- 2022 Russia-Ukraine war → European TTF gas / actual Nord Stream flows: "announcement ≠ physical flow" type; the key dependency is ENTSOG pipeline flow data.
- SVB control group from the same period: regional banks with a different deposit structure that did not fail, used to test whether the system over-extrapolates.
