# CoP 摘要（cop-digest）— 20260911

> **用途**：运行时报告含欧盟且触发 CoP 时，读本文件替代整读原文；需某 Measure 全文或本文件未覆盖处，按「原文锚点」行号区间读 `references/sources/EU-CoP-Transparency-Code-of-Practice.txt`。
> **源**：Code of Practice on Transparency of AI-Generated Content（《AI生成内容透明度行为准则》，EU AI Office，2026-06-10 发布）；txt 114,472 字节 / 1,692 行 / **MD5 52e4dd52a86d239e6fbe18fcb2062fee** / 核验日期 2026-09-05。PDF 为权威原件。行号锚点仅对该 txt 版本有效，txt 变更（重新抽取/重新下载）即锚点整体失效，须按构建规则第七节重建并重核。
> **构建**：2026-09-11，按《cop-digest 构建规则》（references/cop-digest-build-rules.md）执行；版式层清洗（连字断词/页码行/空行），未改措辞。**逐字引用前须按锚点回对原文。**
> **层级定义**（原文照录口径）：will＝为满足 Art. 50(2)/(4)/(5) 合规而必须执行、受市场监管当局监测；encouraged＝自愿但推荐；may＝自愿或提供实现弹性。遵守本准则**不构成**合规的确凿证据（adherence does not constitute conclusive evidence of compliance）。

## 〇、Art. 50 ↔ CoP 对应总表（要旨归纳）

| AI Act 条款 | CoP 覆盖 | 对应 Commitment/Measure |
|---|---|---|
| Art. 50(2) 机器可读标记（提供者） | Section 1 | C1（M1.1–1.4 标记）；C2（M2.1–2.4 检测）；C3（M3.1–3.5 质量要求）；C4（M4.1–4.4 测试与合规）——四组 LEGAL TEXT 均含 50(2) |
| Art. 50(5) 清晰可辨、首次接触时提供 | Section 1 + Section 2 | S1：M2.3（检测结果披露；C2、C4 的 LEGAL TEXT 亦含 50(5)）；S2：M1.1（无障碍）/ M1.2（首次曝光时点） |
| Art. 50(4) 深度伪造与公共利益文本披露（部署者） | Section 2 | S2 C1（M1.1–1.3）、C3（艺术作品）、C4（编辑责任） |
| Art. 50(1) 交互告知、Art. 50(3) 情感识别告知 | **本 CoP 两节不覆盖** | 衔接小节须注明 CoP 无对应措施，不得虚挂钩 |

适用主体：Section 1＝生成式人工智能系统提供者（Art. 2 + 50(2) 范围内）；独立投放于联盟市场的生成式人工智能模型提供者（原文 generative AI models，未用 GPAI 表述）与第三方标记/检测方案提供者可自愿加入。Section 2＝仅部署者，且内容构成深度伪造（Art. 3(60)）或属「无人工审核/编辑责任、为向公众通报公共利益事项而发布的 AI 生成/篡改文本」。SME/SMC 全程按比例（proportionate）适用。

## 一、Section 1：标记与检测（提供者，Art. 50(2)、(5)）

### C1 标记（LEGAL TEXT: Art. 50(2)，recital 133/135）

**M1.1 机器可读标记技术（Machine-readable marking techniques）**〔will〕
- 层级：主 will；Sub-measure 1.1.1（签名元数据）will；1.1.2（不可感知水印）will（极短文本除外）；1.1.3（指纹/日志）may（可选，若实现则 will：仅限输出数据、安全与隐私合规；仅凭指纹/日志不足以满足 Art. 50(2) 与 C3 质量要求）；模型层水印 encouraged（模型提供者）。
- 要点：至少一种机器可读标记；现行技术下单技术不足以满足四要求，故默认**双层**：①数字签名＋时间戳的元数据（防篡改）；②不可感知水印（难分离）。例外：①封闭物理产品内受控生成（单层足够）；②自由文本（元数据无法搭载，单层＝水印即可；>200 token 仍须水印，可靠性可较低，检测访问可按 2.1.2 限专家）；③替代技术：能以公认基准证明同等或更优四要求者可单技术合规（基准出现前可按 M4.2 内部测试证明）。标记可在价值链不同环节实施（人工智能系统提供者自身或上游模型提供者），亦可采用第三方标记/检测技术方案；依赖第三方不减轻签署方自身 Art. 50(2) 责任。
- 关键句："Signatories will implement a multi-layered marking approach to ensure that the outputs of their generative AI systems are marked with at least two layers of machine-readable marking, as specified in Sub-measures 1.1.1 and 1.1.2 below."
- Art.50：50(2)。锚点：L353–452。

