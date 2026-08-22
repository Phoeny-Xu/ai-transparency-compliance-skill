# sources/ — 官方原件目录（黄金原件，供运行时直接核对原文）

> 用途：规则库（cn/eu/ca-rules.md）内容的官方原文依据。引用法条前如需复核原文，直接读本目录文件（PDF用`pypdf`提取；`fitz`/`pymupdf`在部分Windows环境可能因DLL加载策略被拦截，优先用`pypdf`，Windows下仍建议设`PYTHONUTF8=1`）。
> 原则：本目录只放官方一手文本，不放二手解读。

## 中国大陆

| 文件 | 文件全称 | 来源 | 入库日期 |
|------|----------|------|----------|
| CN-GB45438-2025.pdf | 《网络安全技术 人工智能生成合成内容标识方法》（强制性国标） | 用户提供原件（2026-08-08）；公开复核渠道：std.samr.gov.cn | 2026-08-08 |

（暂行办法、标识办法、深度合成规定为gov.cn网页文本，已全文提取进cn-rules.md；公开URL见cn-rules.md头部。）

## 欧盟

| 文件 | 文件全称 | 来源 | 入库日期 |
|------|----------|------|----------|
| EU-AIAct-Art50-excerpt.md | Regulation (EU) 2024/1689（AI Act）Article 50逐字原文excerpt | 用户提供原文；复核渠道：EUR-Lex ELI reg/2024/1689/oj | 2026-08-12 |
| EU-GPAI-Guidelines-C2025-7719-final.pdf | Commission Guidelines on the scope of the obligations for providers of general-purpose AI models（C(2025) 7719 final，2025-11-19） | 用户提供原件；公开渠道：digital-strategy.ec.europa.eu/en/library/guidelines-scope-obligations-providers-general-purpose-ai-models-under-ai-act | 2026-08-19 |
| EU-CoP-Transparency-Code-of-Practice.pdf | Code of Practice on Transparency of AI-generated content（2026-06-10发布） | ec.europa.eu/newsroom/dae/redirection/document/129555 | 2026-08-08 |
| EU-Digital-Omnibus-Reg-2026-1744.pdf | Regulation (EU) 2026/1744（Digital Omnibus on AI，修订AI Act） | EUR-Lex OJ L, 24.7.2026, ELI: reg/2026/1744/oj | 2026-08-08 |
| EU-Art50-Guidelines-C2026-5054.pdf | Commission Guidelines on Art. 50 transparency obligations（C(2026) 5054附件，内容已批准，待全语种正式通过） | 用户提供原件；公开渠道：digital-strategy.ec.europa.eu | 2026-08-08 |
| EU-Art50-Guidelines-Approval-Communication.pdf | Communication C(2026) 5054（批准指南内容，20.7.2026） | 用户提供原件 | 2026-08-08 |
| EU-CoP-Commission-Opinion-C2026-4839.pdf | Commission Opinion C(2026) 4839（8.7.2026，行为准则充分性评估：充分） | 用户提供原件；公开渠道：digital-strategy.ec.europa.eu | 2026-08-08 |
| EU-CoP-AIBoard-Adequacy-Conclusion.pdf | AI Board充分性评估结论（准则Section 1/2均充分覆盖Art. 50(2)(4)(5)） | 用户提供原件 | 2026-08-08 |

（AI Act主条例Reg. (EU) 2024/1689官方文本未打包（144页OJ合订本过大），复核渠道：EUR-Lex ELI reg/2024/1689/oj。**Art. 50逐字原文已单独入库为 EU-AIAct-Art50-excerpt.md**，脚注引用Art. 50时优先取该文件。）

## 加州

| 文件 | 文件全称 | 来源 | 入库日期 |
|------|----------|------|----------|
| CA-SB942-chaptered.md | SB 942 (2024, Ch. 291) California AI Transparency Act签署版全文 | leginfo billTextClient | 2026-08-08 |
| CA-AB853-chaptered.md | AB 853 (2025, Ch. 674)签署版全文（修正案，非清洁版） | leginfo billTextClient | 2026-08-08 |

> 加州合并阅读规则：AB 853修订/新增条款从其为准；SB 942未被触及条款继续有效。合并结论见ca-rules.md。
