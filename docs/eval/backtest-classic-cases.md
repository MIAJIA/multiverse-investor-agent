# 事件驱动交易研究 Agent：经典历史回测案例集（7 例）

整理日期：2026-10-18
用途：给「事件 / 信念 → 因果链 → 条件化交易提案（进场条件、失效条件、关键依赖；默认等待；链条弱时弃权）」这类系统做回测评测。评的不是「赚没赚钱」，而是：在 as_of 时点、只用当时公开信息，正确的条件化推理是什么；哪个依赖最关键；哪个可观测量在什么时候确认或否定了 thesis。

## 使用说明与核实口径

- **as_of** 一律指「决策时点当天」，并在每例注明是盘前还是收盘后。时点资料包只收 as_of 当天或之前发布的材料；少数「数据日期在 as_of 之前、但我能打开的网页转载日期在之后」的条目，单独标了 ⚠️，评测时可选择剔除或换成原始出处。
- **核实方式**：每个 URL 都实际请求过（WebFetch 或 curl），PDF 用 macOS PDFKit 抽文本。核实等级分三档：
  - 【内容】打开了正文，文中数字来自正文；
  - 【标题/日期】页面能打开，但正文是 JS 渲染或被截断，只核实了标题与发布时间；
  - 【未能打开】403 / 付费墙，只作为线索列出，**不用作数据来源**。
- 价格数据统一用 EIA 现货序列（Brent: RBRTED，WTI: RWTCD）和 IMF/FRED 月度镍价，都是可复查的公开序列。期货结算价只在有官方出处（CFTC）时引用。
- 引用原文均不超过 15 个英文单词，其余为本人概括。
- 「立场」是相对于该案例的初始 thesis：supports / contradicts / neutral。

## 总览

| # | 案例 | as_of | 结局类型 | 污染风险 |
|---|---|---|---|---|
| 1 | 2019 Abqaiq 袭击 → 做多 Brent | 2019-09-16（美盘前） | 失效条件 72 小时内可观测地触发；正确动作是「先别动」，然后不进场 | 中高 |
| 2 | 2020-04 OPEC+ 减产 + 低油价 → 抄底 WTI 近月 / USO | 2020-04-17（周五收盘后） | 「宣布 ≠ 现实」+ 工具映射断裂（库容约束）；正确动作是弃权 | 高 |
| 3 | 2022-10 OPEC+ 宣布减产 2 mb/d → 做多 Brent | 2022-10-05（会后） | 「宣布 ≠ 现实」：名义 2 mb/d，实际 OPEC 产量月降约 0.71 mb/d | 中 |
| 4 | 2023-03 SVB 亏损出售证券 + 募资 → 挤兑风险 | 2023-03-08（8-K 发布后、3/9 开盘前） | thesis 成立，确认信号 24 小时内出现；但可操作窗口只有一个交易日 | 高 |
| 5 | 2023-12 胡塞袭击红海 → 集装箱运价上涨 | 2023-12-18 | thesis 成立；中途「恢复通航」公告是假信号 | 中高 |
| 6 | 2022-10 美国对华 AI 芯片出口管制 → NVIDIA 中国收入下滑 | 2022-10-13（规则文本刊登当日） | 推理合理，但因规则里一个具体技术条件（「且」关系）被绕开而失败约一年；规则修补后才成立 | 中高 |
| 7 | 2022-03 俄罗斯供应担忧 → LME 复市后做多镍 | 2022-03-15（复市前一日） | 正确动作是弃权：因果链（制裁 → 实物断供）缺证据，价格由持仓挤兑驱动，交易所规则风险极高 | 中高 |

---

## 案例 1：2019 Abqaiq / Khurais 袭击 → 油价持续上涨？

### 1. 名称 / 时点 / 信念
- **名称**：Abqaiq-Khurais attack, Sept 2019
- **as_of**：2019-09-16（周一，美股开盘前，约 13:00 UTC；Brent 已在亚洲时段跳涨）
- **信念**：9/14 袭击使沙特约 5.7 mb/d 产量中断，供应冲击会让油价持续走高 → 做多 Brent 近月。

### 2. 当时公开的推理
- **Goldman Sachs（Jeffrey Currie、Damien Courvalin，9/15 周日报告，CNBC 9/16 转述）**：结论是有条件的，取决于中断时长。若中断被宣布将持续超过六周，Brent 会快速升破 $75；短期中断影响有限。
- **ING（9/15）**：中断只有几天，市场能较轻松消化；拖到几周，市场会显著收紧。依据：JODI 数据显示沙特 6 月底原油库存约 188 mb，约等于 26 天出口；OPEC 闲置产能七成以上在沙特，其他国家能补的量远小于缺口。
- **IEA（9/14 声明）**：当下市场供应充足，商业库存充裕；未提动用应急库存。
- **美国政府（9/15）**：Trump 授权「如有需要」动用 SPR，数量未定。
- **沙特方面（9/15，据 WSJ/CNBC）**：目标是到周一恢复约三分之一的受损产量。
- **核心因果链**：袭击 → Abqaiq 处理能力受损 → 沙特原油出口减少 → 全球供应缺口 → 闲置产能不足以弥补 → 油价上涨。**关键在中间那一环：出口是否真的减少、减少多久。**
- **当时的结论**：主流是「有条件做」，条件是中断持续时间。

### 3. 时点资料包（≤ 2019-09-16）
| 日期 | 来源 | URL | 一句话内容 | 立场 |
|---|---|---|---|---|
| 2019-09（月初发布，精确发布日未核实） | EIA STEO, September 2019 | https://www.eia.gov/outlooks/steo/archives/sep19.pdf | 袭击前的基线：EIA 预期 2019、2020 年全球库存都在累积，2019 年 Brent 预测下调至约 $63 | contradicts（基本面偏松） |
| 2019-09-15（Reuters 稿，Daily FT 9/16 刊） | IEA statement via Daily FT | https://www.ft.lk/International/IEA-says-oil-markets-well-supplied-after-attack-in-Saudi-Arabia/49-685723 | IEA 称市场供应充足、商业库存充裕，正与沙特及主要国家联络 | contradicts |
| 2019-09-15 | ING THINK "Saudi oil attacks" | https://think.ing.com/articles/saudi-oil-attacks | 几天的中断能消化，几周则会收紧；沙特库存约 26 天出口；闲置产能集中在沙特 | neutral（条件化） |
| 2019-09-15 | CNBC（转述 WSJ） | https://www.cnbc.com/2019/09/15/saudi-arabia-aims-to-restore-one-third-of-lost-oil-output-by-monday-wsj-says.html | 沙特目标在周一前恢复约三分之一受损产量 | contradicts |
| 2019-09-15 | CBS News | https://www.cbsnews.com/news/trump-authorizes-release-emergency-oil-reserve-after-attack-saudi-oil-sites-2019-09-15/ | Trump 授权「如有需要」动用 SPR | contradicts（弱） |
| 2019-09-16 12:06 UTC | CNBC：Goldman 报告 | https://www.cnbc.com/2019/09/16/goldman-sachs-says-an-extended-saudi-outage-could-push-brent-crude-oil-prices-above-75.html | 若中断被宣布超过六周，Brent 将升破 $75；当日 Brent 期货涨约 10% 至 $66.43 | supports（条件化） |

### 4. 事后真相
- **9/17**：Aramco 发布会称 Khurais 已在 24 小时后恢复生产，Abqaiq 当时约 2 mb/d，全部产能 9 月底前恢复；客户发货没有一船被取消或错过。来源：Aramco 新闻稿 https://www.aramco.com/en/news-media/news/2019/saudi-aramco-swiftly-restores-production-capacity
- **9/18**：EIA TWIP 记录 9/16 油价单日涨幅为多年来最大，9/17 因恢复消息回落。https://www.eia.gov/petroleum/weekly/archive/2019/190918/includes/analysis_print.php
- **10/3 前后**：EIA 10 月 STEO 估计沙特原油产量 10 月 3 日已回到中断前水平；9 月平均产量 8.5 mb/d（8 月 9.9）；10 月初油价已回到袭击前水平，2020 年及以后的远月合约甚至低于袭击前。https://www.eia.gov/outlooks/steo/archives/oct19.pdf
- **EIA 证词（2019-10-17）**：几天内业内就报告沙特靠库存与转移国内炼厂用量，把出口恢复到袭击前水平；9/17 Brent 回落到 $65.59；9/30 低于袭击前。https://www.eia.gov/pressroom/testimonies/capuano_10172019.pdf
- **Brent 现货（EIA RBRTED）**：9/13 $61.25 → 9/16 $68.42 → 9/17 $65.59 → 9/30 $60.99 → 10/3 $58.01。https://www.eia.gov/dnav/pet/hist/RBRTED.htm

