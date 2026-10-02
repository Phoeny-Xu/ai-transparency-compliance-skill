# 效力核验清单（阶段3条件触发时执行）



> 触发条件见SKILL.md阶段3（last_verified超90天 / 用户要求复核 / 超出规则库范围 / 命中监控点）。本清单提供各法域核验检索点与报告输出格式。

> 规则库即已核实的官方原文；本清单用于**捕捉规则库打包之后的法规变动**。

> **全称与简称系同一份文件（★）**：同一部法规的正式全称与通行简称是同一份文件（如《互联网信息服务深度合成管理规定》与「深度合成规定」、《生成式人工智能服务管理暂行办法》与「暂行办法」），效力核验**只做一次、效力表只占一行**，不得因正文出现两种写法而重复核验或重复列行。



## 中国大陆



| 法规 | 核验点 | 检索路径 |

|------|--------|----------|

| 深度合成管理规定 | 是否有修订、实施细则、执法案例 | 中国政府网、网信办官网（cac.gov.cn） |

| 生成式AI暂行办法 | 是否有正式办法取代「暂行」、分类分级监管规则出台情况 | 中国政府网、网信办官网 |

| 标识办法 | 配套指引、执法动态、备案材料要求更新 | 网信办官网、算法备案系统公告 |

| GB 45438-2025 | 是否有修改单、替代标准 | 全国标准信息公共服务平台（std.samr.gov.cn） |



## 欧盟



| 法规/文件 | 核验点 | 检索路径 |

|-----------|--------|----------|

| Regulation (EU) 2024/1689 | 新勘误、新修正条例（Digital Omnibus已落地为Reg. (EU) 2026/1744，留意后续修正包） | EUR-Lex（eur-lex.europa.eu，ELI: reg/2024/1689/oj） |

| Art. 50委员会指南 | **监控点**：现为内容批准版C(2026) 5054（2026-07-20），正式通过版（全语种齐备后）是否发布 | 委员会数字战略网站（digital-strategy.ec.europa.eu） |

| 透明度行为准则 | **监控点**：签署名单更新；准则修订（至少每两年评估）；Measure 3.4水印互操作方案进展（2027-02-02节点）；委员会/Board是否改判不充分并启动共同规则；准则修订/补充时重建 cop-digest.md 并升版本；sources txt 变更（MD5 与 digest 头部登记不符）即行号锚点全部失效，重建 digest 并重核锚点；**来源失效降级**：官方 factpage（digital-strategy.ec.europa.eu）遭反爬拦截无法取一手数字时，签署名单数（如 S1 83／S2 152）仅可转引二手监测页快照，并须在报告效力表显式标注「转引自二手监测页、未经一手逐条核对」，不得静默顶替或写死为权威；待反爬解除后下次核验重试一手 | 委员会数字战略网站 |

| Art. 111(4)过渡期 | 2026-12-02届满后的执法口径 | EUR-Lex、委员会官网 |

| 成员国处罚规则 | Art. 99(2)项下成员国配套立法 | 各成员国官方公报（按需） |



## 加州



| 法规 | 核验点 | 检索路径 |

|------|--------|----------|

| B&P Code §§22757–22757.6 | **监控点**：2026/2027会期是否有新修正案（该法域每年会期均可能再修） | leginfo（leginfo.legislature.ca.gov）查最新chaptered text |

| **AB 2713（CAITA §22757.3.1 修正案）** | **已终局**：2026-09-30 州长签署，**Chapter 856, Statutes of 2026**，2027-01-01 operative；检测范围扩大到任何关联来源数据、新增不合规数据安全港、不得剥离加技术可行限定 | leginfo 历史页 https://leginfo.legislature.ca.gov/faces/billHistoryClient.xhtml?bill_id=202520260AB2713 |
| **SB 1000（CAITA 修正案）** | **已核验：2026-09-30 州长签署，Chapter 861, Statutes of 2026，紧急法案即时生效**；后续监控点：2027/2028 会期是否有再修正案与执法口径 | leginfo 法案历史页 https://leginfo.legislature.ca.gov/faces/billHistoryClient.xhtml?bill_id=202520260SB1000 |

| BOT Act（B&P Code §§17940–17943） | 是否修订；§17941的意图、目的和披露抗辩是否仍为现行文本 | leginfo SB 1001 chaptered；`sources/CA-SB1001-BOT-Act-chaptered.md` |

| SB 243／SB 867（陪伴型聊天机器人） | §22601定义/排除及§22602、§22604是否被后续法案修订；SB 867 §22601版本的生效日 | leginfo chaptered；`sources/CA-SB243-chaptered.md`、`CA-SB867-chaptered.md` |

| SB 1119（Adam's Law） | **条款级核验**：§22602修订和§21811自2027-01-01生效；§§21812、21812.5、21813自2027-07-01施行；§21814按AB 1405是否章化选择版本 | leginfo chaptered；`sources/CA-SB1119-chaptered.md` |

| SB 1050（合成表演者广告） | 已章化；2027-01-01普通生效；§17610角色、例外与执法条款是否修订 | leginfo chaptered；`sources/CA-SB1050-chaptered.md` |

| SB 896／AB 3030 | 州政府服务/福利通信及患者临床信息通信披露条款是否修订；人审例外是否变化 | leginfo chaptered；`sources/CA-SB896-chaptered.md`、`CA-AB3030-chaptered.md` |

| **AB 1609（客服机器人）** | **已章化（Chapter 733, 2026-09-28 签署），生效日已核定为 2027-01-01**（章化文本无 operative／urgency 条款，依加州宪法第四条第 8 款(c)(1) 默认规则推算；法案自身以 2027-01-01 为存量基线）；后续监控实施细目与执法口径 | leginfo历史页及`references/sources/CA-AB1609-enrolled.md`（chaptered 版待入库） |

