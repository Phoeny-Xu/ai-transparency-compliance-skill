# AI透明度三地合规术语对照表（内置终稿）

> 用途：本表是 `ai-transparency-compliance` skill 中文正文转述的**唯一译法依据**。报告正文一律以本表为准，未收录术语用法律文献通行译法、禁用工程音译（如「鲁棒性」）。脚注一律引官方原文（不在本表范围）。
> 标注规则：〔法定术语〕= 中国法/欧盟条例固有表述，保持原样不翻译；〔通行〕= 法律文献/官方或权威译文通行译法；〔禁用〕= 工程音译，禁用。
> 校准依据：v1 初稿 → v2 据 4 篇译文（欧盟简化综合条例官方版、AI内容透明度行为准则第二版草稿、Art.50指南草案、加州AI透明法案全文）校准 → v3 据 3 篇译文（欧盟AI生成内容透明度行为准则合规重点解析上/下、加州AI透明度法案演进 SB 942→AB 853→SB 100）补充校准。后两篇为双语长文，可直接对勘英文原词与中文对应。

## 一、欧盟 AI Act（Reg. (EU) 2024/1689）

| 英文原文 | 建议中文 | 性质/依据 |
| --- | --- | --- |
| AI system | 人工智能系统 | 〔法定术语〕Art. 3(1) 定义 |
| provider | 提供者 | 〔通行〕Art. 3(2)；双语行为准则解析全篇用"生成式人工智能系统提供者" |
| deployer | 部署者 | 〔通行〕Art. 3(4)；双语解析用"生成式人工智能系统部署者"，取"部署者"（与信通院等通行中译一致） |
| authorized representative | 授权代表 | 〔通行〕Art. 3(3) |
| importer / distributor | 进口商 / 分销者 | 〔通行〕Art. 3(5)/(6) |
| downstream provider | 下游提供者 | 〔通行〕双语行为准则解析"履行合规义务的下游提供者" |
| general-purpose AI model (GPAI) | 通用人工智能模型 | 〔法定术语〕Art. 3(63)；译文作"通用人工智能（GPAI）模型/系统" |
| GPAI model with systemic risk | 具有系统性风险的通用人工智能模型 | 〔法定术语〕Art. 3(64) |
| transparency obligation | 透明度义务 | 〔通行〕Art. 50 标题 |
| disclosure | 披露 | 〔通行〕向用户传达内容来源/AI属性的行为；含 latent disclosure（隐式披露）、manifest disclosure（显式披露）、user disclosure（用户披露） |
| latent disclosure | 隐式披露 | 〔通行〕对应 manifest disclosure（显式披露）。法定术语 disclosure 本义为"披露"，统一用"隐式披露/显式披露"；"标记"(marking) 为独立概念，单列于本节（对应 Art. 50(2) 机器可读标记），不可混淆 |
| manifest disclosure | 显式披露 | 〔通行〕与 latent disclosure 相对；AB 853 已删除"提供显式披露选项"义务 |
| machine-readable marking / format | 机器可读标记 / 机器可读格式 | 〔通行〕Art. 50(2)；双语解析"实施机器可读的标记技术""确保标记不可移除" |
| marking | 标记 | 〔通行〕双语解析高频"标记"（机器可读标记/可感知标记/不可移除的标记） |
| labelling / labeling | 标注 | 〔通行〕双语解析"标注深度伪造和……文本的义务"（Section 2: Labelling） |
| watermark | 水印 | 〔通行〕Art. 50(2)；双语解析区分"不可感知水印"与"公众可读水印" |
| deep fake | 深度伪造 | 〔通行〕双语行为准则解析 x30 均用"深度伪造"，与 Art.3(60) 定义术语一致。⚠️ **不可与中国"深度合成内容"并列等同**，见下方专条 |
| deep fake（Art. 3(60) 定义） | 由人工智能生成或篡改的图像、音频或视频内容，这些内容与现有的人员、物体、地点、实体或事件相似，会让人误以为是实在的或真实的 | 〔法定术语〕定义本身。注意其范围仅限图像/音频/视频，且须"与真实人/物/地/实体/事件相似、令人误信为真实" |
| deep fake ☎ 与中国法关系 | 欧盟"深度伪造"≠ 中国"深度合成内容"，二者不直接等同 | 〔说明〕中国《互联网信息服务深度合成管理规定》第17条还覆盖文本、沉浸式拟真场景等情形；欧盟 deep fake 仅限音视图且须近似真实，而欧盟对文本另有 Art. 50(1)/(4) 专门规则。**不宜以"谁宽谁窄"简单概括，报告中涉及二者时分别引用各自定义、不得直接画等号** |
| emotion recognition | 情感识别 | 〔通行〕Art. 50(3)；部分译文作"情绪识别" |
| biometric categorisation | 生物识别分类 | 〔通行〕Art. 50(3) |
| synthetic content | 合成内容 | 〔通行〕Art. 50 |
| AI-generated or manipulated content | AI生成或篡改内容 | 〔通行〕双语解析统一"AI生成或篡改（AI-generated or manipulated）" |
| published text / text published on matters of public interest | 有关公共利益事项而发布的文本 | 〔通行〕Art. 50(4) deployer 义务对象；双语解析将"Disclosure of Deep Fakes and Published Text"译作"披露深度伪造与有关公共利益事项而发布的文本"，"published text"系其简称 |
| generative AI system | 生成式人工智能系统 | 〔法定术语〕Art. 3(1) 释义 |
| high-risk | 高风险 | 〔法定术语〕Annex III |
| conformity assessment | 合格评定 | 〔法定术语〕Chapter III |
| notified body | 公告机构 | 〔法定术语〕 |
| Code of Practice | 行为准则 | 〔法定术语〕Art. 56；"可证明合规"非"合规推定" |
| AI Office | 人工智能办公室 | 〔法定术语〕 |
| AI literacy | 人工智能素养 | 〔通行〕Art. 4 |
| digital signature | 数字签名 | 〔通行〕双语解析"数字签名元数据" |
| provenance / provenance information | 来源 / 来源信息 | 〔通行〕欧盟行为准则用"来源信息透明度（Transparency of the Provenance Information）"，译"来源信息"；与中国"溯源信息"、加州"来源数据"分属不同法域，勿混 |
| source chain | 来源链 | 〔通行〕行为准则"来源链透明度" |
| detect / detection | 检测 | 〔通行〕双语解析"检测AI生成或篡改内容""AI检测工具" |
| human review | 人工审核 | 〔通行〕双语解析"有关公共利益事项而发布的文本的人工审核" |
| editorial control | 编辑控制 | 〔通行〕双语解析同上"编辑控制" |
| robustness | 稳健性 | 〔通行〕Art. 15；**禁用"鲁棒性"**。双语解析高频"稳健性/稳健"（有效性、互操作性、稳健性、可靠性）佐证 |
| reliability | 可靠性 | 〔通行〕双语解析与 robustness 并列"reliable" |
| interoperability | 互操作性 | 〔通行〕双语解析"interoperable" |
| effectiveness | 有效性 | 〔通行〕双语解析"effective" |
| accuracy | 准确性 | 〔通行〕Art. 15 |
| cybersecurity | 网络安全 | 〔通行〕Art. 15 |