**M1.2 标记不可移除（Non-removal of markings）**〔will〕
- 层级：主 will（尽力保留元数据标记：(a) 保留、不故意篡改输入内容既有元数据标记；(b) 在可接受使用政策/条款/文档中禁止部署者或第三方故意去除、篡改元数据标记——开源许可人工智能系统/模型仅需文档提示该最佳实践）＋ will（**不投放、不推广**以绕开标记为目的的工具）＋ encouraged（自营在线平台/搜索引擎者确保平台保留元数据标记）。
- 要点：善意合法处理（安全审计、研究等）导致元数据必要修改不违反；对第三方标记与第三方合规不承担责任。
- 关键句："Signatories will neither place or make available on the market, nor promote or advertise the use of tools whose purpose is to circumvent the machine-readable markings added to the AI-generated or manipulated content for transparency."
- Art.50：50(2)。锚点：L453–483。

**M1.3 来源信息透明（可选，Transparency of the provenance information）**〔encouraged〕
- 要点：按 1.1.1 鼓励写入更丰富元数据：人工智能系统名、提供者公司名、生成/篡改时间戳；可含模型标识符（identifier）与版本号；被篡改内容记录修改操作类型（如物体移除）；多项操作编码为单条元数据标记。
- 关键句："Signatories are encouraged to add or record relevant content provenance information within content generated or manipulated by their AI systems, in particular the name of the AI system, the company name of the AI provider, and a timestamp indicating when the content was generated or manipulated."
- Art.50：50(2)（增强）。锚点：L484–498。

**M1.4 可感知标记功能（可选，Functionality for perceptible markings）**〔encouraged〕
- 要点：能生成深度伪造/公共利益文本的提供者，鼓励在系统界面提供可选功能，允许部署者生成时自主直接施加符合 Section 2 的可感知标签；鼓励遵循统一 UX 标准、与平台/媒体 CMS 互操作；部署者的 50(4) 披露责任不因此转移。
- 关键句："…are encouraged to provide an optional functionality in their system's interface and to implement an integrated option that allows deployers and other users to directly apply at their own discretion – upon generation of the output – a perceptible label in consistency with the Commitments and Measures in Section 2 of the Code."
- Art.50：50(4) 支撑。锚点：L499–519。

### C2 检测（LEGAL TEXT: Art. 50(2)、(5)）

**M2.1 标记检测机制（Detection mechanisms for markings）**〔will〕
- 层级：主 will。Sub 2.1.1（提供检测方案）will：**提供方式（一种或多种）**——(i) 公开的、理想情况下标准化的规范（允许任何第三方实现检测机制；encouraged 提供参考实现）；(ii) 软件（如独立可执行文件或库；encouraged 兼容多数操作系统（含技术可行的移动端）、硬件要求尽量低以支持通用设备本地运行）；(iii) 经 API 访问的云端服务。每种标记技术配检测机制；可依赖共享/第三方检测（不影响自身责任）；同时为生成式人工智能模型提供者的签署方，encouraged 在模型投放市场前即提供针对其模型内容的检测机制（便利下游提供者合规）；**免费提供**；例外：月活 <1,000,000 且检测方案运营成本高者，可对单用户超合理阈值的批量请求收取合理费用；对市场监管当局、执法、媒体、事实核查、trusted flaggers、独立研究者、教育科研机构、公民社会组织**始终免费且不限量**；encouraged 与生态各方合作使检测方案直接内置于分发与传播平台。Sub 2.1.2（访问）will：面向可能接触内容的人群提供相应 UI；公众可能接触→对公众开放；受控场景可限那批人；自由文本水印检测可靠性较低，可限_verified expert users_（当局/执法/媒体/研究者等清单），时限至更优技术出现；检测结果可应请求以数字签名格式下载（含内容哈希、检测方案 URL/标记、时间戳）。Sub 2.1.3（隐私/安全）will：(a) 按欧盟隐私与数据保护法；(b) 传输与存储中的保密性与完整性；(c) 数据最小化；(d) 提交内容仅用于检测标记（除 (c) 项所列必要目的外不作他用）；(e) 「零留存」——内容仅存检测期间、随即永久删除，不留逐字副本（流量日志可凭合法基础短期留存以保安全防滥用）；(f) 与风险相称的安全保障（持续保密性、完整性、可用性与韧性）；(g) 跨境传输合规；(h) 网络安全最佳实践（防未授权访问危及底层标记/检测机制）。Sub 2.1.4（退役）will：可退役但须以同/更优且向后兼容的替代方案交接；无替代停运的，向当局提供方案副本以检遗留内容。
- 关键句："Signatories will make available a detection solution, composed of one or more detection mechanisms, to enable deployers, users of their generative AI system, third-party integrators, end-users exposed to the content, and other legitimate parties … to verify whether content has been generated or manipulated by their AI system based on the marking technique(s) implemented pursuant to Commitment 1."
- Art.50：50(2)、50(5)。锚点：L537–659。

**M2.2 取证检测（可选，Forensic detection mechanism）**〔may〕
- 层级：may（可选补充）；若实现则 will（满足 2.1.3 隐私安全与 M2.3 披露、尽力对齐 C3 工艺水平）；可限专家访问（同 2.1.2 文本水印例外）。
- 要点：用于检测标记被剥离的内容；原文定性：发布时取证检测机制未被认定足够成熟、不足以满足 Art. 50(2) 与 C3 的质量要求（原文未作更多表述；「不能单独作为合规手段」系 Sub-measure 1.1.3 对指纹/日志的规则，勿混）。
- 关键句："Signatories may include as part of their detection solution, as an additional optional measure, forensic detection mechanism to detect content generated or manipulated by their AI system or underlying model for which marking has been stripped."
- Art.50：50(2)（补充）。锚点：L660–676。