### 5. 判定要点
- **真正的关键依赖**：沙特**出口装船量**是否下降、下降多久。袭击本身和「5.7 mb/d 停产」的标题都不是。沙特有库存缓冲，可以用库存和国内炼厂用量填补出口。
- **好的进场条件（做多）**：任一可核实信号出现即可：(a) Aramco 或沙特能源部正式表示恢复时间超过约 6 周（Goldman 的门槛）；(b) Aramco 对亚洲 / 欧洲长约客户削减分配量（客户声明或主流通讯社报道）；(c) 油轮追踪显示沙特出口周均值较 8 月下降超过约 1 mb/d，并且持续两周以上。
- **失效条件**：Aramco 给出数周内全面恢复的时间表，且客户确认发货不受影响。9/17 这一条已经满足。
- **系统应有的动作**：
  - 9/16：**先别动**。标题冲击已经计入价格，中断时长未知；最关键的信息（Aramco 时间表、客户分配）预计 24 到 48 小时内就会出来。
  - 9/17：失效条件触发（恢复时间表 + 发货不受影响）→ **弃权 / 不进场**；如已有多头则退出。
  - 10/3：EIA 确认产量恢复，事后验证。
- **评测看点**：模型是否把关键依赖定为「出口 / 客户分配」，而不是「袭击 / 停产标题」；是否把 9/17 的发布会识别为失效触发点；是否意识到 Brent 月差可以当作市场对中断时长的定价（Oilprice 9/18 有此类分析，但发布在 as_of 之后，不进资料包）。

### 6. 污染风险：中高
事件很有名，「油价急涨后很快回落」是常见的复盘素材。模型很可能知道结局，但不一定记得 9/17 发布会和 10/3 恢复的具体时间。评测时可以考虑隐去国家名和设施名做匿名化。

### 7. 已核实 URL
- 【内容】https://www.cnbc.com/2019/09/16/goldman-sachs-says-an-extended-saudi-outage-could-push-brent-crude-oil-prices-above-75.html
- 【内容】https://think.ing.com/articles/saudi-oil-attacks
- 【内容】https://www.cnbc.com/2019/09/15/saudi-arabia-aims-to-restore-one-third-of-lost-oil-output-by-monday-wsj-says.html
- 【内容】https://www.cbsnews.com/news/trump-authorizes-release-emergency-oil-reserve-after-attack-saudi-oil-sites-2019-09-15/
- 【内容】https://www.ft.lk/International/IEA-says-oil-markets-well-supplied-after-attack-in-Saudi-Arabia/49-685723
- 【内容】https://www.eia.gov/outlooks/steo/archives/sep19.pdf
- 【内容】https://www.aramco.com/en/news-media/news/2019/saudi-aramco-swiftly-restores-production-capacity
- 【内容】https://www.eia.gov/petroleum/weekly/archive/2019/190918/includes/analysis_print.php
- 【内容】https://www.eia.gov/todayinenergy/detail.php?id=41413（EIA 2019-09-23）
- 【内容】https://www.eia.gov/todayinenergy/detail.php?id=41513（EIA 2019-10-01）
- 【内容】https://www.eia.gov/outlooks/steo/archives/oct19.pdf
- 【内容】https://www.eia.gov/pressroom/testimonies/capuano_10172019.pdf
- 【内容】https://www.eia.gov/todayinenergy/detail.php?id=42415（EIA 2020-01-07，Brent 9 月底回到袭击前水平）
- 【内容】https://www.eia.gov/todayinenergy/detail.php?id=42675（EIA 2020-01-31，袭击后价格变动为 29 年来最大单日百分比变动）
- 【内容】https://www.eia.gov/dnav/pet/hist/RBRTED.htm
- 【标题/日期】https://www.naturalgasworld.com/oil-markets-well-supplied-iea-73005
- 【内容，as_of 后】https://oilprice.com/Energy/Energy-General/Brent-Spreads-Tell-The-Truth-About-Saudi-Oil-Disruption.html（2019-09-18）
- 【标题/日期，as_of 后】https://gulfnews.com/business/energy/saudi-aramcos-oil-stockpiles-can-cover-lower-output-1.66549232（2019-09-20）
- 【未能打开】IEA 声明原文、Al Arabiya 转载（403）

---

## 案例 2：2020 年 4 月：OPEC+ 史上最大减产 + 油价「便宜」→ 抄底 WTI 近月 / USO？

### 1. 名称 / 时点 / 信念
- **名称**：April 2020 WTI front-month collapse / USO
- **as_of**：2020-04-17（周五收盘后；5 月 WTI 合约 4/21 到期）
- **信念**：OPEC+ 已于 4/12 敲定 9.7 mb/d 减产（5/1 起），WTI 跌到约 $18，是历史低位 → 买入 WTI 近月或 USO 抄底。

### 2. 当时公开的推理
- **IEA（4/15 OMR，CNBC / NPR 转述）**：4 月需求同比少约 29 mb/d；即使有 OPEC+ 和 G20 的决定，上半年隐含库存累积约 12 mb/d，可能在未来几周压垮船、管道、储罐等物流能力。这实际上是「不做近月」的论证。
- **OPEC+（4/12 协议，Hydrocarbon Engineering 4/14 转述公报）**：9.7 mb/d 减产 **5 月 1 日**才生效，到 6/30 止，之后降为 7.7 mb/d。宣布时间与生效时间相差两周以上。
- **EIA（4/15 TWIP）**：低价将导致美国产量下降，但下降是一个按月展开的过程。
- **EIA 周度 Cushing 库存**：3/27 42.8 mb → 4/3 49.2 mb → 4/10 55.0 mb（按 EIA 周三发布惯例，4/10 数据在 4/15 公布），连续单周增加 5.7 到 6.4 mb。EIA 公布的 Cushing 工作库容约 76 mb。
- **USO 自身（8-K，报告日期 4/16）**：以「市场条件和监管要求」为由，从 4/17 起把约 20% 持仓移到次月合约。产品发行方自己在调整结构，这是很强的压力信号。
- **核心因果链（正确版本）**：需求崩塌 → 库存累积速度远超减产速度 → 交割地 Cushing 的未承诺库容耗尽 → 近月合约的持有者无处接货 → 近月对远月深度 contango → 近月价格和展期型 ETF 收益与「油价反弹」脱钩。
- **结论**：抄底叙事是「做」；IEA 和 EIA 的数据指向「不做近月 / 不做 USO」。

### 3. 时点资料包（≤ 2020-04-17）
| 日期 | 来源 | URL | 一句话内容 | 立场 |
|---|---|---|---|---|
| 2020-04-14 | Hydrocarbon Engineering（转述 OPEC+ 公报） | https://www.hydrocarbonengineering.com/refining/14042020/opec-agrees-massive-deal-to-cut-oil-output | 9.7 mb/d 减产自 5/1 起，至 6/30；之后 7.7 mb/d | supports（标题）/ 时间错配 |
| 2020-04-15 | CNBC（IEA OMR） | https://www.cnbc.com/2020/04/15/coronavirus-to-erase-nearly-a-decade-of-oil-demand-growth-in-2020-iea.html | 4 月需求 -29 mb/d；上半年隐含累库 12 mb/d，物流可能被压垮 | contradicts |
| 2020-04-15 | NPR | https://www.npr.org/sections/coronavirus-live-updates/2020/04/15/834868805/oil-prices-keep-slipping-as-demand-drops-by-record-amounts | 储存危机可能在绝对库容用完前就出现，例如管道无空间 | contradicts |
| 2020-04-15 | EIA This Week in Petroleum | https://www.eia.gov/petroleum/weekly/archive/2020/200415/includes/analysis_print.php | EIA 预测美国产量因低价下降，生产端现货出现大幅贴水 | neutral |
| 2020-04-15（数据截至 4/10） | EIA 周度 Cushing 库存序列 | https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=W_EPC0_SAX_YCUOK_MBBL&f=W | Cushing 库存 55.0 mb，两周（3/27→4/10）增加约 12 mb | contradicts |
| 2020-04-16（报告日期） | USO Form 8-K, SEC | https://www.sec.gov/Archives/edgar/data/1327068/000117120020000242/i20244_uso-8k.htm | 4/17 起 80% 近月 + 20% 次月；警告可能无法实现投资目标 | contradicts |

（未能打开、仅作线索：CME Clearing Advisory 20-152（4/8）和 20-160（4/15），据二手转述涉及负价格测试与期权模型切换，cmegroup.com 返回 403。ETF.com 关于 USO 调仓的报道同样 403。）

