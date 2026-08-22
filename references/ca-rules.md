# 加州规则库：California AI Transparency Act（SB 942 经 AB 853 修正，合并文本）

```yaml
last_verified: 2026-08-13
status: 现行有效（SB 942 Ch.291 + AB 853 Ch.674合并）
next_recheck_before: 2026-11-11
```

> 核验日期：2026-08-13
> 来源层级：**官方签署版原文（Chaptered text）**——签署版全文已打包至 `references/sources/CA-SB942-chaptered.md`、`CA-AB853-chaptered.md`
> 官方来源：
> - SB 942（2024, Ch. 291，2024-09-19签署）：https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB942
> - AB 853（2025, Ch. 674，2025-10-13签署）：https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260AB853
> 合并规则（用户指定）：AB 853为修正案非清洁版。AB 853修订的条款（§22757.1定义、§22757.4罚则、§22757.6生效日）以AB 853为准；新增的§22757.3.1/3.2/3.3直接并入；未触及的§22757.2、§22757.3、§22757.5以SB 942原文为准。
> 法典位置：Business and Professions Code, Division 8, Chapter 25（§§22757–22757.6）

> **⚠️ SB 1000 修订风险提示**：SB 1000 为 CAITA 修正案，截至知识截止日**提案/审议中、尚未生效**。其拟议方向可能改写本规则库多项义务（删除§22757.1(d)100万门槛、取消manifest披露选项、修改latent披露、重构第三方许可、删除§22757.5娱乐豁免等），具体以生效文本为准。报告生成时须按 SKILL.md 运行时指令与 sb1000-diff.md 加相应提示；若 SB 1000 已生效，本规则库须全量重核。

---

## 一、生效时间线（合并后）

| 节点 | 内容 | 依据 |
|------|------|------|
| 2026-08-02 | 全章生效（covered provider义务自此适用） | §22757.6（AB 853修正，原SB 942为2026-01-01） |
| 2027-01-01 | large online platform义务生效 | §22757.3.1(c) |
| 2027-01-01 | GenAI hosting platform义务生效 | §22757.3.2(b) |
| 2028-01-01 | capture device manufacturer义务生效，仅适用于2028-01-01起**首次在州内生产销售**的设备 | §22757.3.3(c)及(a) |

## 二、义务主体与义务清单

### 1. Covered provider（GenAI系统提供方）

**定义（§22757.1(d)，AB 853沿用SB 942原文）**：创建、编码或以其他方式生产GenAI系统，且该系统**月访客或用户超100万**、在加州地理边界内公开可访问的主体。

**GenAI系统定义（§22757.1(f)）**：能生成衍生合成内容（含文本、图像、视频、音频）的AI。**注意：定义含文本，但下述实质义务条款（§22757.2、§22757.3）全部仅适用于图像、视频、音频或其组合，不含纯文本输出。**

> **§22757.1(d) 原文（脚注引用用，AB 853修正合并文本）**："'Covered provider' means a person that creates, codes, or otherwise produces a generative artificial intelligence system that has over 1,000,000 monthly visitors or users and is publicly accessible within the geographic boundaries of the state."
>
> **⚠️ 纯文本提供者实质义务豁免（写作时主动提示）**：§22757.2（免费检测工具）与§22757.3（显式/隐式披露）的义务对象均为"image, video, or audio content, or content that is any combination thereof"，**不含纯文本输出**。因此：仅生成文本的GenAI系统（如纯文本LLM/代码生成），即便满足§22757.1(d)门槛构成covered provider，也不触发§22757.2/§22757.3实质义务（因义务对象不含文本）。报告生成时，凡判定为covered provider的主体，应主动核对其输出模态——若仅含文本，应在加州节明确标注"虽构成covered provider，但§22757.2/§22757.3义务因输出为纯文本而不触发"，避免误列义务。

**义务清单**：

