#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lint_terms.py —— 术语与禁用词门禁（L3 的可执行化身）

定位
----
`references/glossary.md` 是中文转述的**唯一译法依据**（SKILL.md L3）；`cop-digest-build-rules.md`
§八另给出一张禁用词表。两者过去都只以散文纪律存在，靠 agent 每轮自觉执行。本脚本把它们
落成可执行的词表扫描器：一次定义、全局执行。

三类检查
--------
1. **禁用词**（E/W 分级）——工程音译与跨法域污染词，如「鲁棒」→「稳健性」。
2. **跨法域污染**——「标识」仅限中国《标识办法》语境；欧盟 writing 用「标记/披露」。
3. **译法一致性**——同一概念在报告内出现两种译法（如「大型网络平台」与「大型在线平台」并存）。

扫描范围（三层，2026-09-15 定）
------------------------------
启发式词表若全文无差别扫射，必然与报告的结构性规则打架（案例16-18 矛盾注入轮暴露三处）：

- **报头 `>` 声明块**：模板强制照搬或元数据（生成日期／法规时效声明／依据／范围声明／
  临近节点提示），**免于 W 级检查**。理由：范围声明原文里就含「溯源数据」（中国 GB 45438
  法定术语），对其中用词报错，等于要求 agent 违反「范围声明原样照搬」。
  范围声明既可写成 `>` 块、也可写成普通段落（modeA-report-template 两种都允许），故按内容信号
  识别而非只认 `>` 前缀。边界与 E-04 共用同一「首个二级标题」分界（`check_report.header_boundary`）。
  注：报头区的**要点概览、未覆盖维度转介卡**系自主撰写，仍受检查。
- **批注节**：判断过程留痕（交付为 Word 批注），免于 W 级检查。与「去个性化」允许批注节
  出现问卷编号同一逻辑；**E-20 硬禁用词仍全文生效，批注节亦然**。
- **正文**：全部检查。

硬约束
------
只读、不改稿（同 check_report.py：自动替换会改坏法条原文与脚注引文，违反 L1）。

用法
----
    python lint_terms.py 报告.md [--jurisdictions CN,EU,CA]
    python lint_terms.py 报告.md --no-waivers   # 校准用：忽略豁免，按原样列出全部命中
    python lint_terms.py --list

`--jurisdictions` 限制**法域节**（CN／EU／CA）的扫描范围，范围外的法域节整套跳过；
与 `check_report --jurisdictions` 同义（S-3，2026-09-19 落地：此前该参数被接收但未生效）。