### 4. 事后真相
- **2020-04-20**：5 月 WTI 合约结算于 **-$37.63**，上市 37 年来首次为负。来源：CFTC 中期报告新闻稿（2020-11-23）https://www.cftc.gov/PressRoom/PressReleases/8315-20 。EIA WTI 现货 4/17 $18.31 → 4/20 -$36.98。https://www.eia.gov/dnav/pet/hist/RWTCD.htm
- **EIA 事后解释（4/22、4/27）**：Cushing 工作库容 76 mb，4/17 已存 60 mb（约 76%），未被承租或承诺的库容更少，所以没有提前安排的合约持有者无法接货。https://www.eia.gov/todayinenergy/detail.php?id=43495
- **USO**：4/28 收盘后 1 拆 8 反向拆股（拆前 NAV $2.04）。按拆股调整后的每份 NAV：2019-12-31 $102.27 → 2020-06-30 $28.02（-72.6%）；同期 WTI 现货 $61.14 → $39.27（-35.8%）。来源：USO 10-Q（2020 Q2）https://www.sec.gov/Archives/edgar/data/1327068/000110465920091976/uso-20200630x10q.htm
- **Cushing 库存拐点**：5/1 当周见顶 65.4 mb，此后 5/8 62.4、5/15 56.9、5/22 53.5（EIA 周度序列）。

### 5. 判定要点
- **真正的关键依赖**：**Cushing 未承诺库容**和近月 / 次月价差（contango 深度），不是 OPEC+ 的减产公告，也不是油价的绝对水平。
- **好的失效条件（对「抄底近月 / USO」而言，as_of 当时已触发）**：Cushing 周增量大于约 4 mb 且利用率超过约 70%，同时距近月到期不足一周；或展期型 ETF 发行方修改展期规则（USO 8-K）。
- **好的进场条件（若表达「油价中期回升」）**：EIA 周度 Cushing 库存**连续两周下降**，且近月价差的 contango 明显收窄；工具用较远月合约，不用近月展期型 ETF。
- **系统应有的动作**：
  - 4/17：**弃权**（近月 / USO）。理由：库容约束可观测，并且已经逼近；减产要到 5/1 才生效。
  - 5/13（5/8 数据，首次去库）→ 先别动；5/20（5/15 数据，连续第二周去库）→ 「油价回升」thesis 的进场条件成立（日期按 EIA 周三发布惯例推算，未逐一核实发布日）。
- **评测看点**：模型能否区分「宣布」（4/12 减产）和「生效」（5/1）；能否把 instrument mapping（现货 ≠ 近月期货 ≠ 展期 ETF）当成因果链的一环；能否主动弃权。

### 6. 污染风险：高
「负油价」极为知名，模型几乎肯定知道 4/20 的结局。建议评测时：(a) 匿名化（换成「某交割地原油合约」）；或 (b) 只评分「关键依赖识别」和「工具映射」两项，不评方向。

### 7. 已核实 URL
- 【内容】https://www.hydrocarbonengineering.com/refining/14042020/opec-agrees-massive-deal-to-cut-oil-output
- 【内容】https://www.cnbc.com/2020/04/15/coronavirus-to-erase-nearly-a-decade-of-oil-demand-growth-in-2020-iea.html
- 【内容】https://www.npr.org/sections/coronavirus-live-updates/2020/04/15/834868805/oil-prices-keep-slipping-as-demand-drops-by-record-amounts
- 【内容】https://www.eia.gov/petroleum/weekly/archive/2020/200415/includes/analysis_print.php
- 【内容】https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=W_EPC0_SAX_YCUOK_MBBL&f=W
- 【内容】https://www.sec.gov/Archives/edgar/data/1327068/000117120020000242/i20244_uso-8k.htm
- 【内容】https://www.cftc.gov/PressRoom/PressReleases/8315-20
- 【内容】https://www.eia.gov/dnav/pet/hist/RWTCD.htm
- 【内容】https://www.eia.gov/todayinenergy/detail.php?id=43495
- 【内容】https://www.eia.gov/petroleum/weekly/archive/2020/200422/includes/analysis_print.php
- 【内容】https://www.sec.gov/Archives/edgar/data/1327068/000110465920091976/uso-20200630x10q.htm
- 【标题/日期】https://www.cnbc.com/2020/04/20/oil-markets-us-crude-futures-in-focus-as-coronavirus-dents-demand.html
- 【未能打开】cmegroup.com 清算通知 20-160 / 20-152；etf.com USO 报道；iea.org OMR；opec.org 新闻稿（403 / 402）

---

## 案例 3：2022-10-05 OPEC+ 宣布减产 2 mb/d → 做多 Brent？

### 1. 名称 / 时点 / 信念
- **名称**：OPEC+ 33rd ONOMM headline cut, Oct 2022
- **as_of**：2022-10-05（会议决定公布后）
- **信念**：OPEC+ 自 11 月起把产量目标下调 2 mb/d，实际供应将收紧约 2 mb/d → 做多 Brent。

### 2. 当时公开的推理
- **Argus（据 QCI 9/19 转述）**：8 月 OPEC+ 实际产量比配额少 3.58 mb/d，创纪录；其中 OPEC-10 少 1.399 mb/d，非 OPEC 盟友少 2.185 mb/d。很多成员早就产不到配额。
- **UBS（9/27）**：需要至少 0.5 mb/d 的减产才能止住短期跌势。
- **Reuters（10/2）**：会议将考虑超过 1 mb/d 的减产。
- **Goldman Sachs（据 QCI 10/5 当日稿）**：有效减产大概只有名义配额减幅的 50% 左右，大部分成员在下调后的配额下仍然合规。
- **配额表（Argaam 10/5）**：沙特、俄罗斯各减 52.6 万桶/日，是减量最大的两国。
- **核心因果链**：配额下调 → **仅对实际产量高于新配额的成员构成约束** → 实际减产 ≈ 有闲置能力的海湾国家（沙特、阿联酋、科威特、伊拉克等）的减量 → 供应收紧幅度远小于标题。
- **当时的结论**：方向偏多，但幅度大约是标题的一半，属于有条件。

### 3. 时点资料包（≤ 2022-10-05）
| 日期 | 来源 | URL | 一句话内容 | 立场 |
|---|---|---|---|---|
| 2022-09-19 | QCI（转述 Argus） | https://qcintel.com/article/opec-misses-august-target-by-record-3-58-million-bpd-report-8553.html | 8 月 OPEC+ 比配额少产 3.58 mb/d，创纪录 | contradicts（标题会夸大） |
| 2022-09-27 | QCI（UBS 观点） | https://qcintel.com/article/only-an-opec-output-cut-can-halt-short-term-brent-losses-ubs-8715.html | 只有 OPEC+ 减产能止住 Brent 短期跌势 | supports |
| 2022-10-02 | BOE Report（Reuters 稿） | https://boereport.com/2022/10/02/opec-to-consider-oil-output-cut-of-more-than-1-million-bpd/ | OPEC+ 将考虑超过 1 mb/d 的减产 | supports |
| 2022-10-05 | QCI | https://qcintel.com/article/opec-slashes-headline-output-by-2-million-bpd-from-november-8880.html | 名义减产 2 mb/d、以 8 月配额为基准；Goldman 称有效减产约为名义的一半 | neutral（方向支持，幅度反对） |
| 2022-10-05 | Argaam | https://www.argaam.com/en/article/articledetail/id/1592696 | 11 月各国配额表 | neutral |

### 4. 事后真相
- **价格（EIA Brent 现货）**：10/5 $94.35 → 10/7 $98.88 → 11/7 $99.87 → 12/9 $76.37。先涨后跌，12 月初已明显低于决定前。下跌期间同时有需求预期、中国防疫政策、俄油价格上限等其他因素，**不能把下跌只归因于减产不足**。https://www.eia.gov/dnav/pet/hist/RBRTED.htm
- **实际执行（Reuters 11 月产量调查，2022-12-01）**：OPEC 11 月产量 29.01 mb/d，环比降 71 万桶/日；分给 OPEC-10 的名义减量约 1.27 mb/d，实际环比降约 72 万桶/日；沙特降约 50 万桶/日，基本落实；安哥拉、尼日利亚反而增产但仍远低于配额；按配额计算的「合规率」达 163%，因为本来就产不够。来源：Oman Observer 转载的 Reuters 稿 https://www.omanobserver.om/article/1129165/business/opec-oil-output-drops-in-nov-after-cut-pledged ；QCI https://www.qcintel.com/article/opec-output-down-700-000-bpd-in-november-after-cuts-implemented-survey-10209.html
- **事后评论**：Bloomberg 专栏（Deccan Herald 10/9 转载）标题称这次减产「10% 真实，90% 幻觉」。https://www.deccanherald.com/amp/story/business%2Fopec-oil-production-cut-could-be-10-real-90-illusion-1152011.html