| 联邦层面动态 | 联邦AI披露立法是否推进、是否涉及preemption | congress.gov（按需） |

| 标准认定 | 「广泛采纳规范」（C2PA等）的最新认定 | 无需每次核验；涉具体技术方案时查 |



## 前瞻节点提醒（报告生成日距节点≤60天时，在报告中加「临近节点提示」）

> 本节为**人读镜像**；机器可读副本见 `scripts/lookups.py` 的 `FORWARD_NODES`（骨架 `build_skeleton.py` 据其自动生成报头「临近节点提示」块）。两处为同一份数据的两面，一致性由 `tests/test_scripts.py` 交叉校验——**改一处必须同步改另一处**。



| 节点日期 | 事项 | 影响对象 |

|----------|------|----------|

| 2027-01-01 | 加州 SB 1119 对 §22602 的修订及 §21811 生效；SB 1050 合成表演者广告规则生效；AB 2713 版 large online platform 义务同日 operative | 加州陪伴型聊天机器人运营者、广告创作者与广告媒介、大型网络平台 |

| 2026-12-02 | 欧盟Art. 111(4)过渡期届满：2026-08-02前投放市场的系统须完成Art. 50(2)合规；新深度伪造/CSAM禁止条款适用 | 欧盟provider（存量系统） |

| 2027-01-01 | 加州SB 1119对§22602的修订及§21811生效；SB 1050合成表演者广告规则生效 | 加州陪伴型聊天机器人运营者、广告创作者与广告媒介 |

| 2027-01-01 | 加州large online platform、GenAI hosting platform义务生效 | 加州平台类主体 |

| 2027-02-02 | 欧盟行为准则Measure 3.4水印检测互操作最低方案落地 | 欧盟provider（准则签署者） |

| 2027-07-01 | 加州SB 1119的§§21812、21812.5、21813开始施行 | 允许儿童继续使用的陪伴型聊天机器人运营者 |

| 2028-01-01 | 加州采集设备制造商义务生效（限2028年起首次州内生产销售设备） | 加州设备制造商 |



## 覆盖发现检索矩阵（触发式深度核验用，2026-09-30）

> 使用条件：仅当用户要求「最新/当前/有没有新规/重新核验」或按「按最新法规重新解读」提出要求时（SKILL.md 阶段3「触发式深度核验」）。**常规报告不执行本矩阵、不得声称做过覆盖发现。**

**加州**——官方来源：leginfo bill search / bill history / bill text / bill status；California Code 对 B&P Code §§22757–22757.6 的最新文本；州长签署/否决/chaptered 状态页。检索词：California AI Transparency Act、CAITA、22757、system provenance、provenance data、generative artificial intelligence、large online platform、AI detection tool、widely adopted specifications。保留 introduced / amended / passed / enrolled / presented to Governor / chaptered / vetoed 全状态记录；候选项须记法案编号、会期、最新版本、送州长日期、chapter 号、operative 日期、修改的法典条款。**已裁定排除项**（2026-09-30 用户裁定，目的域不同：防灾难性风险/选举诚信，非内容标识与场景披露；命中时按排除理由跳过、不重新评估）：SB 53（TFAIA，Ch. 138，§§22757.10 起）、选举类法族（AB 2355 生效／AB 2839、AB 2655 联邦法院阻止中／AB 730 待核）、州长行政令（2026-09-18 AI 安全专家委员会）。**★核验纪律（2026-10-01 新增）**：leginfo 的 billHistory／billStatus 页**不加参数时可能返回陈旧缓存**（本次核 AB 2713 曾缺最后两行「Approved by the Governor」「Chaptered by Secretary of State」）；核签署/章化状态**一律加 `&rev=1` 取新页**，或交叉核 gov.ca.gov 州长签署页。

**欧盟**——官方来源：EUR-Lex（AI Act、修正条例、勘误、授权/实施文件）；European Commission Digital Strategy / AI Office；AI Board 官方文件；Code of Practice 官方版本与充分性意见。检索词：Regulation (EU) 2024/1689、Article 50、AI-generated content transparency、Digital Omnibus、corrigendum、delegated act、implementing act、Code of Practice、AI Board。候选项须区分条例／委员会指南／行为准则／委员会意见／AI Board 结论／成员国配套规则，不得统称「欧盟新法规」。

**中国大陆**——官方来源：中国政府网；国家网信办；全国标准信息公共服务平台；算法备案与主管部门正式公告。检索词：深度合成、生成式人工智能、人工智能生成合成内容标识、GB 45438-2025、配套指引／实施细则／修改单／替代标准／正式执法口径。

**处置纪律**：候选逐项回官方原文核验（二手来源仅作线索）→ 按五分类处置（现行有约束力／已通过待生效／待决法案／非约束性指南／无影响或无法判断）→ 新发现法规报用户裁定是否入库，不得自行入库 → 报告「时效核验说明」节写明核验日期、法域、检索范围与发现结论（含负结论）。

## 核验输出格式



每部法规一行：「{法规名}：现行有效/有修订（说明），核验于{日期}，来源：{官方URL}」。发现与规则库不一致的，以官方原文更新规则库（同步更新元数据头last_verified）并在报告中说明变更。

待决／待生效法案行：「{法案名}：待决（Enrolled，{送州长日期}送州长；条文载明{operative 日期} operative），核验于{日期}，来源：{官方URL}」或「{法案名}：已章化待生效（Chapter {N}，{生效日}生效），核验于{日期}，来源：{官方URL}」。待决法案不得写成现行义务（门禁⑯/⑱/W-18 同向）。