退出码：0=通过；1=有 E；2=仅 W。行内豁免语法与 check_report.py 相同
（`<!-- lint:ignore W-20 -->` / `<!-- lint:ignore-file W-21 -->`）。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _configure_utf8_output() -> None:
    """Windows 默认 GBK 控制台也必须能输出中文诊断。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass


_configure_utf8_output()

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_report import (  # noqa: E402  （同目录同批发布，复用豁免与解析逻辑）
    HEADING_RE,
    WAIVER_RE,
    collect_waivers,
    header_boundary,
    read_text,
    scan_structure,
)
from check_report import Finding  # noqa: E402

CATALOG: list[tuple[str, str, str]] = [
    ("E-20", "E", "无工程音译「鲁棒」（L3 glossary 硬禁用；全文含批注节）"),
    ("W-20", "W", "禁用词/非推荐译法（操纵/溯源信息/AI素养/公共议题/AI系统/GenAI系统/机器可读标识）"),
    ("W-21", "W", "「标识」限中国语境，欧盟/加州节应用「标记/披露」"),
    ("W-22", "W", "同一概念译法一致（无两种译法并存；仅正文，围栏/声明块/批注节不计）"),
    ("W-00", "W", "存在行内豁免（留痕提示）"),
]

LEVEL_BY_CODE = {c: l for c, l, _ in CATALOG}


# ---------------------------------------------------------------------------
# 词表规则（数据结构化，便于逐条声明语境与豁免）
# ---------------------------------------------------------------------------

# 中国法锚点：行内出现任一，即认为该行的用词处在中国法语境（B8-2 事实要件、备案/安评等）
CN_ANCHORS = ("备案", "安评", "安全评估", "事实检验", "境内", "中国", "深度合成", "标识办法", "GB 45438")

# 报头声明信号：模板强制照搬或元数据的行。范围声明既可写成 `>` 块，也可写成普通段落
# （modeA-report-template 明确两种都允许），故不能只认 `>` 前缀，须按内容识别。
DECL_SIGNALS = (
    "生成日期",
    "效力核验日期",
    "法规时效声明",
    "依据：",
    "范围声明",
    "本清单覆盖",
    "本评估覆盖",
    "临近节点提示",
)

# W-21 的判定口径（「标识」的术语性用法）
# 「标识」在中国《标识办法》语境是法定术语，在欧盟/加州节出现多为跨法域污染；
# 但汉语中「标识」还可作动词（标识为AI生成／标识分工／界面标识／持续标识），
# 案例13-15 的 4 处命中全属此类误报。故收敛为：仅带标记术语前缀、或后接名词性成分时命中。
BS_TERM_PREFIX = ("显式", "隐式", "显著", "机器可读", "可感知", "数字水印", "生成合成内容")
BS_TERM_SUFFIX = ("义务", "要求", "方式", "技术", "措施", "制度", "体系", "机制", "不得", "应当", "（", "(")

# 生成式语境标记（用于「AI系统」建议译法的分流）。
# 只在命中词的紧邻窗口内判定，不能整行判定：一份报告里同一行常同时讨论生成式与判别式系统，
# 整行判定会把「判别式检测系统属AI系统（Art. 3(1)）」也建议成「生成式人工智能系统」。
GENAI_MARKERS = re.compile(r"生成合成|生成式|生成或篡改|生成、篡改|行为准则|CoP|人工智能生成合成")
GENAI_WINDOW_BEFORE = 30
GENAI_WINDOW_AFTER = 10


@dataclass(frozen=True)
class BanRule:
    """一条禁用词规则。

    pattern          —— 匹配用
    display          —— 报错信息中的词面（正则不便直显）
    better           —— 默认建议译法
    code / basis     —— 级别与依据
    skip_sections    —— 命中即豁免的节（节标签 CN／EU／CA／ANN／GEN）
    exempt_keywords  —— 行内出现任一即豁免（语境豁免）
    bilingual_exempt —— 行内出现该英文原文即豁免（双语对照行）
    contextual       —— (正则, 建议译法) 列表，按语境分流建议（在命中词紧邻窗口内判定）
    """

    pattern: re.Pattern[str]
    display: str
    better: str
    code: str
    basis: str
    skip_sections: tuple[str, ...] = ()
    exempt_keywords: tuple[str, ...] = ()
    bilingual_exempt: str | None = None
    contextual: tuple[tuple[re.Pattern[str], str], ...] = field(default=())

    def suggestion(self, line: str, match: re.Match[str] | None = None) -> str:
        if match is not None and self.contextual:
            window = line[
                max(0, match.start() - GENAI_WINDOW_BEFORE) : match.end() + GENAI_WINDOW_AFTER
            ]
            for pat, better in self.contextual:
                if pat.search(window):
                    return better
        return self.better


RULES: list[BanRule] = [
    BanRule(
        pattern=re.compile(r"鲁棒"),
        display="鲁棒",
        better="稳健性",
        code="E-20",
        basis="L3／glossary：禁用工程音译（robustness）",
    ),
    BanRule(
        pattern=re.compile(r"操纵"),
        display="操纵",
        better="篡改",
        code="W-20",
        basis="glossary §一：EU manipulated 译「篡改」",
    ),
    BanRule(
        pattern=re.compile(r"溯源信息"),
        display="溯源信息",
        better="来源信息",
        code="W-20",
        basis="glossary §四：EU provenance information 分流为「来源信息」",
    ),
    BanRule(
        pattern=re.compile(r"溯源数据"),
        display="溯源数据",
        better="来源数据",
        code="W-20",
        basis="glossary §二/§四：加州 provenance data 译「来源数据」；中国 GB 45438 的「溯源数据」为另一法定术语",
    ),
    BanRule(
        pattern=re.compile(r"AI\s?素养"),
        display="AI 素养",
        better="人工智能素养",
        code="W-20",
        basis="glossary §一：AI literacy",
    ),
    BanRule(
        pattern=re.compile(r"公共议题"),
        display="公共议题",
        better="有关公共利益事项而发布的文本",
        code="W-20",
        basis="glossary §一：published text；中国 B8-2 事实检验语境为其法定用语，不在此限",
        skip_sections=("CN",),
        exempt_keywords=CN_ANCHORS,
    ),
    BanRule(
        # 负向断言避免误伤 GenAI系统／Generative AI系统 一类子串（案例16-18 轮 N1）
        pattern=re.compile(r"(?<![A-Za-z])AI\s?系统"),
        display="AI系统",
        better="人工智能系统",
        code="W-20",
        basis="glossary §一：AI system 译「人工智能系统」（Art. 3(1) 法定术语）；缩写自「生成式人工智能系统」时作后者",
        bilingual_exempt="AI system",
        contextual=((GENAI_MARKERS, "生成式人工智能系统"),),
    ),
    BanRule(
        # 修 N1 边界后，该类混合简写须独立成条，否则转为漏报（案例16-18 轮 N3）
        pattern=re.compile(r"GenAI\s?系统"),
        display="GenAI系统",
        better="生成式人工智能系统",
        code="W-20",
        basis="glossary §二/§四：generative AI system 译「生成式人工智能系统」（法定简写可首现括注英文）",
    ),
    BanRule(
        pattern=re.compile(r"机器可读标识"),
        display="机器可读标识",
        better="机器可读标记",
        code="W-20",
        basis="glossary §一：marking 译「标记」，「标识」限中国语境",
    ),
]

# 同义并存（同一概念两种译法同时出现即报警）
# 注：不列「来源数据/溯源数据」——glossary §四明定按其法域分流（欧盟来源信息／加州来源
# 数据／中国溯源数据），二者并存属正常，列作并存会必然误报。
PAIRS: list[tuple[str, str, str]] = [
    ("大型网络平台", "大型在线平台", "glossary §二：取「大型网络平台」"),
    ("采集设备", "摄录设备", "glossary §二：取「采集设备」"),
    ("隐式披露", "隐式标记", "glossary §二：本报告统一「隐式披露」"),
    ("显式披露", "显式标记", "glossary §二：本报告统一「显式披露」"),
]


# ---------------------------------------------------------------------------
# 扫描
# ---------------------------------------------------------------------------


def section_map(lines: list[str], in_fence: list[bool]) -> list[str]:
    """逐行标注所在节（CN／EU／CA／ANN／GEN）。

    按标题层级维护区间栈：法域节只在 level>=2 的标题上切换，其下的小节沿用；
    同级或更高级标题切走即回落 GEN（避免「落地建议」沿用加州语境）。
    """
    section = "GEN"
    section_level = 1
    section_of: list[str] = []
    for i, line in enumerate(lines):
        if not in_fence[i]:
            m = HEADING_RE.match(line)
            if m:
                level, t = len(m.group(1)), m.group(2)
                if level >= 2 and ("批注" in t):
                    section, section_level = "ANN", level
                elif level >= 2 and ("中国" in t or "China" in t):
                    section, section_level = "CN", level
                elif level >= 2 and ("欧盟" in t or re.search(r"\bEU\b", t)):
                    section, section_level = "EU", level
                elif level >= 2 and ("加州" in t or "California" in t):
                    section, section_level = "CA", level
                elif level <= section_level:
                    section, section_level = "GEN", level
        section_of.append(section)
    return section_of


def scan(text: str, jurisdictions: set[str] | None = None) -> list[Finding]:
    """扫描术语问题。

    `jurisdictions` 为本次范围（如 {"CN","EU","CA"}）；给定后，**法域节**（CN／EU／CA）
    内仅扫描范围内的法域，范围外的法域节整套跳过（与 `check_report --jurisdictions`
    行为对齐，S-3：此前该参数被接收但从未使用，属「看似能配、其实不生效」）。报头声明区、
    通用节（GEN）、批注节（ANN）的处理不受此参数影响。`None` 表示不限制（全扫）。
    """
    lines = text.splitlines()
    structure = scan_structure(lines)
    in_fence = structure["in_fence"]
    body_start = header_boundary(structure, len(lines))
    section_of = section_map(lines, in_fence)
    scoped = None if jurisdictions is None else {j.strip().upper() for j in jurisdictions}

    # 只移除豁免注释片段、保留同行其余内容（与 check_report 同一处理）：
    # 理由文本里的禁用词不得命中，行内豁免所在行的真实内容也不得因此免检。
    probes = [WAIVER_RE.sub("", line) for line in lines]

    findings: list[Finding] = []

    for i, line in enumerate(lines):
        if in_fence[i]:
            continue
        section = section_of[i]
        # 范围外的法域节整套跳过（S-3）：与 check_report 的 --jurisdictions 同义
        if scoped is not None and section in {"CN", "EU", "CA"} and section not in scoped:
            continue
        probe = probes[i]
        if not probe.strip():
            # 整行只剩豁免注释（文件级豁免常见形态）：无内容可查
            # 若放行扫描，理由文本里的禁用词会命中自己、被自己的豁免吞掉并计入 W-00，造成幻影计数
            continue

        # 报头声明块（`>` 块或按内容识别的声明行）系模板强制照搬／元数据，免于 W 级检查
        # （E-20 除外）。要点概览、未覆盖维度转介卡属自主撰写，不在此限。
        is_decl_block = i < body_start and (
            probe.lstrip().startswith(">") or any(sig in probe for sig in DECL_SIGNALS)
        )
        w_level_ok = (not is_decl_block) and section != "ANN"

        for rule in RULES:
            if rule.code != "E-20" and not w_level_ok:
                continue
            m = rule.pattern.search(probe)
            if not m:
                continue
            if section in rule.skip_sections:
                continue
            if any(k in probe for k in rule.exempt_keywords):
                continue
            if rule.bilingual_exempt and rule.bilingual_exempt in probe:
                continue
            ctx = probe[max(0, m.start() - 6) : m.end() + 8]
            findings.append(
                Finding(
                    rule.code,
                    i + 1,
                    f"「{rule.display}」应为「{rule.suggestion(probe, m)}」（{rule.basis}）",
                    ctx,
                )
            )

    # ---- 跨法域「标识」污染 ----
    for i, line in enumerate(lines):
        if section_of[i] not in {"EU", "CA"}:
            continue
        # 范围外的法域节整套跳过（S-3）
        if scoped is not None and section_of[i] not in scoped:
            continue
        if in_fence[i]:
            continue
        probe = probes[i]
        # 引用中国法名（《…标识办法》）、技术术语（模型标识符）时「标识」正当
        if "标识符" in probe or "标识办法" in probe or "GB 45438" in probe:
            continue
        # 跨法域对照行（如「与欧盟CoP、中国侧条件式标识共用底座」）：行内指称的是中国概念，
        # 不能因所在节是欧盟/加州即判为污染（案例16-18 轮 V2-06 的真实成因）
        if "中国" in probe:
            continue
        for m in re.finditer(r"标识", probe):
            before = probe[max(0, m.start() - 5) : m.start()]
            after = probe[m.end() : m.end() + 3]
            if not (
                any(before.endswith(p) for p in BS_TERM_PREFIX)
                or any(after.startswith(s) for s in BS_TERM_SUFFIX)
            ):
                continue  # 动词性用法（标识为AI生成／标识分工／界面标识）不属术语污染
            ctx = probe[max(0, m.start() - 6) : m.end() + 8]
            findings.append(
                Finding("W-21", i + 1, "欧盟/加州节出现「标识」，应用「标记」或「披露」（glossary §一）", ctx)
            )
            break

    # ---- 译法一致性（N-3：仅正文；围栏内示例、报头照搬声明块、批注节均不计入）----
    # 原实现直接扫原始 `text`，会把代码围栏内的示例与批注节的内部推理一并计入，
    # 产出「仅在批注里并存」之类的误报；现与 W 级扫描范围三层对齐。
    body_probes = [
        probes[i]
        for i in range(len(lines))
        if (not in_fence[i])
        and section_of[i] != "ANN"
        and not (
            i < body_start
            and (probes[i].lstrip().startswith(">") or any(sig in probes[i] for sig in DECL_SIGNALS))
        )
    ]
    body_text = "\n".join(body_probes)
    for a, b, basis in PAIRS:
        if a in body_text and b in body_text:
            findings.append(Finding("W-22", 0, f"译法并存：「{a}」与「{b}」同时出现（{basis}）"))

    return findings


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="术语与禁用词门禁（只读）")
    parser.add_argument("report", nargs="?", help="报告 Markdown 文件")
    parser.add_argument("--jurisdictions", default="CN,EU,CA")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--quiet-waivers", action="store_true")
    parser.add_argument("--no-waivers", action="store_true", help="校准用：忽略全部豁免，按原样列出命中")
    args = parser.parse_args(argv)

    if args.list:
        for code, level, title in CATALOG:
            print(f"[{code}] ({level}) {title}")
        return 0
    if not args.report:
        parser.error("缺少报告文件参数")

    report = Path(args.report)
    if not report.exists():
        print(f"lint_terms: 文件不存在：{report}", file=sys.stderr)
        return 1

    text = read_text(report)
    lines = text.splitlines()
    file_waivers, line_waivers = collect_waivers(lines)
    jurisdictions = {j.strip().upper() for j in args.jurisdictions.split(",") if j.strip()}

    kept, waived = [], []
    for f in scan(text, jurisdictions):
        if args.no_waivers:
            kept.append(f)
            continue
        if f.code in file_waivers or (f.line and f.code in line_waivers.get(f.line, set())):
            waived.append(f)
        else:
            kept.append(f)
    if waived and not args.quiet_waivers and not args.no_waivers:
        kept.append(Finding("W-00", 0, f"存在 {len(waived)} 处行内豁免（留痕，请人工复查是否正当）"))

    kept.sort(key=lambda f: (LEVEL_BY_CODE.get(f.code, "W"), f.code, f.line))

    print(f"=== lint_terms：{report.name} ===")
    for f in kept:
        loc = f"L{f.line}" if f.line else "--"
        print(f"[{f.code}] {loc} {f.message}" + (f"  «{f.snippet}»" if f.snippet else ""))
    if not kept:
        print("通过：未发现术语问题。")

    errors = [f for f in kept if LEVEL_BY_CODE.get(f.code, "W") == "E"]
    warnings = [f for f in kept if LEVEL_BY_CODE.get(f.code, "W") == "W"]
    print(f"--- E 级 {len(errors)} 项 / W 级 {len(warnings)} 项 ---")
    if errors:
        return 1
    return 2 if warnings else 0


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