### 5. 判定要点
- **真正的关键依赖**：11 月起**有闲置能力成员的实际产量**（沙特、阿联酋、科威特、伊拉克），以及合计实际减量，而不是名义配额。可观测量：各家产量调查（Reuters / Platts / Argus 月初发布）、OPEC MOMR 二手来源数据（月中）、油轮出口追踪。
- **好的进场条件（做多「供应收紧」）**：11 月产量调查（约 12/1 发布）显示 OPEC+ 合计实际减量 ≥ 约 1 mb/d，并且 OECD 库存或出口数据随后确认。
- **失效条件**：调查显示实际减量明显低于 1 mb/d，或减量只来自沙特一国、其他有能力成员没有执行。
- **系统应有的动作**：
  - 10/5：**先别动**。标题已经计价；决定性的可观测量（11 月实际产量）最早 12 月初才有；公开分析已经指出有效减量约为名义的一半。
  - 12/1：调查显示 OPEC 环比仅降约 0.71 mb/d → 「2 mb/d 收紧」thesis 未获确认 → **不进场**。
- **评测看点**：模型能否主动把「配额」和「产量」分开，并引用 as_of 前已公开的「8 月少产 3.58 mb/d」来推出名义减产会被稀释；能否给出「何时能拿到实际产量数据」的时间表，而不是凭标题行动。

### 6. 污染风险：中
这次减产本身有名（美沙关系争议），但「实际执行量」和具体调查数字不太可能被模型精确记住。适合作为「宣布 ≠ 现实」的主力案例。

### 7. 已核实 URL
- 【标题/日期】https://qcintel.com/article/opec-misses-august-target-by-record-3-58-million-bpd-report-8553.html
- 【标题/日期】https://qcintel.com/article/only-an-opec-output-cut-can-halt-short-term-brent-losses-ubs-8715.html
- 【内容】https://boereport.com/2022/10/02/opec-to-consider-oil-output-cut-of-more-than-1-million-bpd/
- 【内容】https://qcintel.com/article/opec-slashes-headline-output-by-2-million-bpd-from-november-8880.html
- 【标题/日期】https://www.argaam.com/en/article/articledetail/id/1592696
- 【标题/日期，as_of 后】https://www.argaam.com/en/article/articledetail/id/1592755（10/6，Brent 连涨四日）
- 【标题/日期，as_of 后】https://www.deccanherald.com/amp/story/business%2Fopec-oil-production-cut-could-be-10-real-90-illusion-1152011.html
- 【内容】https://www.omanobserver.om/article/1129165/business/opec-oil-output-drops-in-nov-after-cut-pledged
- 【标题/日期】https://www.qcintel.com/article/opec-output-down-700-000-bpd-in-november-after-cuts-implemented-survey-10209.html
- 【内容】https://www.eia.gov/dnav/pet/hist/RBRTED.htm
- 【未能打开】S&P Global Platts 9 月调查（3.61 mb/d 缺口，403）；iea.org 10 月 OMR（403）；OPEC 新闻稿（403）
- 注：8 月缺口的不同口径（Argus 3.58 / Argus 自身调查 3.4 / Platts 3.61 mb/d）来自搜索摘要，只有 QCI 的 3.58 页面打开过。

---

## 案例 4：2023-03 SVB：亏损出售证券 + 紧急募资 → 挤兑？

### 1. 名称 / 时点 / 信念
- **名称**：Silicon Valley Bank failure, March 2023
- **as_of**：2023-03-08（周三美东收盘后，SVB 8-K 已发布；3/9 开盘前）
- **信念**：SVB 为补流动性亏损出售证券并紧急募资，暴露了加息造成的证券浮亏和存款流失；存款高度集中、大多未受保险，可能发生挤兑 → 做空 SIVB / 回避同类区域银行。

### 2. 当时公开的推理
- **SVB 自己（3/8 8-K，Exhibit 99.3 致利益相关方信）**：卖出几乎全部 AFS 证券，税后亏损约 $1.8B；拟募资约 $2.25B（含 General Atlantic $5 亿）；定期借款由 $15B 增至 $30B；2 月客户「烧钱」仍高，存款低于预期，下调全年存款、NII、NIM 指引。
- **SVB 10-K（2023-02-24 提交）**：HTM 证券按摊余成本约 $91.3B、公允价值约 $76.2B（浮亏约 $15.1B），对比股东权益约 $16B。HTM 数字来自 CFA Institute 3/13 博文对 SVB 财报附注的复述，我未能直接打开 10-K 附注；10-K 正文可核实的部分是存款 $173.1B、股东权益 $16.0B。
- **FDIC（2/28 季度银行业概况）**：全行业证券未实现亏损 $620.4B（HTM $340.9B）；FDIC 主席讲话警告，若银行需要卖券满足流动性，浮亏会变成实亏。
- **FT（2/22）**：报道 SVB 吸引做空者（付费墙未能打开；美联储事后报告引用了这篇报道）。
- **Silvergate（3/8）**：宣布清盘。另一家依赖特定行业存款的银行出事，可能引发同类存户联想。
- **Moody's（3/8 晚）**：把 SVB Financial 从 A3 下调至 Baa1，展望负面（据 Wolf Street 3/11 事后报道，我没有找到 as_of 前发布的可打开来源）。
- **核心因果链**：加息 → 长久期 MBS 浮亏（HTM 不入账）→ 科技客户烧钱、存款流出 → 被迫卖 AFS 实现亏损 + 募资 → 向市场公开了资本缺口 → 未受保险、高度集中的 VC 系存款协同撤离 → 流动性危机。
- **结论**：做空 / 回避，条件取决于募资能否完成、存款是否稳定。

### 3. 时点资料包（≤ 2023-03-08）
| 日期 | 来源 | URL | 一句话内容 | 立场 |
|---|---|---|---|---|
| 2023-02-22 | Financial Times（据美联储报告脚注） | https://www.ft.com/content/0387e331-61b4-4848-9e50-04775b4c3fa7 | SVB 吸引做空者【未能打开】 | supports |
| 2023-02-24 | SVB 10-K（EDGAR 目录时间戳 2023-02-24） | https://www.sec.gov/Archives/edgar/data/719739/000071973923000021/sivb-20221231.htm | 存款 $173.1B，股东权益 $16.0B；HTM 公允价值披露在附注中 | supports |
| 2023-02-28 | FDIC 新闻稿 | https://www.fdic.gov/news/press-releases/2023/pr23013.html | 全行业证券未实现亏损 $620.4B，其中 HTM $340.9B | supports（行业背景） |
| 2023-02-28 | FDIC 主席讲话 | https://www.fdic.gov/news/speeches/2023/spfeb2823.html | 若需卖券满足流动性，浮亏可能变成实亏 | supports |
| 2023-03-08 | Kitco（Reuters 稿） | https://www.kitco.com/news/off-the-wire/2023-03-08/crypto-focused-bank-silvergate-plans-wind-down-operations | Silvergate 计划清盘 | supports（传染） |
| 2023-03-08 17:16（EDGAR 目录时间戳） | SVB 8-K Ex.99.3 | https://www.sec.gov/Archives/edgar/data/719739/000119312523064680/d430920dex993.htm | 卖 AFS 税后亏损 $1.8B、募资 $2.25B、借款增至 $30B、下调存款指引 | supports |
| 2023-03-08 | SVB 8-K Ex.99.2（投资者演示） | https://www.sec.gov/Archives/edgar/data/719739/000119312523064680/d430920dex992.htm | 同上，演示文稿版本 | supports |

### 4. 事后真相
- **3/9**：SIVB 股价跌约 60%（CNBC 3/9 标题）。https://www.cnbc.com/2023/03/09/svb-financial-falls-more-than-50percent-as-tech-bank-looks-to-raise-more-cash.html
- **3/9**：存款流出超过 $40B，管理层预计 3/10 再流出超过 $100B，约占存款基础的 85%。来源：美联储 SVB 事后审查（2023-04-28）https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf 。该报告还写明：2022 年末约 94% 的存款未受保险（FR Y-9C 口径）。
- **3/10 上午**：CNBC 报道募资失败、寻求出售；当天 CDFPI 关闭银行，FDIC 接管。https://www.cnbc.com/2023/03/10/silicon-valley-bank-financial-in-talks-to-sell-itself-after-attempts-to-raise-capital-have-failed-sources-say.html ；https://www.fdic.gov/news/press-releases/2023/pr23016.html
- **3/14（SVB 后续 8-K）**：3/8 出售的 AFS 账面价值约 $23.97B，净收入约 $21.45B，买方为 Goldman Sachs。（来自搜索结果对该 8-K 的摘要，原文未打开，标为未核实。）

### 5. 判定要点
- **真正的关键依赖**：**未受保险存款的流向**，以及 $2.25B 募资能否定价完成。证券浮亏本身已存在数月，只要存款不跑就不致命。
- **实时可观测量**：增发是否在 3/9 收盘前定价（没有定价）；大型 VC 是否公开或半公开建议被投企业撤资；评级行动（3/8 晚 Moody's 下调）；同业（如 Silvergate）事件。存款流出本身**无法实时观测**，只能事后从监管报告得知。这一点对系统设计很重要。
- **好的进场条件（做空 / 回避）**：增发未在宣布后约 24 小时内定价，或主流媒体报道「募资失败 / 寻求出售」。
- **失效条件**：增发足额定价，且有大型机构锚定投资，或出现收购方 / 监管层面的流动性支持声明。
- **系统应有的动作**：
  - 3/8 晚：**有条件做（偏回避）**。至少对「持有 SIVB 多头」应退出；做空的进场条件取决于 3/9 盘中增发进展。
  - 3/9 盘中至收盘：增发未定价且股价崩跌 → 进场条件成立，但空头已在当日大部分兑现。
  - 3/10 盘前：停牌，之后被接管，没有可执行窗口。