## 二、加州（B&P Code §§22757–22757.6，SB 942 经 AB 853 修正；SB 1000 草案待定）

| 英文原文 | 建议中文 | 性质/依据 |
| --- | --- | --- |
| covered provider | 受管辖的提供者 | 〔通行〕§22757.1(d)；用户提供译文作"受管辖的提供者" |
| large online platform | 大型网络平台 | 〔通行〕§22757.3.1；加州演进文章 x3 译"大型网络平台"，取此（非"大型在线平台"） |
| GenAI hosting platform | 生成式人工智能系统托管平台 | 〔通行〕§22757.1(g)；演进文章作"托管生成式人工智能系统的平台" |
| generative AI system | 生成式人工智能系统 | 〔法定术语〕§22757.1 |
| synthetic content | 合成内容 | 〔通行〕§22757.1(f) |
| latent disclosure | 隐式披露 | 〔通行〕§22757.3(b)；演进文章译作"隐式标记"，侧重嵌入标记机制，本报告统一用"隐式披露" |
| manifest disclosure | 显式披露 | 〔通行〕与 latent disclosure 相对；演进文章译作"显式标记"；AB 853 已删除"提供显式披露选项"义务 |
| provenance data | 来源数据 | 〔通行〕§22757.1(j)；演进文章 x11 译"来源数据"（非"溯源数据"）；中国 GB 45438 的"溯源数据"为另一法定术语 |
| personal provenance data | 个人来源数据 | 〔法定术语〕§22757.1 定义，演进文章专条译"个人来源数据" |
| watermark | 水印 | 〔通行〕§22757.3(b) |
| digital signature | 数字签名 | 〔通行〕§22757.1 定义 |
| metadata | 元数据 | 〔通行〕§22757.1(o) |
| AI detection tool / detection interface | AI检测工具 / 检测接口 | 〔通行〕§22757.3(a) |
| capture device | 采集设备 | 〔通行〕§22757.1(b)；演进文章译"采集设备"（非"摄录设备"） |
| capture device manufacturer | 采集设备制造商 | 〔通行〕§22757.3.3；演进文章译"采集设备制造商" |
| clear and conspicuous | 明确且显著 | 〔通行〕§22757.3 |
| materially alter | 实质性修改 | 〔通行〕§22757.1(f) |
| Attorney General | 检察长 | 〔法定术语〕§22757.4 |