**M2.3 检测结果清晰可及披露（Clear and accessible disclosure of detection results）**〔will〕
- 要点：结果清晰易懂；标注依据何种技术（元数据/水印/取证/其他）；纳入水印或元数据中的附加信息；可含 AI 参与比例、改动定位；无障碍（EAA 2019/882、Web Accessibility Directive 2016/2102；encouraged：ETSI EN 301 549、WCAG 2.1 AA）；分层展示（encouraged）防普通用户信息过载。
- 关键句："Signatories will ensure that detection results indicate whether they are based on a metadata marking, a watermark marking, forensic detection or other techniques, to the extent technically feasible."
- Art.50：50(5)。锚点：L677–701。

**M2.4 标记与检测素养支持（可选）**〔encouraged〕
- 要点：向部署者/专家用户提供文档（不含商业秘密）助其选择与使用方案；面向终端用户的素养资源按比例、按场景（含低 人工智能素养、敏感场景）；可与学界/公民社会协作。
- 关键句："Signatories are encouraged to ensure that documentation and other relevant information … is provided to deployers and other expert users to support them in making informed decisions on what marking and associated detection solutions they may use"
- Art.50：50(2)（配套）。锚点：L702–722。

### C3 标记与检测方案质量要求（LEGAL TEXT: Art. 50(2)，recital 133）

总体：四要求（有效性、互操作性、稳健性、可靠性）**跨全部标记技术整体评估**，非逐技术评估；投放市场前按 C4 测试证明，并贯穿生命周期。

**M3.1 有效性（Effectiveness）**〔will〕
- 要点：方案组合使自然人能区分该系统的生成/篡改内容；无量化指标，采用用户测评；encouraged 发布展示规范；may 开展面板研究。
- 关键句："Signatories will implement technical marking and detection solutions which, in conjunction, are fit-for-purpose and capable of enabling natural persons to distinguish content generated or manipulated by their AI system"
- 锚点：L749–760。

**M3.2 可靠性（Reliability）**〔will〕
- 要点：两个维度——名义条件下检测准确率＋随内容长度/尺寸/多样性/语义的变化；用误检率等指标；样本含自有标记内容与他人内容；评估数据尽量未参与训练；跨多样语境报告。
- 关键句："Signatories will implement marking and detection solutions which, in conjunction, achieve a high level of reliability in different expected contexts and across use cases, to the extent technically feasible and in alignment with the state of the art."
- 锚点：L761–781。

**M3.3 稳健性（Robustness）**〔will〕
- 要点：典型处理（就地修改：压缩/截图/同形字等；去同步机制（desynchronisation）：裁剪/旋转/翻译循环等；模拟孔洞（analogue hole）：翻拍/录音）；局部修改（如用户打码）；对抗攻击（复制、去除、再生成、修改，验证标记完整性）；与 M3.2 同指标；encouraged 限流等网络安全实践与威胁评估更新。单层元数据场景不适用本条。
- 关键句："Signatories will implement marking and detection solutions which, together, maintain intended performance levels under varying conditions, covering both common alterations and adversarial attacks, to the extent technically feasible, and in alignment with the state of the art."
- 锚点：L782–817。

**M3.4 互操作性（Interoperability）**〔will〕
- 要点：分阶段。初期：①元数据标记采用既定标准开放检测；②向委员会与利益相关方公开集成/访问信息（encouraged 上网与注册表）；③**2027-02-02 前实现水印检测互操作方案**，四选一：(i) 公开互操作行业标准访问方法（API 路由）、(ii) 内容内公开可读 signpost、(iii) 签署方联合共享检测方案（对参与签署方保持中立〔agnostic，不绑定特定参与方〕，任何签署方（含 SME/SMC）均可加入）、(iv) 同等效果的其他方案；④与委员会善意合作推进标准（encouraged 参加任务组）。后续阶段：标准出台后及时实施。
- 关键句："Signatories will implement an interoperability solution for their detection mechanisms by 2 February 2027 by implementing one or more of the following:"
- Art.50：50(2)。锚点：L818–883。

**M3.5 推进技术水平（可选）**〔encouraged〕
- 要点：研发、基准与参考数据集、红队演练、无提供者绑定的检测方案、参与 Code 任务组。
- 锚点：L884–908。

### C4 测试、验证与合规（LEGAL TEXT: Art. 50(2)、(5)）

**M4.1 合规流程（Compliance process）**〔will〕
- 要点：文档化并持续更新高层合规流程；SME/SMC 按比例；可复用既有流程文档、可依赖第三方/模型层文档（最终责任不减）；开源方案依赖须记录。
- 关键句："Signatories will document, implement, and keep up to date, in line with the state of the art, a compliance process that describes at a high-level how they have implemented the different Measures in this Section of the Code"
- 锚点：L915–933。