| 义务 | 内容 | 条文锚点 |
|------|------|----------|
| 免费AI检测工具 | 供用户评估图/视/音频内容是否由其GenAI系统创建或改变；输出检测到的system provenance data；**不得**输出personal provenance data；公开可访问（可就安全风险设合理限制）；支持上传内容或URL；支持API调用 | §22757.2(a)(1)-(6) |
| 检测工具反馈与隐私限制 | 收集用户反馈改进工具；原则上不得收集/留存工具用户个人信息（反馈opt-in例外）；不得超必要留存提交内容；不得留存personal provenance data | §22757.2(b)(c) |
| 显式披露选项（manifest disclosure） | 向用户提供在图/视/音频中加入显式披露的选项；披露应当标明AI生成、清晰显著适配媒介、技术可行范围内永久或极难移除 | §22757.3(a)(1)-(3) |
| 隐式披露（latent disclosure） | 应当包含；技术可行且合理范围内传达：①提供者名称 ②系统名称与版本号 ③创建/改变时间日期 ④唯一标识符（可直接或通过永久网页链接）；应当可被自家检测工具检测；符合广泛接受的行业标准；技术可行范围内永久或极难移除 | §22757.3(b)(1)-(4) |
| 被许可方合同传导 | 许可第三方使用GenAI系统的，应当合同要求被许可方维持系统加隐式披露的能力；**知悉**被许可方修改系统致其不能加隐式披露的，96小时内撤销许可 | §22757.3(c)(1)(2) |

> **脚注原文块（以下为AB 853修正合并文本原文，写脚注时直接引用英文原文＋条号）**：
>
> **§22757.2(a)(1)-(6)**: "(a) A covered provider shall make available an AI detection tool at no cost to the user that meets all of the following criteria: (1) The tool allows a user to assess whether image, video, or audio content, or content that is any combination thereof, was created or altered by the covered provider's GenAI system. (2) The tool outputs any system provenance data that is detected in the content. (3) The tool does not output any personal provenance data that is detected in the content. (4)(A) Subject to subparagraph (B), the tool is publicly accessible. (B) A covered provider may impose reasonable limitations on access to the tool to prevent, or respond to, demonstrable risks to the security or integrity of its GenAI system. (5) The tool allows a user to upload content or provide a uniform resource locator (URL) linking to online content. (6) The tool supports an application programming interface that allows a user to invoke the tool without visiting the covered provider's internet website."
>
> **§22757.3(a)**: "(a) A covered provider shall offer the user the option to include a manifest disclosure in image, video, or audio content, or content that is any combination thereof, created or altered by the covered provider's GenAI system that meets all of the following criteria: (1) The disclosure identifies content as AI-generated content. (2) The disclosure is clear, conspicuous, appropriate for the medium of the content, and understandable to a reasonable person. (3) The disclosure is permanent or extraordinarily difficult to remove, to the extent it is technically feasible."
>
> **§22757.3(b)**: "(b) A covered provider shall include a latent disclosure in AI-generated image, video, or audio content, or content that is any combination thereof, created by the covered provider's GenAI system that meets all of the following criteria: (1) To the extent that it is technically feasible and reasonable, the disclosure conveys all of the following information, either directly or through a link to a permanent internet website: (A) The name of the covered provider. (B) The name and version number of the GenAI system that created or altered the content. (C) The time and date of the content's creation or alteration. (D) A unique identifier. (2) The disclosure is detectable by the covered provider's AI detection tool. (3) The disclosure is consistent with widely accepted industry standards. (4) The disclosure is permanent or extraordinarily difficult to remove, to the extent it is technically feasible."
>
> **§22757.3(c)**: "(c)(1) If a covered provider licenses its GenAI system to a third party, the covered provider shall require by contract that the licensee maintain the system's capability to include a disclosure required by subdivision (b) in content the system creates or alters. (2) If a covered provider knows that a third-party licensee modified a licensed GenAI system such that it is no longer capable of including a disclosure required by subdivision (b) in content the system creates or alters, the covered provider shall revoke the license within 96 hours of discovering the licensee's action. (3) A third-party licensee shall cease using a licensed GenAI system after the license for the system has been revoked by the covered provider pursuant to paragraph (2)."

### 1.1 多原因不触发的分层表述规则（★强制）

当不触发结论同时具备两类原因时，报告须**分层表述**，禁止并列为等价原因：
- **主导原因（阈值/主体门槛）管辖全章适用性**：如「CA用户约X，远低于§22757.1(d) 100万门槛 → 不构成covered provider，全章义务不触发」。此为前提性、决定全章是否适用的原因，须首先写明。
- **层级抗辩（输出模态不在义务范围）**：如「退一步，即便构成covered provider，本案纯文本输出亦不落入§22757.2/§22757.3（限图像/视频/音频）义务范围」。此为退一步的防守性理由，仅在已先判定构成covered provider时才具有独立意义，须置于主导原因之后。

