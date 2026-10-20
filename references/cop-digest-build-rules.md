# cop-digest 构建规则

> 定位：本文件是 `references/cop-digest.md`（CoP 摘要）的构建规则与质量门禁，供维护期重建摘要时执行。2026-09-14 已随 cop-digest.md 一并合入 skill；第九节为同日已执行的运行时接入清单（13 项，存档备查）。

## 一、定位与用途

- 目的：将《AI生成内容透明度行为准则》整理为可按需检索的摘要，保留全部适用措施、原文锚点与层级信息。
- 保真原则：digest 是**全量**摘要（每个 Measure 一条，不挑拣），不是速查表；逐字引用某 Measure 全文或 digest 未覆盖处，运行时按行号锚点回原文定位读取。
- 与 eu-rules.md 的关系：三层描述同一批 Measure，层级链固定为——**原文 PDF ＞ digest ＞ eu-rules.md §四速查表**。eu-rules 速查表定位为纯导航/编号索引（仅 Commitment–Measure 编号与一句话主题，不承载要点、不作层级判定依据）；逐条展开以 digest 为准，再往上是按锚点回原文；禁止出现第四处独立副本，也禁止速查表回填要点形成与 digest 的双源。

## 二、权威源与引文规则

1. 权威顺序：官方 PDF（`EU-CoP-Transparency-Code-of-Practice.pdf`）＞ txt 抽取件。digest 关键句以 txt 为工作底本，存疑处（断词、缺词）回 PDF 核对。
2. txt 为 PDF 抽取件，存在版式伪影，允许且仅允许以下**版式层清洗**：①行断连字（如「AI -generated」→「AI-generated」）；②页码行与空行剔除；③单词内断行拼接（如「202 7」→「2027」）。**禁止**任何措辞改写、同义替换、语序调整。
3. 每条关键句须能在 txt 中按清洗规则还原对上；无法还原的（抽取缺词）不引用，改转述并标注。
4. 层级动词（will / encouraged / may / commit / shall）**照录原文**，不翻译进关键句；中文要点里转述时按 glossary 口径。

## 三、条目结构模板

每个 Measure 一条，六字段：

```
#### M<编号> <英文标题>（<中文译名，按 glossary>）〔层级〕
- 层级：will；子层级：Sub-measure X（will/may/encouraged）；条件式注明「若…则」
- 要点：<1–3 句中文，含适用例外与关键数值/日期>
- 关键句："<英文原句，可截取，逐字>"
- Art.50：<对应条款>
- 原文锚点：txt L<起始行>–L<结束行>
```

Commitment 级条款（Section 2 的 C3/C4，无 Measure 编号）按同结构单列，编号写「S2-C3」。**分组标题（下含 Measure 子项的 C1/C2）不写 `S2-` 前缀，与 Section 1 一致写 `C1`／`C2`**——即判据为「标题带 `S2-` 前缀者必为无子项的叶子条款」；分组标题本无独立锚点，其锚点归属子 Measure（`cop_digest_verify.py` C-03 会对误加前缀的分组标题报「未登记锚点」）。

## 四、层级标签提取规则

1. 以 Measure 正文首个操作性动词为准：will＝签署方为满足 Art. 50(2)/(4)/(5) 合规而必须执行、受市场监管当局监测；encouraged＝自愿但推荐；may＝自愿或提供实现弹性（两节开头均有此定义，逐字照录不译）。
2. 混合 Measure 记「主层级＋子层级」，如 M1.1 主 will，Sub-measure 1.1.3 may。
3. 条件式义务写「will（若实现X，则…）」，如 M2.2 取证检测：may；若实现，则 will（满足 2.1.3 隐私与 2.3 披露）。
4. encouraged 与 may 并存时分别列出，不合并为「可选」。

## 五、完整性清单（重建后必对）

- Section 1（17）：C1（M1.1–1.4）、C2（M2.1–2.4）、C3（M3.1–3.5）、C4（M4.1–4.4）。
- Section 2（6＋2）：C1（M1.1–1.3）、C2（M2.1–2.3）、C3（Commitment 级）、C4（Commitment 级）。
- 个案适用与覆盖注册表：`cop_case_registry/1` 必须与上述25个叶子单元一一对应，ID分别采用 `S1-Cx-Mx.x`、`S2-Cx-Mx.x`、`S2-C3`、`S2-C4`；不得遗漏、重复或增加不存在的规则。每条至少保留 `id/section/actor/art50_anchor/applicability/signatory_effect/level/will_required/expansion_required/required_points/modality/recommendation_theme/source_anchor`。
- Annex 1：EU 图标三款（AI+GENERATED / AI+MODIFIED / 基础款）一句话记录。
- 关键节点核对（抽查门禁）：2027-02-02 互操作节点（M3.4(c)）、月活<100 万检测服务收费例外（免费义务的例外在 S1 M2.1.1）、自由文本 200 token 水印门槛（M1.1.2 与 Glossary very short text）、published text 放置位置（colophon/头条附近，S2 M1.2.2(f)）、艺术作品例外（S2-C3）、媒体服务提供者编辑例外（S2-C4，Reg (EU) 2024/1083）。

