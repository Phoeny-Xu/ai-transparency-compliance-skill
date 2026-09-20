#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_report.py —— 《三地AI透明度合规义务清单》交付前机器预检（门禁 linter）

定位
----
SKILL.md §6 交付前门禁的**机检子集**。agent 生成报告后、进入人工门禁前运行本脚本，
把「规则写对了、但生成时忘了执行」型漂移从「记忆项」变为「检查项」。

硬约束（★不要改）
----------------
1. **只读，绝不改稿**。本脚本只读报告与规则文件并输出分级结果，不写入任何文件。
   自动改写会触碰法条原文与脚注引文，违反 SKILL.md L1。
2. **不产出法律结论**。只做结构/格式/一致性检查，不做法律定性。
3. 散文规则仍是唯一权威，本脚本只是它的可执行化身。

用法
----
    python check_report.py 报告.md --jurisdictions CN,EU,CA --lang zh-en --mode A
    python check_report.py --list          # 列出全部检查项
    python check_report.py --quiet-waivers # 不输出 W-00 豁免留痕提示（正反用例回归见 tests/test_scripts.py）

退出码
------
    0 = 全部通过
    1 = 存在 E 级（阻断）问题
    2 = 无 E 级、但有 W 级（需人工确认）

行内豁免（防误报逼停）
----------------------
启发式检查必然有假阳性。可在报告里写：

    <!-- lint:ignore W-07 -->                          # 豁免本行
    <!-- lint:ignore-file W-08 -- 本报告为单语附件 -->   # 豁免全文
    <!-- lint:ignore E-03, W-01 -->                     # 逗号分隔多项

豁免须留痕，可由人工复查。豁免本身会以 W-00 提示列出。
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path