> ⚠️ **禁止写法**：「（纯文本且非 covered provider）」此类括号并列——它抹去主次，误导读者以为「纯文本」是主导原因。正确写法见上。

### 2. Large online platform（大型网络平台）——2027-01-01生效

**定义（§22757.1(h)(1)）**：公众可见的社交媒体平台、文件分享平台、大规模消息平台或独立搜索引擎，向未创作/协作创作内容的用户分发内容，**过去12个月独立月用户超200万**。排除宽带接入服务与电信服务（§22757.1(h)(2)）。Mass messaging platform指可同时向超100用户分发内容的直接消息平台（§22757.1(k)）。

**义务清单（§22757.3.1(a)(b)）**：
(1) 检测平台上分发内容中是否嵌入或附有**符合成熟标准制定组织广泛采纳规范**的来源数据；
(2) 提供用户界面披露system provenance data可用性，清晰显著展示内容真实性/来源/修改历史信息，至少含：来源数据是否可用、创建或实质改变内容的GenAI系统或采集设备名称（如适用）、数字签名是否可用；
(3) 允许用户以便捷方式查验全部可用system provenance data（界面直接展示/提供含来源数据的下载/提供链接，三选一即可）；
(4) 技术可行范围内，不得明知而剥离内容中符合广泛采纳规范的system provenance data或数字签名。

> **§22757.3.1(a)原文**（脚注引用用）：「(a) A large online platform shall do all of the following: (1) Detect whether any provenance data that is compliant with widely adopted specifications adopted by an established standards-setting body is embedded into or attached to content distributed on the large online platform. (2)(A) Provide a user interface to disclose the availability of system provenance data that reliably indicates that the content was generated or substantially altered by a GenAI system or captured by a capture device. (B) The user interface required by this paragraph shall make clearly and conspicuously available to users information sufficient to identify the content's authenticity, origin, or history of modification, including, but not limited to, all of the following: (i) Whether provenance data is available. (ii) The name of the GenAI system or capture device that created or substantially altered the content, if applicable. (iii) Whether any digital signatures are available. (3) Allow a user to inspect all available system provenance data that is compliant with widely adopted specifications adopted by an established standards-setting body in an easily accessible manner...」

### 3. GenAI hosting platform（生成式人工智能系统托管平台）——2027-01-01生效，AB 853新增

**定义（§22757.1(g)）**：供加州居民下载GenAI系统**源代码或模型权重**的网站或应用，不论是否有偿。定义未区分自有模型与第三方模型——开发者在自持站点提供**自有**模型权重下载，字面同样落入定义（公开下载即视为加州居民可达）。

**义务（§22757.3.2(a)）**：不得**明知**而提供未按§22757.3设置披露的GenAI系统。

> 文本细节：定义条款用"GenAI hosting platform"，义务条款用"GenAI system hosting platform"，系立法文本措辞不一致，指向同一主体。

> **§22757.3.2(a)原文**（脚注引用用）：「(a) A GenAI system hosting platform shall not knowingly make available a GenAI system that does not place disclosures pursuant to Section 22757.3.」

> **⚠️ 报告撰写区分（★强制，与门禁⑬/㉒协同）**：GenAI hosting platform 属「已落入定义、义务待生效」状态——现行法定义（§22757.1(g)）即可判定构成（贵司通过站点向加州居民提供模型权重下载即落入），但§22757.3.2义务**延缓至2027-01-01生效**。报告须将其与「covered provider 主体资格未达之不触发」**分列**，单列标注「已适用、义务待生效（2027-01-01）」，**不得并列为同一「当前不触发」**。同理适用于 large online platform（§22757.3.1，2027-01-01）、capture device manufacturer（§22757.3.3，2028-01-01）——三者定义均已可落入、仅义务延缓。〔SB 1000拟修订〕提示仅附着 covered provider 类（定义可能变），不得外溢至 hosting platform / large online platform / capture device manufacturer 类（其定义不受 SB 1000 影响）。

### 4. Capture device manufacturer（采集设备制造商）——2028-01-01生效，AB 853新增

**定义（§22757.1(b)(c)）**：生产在加州销售的采集设备（可录制照片、音频、视频的设备，含相机、带摄像头/麦克风的手机、录音设备）的主体；**纯组装商除外**（仅从事采集设备组装者不属于制造商，§22757.1(c)(2)）。