**M4.2 测试、验证与监测（Testing, verification, and monitoring）**〔will〕
- 要点：投放前及此后定期测试（真实场景条件）；公认基准出现前按内部基准与行业最佳实践测试报告；may 引入独立专家红队、may 在 AI 法第 57 条监管沙箱内测评；监测已证实的合规缺陷并纠正；下游提供者可依赖上游/第三方测试结果。
- 关键句："Prior to placing their generative AI system on the market or putting it into service, and regularly thereafter, Signatories will test the compliance of their marking and detection solutions with the requirements and the measures specified in this Section of the Code."
- 锚点：L934–954。

**M4.3 培训（Training）**〔will〕
- 要点：对涉及 Art. 50(2)/(5) 与 **Article 4 AI Act（人工智能素养）**合规岗位人员按比例培训。
- 关键句："Signatories will make proportionate efforts to provide appropriate training to their personnel who have roles relevant to ensuring compliance with Article 50(2) and (5) and Article 4 AI Act."
- 锚点：L955–962。

**M4.4 与市场监管当局合作（Cooperation with market surveillance authorities）**〔will〕
- 要点：按 Art. 74 AI Act 与市场监督条例第 7 条合作；经合理请求提供 M4.1 文档及标记/检测方案访问；Art. 78 保密适用；encouraged 与人工智能办公室（AI Office）/人工智能委员会（AI Board）共享经评估技术信息（EU 存储库）。
- 关键句："Signatories will cooperate with competent market surveillance authorities under the AI Act to demonstrate compliance with Article 50(2) and (5) AI Act and their Commitments under this Section of the Code."
- 锚点：L963–L979（后接 Glossary，L980 起）。

## 二、Section 2：深度伪造与公共利益文本的标注与披露（部署者，Art. 50(4)、(5)；原文标题 Labelling，labelling＝标注）

适用对象（总述）：仅限部署者；「deep fake」＝Art. 3(60) 定义（形似真实的人员、物体、地点、实体或事件且令人误信为真实的 AI 生成/篡改图像、音频、视频）；「published text」＝为向公众通报公共利益事项而发布、**未经人工审核或编辑控制且无自然人/法人承担编辑责任**的 AI 生成/篡改文本。行业良好实践可细化但须公开（will）。

### C1 深度伪造与公共利益文本的披露（LEGAL TEXT: Art. 50(4)、(5)）

总规则：通过 Annex 1 EU 图标或符合规格的同等图标/标签披露；可并入既有行业披露实践（须合规）；贴标不免除其他法律义务（肖像权、版权等）。

**M1.1 设计规格（Design specifications）**〔will〕
- 层级：主 will；二层的「生成/修改」信息与修改内容说明 encouraged；尺寸/样式变化 may（保持清晰可辨）；替代听觉方案（earcon 等）may（须配宣传措施）；无障碍标准 encouraged；平台/搜索引擎（含 DSA 35(1) VLOP/VLOSE）encouraged 采用 EU 图标或在上传接口提供披露方案。
- 要点：视觉可用时——图标主元素为大写「AI」字母（同高、缩放保比例；语言法另定）；视觉不可用（纯音频）——**深度伪造开头简短语音声明**（内容语言或英语，平实语言披露人工来源）；考虑受众多样性（人工智能素养、语言、儿童老人）与敏感行业；无障碍（语音描述、触觉提示、高对比、读屏兼容）。
- 关键句："The disclosure will include, at the beginning of the deep fake itself, a short audible disclaimer in plain and simple natural language, either in the same language as the content or in English, disclosing the artificial origin of the audio deep fake in a perceivable manner."
- Art.50：50(4)、50(5)。锚点：L1348–1419。

**M1.2 放置规格（Placement specifications）**〔will〕
- 层级：主 will；全程显示与下游协作 encouraged；封闭专业场景 UI 放置 may；文本部分标注 may；短文本上下文提示 may（仍须贴标）。
- 要点：①总原则：放置无须用户交互即被注意；可见时长足够；**直接嵌入内容**（除非有等效替代，如界面覆盖层）；首次接触时清晰可辨。②视觉可用：图片/视频右上角等无遮挡处；视频开头＋固定间隔＋插播后重复显示；纯视觉深度伪造中语音披露仅作附加且必须伴随视觉披露；音频深度伪造有屏时加视觉披露；**公共利益文本**：文本上方/顶部标题附近或文首版权栏（colophon）。③纯音频：首次接触前听觉声明＋适当间隔提醒（含插播后）。
- 关键句："For published text, Signatories will place the icon or equivalent label, for example above or at the top of the text, near the headline of the text, or in the colophon at the beginning of the text, as long as placement is clear, consistent, and distinguishable for the end-user."
- Art.50：50(5)。锚点：L1420–1503。

**M1.3 自愿参加 Code 任务组（可选）**〔encouraged〕
- 要点：支持 EU 图标迭代（含 audio-only 版）、交互式第二层、披露方法一致化、行业良好实践。
- 锚点：L1504–1528。