- **评测看点**：(a) 关键依赖要定为「存款流向 + 募资完成」，而不是「HTM 浮亏」本身；(b) 系统要意识到「等证据」的代价：确认信号和不可交易几乎同时到来，所以 thesis 要以「风险规避 / 退出多头」的形式表达，不能只等进场；(c) 对其他区域银行的外推需要逐家看存款结构，不能一概而论（可作为追问）。

### 6. 污染风险：高
2023 年最知名的银行事件之一。模型必然知道结局。建议只评「关键依赖」「可观测量是否实时可得」「执行窗口」三项，或用另一家同期但结局不同的银行做对照组（本文件未收录，需另行研究）。

### 7. 已核实 URL
- 【标题/日期】https://www.sec.gov/Archives/edgar/data/719739/000071973923000021/sivb-20221231.htm（存款与权益数字来自正文；EDGAR 目录 https://www.sec.gov/Archives/edgar/data/719739/000071973923000021/ 显示 2023-02-24）
- 【内容】https://www.sec.gov/Archives/edgar/data/719739/000119312523064680/d430920dex993.htm
- 【内容】https://www.sec.gov/Archives/edgar/data/719739/000119312523064680/（目录，时间戳 2023-03-08 17:16:05）
- 【未逐页打开】https://www.sec.gov/Archives/edgar/data/719739/000119312523064680/d430920dex992.htm（存在于上述目录）
- 【内容】https://www.fdic.gov/news/press-releases/2023/pr23013.html
- 【内容】https://www.fdic.gov/news/speeches/2023/spfeb2823.html
- 【标题】https://www.kitco.com/news/off-the-wire/2023-03-08/crypto-focused-bank-silvergate-plans-wind-down-operations
- 【标题/日期】https://www.cnbc.com/2023/03/09/svb-financial-falls-more-than-50percent-as-tech-bank-looks-to-raise-more-cash.html
- 【标题/日期】https://www.cnbc.com/2023/03/10/silicon-valley-bank-financial-in-talks-to-sell-itself-after-attempts-to-raise-capital-have-failed-sources-say.html
- 【标题/日期】https://www.cnbc.com/2023/03/11/silicon-valley-banks-demise-began-with-downgrade-threat.html
- 【内容】https://wolfstreet.com/2023/03/11/svb-financial-had-investment-grade-credit-ratings-from-moodys-and-sp-up-to-collapse-then-ratings-got-slashed-in-one-fell-swoop-to-default/
- 【标题】https://www.fdic.gov/news/press-releases/2023/pr23016.html
- 【内容】https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf
- 【内容】https://www.federalreserve.gov/newsevents/pressreleases/bcreg20230428a.htm
- 【标题/日期】https://www.cnbc.com/2023/03/28/svb-customers-tried-to-pull-nearly-all-deposits-in-two-days-barr-says.html
- 【内容】https://blogs.cfainstitute.org/blog/2023/03/13/the-svb-collapse-fasb-should-eliminate-hide-til-maturity-accounting/（HTM $91.3B / $76.2B 的出处，二手）
- 【标题/日期】https://rationalwalk.com/the-fall-of-silicon-valley-bank/
- 【未能打开】FT 2/22 原文（403）；CDFPI 关闭公告（403）

---

## 案例 5：2023-12 胡塞袭击红海 → 集装箱运价上涨？

### 1. 名称 / 时点 / 信念
- **名称**：Red Sea / Houthi attacks and container freight, Dec 2023
- **as_of**：2023-12-18（周一；BP 暂停红海航行、美国宣布 Operation Prosperity Guardian 当天）
- **信念**：主要班轮公司暂停经红海 / 苏伊士航行、绕行好望角 → 有效运力下降、航程拉长 → 亚欧集装箱现货运价大幅上涨（工具：运价指数或期货、班轮公司股票）。

### 2. 当时公开的推理（Reuters 12/18 汇总）
- **ABN Amro（Albert Jan Swart）**：正在绕行的班轮公司约占全球集装箱运力一半；绕行拉长航程，成本上升。
- **ING（Rico Luman）**：绕行至少多一周航程；12 月下旬出现延误，影响延续到 1 月、可能 2 月。
- **Freightos CEO（Zvi Schreiber）**：长航线运价可能上涨，但承运人有过剩运力可调配，运价不太可能涨到疫情时期水平。这是对幅度的反方意见。
- **背景数据**：Drewry WCI 综合指数 11/30 为 $1,382/FEU，12/14 为 $1,521（周涨 4%，同比仍低 28%）。行业处于运力过剩周期。
- **核心因果链**：袭击风险 → 承运人暂停经曼德海峡 → 绕行好望角（多 1 到 2 周）→ 有效运力被航程吸收 → 现货运价上涨。反向力量是行业新船交付带来的过剩运力。
- **结论**：方向偏涨，幅度有争议（Freightos 偏保守）。

### 3. 时点资料包（≤ 2023-12-18）
| 日期 | 来源 | URL | 一句话内容 | 立场 |
|---|---|---|---|---|
| 2023-12-02（数据 11/30） | Hellenic Shipping News（Drewry WCI） | https://www.hellenicshippingnews.com/?p=1017031 | WCI 持平于 $1,382，同比降 40% | neutral（基线低） |
| 2023-12-15 | Al Jazeera | https://www.aljazeera.com/news/2023/12/15/yemen-rebels-hit-cargo-ship-in-latest-red-sea-attack | 多家航运公司在袭击后暂停红海航程 | supports |
| 2023-12-15 | CNBC | https://www.cnbc.com/2023/12/15/maersk-to-pause-all-container-ship-traffic-through-the-red-sea.html | Maersk 暂停所有经红海的集装箱航行，直至另行通知 | supports |
| ⚠️ 数据 2023-12-14，网页 12-19 | Cyprus Shipping News（Drewry WCI） | https://cyprusshippingnews.com/2023/12/19/world-container-index-up-by-4-according-to-drewry/ | WCI 升 4% 至 $1,521；上海-鹿特丹 +7% | supports（弱） |
| 2023-12-18 | Arab News PK（Reuters 稿） | https://www.arabnews.pk/node/2427861/business-economy | ABN Amro / ING / Freightos 观点；MSC、Maersk、CMA CGM、Hapag-Lloyd、Evergreen 的绕行或暂停 | supports（方向），Freightos 观点 contradicts（幅度） |
| 2023-12-18 | Deccan Herald（Reuters 稿） | https://www.deccanherald.com/world/red-sea-attacks-force-rerouting-of-vessels-disrupting-supply-chains-2815827 | 红海袭击迫使船只改道、扰乱供应链 | supports |
| 2023-12-18 | Stars and Stripes | https://www.stripes.com/theaters/middle_east/2023-12-18/bp-suspends-red-sea-shipping-12405082.html | BP 暂停红海航运 | supports |

### 4. 事后真相
- **运价（Drewry WCI 综合）**：12/21 $1,661（+9%）→ 2024-01-11 $3,072（周 +15%，同比 +44%）→ 01-18 $3,777（周 +23%，同比 +82%）。约一个月涨了一倍半。https://airfreight.news/articles/full/drewry-world-container-index-21-dec ；https://www.hellenicshippingnews.com/?p=1023073 ；https://www.hellenicshippingnews.com/drewry-world-container-index-up-23-last-week/
- **假信号（宣布 ≠ 现实）**：12/24 Maersk 以多国护航行动为由宣布准备恢复红海航行，同时提示风险并未消除（Malay Mail / Caixin 12/25-26 转载）。12/30 至 31 Maersk Hangzhou 遭袭，Maersk 12/31 先暂停 48 小时，随后延长为直至另行通知（Fox Business 12/31、gCaptain、Enterprise 1/2）。
- **实际通航（IMF PortWatch，IMF 博客 2024-03-07）**：2024 年前两个月苏伊士运河贸易量同比下降约 50%，好望角通行量同比增加约 74%。