## 三、中国（深度合成规定 / 暂行办法 / 标识办法 / GB 45438-2025）

| 原文表述 | 建议中文 | 性质/依据 |
| --- | --- | --- |
| 深度合成服务提供者 | 深度合成服务提供者 | 〔法定术语〕深度合成规定第23条，保持原样 |
| 深度合成服务技术支持者 | 深度合成服务技术支持者 | 〔法定术语〕第23条 |
| 生成式人工智能服务提供者 | 生成式人工智能服务提供者 | 〔法定术语〕暂行办法第22条 |
| 网络信息内容传播服务提供者 | 网络信息内容传播服务提供者 | 〔法定术语〕标识办法第6条 |
| 应用程序分发平台 | 应用程序分发平台 | 〔法定术语〕深度合成规定第13条 |
| 显著标识 | 显著标识 | 〔法定术语〕深度合成规定第17条 |
| 隐式标识 | 隐式标识 | 〔法定术语〕深度合成规定第16条 |
| 生成合成内容 | 生成合成内容 | 〔法定术语〕标识办法 |
| 深度合成内容 | 深度合成内容 | 〔法定术语〕深度合成规定；⚠️ 与欧盟"深度伪造（deep fake）"概念相关但**不等同**——中国法还覆盖文本、沉浸式拟真场景（第17条），欧盟 deep fake 仅限音视图且须近似真实 |
| 舆论属性或社会动员能力 | 舆论属性或社会动员能力 | 〔法定术语〕安全评估规定第2条 |
| 溯源数据 / 元数据 | 溯源数据 / 元数据 | 〔法定术语〕GB 45438-2025；注：此"溯源数据"为中国法独立术语，与加州 provenance data 译"来源数据"、欧盟 provenance information 译"来源信息"分属不同法域，勿混用 |

## 四、通用术语

| 英文原文 | 建议中文 | 性质/依据 |
| --- | --- | --- |
| transparency | 透明度 | 〔通行〕 |
| disclosure | 披露 | 〔通行〕见第一节 latent/manifest disclosure |
| marking | 标记 | 〔通行〕嵌入内容的标识（机器可读/可感知/不可移除） |
| labelling | 标注 | 〔通行〕对内容打标/标注来源的行为 |
| detect / detection | 检测 | 〔通行〕 |
| robustness | 稳健性 | 〔通行〕；同欧盟，禁用"鲁棒性" |
| reliability | 可靠性 | 〔通行〕 |
| interoperability | 互操作性 | 〔通行〕 |
| effectiveness | 有效性 | 〔通行〕 |
| synthetic content | 合成内容 | 〔通行〕 |
| watermark | 水印 | 〔通行〕 |
| machine-readable | 机器可读 | 〔通行〕 |
| provenance | 来源（欧盟/加州）｜溯源（中国） | 〔通行〕按法域分流：欧盟 provenance information→来源信息，加州 provenance data→来源数据，中国→溯源信息/溯源数据 |

---

### 校准要点（据 3 篇新译文）

1. **深度伪造更正**：双语行为准则解析 x30 一致用"深度伪造"，据 Art. 3(60) 定义；明确欧盟 deep fake 不可与中国深度合成内容并列等同（中国第17条还含文本、沉浸式拟真场景）。
2. **latent / manifest disclosure 译法**：latent disclosure→隐式披露，manifest disclosure→显式披露。以法定术语 disclosure 本义"披露"为准、统一用"隐式披露/显式披露"；"标记"(marking) 为独立术语（对应 Art. 50(2) 机器可读标记），不与披露混淆。
3. **公共利益文本**：published text / text published on matters of public interest→有关公共利益事项而发布的文本（Art. 50(4) deployer 义务对象）。
4. **AI生成或操纵→AI生成或篡改**：双语解析统一"AI生成或篡改（AI-generated or manipulated）"。
5. **新增术语（双语解析高频词）**：标记 marking、标注 labelling、检测 detect、来源信息 provenance information（与加州来源数据/中国溯源信息分流）、个人来源数据 personal provenance data（加州）、可靠性 reliability、互操作性 interoperability、有效性 effectiveness、下游提供者 downstream provider、人工审核 human review、编辑控制 editorial control、披露 disclosure。
6. **加州专属更正**：large online platform→大型网络平台、capture device→采集设备（非摄录设备）、provenance data→来源数据（非溯源数据）。