## 六、质量门禁

1. 重建后逐 Measure 与原文锚点区间比对一遍（防串行、防漏段）。
2. 抽查率 ≥20%（≥5 条）的关键句逐字回对 txt；关键节点（第五节清单）100% 回对。
3. 中文要点不得引入原文没有的数值、日期、主体；转述标「要旨归纳」不需要——digest 的「要点」字段本身即转述字段，但数字与层级必须照原文。
4. digest 头部必须登记所依 txt 的 MD5 与总行数；重建时先对 sources txt 重新计算哈希，与头部登记不一致（txt 变更/重新抽取）即视为全部行号锚点失效，须重建 digest 并重核全部锚点后方可使用，禁止沿用旧锚点静默漂移。
5. `scripts/cop_digest_verify.py` 同时校验固定注册表的25项ID、必填字段、原文锚点与正文单元一致性；注册表校验未通过时不得生成或交付欧盟报告。

## 七、重建触发

- 90 天复核命中 CoP 监控点；CoP 官方修订/补充（含 task force 产出：交互式第二层、audio-only 图标等 Annex 1 预告项）→ 重建 digest 并复核锚点。
- **txt 变更即重建**：sources txt 重新抽取（重新抽取或重新下载）或 MD5 与 digest 头部登记不符 → 行号锚点整体失效且不会报错（静默漂移），必须重建 digest、重核全部锚点并更新头部 md5/行数登记；此触发并入 validity-checklist.md 的 CoP 监控点。
- digest 头部只记录源文件、源文件校验值、行数与清洗说明，不记录构建人等个人信息。

## 八、术语门禁（强制）

digest 的中文措辞与 skill 报告正文执行同一术语纪律，构建/重建时逐词过检：

1. **译法以 `references/glossary.md` 为唯一依据**。高频禁译项：robustness＝稳健性（禁「鲁棒性」）；EU marking＝标记（「标识」仅用于中国《标识办法》法定语境，跨法域混用会造成概念污染）；EU manipulated＝篡改（非「操纵」）；EU provenance information＝来源信息（「溯源」仅用于中国 GB 45438）；published text＝有关公共利益事项而发布的文本（非「公共议题文本」）；AI literacy＝人工智能素养；labelling＝标注（EU Section 2）；生成式人工智能系统（不缩作「AI 系统」）。
   - **AI system 的译法按语境分流**：Art. 3(1) 定义项及 Art. 50(1)/(2) 条文里的一般「AI system」译**人工智能系统**；仅在确指生成式系统（缩写自「生成式人工智能系统」，多见于 Art. 50(2)、CoP）时译**生成式人工智能系统**。不得一律套用后者——判别式系统（如内容检测工具）被写成「生成式人工智能系统」会构成定性错误。
   - **「GenAI系统」属混合简写**，应作「生成式人工智能系统」（法定简写可首现括注英文），不得以「GenAI系统」直接在中文正文里充当译名。
2. **机构名首现全称**：AI Office＝人工智能办公室、AI Board＝人工智能委员会，首现附英文。
3. **术语一致性回检**：写入后全文扫描禁用词表（鲁棒／操纵／溯源信息／AI 素养／公共议题／AI 系统／GenAI系统／机器可读标识），残留＝0 方可定稿；「标识」仅允许出现在「模型标识符（identifier）」等中国法语境。
   - 脚本侧：`scripts/cop_digest_verify.py` 的 `C-06` 与报告术语门禁共用同一张词表（`scripts/lint_terms.py` 的 `RULES`），改词表两处同步；digest 是纯文本、不适用报告的声明区／批注节豁免。
   - 报告侧（`scripts/lint_terms.py`）的 W 级检查**不扫报头声明区与批注节**，因为范围声明是强制照搬原文、批注节是判断过程留痕；口径见 `references/reporting-rules.md` §三.4。
4. **运行时联动**：若 glossary 更新译法，digest 同步重建（列入第七节重建触发）。
5. **禁止第三译法**：digest 与 eu-rules.md 速查表、报告正文之间发现译法冲突时，以 glossary 为准并回改冲突文件。