### 5. 判定要点
- **真正的关键依赖**：曼德海峡 / 苏伊士运河的**实际集装箱船通行量**（PortWatch 日度通行估计、船舶追踪），以及承运人**整条航线**的绕行安排，而不是「恢复通航」「护航联盟成立」这类公告。
- **好的进场条件**：(a) 前五大班轮公司中至少三家公告整条亚欧航线绕行；(b) 苏伊士集装箱船周通行量较 11 月均值下降超过约 30%（PortWatch）；(c) WCI 或 FBX 亚欧现货连续两周上涨。12/18 时 (a) 已满足；(c) 要到 12/21 WCI +9% 才有第二周上涨。
- **失效条件**：PortWatch 显示苏伊士集装箱船通行量连续两周回升到 11 月均值的约 70% 以上；**仅有承运人「准备恢复」的公告不算**。
- **系统应有的动作**：
  - 12/18：**先别动 / 有条件**。方向证据充分，但运价确认只有一周（+4%），且存在运力过剩的反方观点。
  - 12/21 前后：WCI 第二周上涨 → **进场条件成立**。
  - 12/24：Maersk 宣布恢复 → **不退出**，等实际通行数据。12/31 再次暂停证实了这一点。
  - 退出条件：等 PortWatch 通行量回升，本案例观察期内（至 2024-03）未出现。
- **评测看点**：模型能否把「护航联盟 / 恢复航行」公告当作需要验证的假设而非退出信号；能否提出 PortWatch 这类直接测量物理流量的可观测量。

### 6. 污染风险：中高
红海危机广为人知，模型知道运价大涨。但 12/24 恢复公告与 12/31 再暂停的细节、WCI 的周度节奏，模型未必精确记得。适合重点评「对假信号的处理」。

### 7. 已核实 URL
- 【内容】https://www.hellenicshippingnews.com/?p=1017031
- 【标题/日期】https://www.aljazeera.com/news/2023/12/15/yemen-rebels-hit-cargo-ship-in-latest-red-sea-attack
- 【标题/日期】https://www.cnbc.com/2023/12/15/maersk-to-pause-all-container-ship-traffic-through-the-red-sea.html
- 【标题/日期】https://cyprusshippingnews.com/2023/12/19/world-container-index-up-by-4-according-to-drewry/
- 【内容】https://www.arabnews.pk/node/2427861/business-economy
- 【标题/日期】https://www.deccanherald.com/world/red-sea-attacks-force-rerouting-of-vessels-disrupting-supply-chains-2815827
- 【标题】https://www.stripes.com/theaters/middle_east/2023-12-18/bp-suspends-red-sea-shipping-12405082.html
- 【内容】https://airfreight.news/articles/full/drewry-world-container-index-21-dec
- 【内容】https://www.hellenicshippingnews.com/?p=1023073
- 【内容】https://www.hellenicshippingnews.com/drewry-world-container-index-up-23-last-week/
- 【标题/日期】https://www.ajot.com/news/drewry-world-container-index-11-jan
- 【标题】https://www.malaymail.com/news/money/2023/12/25/shipping-giant-maersk-prepares-to-resume-operations-in-red-sea/109132
- 【标题】https://www.caixinglobal.com/2023-12-26/maersk-prepares-to-return-to-red-sea-under-us-led-protection-102149759.html
- 【标题/日期】https://www.foxbusiness.com/markets/maersk-pauses-red-sea-voyages-day-after-houthis-attack-ship
- 【标题】https://gcaptain.com/maersk-pausing-red-sea-transits-until-further-notice/
- 【标题】https://enterpriseam.com/logistics/2024/01/02/maersk-reconsiders-decision-to-ramp-up-red-sea-transit-as-houthi-attacks-continue/
- 【内容】https://www.imf.org/en/blogs/articles/2024/03/07/red-sea-attacks-disrupt-global-trade/index.md
- 【标题】https://www.thedailystar.net/business/news/red-sea-attacks-disrupt-global-trade-3562626
- 【未能打开】UNCTAD 2024-02 新闻稿（403；搜索摘要称苏伊士通行量较峰值降 42%，未核实）；Axios 12/19（403）；imf.org 博客 HTML 版（403，但 index.md 版本已打开）

---

## 案例 6：2022-10 美国对华先进计算芯片出口管制 → NVIDIA 中国数据中心收入下滑？

### 1. 名称 / 时点 / 信念
- **名称**：BIS Oct 7, 2022 advanced computing rule & NVIDIA A800
- **as_of**：2022-10-13（规则文本在 Federal Register 正式刊登当日；先进计算条款 10/21 生效）
- **信念**：美国对中国出口高端 AI 芯片实施许可证管制 → NVIDIA 对华数据中心 GPU 销售大幅受限 → 看空 NVIDIA 中国数据中心收入（以及 NVDA）。

### 2. 当时公开的推理
- **NVIDIA 自己（8-K，2022-08-31 签署，事件日 8/26）**：美国政府对 A100、H100 及含这些芯片的系统、以及性能大致相当于 A100 的未来芯片，对华（含香港）和俄罗斯出口新增许可证要求；三季度展望中约 **$4 亿**对华潜在销售可能受影响；可能需要把部分业务移出中国。
- **9/1 更新（CnEVPost 9/2 转述）**：美国政府允许 H100 在华继续研发，香港设施可用于履约至 2023-09-01。部分缓和。
- **BIS（10/7 新闻稿）**：把部分先进计算芯片加入管制清单，对用于中国超算和半导体生产的物项要求许可证；先进计算与超算条款 10/21 生效。
- **规则文本（Federal Register 10/13，ECCN 3A090）**：受控芯片要**同时**满足两个条件：(1) 总双向传输速率 ≥ 600 GB/s，**且** (2) 位长 × TOPS ≥ 4800。这个「且」是关键：把互连带宽压到 600 GB/s 以下的产品就不受该条款约束。
- **核心因果链（看空版）**：许可证要求 → 无法向中国客户交付 A100/H100 → 中国数据中心收入流失（事后 FY2024 10-K 披露：FY2023 中国约占数据中心收入的 19%；as_of 时点没有这个精确比例）。
- **当时的结论**：看空，NVIDIA 自己给出了量化敞口；但规则的技术定义留下了产品重设计的空间。

### 3. 时点资料包（≤ 2022-10-13）
| 日期 | 来源 | URL | 一句话内容 | 立场 |
|---|---|---|---|---|
| 2022-08-31 | NVIDIA 8-K, SEC | https://www.sec.gov/Archives/edgar/data/1045810/000104581022000146/nvda-20220826.htm | A100/H100 对华出口需许可证；Q3 约 $4 亿对华销售可能受影响 | supports |
| 2022-09-02 | Tom's Hardware | https://www.tomshardware.com/news/us-export-rules-may-cost-nvidia-400-million-prevent-h100-development | 新规可能让 NVIDIA 损失 $4 亿并影响 H100 开发 | supports |
| 2022-09-02 | CnEVPost | https://cnevpost.com/2022/09/02/nvidia-says-it-got-us-permit-to-export-key-chips-in-updated-filing/ | NVIDIA 获准在华继续 H100 研发、香港履约至 2023-09 | contradicts（缓和） |
| 2022-10-07 | BIS 新闻稿 | https://www.bis.gov/press-release/commerce-implements-new-export-controls-advanced-computing-semiconductor-manufacturing-items-peoples | 新管制范围与分阶段生效日（10/7、10/12、10/21） | supports |
| 2022-10-13 | Federal Register 规则全文（govinfo PDF） | https://www.govinfo.gov/content/pkg/FR-2022-10-13/pdf/2022-21658.pdf | 3A090 门槛：600 GB/s 双向传输**且** 4800 TOPS×bit | neutral（关键细节：存在合规改型空间） |
| 2022-10-13 | Federal Register 网页版 | https://www.federalregister.gov/documents/2022/10/13/2022-21658/implementation-of-additional-export-controls-certain-advanced-computing-and-semiconductor-manufacturing | 同上（网页对自动抓取有拦截，PDF 版已核实） | neutral |

### 4. 事后真相
- **2022-11-07/08**：NVIDIA 向 Reuters 确认 A800 已于三季度投产，作为面向中国客户的 A100 替代品，称其满足美国政府降低管制的测试且无法被编程突破。来源：Data Center Knowledge 11/8 https://www.datacenterknowledge.com/supercomputers/nvidia-skirts-us-expert-controls-china-alternative-chip ；CnEVPost 11/8；Caixin 11/8。
- **2022-11-16（Q3 FY23 财报）**：数据中心收入 $3.83B，同比 +31%，环比 +1%（NVIDIA 新闻稿）。Jon Peddie 11/18 转述管理层：出口限制影响了三季度收入，但下降「大部分被」对华替代产品销售抵消。新闻稿本身未提中国。
- **FY2024 10-K（截至 2024-01-28）**：对华销售占数据中心收入的比例从 FY2023 的 19% 降至 FY2024 的 14%；FY2024 Q4 降到个位数中段。
- **2023-10-17 BIS 修订**：规则**去掉了「互连带宽」参数**，新增「性能密度」门槛，明确是为了预防未来的绕道。https://www.bis.gov/press-release/commerce-strengthens-restrictions-advanced-computing-semiconductors-semiconductor-manufacturing-equipment
- **2023-10-23/24（NVIDIA 8-K）**：美国政府通知 A100、A800、H100、H800、L40S 的许可证要求立即生效（原定 30 天后）；NVIDIA 称预计近期不会对财务产生实质影响（全球需求强劲）。https://www.sec.gov/Archives/edgar/data/1045810/000104581023000221/nvda-20231023.htm