def _configure_utf8_output() -> None:
    """Windows 默认 GBK 控制台也必须能输出中文诊断和圈码。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass


_configure_utf8_output()

# ---------------------------------------------------------------------------
# 检查项目录
# ---------------------------------------------------------------------------

CATALOG: list[tuple[str, str, str]] = [
    # (code, level, title)
    ("E-01", "E", "「效力核验记录」节存在（L6）"),
    ("E-02", "E", "「范围声明」存在"),
    ("E-03", "E", "正文去个性化（无问卷编号/环节编号/内部流程术语，L5）"),
    ("E-04", "E", "正文（首个二级标题之后）无 blockquote（`>`）；报头声明区允许（L5）"),
    ("E-05", "E", "脚注引用与定义配对，无孤儿脚注（③）"),
    ("E-06", "E", "无 glossary 硬禁用词（「鲁棒」，L3）"),
    ("E-07", "E", "中国节按「总体要求→显式→隐式」三段式组织（⑫；标识义务主体适用）"),
    ("W-13", "W", "角色疑似仅分发/传播平台（无标识义务主体）而中国节出现标识术语——请确认主体定性（⑫）"),
    ("E-08", "E", "欧盟节含 CoP Commitment 分组（⑭）"),
    ("E-09", "E", "范围含加州时效力核验节含 SB 1000 状态行（⑮）"),
    ("E-10", "E", "义务详述节每项含字段行（责任主体/生效适用/未合规后果，阶段4硬性要求1）"),
    ("E-11", "E", "义务详述节每项含「证据等级」字段（阶段4硬性要求3）"),
    ("E-12", "E", "模式B 小节存在性：欧盟各主体「成文法义务与行为准则义务的衔接」／对比第七节「相同点·不同点·共通要求·单法域特别规定」（㉑）"),
    ("W-01", "W", "斜体（`*…*`）不用于承载警示（报告格式铁律）"),
    ("W-02", "W", "脚注非概括性（不以「含」「等」起止）"),
    ("W-03", "W", "正文义务措辞不混用「必须」（L3 应用「应当」/「建议」）"),
    ("W-04", "W", "范围不含加州时效力核验节不得出现 SB 1000 / leginfo 行（对方 B9）"),
    ("W-05", "W", "罚则对比表单元格不含「前瞻」类字样（对方 B10）"),
    ("W-06", "W", "义务总览「不适用」行占比未超阈值（对方 B8）"),
    ("W-07", "W", "加州三类状态不括号并列（⑯⑰⑱）"),
    ("W-08", "W", "中英双语段段对应（⑳，仅 --lang zh-en）"),
    ("W-09", "W", "欧盟节无「仅内部使用→不适用」类已知反模式结论（对方 A1 弱信号）"),
    ("W-10", "W", "中国节涉及备案/安评时标注「非透明度义务」（⑬）"),
    ("W-11", "W", "范围声明与 modeA-questionnaire 模板高度一致（⑧）"),
    ("W-12", "W", "CoP 已展开但按 Commitment（C1–C4）分组（⑭）"),
    ("W-14", "W", "效力核验记录覆盖率：正文援引法规数 ≤ 效力表行数（L6「每部被引法规一行」；§条号族按条号主体归并为同一部法）"),
    ("W-15", "W", "模式A 报告含「义务详述」节（节整体缺失时 E-10/E-11/W-14 将全部静默跳过）"),
    ("W-16", "W", "正文无确定性推定措辞（④ 不确定项应以「若X则Y」呈现；假设节/批注节豁免；仅模式A）"),
    ("W-17", "W", "模式A 报告含「未覆盖维度与转介卡」段且条目≥1，条目须落指针库或标「需另行专项评估」（⑨）"),
    ("W-18", "W", "「前瞻变更提示」块未挂于「已适用／义务待生效」类小节（⑱）"),
    ("W-19", "W", "模式A 报告批注节含「回填确认记录」条目（⑦ 的可机器化边缘；批注节整体缺失时亦报）"),
    ("W-23", "W", "检查项前置信号未命中致本项未执行（E-12 模板判定／W-11 范围声明原文），须人工确认"),
    ("W-24", "W", "模式B 报告出现独立的 CoP 措施章节——CoP 应随欧盟义务就地展开，不得单独成节（⑭）"),
    ("W-25", "W", "模式B 报告出现模式A 专有语汇（画像事实／画像推断／用户答「不确定」）——modeB 跳过问卷、不针对具体产品（批注语义）"),
    ("W-00", "W", "存在行内豁免（留痕提示）"),
]

LEVEL_BY_CODE = {code: level for code, level, _ in CATALOG}
TITLE_BY_CODE = {code: title for code, _, title in CATALOG}

# ---------------------------------------------------------------------------
# 正则与常量
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
WAIVER_RE = re.compile(
    r"<!--\s*lint:ignore(-file)?\s+((?:[EW]-\d{2})(?:\s*,\s*[EW]-\d{2})*)\s*(?:--[^>]*)?-->"
)
FOOTNOTE_DEF_RE = re.compile(r"^\s*\[\^([^\]\s]+)\]:")
FOOTNOTE_REF_RE = re.compile(r"\[\^([^\]\s]+)\]")

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z]")
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")

# 去个性化：问卷编号只匹配「后面不是字母/数字/CJK」的形式，避免误伤 A4纸 / B2B
DEPERSONALIZE_PATTERNS = [
    (re.compile(r"(?<![0-9A-Za-z])[AB]\d{1,2}(?![0-9A-Za-z\u4e00-\u9fff])"), "问卷编号"),
    (re.compile(r"环节[①②③④⑤⑥⑦]"), "环节编号"),
    (re.compile(r"阶段[1-4](?![0-9])"), "阶段编号"),
    (re.compile(r"回填确认"), "内部流程术语"),
    (re.compile(r"问卷"), "内部流程术语"),
]

# 加州三态括号并列的已知反模式
CA_SLASH_RE = re.compile(r"（[^）]{0,80}/[^）]{0,80}）")
CA_CLASS_WORDS = ("covered provider", "大型网络平台", "hosting platform", "capture device")
CA_NEGATION_WORDS = ("不适用", "不触发", "未达", "非")

ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)([^*\n]{1,80}?)\*(?!\*)")

BOLD_MARK_RE = re.compile(r"\*{1,2}")

# ---------------------------------------------------------------------------
# E-10/E-11/W-14/W-15：义务详述节字段化与效力核验覆盖率（阶段4 硬性要求1/3；L6）
# ---------------------------------------------------------------------------
# 说明：本组检查只做「结构/字段存在性」判定，不产出法律结论（见文件头硬约束 2）。
ITEM_RE = re.compile(r"^\s*\*\*[（(]\d+[)）]\s*")   # 义务条目行：**(1) {义务名称}**
# CoP 分组行过滤器：CoP 的 C1–C4 措施分组由 ⑭／E-08／W-12 治理，不得计入义务条目，
# 否则 E-10/E-11 会与 ⑭ 双重治理（2026-09-18 实测定：实产报告的分组行写作 `- (n) …`，
# 本就不匹配 ITEM_RE；此过滤器防的是「按模板加粗书写」与「整节豁免」两种误路）。
COP_GROUP_RE = re.compile(r"[（(]C[1-4][)）]|CoP|行为准则|准则")
# 字段名（含别名）：模板正文自己写作「生效日期」（modeA-report-template L9），字段块写作
# 「生效/适用」（同文件 L73）——两种写法一律归一到「生效/适用」，否则会误报字段缺失。
_FIELD_NAMES_PAT = (
    r"责任主体|优先级|生效\s*/\s*适用|生效日期|适用日期|技术细则|未合规后果|证据等级|效力状态"
)
FIELD_RE = re.compile(r"^\s*[-*]\s*(" + _FIELD_NAMES_PAT + r")\s*[:：]")
# 字段名提取（2026-09-18 实测校准）：实产报告常把多个字段写在同一行
# （如 `- 责任主体：X ｜ 优先级：Y ｜ 生效/适用：Z`），只按行首取会漏计 → 误报「字段不全」。
FIELD_TOKEN_RE = re.compile(r"(" + _FIELD_NAMES_PAT + r")\s*[:：]")
FIELD_ALIASES = {"生效日期": "生效/适用", "适用日期": "生效/适用"}
CORE_FIELDS = ("责任主体", "生效/适用", "未合规后果")   # E-10 三个核心字段
EVIDENCE_FIELD = "证据等级"                            # E-11


def canon_field(name: str) -> str:
    """字段名归一：去空白 + 别名映射（生效日期／适用日期 → 生效/适用）。"""
    n = re.sub(r"\s+", "", name)
    return FIELD_ALIASES.get(n, n)


# 「零义务／非义务」条目信号：这类 `**(n)**` 条目无义务可履行（或系实务提示），
# 自无「生效/适用」「未合规后果」可言，不应据以报字段缺失。
# 来源＝实产语料（2026-09-18 校准）：案例13 中国大陆「不适用」、案例18 欧盟「不触发」、
# 案例18 中国大陆「非义务，实务提示」三类均属此列。
NON_DUTY_SIGNALS = ("不适用", "不触发", "非义务", "实务提示", "衔接说明")
# 义务详述节的标题关键词（模式A 模板作「## 三、分法域义务详述」）
DETAIL_HEADING_KEYS = ("义务详述", "义务清单")

LAW_REF_RES = [
    re.compile(r"《[^》\n]{2,40}》"),
    re.compile(r"Regulation\s*\(EU\)\s*\d{4}/\d+"),
    # § 条号只取**条号主体**（5 位），剥掉子节号：§22757.1(d)／§22757.3.2 均归并为「§22757」一部法。
    # 否则同部法 §22757 的子节族会被逐条计成 N 部「法规」，而效力表按「每部被引法规一行」只有 1 行，
    # 触发误报 W-14（「疑有法规未登记效力状态」）。该缺陷由 agent2 实测发现（2026-09-19）。
    re.compile(r"§\s*\d{5}"),
    re.compile(r"SB\s*\d{3,4}"),
]
# 不计入「正文援引法规」统计的排除项：①自指书名号；②背景/排除性提及（非义务法规）。
# 白名单制（从规则库效力核验要点动态取名单）留作后续升级，先以停用词表 + W 级缓冲控制误报。
LAW_STOPWORDS = (
    "《三地AI透明度合规义务清单》",
    "《互联网信息服务算法推荐管理规定》",
)
# 精度处理（2026-09-18 实测）：
#  ① 来源列 URL 内的 bill_id（如 `…bill_id=202520260SB1000`）会命中 `SB\s*\d{3,4}`，
#     属「链接标识符」而非法规援引 → 扫描前先抹掉 URL；
#  ② `SB 1000` 与 `SB1000` 系同一部法规的两种写法 → 比对前统一去空白，防重复计数。
URL_RE = re.compile(r"https?://\S+")
LAW_STOPWORDS_NORM = {re.sub(r"\s+", "", s) for s in LAW_STOPWORDS}


# ---------------------------------------------------------------------------
# W-16/W-17/W-18/E-12：事实客观性与结构承载（④⑨⑱㉑；2026-09-18 批G 新增）
# ---------------------------------------------------------------------------
# ④ 确定性推定措辞（仅模式A；假设节与批注节豁免——该两处本就承载「最严口径推定」）。
#    规则原文＝§6④「不确定项以『若X则Y』＋待核事实清单呈现，无『推定为具备/达量/已实施』」。
#    只枚举「推定为＋事实完成语」与「视为（已）＋事实完成语」两类**确定性**措辞；
#    「保守推定」「推定口径」「非推定」等不构成指控（并非把未核实事实当成已具备）。
PRESUMPTION_RE = re.compile(
    r"推定为[^。\n]{0,12}?(?:具备|达量|已实施|达到|符合|构成|满足|存在|超过)"
    r"|视为(?:已)?(?:具备|实施|达量|达到|符合|构成|满足)"
)
# ⑨ 未覆盖维度与转介卡：位于报头区但系**自主撰写段**、不属声明区豁免（reporting-rules §三.4）。
SCOPE_SECTION_KEY = "未覆盖维度"
# 条目形态：无序/有序列表项。
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)、]\s+)")
# 二层弱检：条目须落「指针库已收录维度」或显式标注「需另行专项评估」（未收录者一律写后者）。
POINTER_REF_HINTS = ("另行专项评估", "指针库", "out-of-scope-pointer")
# ⑱ 前瞻变更提示块：仅附「主体资格未达」类，不得外溢至「已适用／义务待生效」类小节。
FORESIGHT_KEYS = ("前瞻变更提示", "前瞻提示")
FORESIGHT_FORBIDDEN_IN_HEADING = (
    "已适用", "义务待生效", "2027-01-01", "2028-01-01", "2027-02-02",
)
# ㉑ 模式B 小节存在性：以各模板的特征标题识别所用模板，避免对另一模板误报。
MODE_B_COMPARISON_SIGNALS = ("对比矩阵", "差异评析", "概念对齐", "对比报告")
# 「分析评论」是对比模板的普通章节名，不能单独把报告识别成研究模板。
MODE_B_RESEARCH_SIGNALS = ("规则体系总览", "义务主体与义务内容")
MODE_B_JOINT_HEADING_KEY = "成文法义务与行为准则义务的衔接"
MODE_B_COMPARISON_SECTION_KEY = "相同点"
MODE_B_COMPARISON_SECTION_ALT = ("不同点", "共通要求")
# ⑭ CoP 相关性门：CoP 仅覆盖 Art. 50(2)/(4)/(5)；专题对比若只涉 Art. 50(1)/(3)，未展开 CoP 不构成缺陷。
COP_CONTEXT_KEYS = ("50(2)", "50（2）", "50(4)", "50（4）", "机器可读", "深度伪造", "公共利益")
# ⑭ 独立成节的 CoP 标题（应就地展开）：二级标题且同时含「准则是/CoP」与「措施/展开/要点」字样。
MODE_B_COP_STANDALONE_RE = re.compile(
    r"(?:CoP|行为准则)[^\n]{0,40}(?:措施|展开|要点)|(?:措施|展开|要点)[^\n]{0,40}(?:CoP|行为准则)"
)
# W-25 模式B 报告的模式A 残留语汇（2026-09-20）：modeB 跳过问卷、不针对具体产品，
# 以下 modeA 专有输入概念不应出现在 modeB 报告（2026-09-20 用户质疑「modeB 不涉及具体
# 产品，为什么会有画像事实和假设与不确定？」后，经全仓溯源确认为 modeA 模板复制残留）。
# 两条边界（均经语料回归裁定）：
#   ① 用**精确短语**而非裸词：不扫「画像」——modeB 转介卡会合法提及 GDPR 的「画像」（Art. 4(4)）。
#   ② **不收「回填确认」**：它属另一类问题（模式A ⑦ 回填确认记录，modeA 报告中系法定必填、
#      正文滥用另由 E-03「内部流程术语」治理），并入本码会对合法 modeA 报告及讨论问卷机制的
#      文档大面积误报（实测工作区 24 份文件 67 处命中全由此词贡献）。
MODE_A_RESIDUE_PATTERNS = (
    (re.compile(r"画像事实"), "画像事实"),
    (re.compile(r"画像推断"), "画像推断"),
    (re.compile(r"用户答\s*[「“\"]?\s*不确定"), "用户答「不确定」"),
)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    code: str
    line: int  # 1-based；0 表示全局
    message: str
    snippet: str = ""

    @property
    def level(self) -> str:
        return LEVEL_BY_CODE.get(self.code, "W")


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------


def read_text(path: Path) -> str:
    # utf-8-sig：兼容 Windows PowerShell 5.1 `Set-Content -Encoding UTF8` 写出的 BOM。
    # 带 BOM 时首行标题会变成「\ufeff# …」而使标题正则失配，属静默降级一类隐患。
    return path.read_text(encoding="utf-8-sig", errors="replace")


def header_boundary(structure: dict, total: int) -> int:
    """报头声明区与正文的分界线 = 首个二级标题的行号。

    该界线同时服务两处规则：
    - E-04：报头声明区可用 `>`、正文禁用（2026-09-15 用户裁定）；
    - lint_terms：报头声明区为**术语豁免区**（范围声明等系【呈现·照搬】原文，
      对其中用词报错会与「范围声明原样照搬」的要求直接冲突）。

    报告中若一个二级标题都没有（结构本身不合规），返回 0 即全线从严，
    避免「没有分界线」反而使两处规则同时静默失效。
    """
    body_start = structure.get("body_start", total)
    return body_start if body_start < total else 0


def scan_structure(lines: list[str]) -> dict:
    """返回 in_fence / annot_start / headings / 效力核验节区间。"""
    in_fence = [False] * len(lines)
    fence = False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence[i] = True
            fence = not fence
            continue
        in_fence[i] = fence

    annot_start = None
    headings: list[tuple[int, int, str]] = []  # (index, level, text)
    for i, line in enumerate(lines):
        if in_fence[i]:
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        level, text = len(m.group(1)), m.group(2)
        headings.append((i, level, text))
        if annot_start is None and level <= 3 and "批注" in text:
            annot_start = i

    def section_span(keyword: str, max_level: int = 3, min_level: int = 2):
        # 只认二级及以上标题：文档主标题（H1）常含全部法域名，误当节首会使区间塌成全文
        for idx, (i, level, text) in enumerate(headings):
            if min_level <= level <= max_level and keyword in text:
                end = len(lines)
                for j, lv, _ in headings[idx + 1 :]:
                    if lv <= level:
                        end = j
                        break
                return i, end
        return None

    body_start = len(lines)
    for i, level, _ in headings:
        if level >= 2:
            body_start = i
            break

    return {
        "in_fence": in_fence,
        "annot_start": annot_start,
        "headings": headings,
        "body_start": body_start,
        "validity": section_span("效力核验"),
        "cn": section_span("中国"),
        "eu": section_span("欧盟"),
        "ca": section_span("加州"),
    }


def body_range(structure: dict, total: int) -> range:
    end = structure["annot_start"] if structure["annot_start"] is not None else total
    return range(0, end)


def collect_waivers(lines: list[str]) -> tuple[set[str], dict[int, set[str]]]:
    """返回 (全文豁免集合, 行号→豁免集合)。"""
    file_waivers: set[str] = set()
    line_waivers: dict[int, set[str]] = {}
    for i, line in enumerate(lines, start=1):
        for m in WAIVER_RE.finditer(line):
            is_file, codes = m.group(1), m.group(2)
            parsed = {c.strip() for c in codes.split(",") if c.strip()}
            if is_file:
                file_waivers |= parsed
            else:
                stripped = WAIVER_RE.sub("", line).strip()
                target = i if stripped else i + 1  # 独占一行时豁免下一行
                line_waivers.setdefault(target, set()).update(parsed)
    return file_waivers, line_waivers


# ---------------------------------------------------------------------------
# 各项检查
# ---------------------------------------------------------------------------


def check_report(path: Path, jurisdictions: set[str], lang: str, mode: str, root: Path) -> list[Finding]:
    text = read_text(path)
    # 豁免注释（`<!-- lint:ignore … -->`）是**元信息**，不是报告内容：只移除注释片段本身、
    # 保留同行其余内容。理由文本里若出现问卷编号或禁用词（如案例16 的文件级豁免理由里写了
    # 「B8-2」），会被当成正文命中而误报、甚至阻断交付；而整行抹掉又会连带抹掉行内豁免
    # 所在行的真实内容，等于绕过豁免机制，故只做片段替换。
    # 豁免解析另走 raw_lines，机制不受影响。
    raw_lines = text.splitlines()
    lines = [WAIVER_RE.sub("", l) for l in raw_lines]
    structure = scan_structure(lines)
    in_fence = structure["in_fence"]
    annot_start = structure["annot_start"]
    findings: list[Finding] = []

    def in_body(i: int) -> bool:
        return (annot_start is None or i < annot_start) and not in_fence[i]

    # ---- E-01 效力核验记录节 ----
    if structure["validity"] is None:
        findings.append(Finding("E-01", 0, "未找到「效力核验记录」节（L6：任何报告不得省略）"))

    # ---- E-02 范围声明 ----
    scope_hits = [i for i, l in enumerate(lines) if "本评估覆盖" in l or "不覆盖" in l]
    if mode == "A" and not scope_hits:
        findings.append(Finding("E-02", 0, "未找到「范围声明」（应原样照搬 modeA-questionnaire 的范围声明）"))
    elif mode == "B" and not any(
        marker in line for line in lines for marker in ("对比范围", "研究范围", "梳理范围", "本报告范围", "本评估覆盖")
    ):
        findings.append(Finding("E-02", 0, "模式B未找到对比/研究范围声明（应明确法域、主题和不覆盖范围）"))

    # ---- E-03 去个性化 ----
    for i, line in enumerate(lines):
        if not in_body(i):
            continue
        probe = CODE_SPAN_RE.sub("", line)
        for pattern, kind in DEPERSONALIZE_PATTERNS:
            m = pattern.search(probe)
            if m:
                findings.append(
                    Finding("E-03", i + 1, f"正文出现{kind}「{m.group(0)}」（L5 去个性化）", m.group(0))
                )
                break

    # ---- E-04 blockquote ----
    # 规则边界（2026-09-15 用户裁定，非临时口径）：
    #   报头声明区 = 文档主标题至首个二级标题之间。该区允许以 `>` 呈现「生成日期／法规
    #   时效声明／依据／范围声明」等声明性内容（modeA-report-template 自身即为 `>`）。
    #   正文 = 首个二级标题（含）之后。正文内一律禁用 `>` 承载任何内容。
    # 裁定理由：报头声明是读者预期中的元数据块，与正文陈述混同风险低；正文用灰色块
    #   会让读者误认作法规原文引文，故从严。规则同时写入 modeA-report-template 格式铁律、
    #   reporting-rules §二 与 SKILL.md §6 ⑲，三处口径一致。
    body_start = header_boundary(structure, len(lines))
    for i, line in enumerate(lines):
        if not in_body(i) or i < body_start:
            continue
        if line.lstrip().startswith(">"):
            findings.append(Finding("E-04", i + 1, "正文出现 blockquote（L5 禁引用块承载推理）", line.strip()[:60]))

    # ---- E-05 脚注配对 ----
    # 注意：定义行自身含有 `[^name]`，必须 continue 掉，否则定义行会被当成引用，
    # 使「未被引用的脚注定义」永不触发（E-05 半失效）。
    defs, refs = set(), set()
    for i, line in enumerate(lines):
        m = FOOTNOTE_DEF_RE.match(line)
        if m:
            defs.add(m.group(1))
            continue
        if annot_start is not None and i >= annot_start:
            continue
        for r in FOOTNOTE_REF_RE.finditer(line):
            refs.add(r.group(1))
    for name in sorted(refs - defs):
        findings.append(Finding("E-05", 0, f"孤儿脚注：正文引用了 [^{name}] 但无对应定义（③）"))
    for name in sorted(defs - refs):
        findings.append(Finding("E-05", 0, f"未被引用的脚注定义：[^{name}]（③ 无孤儿脚注）"))

    # ---- E-06 硬禁用词 ----
    for i, line in enumerate(lines):
        if not in_body(i):
            continue
        if "鲁棒" in line:
            findings.append(Finding("E-06", i + 1, "出现「鲁棒」（L3 应为「稳健性」，禁用工程音译）", "鲁棒"))

    # ---- E-07 中国节三段式 ----
    # 仅当中国节确含标识义务时才要求三段式；纯内部使用等零义务场景无标识义务可组织。
    if "CN" in jurisdictions and structure["cn"] is not None:
        start, end = structure["cn"]
        seg = "\n".join(lines[start:end])
        # 「应当…标识」判定须排除核验/查验/审核类动词（V3-04）：分发平台第7条
        # 核验转述句（「应当核验其生成合成内容标识相关材料」）不是标识义务句。
        has_label_terms = bool(re.search(r"显式标识|隐式标识|显著标识|生成合成内容标识", seg))
        duty_iter = re.finditer(r"应当[^。\n]{0,40}?(标识|标注)", seg)
        has_label_duty = False
        for m in duty_iter:
            span = m.group(0)
            if re.search(r"(核验|核查|查验|审核|留痕|检查|复核)", span):
                continue
            has_label_duty = True
            break
        # 主体识别（V3-04 结构层）：角色表仅含分发/传播平台（B1_4/B4_2 语境的
        # 「应用程序分发平台」「网络信息内容传播服务提供者」）而无标识义务主体
        # （深度合成/生成式服务提供者/技术支持者）时，中国节不应按三段式强制——
        # 降级 W-13 提示复核主体定性，不硬性阻断。
        duty_body_present = bool(re.search(r"深度合成服务提供者|生成式人工智能服务提供者|技术支持者|内容发布者", seg))
        distributor_only = bool(re.search(r"应用程序分发平台|网络信息内容传播服务提供者", seg)) and not duty_body_present
        # 「总体要求」层允许等价小标题措辞（如「总体标识义务框架」）：只在标签行里认「总体」
        label_lines = "\n".join(l for l in lines[start:end] if l.lstrip().startswith(("#", "**")))
        slots = {
            "总体要求": ("总体要求" in seg) or ("总体" in label_lines),
            "显式标识": "显式标识" in seg,
            "隐式标识": "隐式标识" in seg,
        }
        missing = [k for k, ok in slots.items() if not ok]
        if has_label_duty and missing:
            findings.append(
                Finding("E-07", start + 1, f"中国节缺少三段式小标题：{'; '.join(missing)}（⑫ 总体要求→显式→隐式）")
            )
        elif has_label_terms and missing and distributor_only:
            # V3-04 结构层：分发/传播平台独大且含标识术语但无标识义务句——
            # 三段式本不适用（无标识义务可组织），降级 W-13 提示复核主体定性，
            # 既不硬性阻断、也不静默放过（案例19 误报的结构性出口）。
            findings.append(
                Finding(
                    "W-13",
                    start + 1,
                    "中国节疑似仅分发/传播平台角色（无标识义务主体）却含标识术语——请确认主体定性；若确无标识义务，三段式不适用（⑫）",
                )
            )

    # ---- E-08 / W-12 欧盟节 CoP 展开与分组 ----
    # CoP 只覆盖 Art. 50(2)/(4)；纯 Art. 50(1)/(3) 场景 CoP 本不覆盖，不构成缺陷。
    # 分两级：完全未展开 → E；已展开但未按 Commitment 分组 → W（实质合规、标注不合规）。
    if "EU" in jurisdictions and structure["eu"] is not None:
        start, end = structure["eu"]
        seg = "\n".join(lines[start:end])
        cop_relevant = any(k in seg for k in COP_CONTEXT_KEYS)
        if cop_relevant:
            has_commitment = bool(re.search(r"\bC[1-4]\b|Commitment|承诺[一二三四1-4]", seg))
            has_measure = bool(re.search(r"\bM[1-4]\.\d", seg))
            if not has_commitment and not has_measure:
                findings.append(Finding("E-08", start + 1, "欧盟节涉 Art. 50(2)/(4) 但未见 CoP 展开（⑭ 应分点展开、不得只搬速查表）"))
            elif not has_commitment:
                findings.append(Finding("W-12", start + 1, "CoP 已逐条展开但未按 Commitment 分组（⑭ 建议补 C1–C4 分组）"))

    # ---- E-09 / W-04 SB 1000 行（限定在效力核验节内判定）----
    if structure["validity"] is not None:
        start, end = structure["validity"]
        seg = "\n".join(lines[start:end])
        has_sb1000 = "SB 1000" in seg or "SB1000" in seg or "leginfo" in seg
        if "CA" in jurisdictions and not has_sb1000:
            findings.append(Finding("E-09", start + 1, "范围含加州，但效力核验节缺 SB 1000 状态行（⑮）"))
        if "CA" not in jurisdictions and has_sb1000 and mode == "A":
            findings.append(
                Finding("W-04", start + 1, "范围不含加州，效力核验节却出现 SB 1000 / leginfo 行，建议移除（对方 B9）")
            )

    # ---- E-10 / E-11 / W-15 义务详述节字段化（阶段4 硬性要求1/3）----
    # 背景：阶段4 硬性要求 1/3 明令每项义务含「责任主体/生效适用/未合规后果」与「证据等级」，
    # 但原 §6 无对应条目、无机器码——4 份实产报告机检 0E/0W 双绿却普遍缺字段（2026-09-18 排查）。
    # 仅模式A 适用：模式B 用另一套模板（modeB-*），本无「义务详述」节。
    if mode == "A":
        # 节标题**只认二级标题**：文档 H1 常作「…合规义务清单」，若并入 `level <= 2`
        # 会把主标题误当节首（2026-09-18 实测：detail 落到 L1，子标题切分为空、
        # 三个检查全部静默失效、且 W-15 因 detail 非空而不报——属最隐蔽的一类假绿）。
        detail = None
        for i, level, t in structure["headings"]:
            if level == 2 and any(k in t for k in DETAIL_HEADING_KEYS):
                detail = i
                break
        if detail is None:
            # W-15：节整体缺失时 E-10/E-11 会静默跳过（与 E-01/E-02 的节存在性检查对齐）
            findings.append(
                Finding(
                    "W-15",
                    0,
                    "未找到「义务详述」节（模式A 报告应含「三、分法域义务详述」；节缺失时字段类检查全部失效）",
                )
            )
        else:
            end = len(lines)
            for i, level, _ in structure["headings"]:
                if i > detail and level <= 2:
                    end = i
                    break
            # 以 level>=3 标题切法域小节；无子标题则整节视作一个小节（宁可粗报、不可漏报）
            sub_bounds = [(i, lv, t) for i, lv, t in structure["headings"] if detail < i < end and lv >= 3]
            spans: list[tuple[str, int, int]] = []
            for k, (i, lv, t) in enumerate(sub_bounds):
                stop = sub_bounds[k + 1][0] if k + 1 < len(sub_bounds) else end
                spans.append((t, i, stop))
            if not spans:
                spans = [("（整节）", detail, end)]
            for name, s, e in spans:
                seg = lines[s:e]
                # 排除两类非义务条目：
                #  ① CoP 分组行（C1–C4）——归 ⑭／E-08／W-12，防双重治理；
                #  ② 零义务／非义务条目（NON_DUTY_SIGNALS）——无义务可履行，自无字段可言。
                items = [
                    ln for ln in seg
                    if ITEM_RE.match(ln)
                    and not COP_GROUP_RE.search(ln)
                    and not any(sig in ln for sig in NON_DUTY_SIGNALS)
                ]
                fields = [ln for ln in seg if FIELD_RE.match(ln)]
                field_names: set[str] = set()
                for ln in seg:
                    field_names.update(canon_field(tok) for tok in FIELD_TOKEN_RE.findall(ln))
                if items and not fields:
                    findings.append(
                        Finding(
                            "E-10",
                            s + 1,
                            f"「{name}」节义务条目存在但整节无字段行（每项应含责任主体/生效适用/未合规后果，阶段4硬性要求1）",
                        )
                    )
                elif items and not set(CORE_FIELDS) <= field_names:
                    miss = "、".join(f for f in CORE_FIELDS if f not in field_names)
                    findings.append(
                        Finding("E-10", s + 1, f"「{name}」节字段不全，缺：{miss}（阶段4硬性要求1）")
                    )
                if items and EVIDENCE_FIELD not in field_names:
                    findings.append(
                        Finding("E-11", s + 1, f"「{name}」节义务条目未标「证据等级」（阶段4硬性要求3）")
                    )

    # ---- W-14 效力核验记录覆盖率（L6「每部被引法规一行」）----
    # 依赖与「是否存在义务详述节」无关（缺该节者更应查），故不设 detail 前置。
    if structure["validity"] is not None:
        v_start, v_end = structure["validity"]
        verify_rows = 0
        for ln in lines[v_start:v_end]:
            if ln.strip().startswith("|") and ln.count("|") >= 3:
                if re.match(r"^\s*\|[\s:\-|]+\|\s*$", ln):
                    continue
                first = ln.strip().strip("|").split("|")[0].strip()
                if first and first not in ("法规",):
                    verify_rows += 1
        body_end = annot_start if annot_start is not None else len(lines)
        body_text = "\n".join(lines[body_start:body_end])   # 正文（首个二级标题起）
        scan_text = URL_RE.sub(" ", body_text)              # 抹掉 URL，防 bill_id 被当法规
        cited: set[str] = set()
        for rx in LAW_REF_RES:
            for m in rx.finditer(scan_text):
                tok = re.sub(r"\s+", "", m.group(0))        # 归一空白：SB 1000 ≡ SB1000
                if tok not in LAW_STOPWORDS_NORM:
                    cited.add(tok)
        if len(cited) > verify_rows:
            findings.append(
                Finding(
                    "W-14",
                    v_start + 1,
                    f"正文援引 {len(cited)} 部法规，效力核验记录仅 {verify_rows} 行——疑有法规未登记效力状态（L6）",
                )
            )

    # ---- E-12 模式B 小节存在性（㉑）----
    # 仅模式B 生效：模式B 两套模板（单法域梳理 / 对比报告）各有硬性小节要求。
    # 以模板特征标题识别所用模板——识别信号取自「即使该小节缺失也仍存在的」同模板他节，
    # 避免「用待检小节自身做信号」导致缺失时检查静默失效（本轮最需防的一类假绿）。
    if mode == "B":
        heading_texts = [t for _, _, t in structure["headings"]]
        is_comparison = any(sig in t for t in heading_texts for sig in MODE_B_COMPARISON_SIGNALS)
        is_research = any(sig in t for t in heading_texts for sig in MODE_B_RESEARCH_SIGNALS)
        # W-23 兜底（2026-09-19）：信号未命中时 E-12 本会静默不执行——须显式留痕，
        # 否则「模板换了、检查项整体失效」会被当成「通过」（静默失效的典型形态）。
        if not (is_comparison or is_research):
            findings.append(
                Finding(
                    "W-23",
                    0,
                    "模式B 未匹配到已知模板特征标题（对比矩阵…／规则体系总览…），E-12 小节存在性判定未执行——请人工核对（㉑）",
                )
            )
        if is_comparison:
            has_same = any(MODE_B_COMPARISON_SECTION_KEY in t for t in heading_texts)
            has_alt = any(any(a in t for a in MODE_B_COMPARISON_SECTION_ALT) for t in heading_texts)
            if not (has_same and has_alt):
                findings.append(
                    Finding("E-12", 0, "模式B 对比报告缺第七节「相同点、不同点、共通要求与单法域特别规定」（㉑）")
                )
        if is_research and "EU" in jurisdictions:
            if not any(MODE_B_JOINT_HEADING_KEY in t for t in heading_texts):
                findings.append(
                    Finding("E-12", 0, "模式B 欧盟单法域梳理缺各主体「成文法义务与行为准则义务的衔接」小节（㉑）")
                )

        # ---- E-08／W-24 模式B 的 CoP 就地展开（⑭，2026-09-19 新增）----
        # 背景：对比模板原要求另设独立「CoP 措施要点展开」章节，用户裁定改为**随欧盟义务就地展开**
        # （矩阵欧盟列标编号＋层级标签＋措施要点摘要；第五节各主体项下四要素逐条详述）。
        # 独立节取消后暴露一处**静默失效**：对比报告无「欧盟」节标题，上面依赖 structure["eu"]
        # 的 E-08 在对比报告中永不触发——CoP 这一 ★强制项对对比报告实际处于无检状态，必须先补。
        # 相关性门（COP_CONTEXT_KEYS）：专题对比若只涉 Art. 50(1)/(3)，CoP 本不覆盖，不报。
        if is_comparison and "EU" in jurisdictions:
            seg_end = annot_start if annot_start is not None else len(lines)
            seg = "\n".join(lines[body_start:seg_end])       # 正文（首个二级标题起，排除批注节）
            has_measure = bool(re.search(r"\bM[1-4]\.\d|Measure\s*[1-4]\.[0-9]|措施\s*[1-4]\.[0-9]", seg))
            has_commitment = bool(re.search(r"\bC[1-4]\b|Commitment|承诺[一二三四1-4]", seg))
            if not has_measure and not has_commitment and any(k in seg for k in COP_CONTEXT_KEYS):
                findings.append(
                    Finding(
                        "E-08",
                        0,
                        "模式B 对比报告涉 Art. 50(2)/(4) 却全篇未见 CoP 展开（⑭ 应随欧盟义务就地展开："
                        "矩阵欧盟列标编号＋层级标签＋措施要点摘要、第五节各主体项下四要素详述）",
                    )
                )
        # W-24：不得另设独立的 CoP 措施章节（用户裁定「不需要单独一节」）。
        if is_comparison or is_research:
            for i, level, title_text in structure["headings"]:
                if level == 2 and MODE_B_COP_STANDALONE_RE.search(title_text):
                    findings.append(
                        Finding(
                            "W-24",
                            i + 1,
                            f"模式B 报告出现独立的 CoP 章节「{title_text[:40]}」——应随欧盟义务就地展开"
                            "（矩阵欧盟列＋第五节各主体项下），不得单独成节（⑭）",
                        )
                    )

        # ---- W-25 模式B 报告出现 modeA 专有语汇（2026-09-20 新增）----
        # 背景：modeB 跳过问卷、不针对具体产品，但两套 modeB 模板的批注子节占位句长期沿用
        # modeA 语汇（「画像事实→定义条款→义务条款」「用户答『不确定』」），系
        # modeA-report-template 与问卷落盘机制的复制残留。**该处此前无任何机检码覆盖**
        # （W-19 仅管模式A 的「回填确认记录」条目是否存在），故残留可长期存活，
        # 且 check_report／lint_terms 双绿不会暴露它——判缺陷不得以「双绿」为依据。
        # 扫描范围＝**全篇**（不在批注节设边界）：这三类语汇在 modeB 的正文与批注节均无
        # 合法用途；只扫批注节会在「正文写进去」时留新盲区。报头声明区照扫（范围声明／
        # 时效声明文本不含这些语汇，已核）。仅模式B 生效，modeA 合法使用不报。
        # 门控＝**模板特征标题命中**（is_comparison／is_research，同 W-24）：本码针对
        # 「modeB 报告」；工作区大量为「关于 skill 的」工作稿与归档模板，不加门控会误报
        # （语料回归实测：不加门控时 24 份文件命中）。模板未命中时 W-23 已出留痕提示。
        if is_comparison or is_research:
            for i, line in enumerate(lines):
                if in_fence[i] or line.lstrip().startswith("<!--"):
                    continue
                probe = CODE_SPAN_RE.sub("", line)
                for residue_re, display in MODE_A_RESIDUE_PATTERNS:
                    hit = residue_re.search(probe)
                    if hit:
                        findings.append(
                            Finding(
                                "W-25",
                                i + 1,
                                f"模式B 报告出现模式A 专有语汇「{display}」——modeB 跳过问卷、"
                                "不针对具体产品，主体认定应据「法定构成要件→义务条款」推演，"
                                "不确定项应为「法规效力／解释／范围层面」者，而非产品画像与问卷作答",
                                hit.group(0)[:40],
                            )
                        )
                        break   # 每行只报一次，避免同一行多个语汇刷屏

    # ---- W-16 确定性推定措辞（④，仅模式A）----
    if mode == "A":
        assume_spans: list[tuple[int, int]] = []
        for idx, (i, level, t) in enumerate(structure["headings"]):
            if "假设" in t:
                stop = len(lines)
                for j, lv, _ in structure["headings"][idx + 1:]:
                    if lv <= level:
                        stop = j
                        break
                assume_spans.append((i, stop))
        for i, line in enumerate(lines):
            if not in_body(i) or i < body_start or in_fence[i]:
                continue
            if any(s <= i < e for s, e in assume_spans):
                continue
            m = PRESUMPTION_RE.search(CODE_SPAN_RE.sub("", line))
            if m:
                findings.append(
                    Finding(
                        "W-16",
                        i + 1,
                        f"正文出现确定性推定措辞「{m.group(0)}」——④ 不确定项应以「若X则Y」＋待核事实清单呈现",
                        m.group(0)[:40],
                    )
                )

    # ---- W-17 未覆盖维度与转介卡（⑨，仅模式A）----
    # 该段物理位置在报头区（首个二级标题之前），但系自主撰写、不属声明区豁免，
    # 故**不套用 body_start 边界**（与 reporting-rules §三.4 一致）；批注节仍豁免。
    if mode == "A":
        def _w17_ok(i: int, line: str) -> bool:
            if in_fence[i] or line.lstrip().startswith("<!--"):
                return False
            return not (annot_start is not None and i >= annot_start)

        sec_idx = None
        for i, line in enumerate(lines):   # 优先认节标题形态，避免命中报头声明中的提及
            if not _w17_ok(i, line):
                continue
            stripped = line.lstrip()
            if stripped.startswith("**" + SCOPE_SECTION_KEY) or (
                HEADING_RE.match(line) and SCOPE_SECTION_KEY in line
            ):
                sec_idx = i
                break
        if sec_idx is None:                # 退路：任意位置首次出现
            for i, line in enumerate(lines):
                if _w17_ok(i, line) and SCOPE_SECTION_KEY in line:
                    sec_idx = i
                    break
        if sec_idx is None:
            findings.append(
                Finding("W-17", 0, "未找到「未覆盖维度与转介卡」段（⑨ 模式A 报告应含此段并按产品列出）")
            )
        else:
            stop = len(lines)
            for j in range(sec_idx + 1, len(lines)):
                if HEADING_RE.match(lines[j]):
                    stop = j
                    break
            items = [lines[j] for j in range(sec_idx + 1, stop) if LIST_ITEM_RE.match(lines[j])]
            if not items:
                findings.append(
                    Finding(
                        "W-17",
                        sec_idx + 1,
                        "「未覆盖维度与转介卡」段无条目（⑨ 每项一行，仅引 out-of-scope-pointer.md 收录内容）",
                    )
                )
            else:
                for it in items:           # 二层弱检：落指针库或标「需另行专项评估」
                    if not any(h in it for h in POINTER_REF_HINTS):
                        findings.append(
                            Finding(
                                "W-17",
                                sec_idx + 1,
                                "未覆盖维度条目疑非指针库已收录内容（未收录者应写「需另行专项评估」，⑨）",
                                it.strip()[:40],
                            )
                        )

    # ---- W-18 前瞻变更提示块归属（⑱）----
    for i, line in enumerate(lines):
        if not in_body(i) or i < body_start or in_fence[i]:
            continue
        if not any(k in line for k in FORESIGHT_KEYS):
            continue
        enclosing = None
        for j, _level, t in structure["headings"]:
            if j < i:
                enclosing = t
            else:
                break
        if enclosing and any(w in enclosing for w in FORESIGHT_FORBIDDEN_IN_HEADING):
            findings.append(
                Finding(
                    "W-18",
                    i + 1,
                    f"「前瞻变更提示」块挂于「{enclosing[:30]}」小节——⑱ 该块仅附「主体资格未达」类，"
                    "不得附「已适用／义务待生效」类",
                    enclosing[:40],
                )
            )

    # ---- W-19 批注节「回填确认记录」（⑦ 的可机器化边缘）----
    # ⑦「回填确认记录**客观**（含确认/更正内容，无空洞断言）」的客观性机器不可判，
    # 但「条目是否存在」可查。该条目按模板批注 §4 落于批注节——正文出现「回填确认」
    # 反属 E-03 违规（内部流程术语），故只在批注节内查找。
    # 防静默失效：批注节整体缺失时同样报出，否则本码永不触发＝假绿。
    if mode == "A":
        if annot_start is None:
            findings.append(
                Finding(
                    "W-19",
                    0,
                    "未找到「批注」节（⑦ 回填确认记录须落于批注节；§6 ⑲ 排版三分离亦要求推理归此节）",
                )
            )
        elif "回填确认" not in "\n".join(lines[annot_start:]):
            findings.append(
                Finding("W-19", annot_start + 1, "批注节未见「回填确认记录」条目（§6 ⑦；模板批注 §4）")
            )

    # ---- W-01 斜体警示 ----
    # 仅报「含中文的斜体」：模板允许英文法学术语/法规名等约定俗成场景用斜体，中文斜体才是违规。
    for i, line in enumerate(lines):
        if not in_body(i):
            continue
        probe = CODE_SPAN_RE.sub("", line)
        m = ITALIC_RE.search(probe)
        if m and CJK_RE.search(m.group(1)) and m.group(1).strip() == m.group(1):
            findings.append(Finding("W-01", i + 1, "正文出现中文斜体，报告格式铁律禁以斜体承载提示/警示", m.group(0)[:40]))

    # ---- W-02 概括性脚注 ----
    # 脚注定义行（`[^label]: …`）在全篇任意位置均可出现，故按定义语法扫描全文、
    # 不以「脚注」小节标题设边界（原 in_footnotes 变量计算后从未使用，系残留，已删）。
    for i, line in enumerate(lines):
        m = FOOTNOTE_DEF_RE.match(line)
        if not m:
            continue
        body = line.split("]:", 1)[1].strip() if "]:" in line else ""
        if not body:
            continue
        stripped = BOLD_MARK_RE.sub("", body).lstrip()
        if stripped[:1] in {"含", "等"} or stripped.endswith("等") or "……" in stripped:
            findings.append(
                Finding("W-02", i + 1, "脚注疑似概括性（以「含」「等」起止或含省略号）；应为官方原文全文（③）", stripped[:40])
            )

    # ---- W-03 「必须」措辞 ----
    for i, line in enumerate(lines):
        if not in_body(i):
            continue
        for m in re.finditer(r"必须", line):
            ctx = line[max(0, m.start() - 3) : m.start() + 4]
            if "无须" in ctx or "不必" in ctx:
                continue
            findings.append(Finding("W-03", i + 1, "正文出现「必须」，L3 应用「应当」（强制）或「建议」（非强制）", "必须"))
            break

    # ---- W-05 罚则表前瞻混排 ----
    if structure["headings"]:
        start = None
        for i, level, t in structure["headings"]:
            if "罚则" in t:
                start = i
                break
        if start is not None:
            end = len(lines)
            for i, level, _ in structure["headings"]:
                if i > start and level <= 2:
                    end = i
                    break
            for i in range(start, end):
                if any(k in lines[i] for k in ("前瞻", "待生效", "尚未生效", "待州长签署", "SB 1000 新增", "生效后")):
                    findings.append(
                        Finding("W-05", i + 1, "罚则对比表出现「前瞻/待生效」字样，防误读为现行法（对方 B10）", lines[i].strip()[:60])
                    )

    # ---- W-06 「不适用」行占比 ----
    overview_start = None
    for i, level, t in structure["headings"]:
        if "义务总览" in t:
            overview_start = i
            break
    if overview_start is not None:
        end = len(lines)
        for i, level, _ in structure["headings"]:
            if i > overview_start and level <= 2:
                end = i
                break
        rows = [l for l in lines[overview_start:end] if l.strip().startswith("|") and l.count("|") >= 3]
        rows = [r for r in rows if not re.match(r"^\s*\|[\s:\-|]+\|\s*$", r)]
        if len(rows) > 1:
            na = sum(1 for r in rows if "不适用" in r)
            ratio = na / len(rows)
            if ratio > 0.6:
                findings.append(
                    Finding(
                        "W-06",
                        overview_start + 1,
                        f"义务总览「不适用」行占比 {na}/{len(rows)}（{ratio:.0%}）偏高，核对是否属零义务场景应精简结构（对方 B8）",
                    )
                )

    # ---- W-07 加州三态括号并列 ----
    if "CA" in jurisdictions:
        for i, line in enumerate(lines):
            if not in_body(i):
                continue
            for m in CA_SLASH_RE.finditer(line):
                chunk = m.group(0)
                if any(w in chunk for w in CA_CLASS_WORDS) and any(n in chunk for n in CA_NEGATION_WORDS):
                    findings.append(
                        Finding("W-07", i + 1, "加州三类状态疑以括号并列（⑯⑰⑱ 应分层、不混框）", chunk[:60])
                    )

    # ---- W-08 双语段段对应 ----
    if lang == "zh-en":
        cn_only = 0
        bilingual = 0
        for i in body_range(structure, len(lines)):
            if in_fence[i]:
                continue
            line = lines[i].strip()
            if not line or line.startswith("#") or line.startswith("|") or FOOTNOTE_DEF_RE.match(line):
                continue
            has_cn, has_latin = bool(CJK_RE.search(line)), bool(LATIN_RE.search(line))
            if has_cn and not has_latin:
                cn_only += 1
            elif has_cn and has_latin:
                bilingual += 1
        total = cn_only + bilingual
        if total >= 20 and cn_only / total > 0.85:
            findings.append(
                Finding(
                    "W-08",
                    0,
                    f"双语格式启发式：正文中文单语段落 {cn_only}/{total}（{cn_only / total:.0%}），疑缺英文对照（⑳）",
                )
            )

    # ---- W-09 欧盟 own-use 反模式 ----
    if structure["eu"] is not None:
        start, end = structure["eu"]
        for i in range(start, end):
            line = lines[i]
            if "仅内部使用" in line or "内部使用" in line:
                window = "\n".join(lines[i : i + 3])
                if re.search(r"不适用|不构成|无义务|不触发", window):
                    findings.append(
                        Finding(
                            "W-09",
                            i + 1,
                            "欧盟节出现「内部使用→不适用」类结论，注意 Art. 3(3)/(11) own-use 亦构成 provider（对方 A1 弱信号，非结论）",
                            line.strip()[:60],
                        )
                    )

    # ---- W-10 非透明度义务标注 ----
    if "CN" in jurisdictions and structure["cn"] is not None:
        start, end = structure["cn"]
        seg = "\n".join(lines[start:end])
        if ("算法备案" in seg or "安全评估" in seg) and "非透明度义务" not in seg:
            findings.append(
                Finding("W-10", start + 1, "中国节涉及备案/安评但未见「非透明度义务」标注（⑬）")
            )

    # ---- W-11 范围声明一致性 ----
    # 依赖「问卷模板中那一段特定措辞的正则命中」才可执行；信号缺失时须留痕（W-23），
    # 不静默跳过（模板改版后 W-11 整体失效会被误当「通过」）。
    if mode == "A" and scope_hits:
        q_path = root / "assets" / "modeA-questionnaire.md"
        if not q_path.exists():
            findings.append(
                Finding("W-23", 0, "问卷模板不存在（assets/modeA-questionnaire.md），W-11 范围声明一致性未执行（⑧）")
            )
        else:
            q_text = read_text(q_path)
            m = re.search(r"范围声明（声明后开始问卷）\*\*：\s*\n+\s*>\s*【呈现·照搬】(.*)", q_text)
            if m is None:
                findings.append(
                    Finding(
                        "W-23",
                        0,
                        "未在问卷模板中匹配到「范围声明」原文段（措辞/结构已变），W-11 未执行——请人工核对（⑧）",
                    )
                )
            else:
                canonical = normalize(m.group(1))
                actual = normalize("\n".join(lines[i] for i in scope_hits))
                ratio = difflib.SequenceMatcher(None, canonical, actual).ratio()
                if ratio < 0.55:
                    findings.append(
                        Finding("W-11", scope_hits[0] + 1, f"范围声明与模板相似度 {ratio:.0%}，核对是否原样照搬（⑧）")
                    )

    return findings


def normalize(text: str) -> str:
    text = BOLD_MARK_RE.sub("", text)
    text = re.sub(r"^[\s>]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", "", text)
    return text


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="《三地AI透明度合规义务清单》交付前机器预检（只读）")
    parser.add_argument("report", nargs="?", help="报告 Markdown 文件")
    parser.add_argument("--jurisdictions", default="CN,EU,CA", help="本次范围，如 CN,EU,CA")
    parser.add_argument("--lang", default="zh", choices=["zh", "zh-en"], help="报告语言")
    parser.add_argument("--mode", default="A", choices=["A", "B"], help="模式A/模式B")
    parser.add_argument("--root", default=None, help="skill 根目录（默认脚本上级目录）")
    parser.add_argument("--list", action="store_true", help="列出全部检查项")
    parser.add_argument("--quiet-waivers", action="store_true", help="不输出 W-00 豁免留痕提示")
    args = parser.parse_args(argv)

    if args.list:
        for code, level, title in CATALOG:
            print(f"[{code}] ({level}) {title}")
        return 0

    if not args.report:
        parser.error("缺少报告文件参数")

    report = Path(args.report)
    if not report.exists():
        print(f"check_report: 文件不存在：{report}", file=sys.stderr)
        return 1

    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    jurisdictions = {j.strip().upper() for j in args.jurisdictions.split(",") if j.strip()}

    lines = read_text(report).splitlines()
    file_waivers, line_waivers = collect_waivers(lines)

    findings = check_report(report, jurisdictions, args.lang, args.mode, root)

    kept: list[Finding] = []
    waived: list[Finding] = []
    for f in findings:
        if f.code in file_waivers or (f.line and f.code in line_waivers.get(f.line, set())):
            waived.append(f)
        else:
            kept.append(f)

    if waived and not args.quiet_waivers:
        kept.append(Finding("W-00", 0, f"存在 {len(waived)} 处行内豁免（留痕，请人工复查是否正当）"))

    kept.sort(key=lambda f: (f.level, f.code, f.line))
    errors = [f for f in kept if f.level == "E"]
    warnings = [f for f in kept if f.level == "W"]

    print(f"=== check_report：{report.name} ===")
    print(f"范围={','.join(sorted(jurisdictions)) or '-'} 语言={args.lang} 模式={args.mode}")
    if not kept:
        print("通过：未发现问题。")
    for f in kept:
        loc = f"L{f.line}" if f.line else "--"
        print(f"[{f.code}] {loc} {f.message}" + (f"  «{f.snippet}»" if f.snippet else ""))
    print(f"--- E 级 {len(errors)} 项 / W 级 {len(warnings)} 项 ---")
    if errors:
        print("结论：存在 E 级问题，**不得交付**，修正后重跑。")
        return 1
    if warnings:
        print("结论：无 E 级；W 级须逐条处置或豁免后方可进入人工门禁。")
        return 2
    print("结论：机器预检通过，请继续人工门禁（SKILL.md §6）。")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