**全章排除（§22757.5，SB 942原文，AB 853未触及）**：本章不适用于专供非用户生成（non-user-generated）的视频游戏、电视、流媒体、电影或交互体验的产品、服务、网站或应用。

**义务（§22757.3.3(a)，限2028-01-01起首次在州内生产销售的设备）**：
(1) 向用户提供在采集内容中加入隐式披露的选项，披露传达：制造商名称、设备名称与版本号、创建/改变时间日期；
(2) **默认**在设备采集内容中嵌入隐式披露。
仅应当在技术可行且符合广泛采纳规范的范围内遵守（§22757.3.3(b)）。

> 规制方向提示：该义务是为**真实内容**嵌入来源数据（证明"真"），与标记AI生成内容方向相反。

> **§22757.3.3(a)原文**（脚注引用用）：「(a) A capture device manufacturer shall, with respect to any capture device the capture device manufacturer first produced for sale in the state on or after January 1, 2028, do both of the following: (1) Provide a user with the option to include a latent disclosure in content captured by the capture device that conveys all of the following information: (A) The name of the capture device manufacturer. (B) The name and version number of the capture device that created or altered the content. (C) The time and date of the content's creation or alteration. (2) Embed latent disclosures in content captured by the device by default.」

### 5. 第三方被许可方

许可被covered provider依§22757.3(c)(2)撤销后，应当停止使用该GenAI系统（§22757.3(c)(3)）。

## 三、豁免

§22757.5：本章不适用于** exclusively非用户生成**的电子游戏、电视、流媒体、电影或交互体验产品/服务/网站/应用。

> **§22757.5原文**（脚注引用用）：「This chapter does not apply to any product, service, internet website, or application that provides exclusively non-user-generated video game, television, streaming, movie, or interactive experiences.」

## 四、罚则与执法（§22757.4，AB 853修正后）

| 项目 | 内容 |
|------|------|
| 罚款 | 违反本章者按**每次违规5,000美元**计（§22757.4(a)(1)） |
| 按日计罚 | covered provider、large online platform、capture device manufacturer违规的，**每日视为独立违规**（§22757.4(b)）。注意：GenAI hosting platform**未被列入**按日计罚列举 |
| 胜诉方费用 | 胜诉原告可获合理律师费与成本（§22757.4(a)(2)） |
| 被许可方违规 | 检察长、郡法律顾问、市检察官可诉请禁令救济+合理律师费与成本（§22757.4(c)） |
| 执法主体 | 检察长（Attorney General）、市检察官（city attorney）、郡法律顾问（county counsel） |

> **§22757.4原文**（AB 853修正后文本，脚注引用用）：「(a)(1) A violator of this chapter shall be liable for a civil penalty in the amount of five thousand dollars ($5,000) per violation to be collected in a civil action filed by the Attorney General, a city attorney, or a county counsel. (2) A prevailing plaintiff in an action brought pursuant to this subdivision shall be entitled to all reasonable attorney's costs and fees. (b) Each day that a covered provider, large online platform, or capture device manufacturer is in violation of this chapter shall be deemed a discrete violation.」

## 五、效力核验要点（每次使用前复核）

1. leginfo上B&P Code §§22757–22757.6是否有新修正案（2026年会期后续法案）。
2. AI Omnibus之外的联邦层面立法（如联邦AI披露法案）是否抢占（preemption）动态。
3. C2PA等标准组织规范更新是否影响"广泛采纳规范"的认定。

## 六、与二手资料的出入记录（本次原文核实纠正）

1. 采集设备制造商义务生效日为**2028-01-01**（律所解读多写2027），且仅覆盖2028年起首次在州内生产销售的设备。
2. 最终签署版**无**"向第三方应用开放硬件级溯源能力"要求（该要求存在于2025年3月委员会分析稿，未入最终文本）；最终文本为"提供隐式披露选项+默认嵌入"。
3. "2027-01-01起covered provider不得提供缺少披露的系统"系二手资料误植——该禁止针对的是GenAI hosting platform（§22757.3.2）。
4. GenAI hosting platform义务内容为"不得明知而提供未按§22757.3设置披露的GenAI系统"，非二手资料所述"提供显式披露选项"。