### 5. 判定要点
- **真正的关键依赖**：规则的**技术门槛定义**，以及 NVIDIA 能否推出不触发门槛、客户仍愿意买的改型产品。as_of 当时就可以从规则原文读出「600 GB/s **且** 4800」的结构，这是全案最值钱的细节。
- **好的进场条件（看空中国收入）**：NVIDIA 在下一份 10-Q / 财报电话会中确认中国数据中心收入显著下降，且**没有**合规替代品出货。
- **失效条件**：NVIDIA 或主流媒体确认合规改型产品（A800）已量产或出货；或财报称下降「大部分被抵消」。11/8 和 11/16 都触发了。
- **再武装条件**：BIS 修订规则、去掉被绕开的参数（2023-10-17），并且改型产品被点名纳入（2023-10-23 8-K）。之后看空中国收入的 thesis 成立（FY24 Q4 降到个位数中段）。
- **系统应有的动作**：
  - 10/13：**先别动**。读完规则发现「且」结构 → 关键依赖是合规改型；同时 NVDA 股价主要受 AI / 数据中心整体需求驱动，「对华管制 → NVDA 股价」这条链偏弱。若工具是 NVDA 股票，倾向**弃权**；若工具是「NVIDIA 中国收入占比」这类可验证指标，等下个财报。
  - 11/8 至 11/16：失效条件触发 → **不进场**。
  - 2023-10-17 至 10-24：再武装条件触发 → 「中国收入下滑」thesis 进场条件成立（用中国收入占比验证，不是股价）。
- **评测看点**：模型是否会读规则原文找门槛结构，而不是只看新闻标题；能否区分「公司层面收入」和「股价」两种工具，并在后者上弃权（链条弱）。

### 6. 污染风险：中高
A800/H800 的绕道和 2023 年的修补都很有名，模型大概率知道。但「600 GB/s 且 4800」的门槛细节和具体时间线不一定记得准确。建议重点评：是否从规则文本推出「存在改型空间」这一步。

### 7. 已核实 URL
- 【内容】https://www.sec.gov/Archives/edgar/data/1045810/000104581022000146/nvda-20220826.htm
- 【标题/日期】https://www.tomshardware.com/news/us-export-rules-may-cost-nvidia-400-million-prevent-h100-development
- 【标题/日期】https://cnevpost.com/2022/09/02/nvidia-says-it-got-us-permit-to-export-key-chips-in-updated-filing/
- 【内容】https://www.bis.gov/press-release/commerce-implements-new-export-controls-advanced-computing-semiconductor-manufacturing-items-peoples
- 【内容】https://www.govinfo.gov/content/pkg/FR-2022-10-13/pdf/2022-21658.pdf
- 【已请求，返回 200 但正文被拦截页替代】https://www.federalregister.gov/documents/2022/10/13/2022-21658/implementation-of-additional-export-controls-certain-advanced-computing-and-semiconductor-manufacturing
- 【内容】https://www.datacenterknowledge.com/supercomputers/nvidia-skirts-us-expert-controls-china-alternative-chip
- 【标题/日期】https://cnevpost.com/2022/11/08/nvidia-offers-a800-chip-for-china/
- 【标题】https://www.caixinglobal.com/2022-11-08/nvidia-to-sell-new-chip-in-china-it-says-meets-us-export-ban-101962115.html
- 【内容】https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2023
- 【内容】https://www.jonpeddie.com/news/nvidia-q3-fy23-results/
- 【标题/日期】https://www.cnbc.com/2022/11/16/nvidias-quarter-fails-to-excite-but-offers-enough-hope-that-octobers-bottom-can-hold.html
- 【内容】https://www.sec.gov/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm
- 【内容】https://www.bis.gov/press-release/commerce-strengthens-restrictions-advanced-computing-semiconductors-semiconductor-manufacturing-equipment
- 【内容】https://www.sec.gov/Archives/edgar/data/1045810/000104581023000221/nvda-20231023.htm
- 【未逐页打开】Mayer Brown 2022-11 通讯（200，未读正文）

---

## 案例 7：2022-03 LME 镍：俄罗斯供应担忧 → 复市后做多镍？

### 1. 名称 / 时点 / 信念
- **名称**：LME nickel short squeeze and trade cancellation, March 2022
- **as_of**：2022-03-15（LME 宣布 3/16 复市、公布涨跌停幅度当天）
- **信念**：俄罗斯是主要镍生产国，Nornickel 是高等级镍的主要供应商；入侵乌克兰后的制裁会切断俄镍供应 → LME 复市后做多镍。

### 2. 当时公开的推理
- **LME（Notice 22/057，3/10）**：3/7 的大幅上涨仍属有序；3/8 凌晨的价格「并未反映基础实物市场」，市场失序，因此 08:15 暂停交易，并取消 3/8 零点以后的所有成交，退回到 3/7 收盘；同时担心保证金追缴引发连锁违约。
- **Tsingshan 与银行的 standstill（Bloomberg 稿，Daily Maverick 3/15；Caixin 3/15）**：银行同意暂不平仓、不追加保证金；Tsingshan 仍持有超过 15 万吨空头，承诺在市场恢复正常后有序减仓。这说明价格的主要驱动力是**持仓挤兑**。
- **LME（Notice 22/064，3/14；22/067，3/15）**：3/16 08:00 复市；所有基本金属设涨跌停，镍为 ±5%；交割递延；设立持仓问责水平。
- **Nornickel / Potanin（AFP 3/12，O Povo 转载）**：有物流困难（部分欧洲港口拒收、空运受限），计划把欧美订单转向中国等国但「尚未这样做」；WSJ 认为 Nornickel 可能「大到不能制裁」。
- **AFP（3/7 晚 / 3/8，ABS-CBN 转载）**：标题称镍创纪录高位，俄罗斯为主要生产国。
- **核心因果链（信念版）**：入侵 → 制裁 → 俄镍出口受阻 → 实物短缺 → 价格上涨。**缺失的证据**：Nornickel 没有被制裁；出口在继续（虽有物流摩擦）；3/7 至 3/8 的价格跳涨被交易所自己定性为不反映实物市场。
- **结论**：作为评测「正确答案」，应当**弃权**。因果链中「制裁 → 实物断供」没有证据；价格信号被持仓挤兑污染；交易工具本身（LME 镍）有取消成交、涨跌停、系统停摆等规则风险。

### 3. 时点资料包（≤ 2022-03-15）
| 日期 | 来源 | URL | 一句话内容 | 立场 |
|---|---|---|---|---|
| 2022-03-08 00:43 UTC | ABS-CBN（AFP 稿） | https://abs-cbn.com/business/03/08/22/nickel-soars-to-record-high-of-54880-per-ton | 镍创纪录高位 $54,880/吨 | supports（价格叙事） |
| 2022-03-10 | LME Notice 22/057（ISDA 托管） | https://www.isda.org/a/KR0gE/TRADING-22-057-NICKEL-MARKET-UPDATE.pdf | 暂停并取消 3/8 成交，原因是价格不反映实物市场、存在系统性保证金风险 | contradicts |
| 2022-03-12 | O Povo（AFP 稿，葡萄牙语） | https://www.opovo.com.br/noticias/mundo/2022/03/12/gigante-da-mineracao-russa-nornickel-enfrenta-primeiras-dificuldades-devido-a-sancoes-contra-a-russia.html | Nornickel 有物流困难但未断供，尚未转向；可能「大到不能制裁」 | contradicts（断供证据不足）/ neutral |
| 2022-03-14 | LME Notice 22/064 | https://www.lme.com/-/media/Files/News/Notices/2022/03/TRADING-22-064-NICKEL-MARKET-UPDATE-RESUMPTION-OF-TRADING.pdf | 3/16 复市；全部基本金属设涨跌停；交割递延；持仓问责 | neutral（工具规则风险） |
| 2022-03-15 | LME Notice 22/067（ISDA 托管） | https://isda.org/a/LA0gE/TRADING-22-067-NICKEL-MARKET-UPDATE-DAILY-PRICE-LIMITS.pdf | 镍日涨跌停 ±5% | neutral（工具规则风险） |
| 2022-03-15 | Daily Maverick（Bloomberg 稿） | https://www.dailymaverick.co.za/article/2022-03-15-lme-to-reopen-nickel-market-march-16-after-xiang-short-squeeze/ | Tsingshan 与银行达成 standstill，仍有超过 15 万吨空头；LME 要求披露超过 600 吨的持仓 | contradicts（价格由持仓驱动） |
| 2022-03-15 | Caixin Global | https://www.caixinglobal.com/2022-03-15/chinese-nickel-giant-secures-deal-to-avoid-further-margin-calls-101855706.html | 中国镍业巨头达成协议，避免进一步追加保证金 | contradicts |