### C2 内部流程

**M2.1 内部合规流程（Internal compliance process）**〔will〕
- 要点：按规模建立/维持合规流程与文档（描述如何用图标/等效标签实现披露义务）；encouraged 公开披露方案说明；常规使用 AI 生成此类内容者建立设计/放置落实核验流程；媒体服务提供者（Reg (EU) 2024/1083 第 2(2) 条）可沿用既有程序与专业标准。
- 关键句："Signatories will put in place or maintain appropriate internal compliance processes and documentation that specifies how they implement the disclosure obligations using the icon or equivalent label."
- 锚点：L1535–1560。

**M2.2 认知与素养（Awareness and literacy）**〔will〕
- 要点：按比例确保相关人员知悉 50(4)/(5) 披露义务；encouraged 培训（何时须披露、流程、编辑责任场景、艺术作品、无障碍、纠错）。
- 关键句："Signatories will make efforts proportionate to their size, available organisational resources, and capacities to ensure awareness of the disclosure obligations under Article 50(4) and (5) AI Act among their personnel"
- 锚点：L1561–1576。

**M2.3 评审、反馈与当局合作（Review, feedback and cooperation）**〔will〕
- 要点：内部评审＋外部反馈；encouraged 设举报渠道（trusted flaggers、研究者、事实核查）；对已证实的错误贴标**无不延误地**整改；与主管当局合作。
- 关键句："Signatories will review cases that have been reported in a substantiated manner as mislabelled or incorrectly labelled and take measures to remedy cases of non-compliance with Article 50(4) and (5) without undue delay."
- 锚点：L1577–1591。

### S2-C3 艺术创意作品披露（Commitment 级，无 Measure）〔will＋may〕
- 要点：Art. 50(4) 但书场景——明显艺术、创意、讽刺、虚构类作品：披露以不妨碍作品展示与欣赏的方式实施；will：按 M1.1 设计规格、首次接触时（说明/片尾字幕等）清晰可辨、可感知时长；数字交互场景 may 置于帧旁/界面/悬停显示等上下文位置（无须专门动作即可感知）；非数字场景 may 在入口/售票处/说明书/包装提供。
- 关键句："Signatories commit to implement measures to disclose deep fakes that form part of evidently artistic, creative, satirical, fictional or analogous work or programmes in a way that does not hamper the display or enjoyment of the work"
- 锚点：L1592–1621。

### S2-C4 公共利益文本的人工审核与编辑控制（Commitment 级）〔may／commit＋will〕
- 要点：媒体服务提供者（Reg (EU) 2024/1083）可凭既有编辑程序依赖 Art. 50(4) 第二段的**编辑例外**；其他签署方承诺建立/调整/维持**发布前人工审核或编辑控制**政策并落实编辑责任人；will：①标明编辑责任人（姓名/角色/联系方式）；②概述组织措施与人力配置（无须逐篇记录）；承诺公开编辑责任联系方式；不影响媒体自由与消息来源保护。
- 关键句："All other Signatories … commit to establish, adapt, or maintain appropriate policies for human review or editorial control prior to publication and that a natural or legal person holds editorial responsibility for the publication."
- 锚点：L1622–L1651（后接 Annex，L1655 起）。

## 三、Annex 1 与关键术语

- **Annex 1 EU 图标**：三款——全 AI 生成（AI+GENERATED）、部分 AI 篡改（AI+MODIFIED）、基础款（可加交互层/替代文本标签）；公开免费使用、无须署名；任务组将开发交互第二层与 audio-only 图标。
- 关键术语（节选自 Glossary，全表见原文 L980–L1106）：**free-form text**（无容器结构的裸文本）；**containerised text**（PDF/Word/HTML 等容器内文本）；**very short text**（<200 token，现行技术难以可靠水印）；**watermark**（不可感知且稳健（robust）、内嵌于内容本体）；**fingerprinting**（感知哈希）；**forensic detection**（无需预先标记的取证检测）；**signpost**（指示用哪个检测方案的公开标记，互操作机制）；**deep fake**（Art. 3(60) AI Act）。

## 四、个案适用与覆盖注册表（机器可读）

本注册表固定登记全部 25 个规则单元，只表达规则条件，不预判任何具体产品。个案分析时按主体、内容类型、模态、例外与 B11 签署事实逐条填写 `cop_case_matrix/1`：相关 Section 的每条记录只能归入 `applicable`（适用）、`conditional`（条件适用）、`not_applicable`（不适用）或 `to_verify`（待核实）之一。`will_required=true` 表示该规则在个案中归为适用/条件适用时，报告必须出现；`expansion_required=true` 的三个 Section 1 关键措施还须覆盖全部 `required_points`。签署与否不改变 AI Act Art. 50 的成文法义务；`signatory_effect` 仅说明准则承诺层的效果。