### 4. 事后真相
- **3/16 复市**：3 个月镍一开盘就跌到 5% 跌停；LMEselect 因技术问题停到 14:00；收盘价触发「disruption event」（Notice 22/072）。3/17 起涨跌停放宽到 8%（Notice 22/073）。
- **月度均价（IMF，FRED PNICKUSDM，$/吨）**：2022-02 24,016 → 03 33,924 → 04 33,134 → 05 28,229 → 06 25,877 → 07 21,482。https://fred.stlouisfed.org/data/PNICKUSDM.txt
- **实物供应**：Fortune（2022-07-07）称当时制裁尚未造成实际的镍供应中断；Tsingshan 5 月把空头从超过 15 万吨降到 6 万吨，6 月底基本平完。https://fortune.com/2022/07/07/big-shot-billionaire-xiang-guangda-who-broke-nickel-market-clawed-short-squeeze-back-from-10-billion-loss/
- **两年后**：2024-04 美英才禁止交易所接受新生产的俄罗斯铝、铜、镍；Nornickel 称会继续履行合同（Mining.com / Reuters 2024-04-16）。我**未找到**能直接证明 Nornickel 本身在 2022 年未被列入美 / 欧 / 英制裁名单的一手名单来源，这一点标为未核实。
- **法律后果**：英国高等法院 2023-11-29 驳回 Elliott、Jane Street 对 LME 取消交易的挑战（Stephenson Harwood 2023-12-05 简报）。https://www.stephensonharwood.com/insights/london-metal-exchange-wins-high-court-ruling-over-cancelled-nickel-trades/

### 5. 判定要点
- **真正的关键依赖**：(1) 俄罗斯镍的**实际出口流**（海关 / 出口数据、Nornickel 销售与发运、对 Nornickel 本身的制裁指定）；(2) 价格是否由实物驱动，而不是由持仓结构驱动（大额空头的 standstill / 平仓进度）；(3) 交易所规则（取消成交、涨跌停、停摆）。
- **若要进场做多（假设性）**：对 Nornickel 或俄镍出口的正式制裁指定，或可核实的出口量大幅下降（例如季度销量同比下降超过约 20%），并且 LME 涨跌停恢复到常规水平、连续多日正常交易。
- **失效条件（as_of 当时已具备）**：交易所公开定性价格不反映实物市场；最大空头与银行达成 standstill；公司本身未被制裁、出口在继续。
- **系统应有的动作**：
  - 3/15：**弃权**。理由有三：链条中的实物环节没有证据、价格信号被污染、工具规则风险不可量化。
  - 后续：直到观察期结束都没有出现进场条件。2024-04 的美英措施只针对交易所交割与进口，不等于实物断供。
- **评测看点**：模型能否把「价格暴涨」与「实物短缺」分开；能否识别交易所规则本身就是因果链上的一环（取消成交会让「方向正确」的仓位也无法兑现）；能否在宏大的地缘叙事面前给出弃权。

### 6. 污染风险：中高
LME 镍逼空、取消交易、Tsingshan 在金融媒体里很出名，模型很可能知道。但「复市当日跌停 + 系统故障」和 3 到 7 月的月度回落路径，不一定记得清。可以匿名化成「某交易所某金属」，以降低污染。

### 7. 已核实 URL
- 【标题/日期】https://abs-cbn.com/business/03/08/22/nickel-soars-to-record-high-of-54880-per-ton
- 【内容】https://www.isda.org/a/KR0gE/TRADING-22-057-NICKEL-MARKET-UPDATE.pdf
- 【内容】https://www.opovo.com.br/noticias/mundo/2022/03/12/gigante-da-mineracao-russa-nornickel-enfrenta-primeiras-dificuldades-devido-a-sancoes-contra-a-russia.html
- 【内容】https://www.lme.com/-/media/Files/News/Notices/2022/03/TRADING-22-064-NICKEL-MARKET-UPDATE-RESUMPTION-OF-TRADING.pdf
- 【内容】https://isda.org/a/LA0gE/TRADING-22-067-NICKEL-MARKET-UPDATE-DAILY-PRICE-LIMITS.pdf
- 【内容】https://www.dailymaverick.co.za/article/2022-03-15-lme-to-reopen-nickel-market-march-16-after-xiang-short-squeeze/
- 【标题】https://www.caixinglobal.com/2022-03-15/chinese-nickel-giant-secures-deal-to-avoid-further-margin-calls-101855706.html
- 【内容】https://www.isda.org/a/YiPgE/TRADING-22-072-NICKEL-CLOSING-PRICES.pdf
- 【内容】https://www.isda.org/a/fiPgE/TRADING-22-073-CHANGES-TO-DAILY-PRICE-LIMITS-FOR-NICKEL.pdf
- 【内容】https://fred.stlouisfed.org/data/PNICKUSDM.txt
- 【内容】https://fortune.com/2022/07/07/big-shot-billionaire-xiang-guangda-who-broke-nickel-market-clawed-short-squeeze-back-from-10-billion-loss/
- 【标题】https://www.mining.com/web/nickel-tycoon-has-cut-big-short-position-by-more-than-half/
- 【内容】https://www.mining.com/web/nornickel-says-new-western-sanctions-raise-risk-of-metals-market-disruption/（2024-04-16）
- 【标题/日期】https://www.stephensonharwood.com/insights/london-metal-exchange-wins-high-court-ruling-over-cancelled-nickel-trades/
- 【标题/日期】https://www.wesa.fm/2022-03-18/a-wild-ride-for-global-nickel-market（as_of 后，未使用其内容）
- 【未能打开】Mining Weekly / Creamer Media 3/7 报道（含 JPMorgan 关于俄罗斯约占全球镍 10%、Nornickel 占电池级镍 15–20% 的说法，只见于搜索摘要，未核实）；S&P Global 3/15 报道（403）；WisdomTree 3/25 博文（403）；BNN Bloomberg 页面（只返回首页）

---

## 未能核实 / 需注意的事项（汇总）

1. **被拦截的一手来源**：IEA（OMR、声明）、OPEC 新闻稿、CME 清算通知、UNCTAD、S&P Global、ETF.com、FT、CDFPI 均返回 403 / 402 / 付费墙。相关事实只用了能打开的二手转述（CNBC、NPR、QCI、Reuters 转载稿等），或明确标为「未核实」。
2. **SVB 10-K 的 HTM 数字**（摊余成本 $91.3B / 公允价值 $76.2B）来自 CFA Institute 博文，我没能直接打开 10-K 附注（WebFetch 截断，SEC 拒绝 curl）。未受保险存款比例用的是美联储事后报告的 94%（FR Y-9C 口径）；10-K 自己披露的数字未核实。
3. **SVB 3/14 后续 8-K** 中 AFS 账面 $23.97B、净收入 $21.45B、买方 Goldman 的说法来自搜索摘要，原文未打开。
4. **Moody's 3/8 对 SVB 的降级**：没有找到 as_of 前发布、能打开的来源，只有 3/11 的事后报道（Wolf Street、CNBC）。
5. **OPEC+ 8 月缺口的多种口径**（3.4 / 3.58 / 3.61 mb/d）：只有 QCI 的 3.58 页面打开过，正文是 JS 渲染，只核实了标题和日期，具体拆分（1.399 / 2.185）来自搜索摘要。
6. **Nornickel 在 2022 年是否被制裁**：我没有找到可打开的一手制裁名单来源来证实「未被制裁」，只有间接证据（Fortune 2022-07：制裁未造成实际供应中断；AFP 2022-03 引 WSJ「大到不能制裁」）。
7. **EIA 周度数据的发布日**（Cushing 4/10 数据于 4/15 发布、5/8 数据于 5/13 发布等）是按 EIA 周三发布惯例推算的，没有逐一核实。EIA 2019-09 STEO 的精确发布日也未核实。
8. **Drewry 12/14 的 WCI 数据**：我能打开的转载页发布于 12/19（as_of 之后），已在资料包中标 ⚠️。
9. **多处只核实了标题 / 日期**（JS 渲染页面），详见各案例第 7 节的标注。评测前如需正文，建议人工补看或换成可打开的转载。
10. **价格比较**：全部用 EIA / IMF 现货或月均序列，**不是**期货结算价（负油价的 -$37.63 来自 CFTC，属例外）。用期货做评分时需要另取数据。

## 备选（未收录，可扩充）
- 2021-03 Ever Given 搁浅（3/23 至 3/29 起浮）：「弃权 / 短暂冲击」型；需另找 as_of 前的资料包。
- 2022 俄乌战争 → 欧洲 TTF 天然气 / Nord Stream 实际流量：「宣布 ≠ 实物流量」型，关键依赖是 ENTSOG 管道流量数据。
- SVB 同期对照组：存款结构不同、没有倒闭的区域银行，用来测试系统会不会过度外推。