<!-- COP_CASE_REGISTRY_JSON_START -->
```json
{
  "schema": "cop_case_registry/1",
  "records": [
    {
      "id": "S1-C1-M1.1",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)"],
      "applicability": "provider向欧盟市场投放或投入使用生成式人工智能系统，且输出属于Art. 50(2)覆盖内容；结合自由文本、封闭物理环境和同等替代技术例外判断",
      "signatory_effect": "签署Section 1时，will部分为准则承诺；未签署、计划签署或状态不确定均不替代Art. 50(2)义务",
      "level": "will+may+encouraged",
      "will_required": true,
      "expansion_required": true,
      "required_points": ["multi_layer", "signed_metadata", "imperceptible_watermark", "short_text_or_closed_exception", "alternative_technology_equivalence", "third_party_no_release"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "machine-readable-marking",
      "source_anchor": "L353-L452"
    },
    {
      "id": "S1-C1-M1.2",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)"],
      "applicability": "Section 1范围内的provider处理既有标记、制定使用政策或提供相关工具",
      "signatory_effect": "签署Section 1时，will部分为准则承诺；encouraged部分仍为推荐",
      "level": "will+encouraged",
      "will_required": true,
      "expansion_required": true,
      "required_points": ["preserve_existing_metadata", "terms_prohibit_removal", "no_circumvention_tools", "legitimate_processing_exception", "platform_preservation_encouraged"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "marking-preservation",
      "source_anchor": "L453-L483"
    },
    {
      "id": "S1-C1-M1.3",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)"],
      "applicability": "provider选择在标记中加入扩展来源信息时",
      "signatory_effect": "encouraged措施，即使签署Section 1亦属推荐",
      "level": "encouraged",
      "will_required": false,
      "expansion_required": false,
      "required_points": ["system_provider_timestamp", "model_version_optional", "manipulation_operation"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "provenance-information",
      "source_anchor": "L484-L498"
    },
    {
      "id": "S1-C1-M1.4",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(4)"],
      "applicability": "系统可生成深度伪造或有关公共利益事项而发布的文本，且provider可向deployer提供可感知标注功能时",
      "signatory_effect": "encouraged措施，不转移deployer的Art. 50(4)责任",
      "level": "encouraged",
      "will_required": false,
      "expansion_required": false,
      "required_points": ["optional_interface_label", "section2_consistency", "deployer_responsibility_retained"],
      "modality": ["text", "image", "audio", "video"],
      "recommendation_theme": "perceptible-disclosure-support",
      "source_anchor": "L499-L519"
    },
    {
      "id": "S1-C2-M2.1",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)", "50(5)"],
      "applicability": "provider实施机器可读标记并需向相关人群提供相应检测能力时",
      "signatory_effect": "签署Section 1时为will准则承诺，并包含若干encouraged实现选项",
      "level": "will+encouraged",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["public_spec_software_or_cloud_api", "free_access_rule", "always_free_unlimited_groups", "audience_access_ui", "privacy_security_zero_retention", "retirement_handover"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "detection-access",
      "source_anchor": "L537-L659"
    },
    {
      "id": "S1-C2-M2.2",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)"],
      "applicability": "provider选择提供用于识别标记已被剥离内容的取证检测时",
      "signatory_effect": "主措施为may；一旦实施，隐私安全、结果披露和质量对齐要求转为条件性will",
      "level": "may+conditional-will",
      "will_required": false,
      "expansion_required": false,
      "required_points": ["forensic_optional", "conditional_privacy_disclosure", "expert_access_possible"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "forensic-detection",
      "source_anchor": "L660-L676"
    },
    {
      "id": "S1-C2-M2.3",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(5)"],
      "applicability": "provider向用户或其他主体提供检测结果时",
      "signatory_effect": "签署Section 1时为will准则承诺；分层展示等为encouraged",
      "level": "will+encouraged",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["clear_results", "technique_basis", "additional_information", "accessibility", "layered_display_encouraged"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "detection-results",
      "source_anchor": "L677-L701"
    },
    {
      "id": "S1-C2-M2.4",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)"],
      "applicability": "provider可向部署者、专家用户或终端用户提供标记与检测素养支持时",
      "signatory_effect": "encouraged措施，即使签署Section 1亦属推荐",
      "level": "encouraged",
      "will_required": false,
      "expansion_required": false,
      "required_points": ["expert_documentation", "end_user_literacy", "stakeholder_collaboration"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "ai-literacy",
      "source_anchor": "L702-L722"
    },
    {
      "id": "S1-C3-M3.1",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)"],
      "applicability": "Section 1范围内标记与检测方案的整体有效性评估",
      "signatory_effect": "签署Section 1时为will准则承诺",
      "level": "will+encouraged+may",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["natural_person_distinguish", "user_testing", "display_specification_optional"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "quality-assurance",
      "source_anchor": "L749-L760"
    },
    {
      "id": "S1-C3-M3.2",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)"],
      "applicability": "Section 1范围内标记与检测方案的可靠性评估",
      "signatory_effect": "签署Section 1时为will准则承诺",
      "level": "will",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["accuracy_nominal_conditions", "variation_by_content", "false_detection_metrics", "diverse_contexts"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "quality-assurance",
      "source_anchor": "L761-L781"
    },
    {
      "id": "S1-C3-M3.3",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)"],
      "applicability": "除单层元数据场景外，对标记与检测方案进行典型处理、局部修改和对抗攻击测试",
      "signatory_effect": "签署Section 1时为will准则承诺",
      "level": "will+encouraged",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["common_alterations", "local_edits", "adversarial_attacks", "metadata_single_layer_exception", "threat_update"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "quality-assurance",
      "source_anchor": "L782-L817"
    },
    {
      "id": "S1-C3-M3.4",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)"],
      "applicability": "provider的元数据和水印检测机制需与生态参与者互操作时",
      "signatory_effect": "签署Section 1时为will准则承诺；任务组参与等为encouraged",
      "level": "will+encouraged",
      "will_required": true,
      "expansion_required": true,
      "required_points": ["open_metadata_standard", "publish_integration_information", "deadline_2027_02_02", "four_path_options", "commission_cooperation", "future_standard_adoption"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "interoperability",
      "source_anchor": "L818-L883"
    },
    {
      "id": "S1-C3-M3.5",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)"],
      "applicability": "provider参与推进标记和检测技术、基准、数据集或任务组时",
      "signatory_effect": "encouraged措施，即使签署Section 1亦属推荐",
      "level": "encouraged",
      "will_required": false,
      "expansion_required": false,
      "required_points": ["research_benchmarks_datasets", "red_teaming", "provider_agnostic_detection", "task_force"],
      "modality": ["text", "image", "audio", "video", "other"],
      "recommendation_theme": "state-of-art-development",
      "source_anchor": "L884-L908"
    },
    {
      "id": "S1-C4-M4.1",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)", "50(5)"],
      "applicability": "Section 1范围内建立、记录和持续更新合规流程",
      "signatory_effect": "签署Section 1时为will准则承诺，SME/SMC按比例",
      "level": "will",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["documented_process", "kept_current", "third_party_reliance_documented", "responsibility_retained"],
      "modality": ["all"],
      "recommendation_theme": "compliance-governance",
      "source_anchor": "L915-L933"
    },
    {
      "id": "S1-C4-M4.2",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)", "50(5)"],
      "applicability": "Section 1范围内在投放前及生命周期内测试、验证和监测标记与检测方案",
      "signatory_effect": "签署Section 1时为will准则承诺；独立红队与监管沙箱为may",
      "level": "will+may",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["pre_market_testing", "periodic_real_world_testing", "benchmark_or_internal_report", "defect_monitoring_remediation", "downstream_reliance"],
      "modality": ["all"],
      "recommendation_theme": "testing-monitoring",
      "source_anchor": "L934-L954"
    },
    {
      "id": "S1-C4-M4.3",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)", "50(5)", "Art.4"],
      "applicability": "人员岗位与Art. 50(2)/(5)及人工智能素养合规相关时",
      "signatory_effect": "签署Section 1时为will准则承诺，按规模和资源比例实施",
      "level": "will",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["relevant_personnel", "proportionate_training", "article4_link"],
      "modality": ["all"],
      "recommendation_theme": "training-awareness",
      "source_anchor": "L955-L962"
    },
    {
      "id": "S1-C4-M4.4",
      "section": "Section 1",
      "actor": "provider",
      "art50_anchor": ["50(2)", "50(5)"],
      "applicability": "市场监管当局就Art. 50合规提出合理要求或开展监督时",
      "signatory_effect": "签署Section 1时为will准则承诺；向AI Office/AI Board共享信息为encouraged",
      "level": "will+encouraged",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["authority_cooperation", "process_document_access", "solution_access", "confidentiality"],
      "modality": ["all"],
      "recommendation_theme": "authority-cooperation",
      "source_anchor": "L963-L979"
    },
    {
      "id": "S2-C1-M1.1",
      "section": "Section 2",
      "actor": "deployer",
      "art50_anchor": ["50(4)", "50(5)"],
      "applicability": "deployer生成或篡改并披露深度伪造，或发布满足Art. 50(4)条件的公共利益文本",
      "signatory_effect": "签署Section 2时，主will为准则承诺；二层信息、无障碍标准等按各自层级",
      "level": "will+encouraged+may",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["visual_icon_spec", "audio_disclaimer", "audience_diversity", "accessibility", "second_layer_optional"],
      "modality": ["text", "image", "audio", "video"],
      "recommendation_theme": "perceptible-disclosure-design",
      "source_anchor": "L1348-L1419"
    },
    {
      "id": "S2-C1-M1.2",
      "section": "Section 2",
      "actor": "deployer",
      "art50_anchor": ["50(5)"],
      "applicability": "Section 2披露标签需按内容模态和发布环境确定放置、时点与持续时间",
      "signatory_effect": "签署Section 2时，主will为准则承诺；若干展示选项按encouraged/may",
      "level": "will+encouraged+may",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["first_exposure", "sufficient_duration", "direct_embedding_or_equivalent", "visual_placement", "published_text_placement", "audio_repeat"],
      "modality": ["text", "image", "audio", "video"],
      "recommendation_theme": "perceptible-disclosure-placement",
      "source_anchor": "L1420-L1503"
    },
    {
      "id": "S2-C1-M1.3",
      "section": "Section 2",
      "actor": "deployer",
      "art50_anchor": ["50(4)", "50(5)"],
      "applicability": "deployer选择参与EU图标、audio-only方案和交互式第二层等任务组工作时",
      "signatory_effect": "encouraged措施，即使签署Section 2亦属推荐",
      "level": "encouraged",
      "will_required": false,
      "expansion_required": false,
      "required_points": ["task_force_participation", "icon_iteration", "interactive_second_layer"],
      "modality": ["text", "image", "audio", "video"],
      "recommendation_theme": "disclosure-standardisation",
      "source_anchor": "L1504-L1528"
    },
    {
      "id": "S2-C2-M2.1",
      "section": "Section 2",
      "actor": "deployer",
      "art50_anchor": ["50(4)", "50(5)"],
      "applicability": "deployer需建立与其规模相称的披露合规流程和文档",
      "signatory_effect": "签署Section 2时为will准则承诺；公开说明为encouraged",
      "level": "will+encouraged",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["compliance_process_documentation", "design_placement_verification", "media_existing_procedures"],
      "modality": ["all"],
      "recommendation_theme": "disclosure-governance",
      "source_anchor": "L1535-L1560"
    },
    {
      "id": "S2-C2-M2.2",
      "section": "Section 2",
      "actor": "deployer",
      "art50_anchor": ["50(4)", "50(5)"],
      "applicability": "相关人员参与深度伪造或公共利益文本披露流程时",
      "signatory_effect": "签署Section 2时为will准则承诺；培训为encouraged",
      "level": "will+encouraged",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["personnel_awareness", "proportionate_resources", "training_topics"],
      "modality": ["all"],
      "recommendation_theme": "training-awareness",
      "source_anchor": "L1561-L1576"
    },
    {
      "id": "S2-C2-M2.3",
      "section": "Section 2",
      "actor": "deployer",
      "art50_anchor": ["50(4)", "50(5)"],
      "applicability": "deployer需评审披露运行、处理错误标注反馈并与主管当局合作时",
      "signatory_effect": "签署Section 2时为will准则承诺；举报渠道为encouraged",
      "level": "will+encouraged",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["internal_review", "external_feedback", "mislabel_remedy_without_delay", "authority_cooperation"],
      "modality": ["all"],
      "recommendation_theme": "review-remediation",
      "source_anchor": "L1577-L1591"
    },
    {
      "id": "S2-C3",
      "section": "Section 2",
      "actor": "deployer",
      "art50_anchor": ["50(4)", "50(5)"],
      "applicability": "深度伪造构成明显艺术、创意、讽刺、虚构或类似作品/节目时",
      "signatory_effect": "签署Section 2时，非妨碍式披露与首次接触要求为commit/will；位置选项为may",
      "level": "commit+will+may",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["non_hampering_disclosure", "m1_1_design", "first_contact", "perceivable_duration", "digital_or_offline_context_options"],
      "modality": ["image", "audio", "video", "other"],
      "recommendation_theme": "artistic-work-disclosure",
      "source_anchor": "L1592-L1621"
    },
    {
      "id": "S2-C4",
      "section": "Section 2",
      "actor": "deployer",
      "art50_anchor": ["50(4)"],
      "applicability": "deployer发布有关公共利益事项的AI生成或篡改文本，并评估媒体服务提供者编辑例外或其他主体的发布前人工审核政策时",
      "signatory_effect": "签署Section 2时，其他签署方承担commit及will信息披露要求；媒体服务提供者可依既有编辑程序",
      "level": "may+commit+will",
      "will_required": true,
      "expansion_required": false,
      "required_points": ["media_editorial_exception", "prepublication_human_review_policy", "editorial_responsible_person", "responsible_person_details", "organisation_staffing_summary", "public_contact"],
      "modality": ["text"],
      "recommendation_theme": "editorial-governance",
      "source_anchor": "L1622-L1651"
    }
  ]
}
```
<!-- COP_CASE_REGISTRY_JSON_END -->

## 五、构建记录

- 源：`references/sources/EU-CoP-Transparency-Code-of-Practice.txt`（114,472 B / 1,692 L）＋同名 PDF（1,213,943 B）；规则库 last_verified 2026-09-05。
- 报告逐字引用前，仍须按锚点回对原文。
- 勘误（2026-09-18）：Section 2 两个**分组标题**原误写为 `### S2-C1`／`### S2-C2`，与构建规则 §五「Section 2：C1（M1.1–1.3）、C2（M2.1–2.3）、C3（Commitment 级）、C4（Commitment 级）」及 §三「仅 Commitment 级条款（无 Measure 编号者）编号写『S2-C3』」不符——分组标题应与 Section 1 一致写 `C1`／`C2`。已改回；`cop_digest_verify.py` 的 C-03 报「未登记锚点」即此漂移的检出信号（分组标题本无独立锚点，其锚点归属子 Measure）。**判据：标题含 `S2-` 前缀者必为无 Measure 子项的叶子条款。**
