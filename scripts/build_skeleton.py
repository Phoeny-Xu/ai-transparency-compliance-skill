#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_skeleton.py —— 由结构化问卷答案生成报告骨架

定位
----
阶段4「生成报告」过去完全靠 agent 手工拼表：待核事实清单、角色判定表、义务总览行、
效力核验记录表，四张表的**行集合**其实由答案唯一决定（哪些法域在范围内、哪些环节触发），
行内**结论**才需要判断。本脚本只做前者（机械、可复现），后者一律留 `{待填：…}` 占位。

三条红线（与 P0 一致）
----------------------
1. 不写判断：本脚本不输出任何法律定性文字，只输出表头、行主键与占位符。第三节输出的
   是**字段结构占位**（字段名＋`{待填：…}`）：字段名取自报告模板、非法律判断，字段值一律占位。
2. 不覆盖＋不越过答案级问题：输出文件已存在时默认拒绝写入；答案存在详情不完整、值域无法识别或能力与模态矛盾时默认拒绝生成——两者均须显式 `--force` 放行。
3. 同源：档位、SB 1000 基准等取值直接复用 `resolve_triggers.py` / `lookups.py`，
   不另抄一份规则数据（避免与规则库分叉）。

用法
----
    python build_skeleton.py survey_audit.json                 # 打印到 stdout
    python build_skeleton.py survey_audit.json -o 骨架.md
    python build_skeleton.py survey_audit.json -o 骨架.md --force

骨架态预期机检结果
------------------
骨架是**内容待填**的中间产物。对骨架跑 `check_report.py` 时，**E-02（未找到「范围声明」）与
W-17（未找到「未覆盖维度与转介卡」段）属预期**（由 agent 成稿时补齐，其原文在报告模板中）。
但 **E-03（问卷编号/内部术语）、E-04（正文 blockquote）、E-13（场景法规缺独立效力行）、
W-14（援引法规多于效力表行）、W-19（批注节缺「回填确认记录」）必须为零**——前四类由生成器自身文字/格式产生，第五类靠
本脚本给出具名占位（§4）保障；它们若报警，属本脚本缺陷而非报告缺陷——否则「对骨架跑机检」
者会把脚本问题误当成稿问题。回归见 `tests/test_scripts.py::BuildSkeletonTests`。

输入契约见 `references/survey-audit-schema.md`。
退出码：0=生成成功；1=答案级问题（统计详情不完整、值域无法识别或能力与模态矛盾，须弹窗澄清后重跑）；2=未执行（输入缺失/结构不符/输出已存在且未加 --force）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lookups import ab1609_baseline, forward_nodes_within, sb1000_baseline  # noqa: E402
from resolve_triggers import (
    _a3_generates,
    cross_check_b13_expressive_work_gate,
    cross_check_b13_gate,
    cross_check_capability_modality,
    cross_check_chat_confirmation,
    cross_check_derived_keys,
    cross_check_scale,
    china_connection_points,
    derive_b5b_chat_status,
    resolve_b12_companion_status,
    resolve_b12_human_misidentification_status,
)  # noqa: E402
from survey_io import AuditFormatError, load_audit  # noqa: E402

# ---------------------------------------------------------------------------
# 法域归一
# ---------------------------------------------------------------------------

JURIS_NORM = {
    "中国大陆": "中国大陆",
    "中国": "中国大陆",
    "CN": "中国大陆",
    "欧盟": "欧盟",
    "EU": "欧盟",
    "加州": "加州",
    "美国加州": "加州",
    "CA": "加州",
}

JURIS_ORDER = ["中国大陆", "欧盟", "加州"]

PLACEHOLDER = "{待填：…}"

# 「三、分法域义务详述」每项义务的字段名（顺序与 assets/modeA-report-template.md 字段块一致）。
# 骨架只输出「字段名＋占位值」的结构，不写任何字段值／法律定性。
DUTY_FIELD_LABELS = (
    "责任主体",
    "优先级",
    "生效/适用",
    "技术细则",
    "未合规后果",
    "证据等级",
    "效力状态",
)

# B10 现状盘点（已实施的透明度标识措施）落盘规范值；顺序即骨架列示顺序。
# 仅 A3 含生成模态（非空数组）的产品采集——与 resolve_triggers.TRIGGER_TABLE 的 B10 行
# 同门控（A3 在此是适用性闸门：纯分析型产品不问，避免被迫答语义错误的「尚未实施」）。
B10_VALUES = [
    "界面文字或语音提示",
    "画面角标或可见标记",
    "隐式标识（元数据/水印）",
    "仅合同或条款约定",
    "尚未实施",
]

B10_CHAT_VALUES = [
    "AI交互身份提示",
    "未成年人适龄AI身份提示",
    "长时间互动周期提示",
]
B10_AD_VALUES = ["合成表演者广告披露"]


def relevant_b10_values(answers: dict) -> list[str]:
    """只返回已触发模块对应的现状盘点值，避免未适用措施进入差距表。"""
    values = list(B10_VALUES)
    # B-11′：权威值由代码重算（卡未进入判定 → not_triggered），不直读落盘派生键
    if resolve_b12_companion_status(answers) in {"yes", "conditional"}:
        values.extend(B10_CHAT_VALUES)
    b13 = answers.get("B13")
    if isinstance(b13, dict) and b13.get("role") in {
        "creator", "advertising_medium", "both", "unknown"
    }:
        values.extend(B10_AD_VALUES)
    return values

# 各法域效力核验记录表的法规行（机械化，来自各自规则库覆盖范围）
VERIFY_ROWS = {
    "中国大陆": [
        ("《互联网信息服务深度合成管理规定》", "现行有效"),
        ("《生成式人工智能服务管理暂行办法》", "现行有效"),
        ("《人工智能生成合成内容标识办法》", "现行有效"),
        ("GB 45438-2025《网络安全技术 人工智能生成合成内容标识方法》", "现行有效"),
    ],
    "欧盟": [
        ("Regulation (EU) 2024/1689（AI Act）Art. 50", "现行有效"),
        ("Digital Omnibus Reg. (EU) 2026/1744", "已生效（2026-07-27）"),
        ("《AI生成内容透明度行为准则》（CoP）", "非约束性准则；按报告日核验版本与签署状态"),
    ],
    "加州": [
        ("B&P Code §§22757–22757.6（SB 942 经 AB 853 修正）", "已生效（2026-08-02）"),
    ],
}


def normalise_jurisdictions(raw: object) -> list[str]:
    """把 A6 的原始取值归一为有序法域列表（只作触发条件）。"""
    out: list[str] = []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return out
    for item in raw:
        key = JURIS_NORM.get(str(item).strip())
        if key and key not in out:
            out.append(key)
    return [j for j in JURIS_ORDER if j in out]


# ---------------------------------------------------------------------------
# 待核事实清单（三列）
# ---------------------------------------------------------------------------


def pending_facts(answers: dict) -> list[tuple[str, str, str]]:
    """从答案里挑出「不确定」项，机械展开为待核事实行（不含法律定性）。

    注：历史上接收过一个 `jurisdictions` 形参，但函数体从未使用（量级遍历直接走
    `A4a.items()`，不依赖外部法域列表），已于 2026-09-17 移除，避免误导维护者。
    """
    rows: list[tuple[str, str, str]] = []
    a4a = answers.get("A4a") or {}
    if isinstance(a4a, dict):
        for juris, band in a4a.items():
            if str(band).strip() == "不确定":
                rows.append(
                    (
                        f"{juris}的月活/用户量级档位未确认",
                        f"{juris}适用性所依赖的规模门槛是否达到",
                        "业务方（运营数据）/最近一期统计口径说明",
                    )
                )

    if str(answers.get("B3a", "")).strip() == "不确定":
        rows.append(
            (
                "产品 monthly visitors or users 是否超100万（统计地域、窗口和去重方法待核）",
                "加州 covered provider 主体门槛是否达到",
                "业务方（系统访客/用户统计详情）/统计报表与口径说明",
            )
        )
    elif answers.get("B3a") and not answers.get("B3a_details"):
        rows.append(
            (
                "B3a统计详情（访客/用户、地域、周期、去重和原始数值）缺失",
                "加州 covered provider 100万门槛的统计口径是否可审计",
                "业务方（产品/运营数据）/统计报表与口径说明",
            )
        )

    if str(answers.get("B4_2c", "")).strip() == "不确定":
        rows.append(
            (
                "内容传播平台此前12个月逐月独立用户量级",
                "加州 large online platform 量级关是否通过",
                "业务方（平台侧逐月独立用户）/统计口径说明",
            )
        )
    elif answers.get("B4_2c") and not answers.get("B4_2c_details"):
        rows.append(
            (
                "B4②平台此前12个月逐月独立用户详情缺失",
                "加州 large online platform 200万门槛的时间窗口、统计对象和聚合方式",
                "业务方（平台分析报表）/逐月用户数据与去重方法",
            )
        )
    platform_details = answers.get("B4_2c_details")
    if isinstance(platform_details, dict):
        monthly = platform_details.get("monthly_values")
        if isinstance(monthly, list) and len(monthly) != 12:
            rows.append(
                (
                    "B4②平台逐月数据未覆盖完整此前12个月",
                    "large online platform 200万门槛的完整观察窗口",
                    "业务方（平台分析报表）/补齐缺失月份并说明原因",
                )
            )

    a4c = answers.get("A4c") or {}
    if isinstance(a4c, dict):
        for juris, factors in a4c.items():
            if "尚未核实" in factors or "不确定" in factors:
                rows.append(
                    (
                        f"{juris}法域连接点辅助因素尚未核实",
                        f"{juris}法域适用性事实的证据完整性",
                        "业务方（运营、商店、支付、实体和营销资料）/法务确认",
                    )
                )

    # B1_3／B1_4 的「不确定」：与 overview_rows 的门控配套，须同时出现行与待核行。
    if str(answers.get("B1_3", "")).strip() == "不确定":
        rows.append(
            (
                "是否通过网站或应用向他人提供模型权重或源码下载",
                "加州 GenAI hosting platform 主体是否成立（§22757.1(g)）",
                "业务方（官网/下载入口）/产品与法务确认",
            )
        )

    if str(answers.get("B1_4", "")).strip() == "不确定":
        rows.append(
            (
                "是否自身运营应用程序分发平台或应用商店",
                "中国应用程序分发平台（环节⑤）主体是否成立",
                "业务方（产品线/商店运营方）/法务确认",
            )
        )

    if str(answers.get("B6", "")).strip() == "不确定":
        rows.append(
            (
                "贵司是否自身发布以向公众通报公共利益事项为目的的AI生成文本",
                "欧盟 Art. 50(4) 公共利益文本披露义务是否触发",
                "业务方（内容发布渠道/编辑流程）/法务确认",
            )
        )

    # B-7（2026-09-23）：Art. 50(4) 第 1-2 项（深度伪造）与 B6（第 3 项·公共利益文本）
    # 同卡采集、独立落盘；「不确定」按最严口径列入待核（列待核范围，非推定成立）。
    if str(answers.get("B6_deepfake", "")).strip() == "不确定":
        rows.append(
            (
                "贵司生成/篡改的图像、音频或视频是否构成深度伪造（描绘可辨识自然人或可被误认为真实的事件）",
                "欧盟 Art. 50(4) 第1-2项深伪披露义务是否触发",
                "业务方（内容形态/素材来源）/法务确认",
            )
        )

    if str(answers.get("A2", "")).strip() == "不确定":
        rows.append(
            (
                "服务对象是B2C还是B2B（是否向不特定企业开放注册）",
                "内容是否流向公众，影响中国算法备案与安全评估的法定触发状态",
                "业务方（客户类型）/销售合同样本",
            )
        )

    a4b = answers.get("A4b") or {}
    if isinstance(a4b, dict) and str(a4b.get("中国", "")).strip() == "不确定":
        rows.append((
            "中国大陆主动提供/被动可达事实",
            "中国境内应用深度合成技术与向境内公众提供生成式服务的连接点",
            "业务方（营销、注册、支付、语言界面、境内实体）/业务与法务确认",
        ))
    for key, label, effect in (
        ("B8_1", "产品生成或承载内容是否面向公众传播", "中国算法备案与安全评估的内容去向事实"),
        ("B8_2", "生成内容是否涉及新闻资讯、公共议题或社会热点类信息", "中国算法备案与安全评估的内容属性事实"),
        ("B8_3", "中国境内终端消费者量级", "中国算法备案与安全评估的规模事实"),
        ("B8_4", "算法备案和安全评估实施状态", "中国非透明度义务的已实施状态"),
        ("B9", "是否具备情感识别或生物特征分类功能", "欧盟 Art. 50(3) 条件式义务"),
    ):
        if str(answers.get(key, "")).strip() in {"不确定", ""} and key in answers:
            rows.append((label, effect, "业务方/产品文档/法务确认"))

    if resolve_b12_companion_status(answers) == "conditional":
        rows.append((
            "陪伴型聊天机器人定义或排除要件尚未确认",
            "加州陪伴型聊天机器人场景义务是否适用",
            "产品、运营与法务/功能说明、交互样例及访问政策",
        ))
    if resolve_b12_human_misidentification_status(answers) == "conditional":
        rows.append((
            "理性人是否可能误认正在与真人互动尚待核实",
            "加州聊天机器人AI身份通知义务是否触发",
            "产品与法务/交互开场、身份线索及界面样例",
        ))
    b13 = answers.get("B13")
    if isinstance(b13, dict) and b13.get("role") == "unknown":
        rows.append((
            "广告活动中的创作者或广告媒介角色尚未确认",
            "加州合成表演者广告规则的适用路径",
            "营销、广告运营与法务/广告制作及投放合同",
        ))
    recheck = answers.get("AB1609_recheck")
    if isinstance(recheck, dict) and recheck.get("recheck_required") is True:
        rows.append((
            "全美总年营收接近AB 1609门槛，须在复评节点取得新数据",
            "AB 1609如生效后的主体门槛是否达到",
            f"财务与法务/{recheck.get('recheck_by', '下一财年数据可得后')}",
        ))

    # agent2（2026-09-28）：4a 前置分流——存在作品广告时，(d)(4) 例外两要件待核
    b13 = answers.get("B13")
    if isinstance(b13, dict):
        ew_present = b13.get("expressive_work_ad_present")
        role = b13.get("role")
        if ew_present in {"yes", "unknown"} and role in {"creator", "both"}:
            rows.append((
                "表现性作品例外两要件（是否为作品广告＋用法是否与作品本体内一致）",
                "加州合成表演者广告披露义务是否因 §17610(d)(4) 例外不适用",
                "广告制作团队/广告成片与作品本体素材",
            ))

    if not rows:
        rows.append(("（本次无不确定项，无需待核）", PLACEHOLDER, PLACEHOLDER))
    return rows


# ---------------------------------------------------------------------------
# 现状盘点（B10）：已实施措施机械列示＋集合差（不做任何法律定性）
# ---------------------------------------------------------------------------

def current_practices_block(answers: dict) -> list[str]:
    """现状盘点（B10）块：生成型产品（A3 非空）机械列示已实施措施与待补齐类别。

    只做机械列示与集合差，不写任何法律定性：
    - A3 为空（纯分析型）→ 返回空列表（B10 未触发，整块不生成，不写「尚未实施」误导）；
    - A3 非空而未采集 B10 → 头部＋「未采集现状盘点」占位（报告模板要求不得留空误导）；
    - 仅含「尚未实施」→ 写提示句；与其余规范值并存 → 按部分实施列示（schema 容错口径）；
    - 待补齐列＝值域中未填报的措施类别占位（义务主题由 agent 补全）；
    - 填报值不在规范值域 → 打印 **stderr** 诊断（须弹窗澄清归一后重跑，见 schema「B10 取值域」）；
      不写进报告——该提示是数据质量诊断而非报告内容。
    """
    if not _a3_generates(answers):
        return []

    raw = answers.get("B10_current_practices")
    if isinstance(raw, (list, tuple)):
        values = [str(v).strip() for v in raw]
    elif isinstance(raw, str) and raw.strip():
        values = [raw.strip()]
    else:
        values = []

    if not values:
        return [
            "### 现状盘点（已实施 vs 待补齐）",
            "",
            "未采集现状盘点，不得留空误导为「已全覆盖」。",
            "",
        ]

    applicable_values = relevant_b10_values(answers)
    known = [v for v in values if v in applicable_values]
    unknown = [v for v in values if v not in applicable_values]

    if known == ["尚未实施"]:
        done = "尚未实施任何透明度标识措施"
    else:
        shown = [v for v in known if v != "尚未实施"]
        done = "、".join(shown) if shown else "（无）"
        if "尚未实施" in known and shown:
            done += "（另填报「尚未实施」，按部分实施处理）"

    todo = [v for v in applicable_values if v != "尚未实施" and v not in known]
    todo_cell = (
        "；".join(v + "：" + PLACEHOLDER for v in todo) if todo else "（已填报全部措施类别）"
    )

    lines: list[str] = []
    lines.append("### 现状盘点（已实施 vs 待补齐）")
    lines.append("")
    lines.append("| 已实施措施（自述，待核验） | 待补齐项（建议，非法律结论） |")
    lines.append("|---|---|")
    lines.append("| " + done + " | " + todo_cell + " |")
    if unknown:
        # 数据质量诊断，非报告内容 → 走 stderr，不进报告。
        # 若写进报告，正文会同时触发 E-03（含问卷编号 B10）与 E-04（blockquote 承载内容），
        # 使「对骨架跑机检」者把生成器自身的排版缺陷误判为报告缺陷。
        print(
            "[build_skeleton] 填报值不在规范值域内：" + "、".join(unknown)
            + "（须弹窗澄清并归一至规范值后重跑，见 references/survey-audit-schema.md「B10 取值域」）",
            file=sys.stderr,
        )
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# 义务总览行（价值链环节由答案机械决定，法域单元格留占位）
# ---------------------------------------------------------------------------


def overview_rows(answers: dict, jurisdictions: list[str]) -> list[tuple[str, dict[str, str]]]:
    """按价值链环节生成总览行；单元格一律占位，不做定性。"""
    rows: list[tuple[str, dict[str, str]]] = []

    a1 = str(answers.get("A1", ""))
    if "自研" in a1 and "部分" not in a1:
        rows.append(("模型自研自训", {}))
    elif "部分自研" in a1:
        rows.append(("模型自研自训（部分）", {}))
    if "授权接入" in a1 or "开源微调" in a1:
        rows.append(("上游模型接入", {}))

    rows.append(("应用服务提供", {}))

    if str(answers.get("B1_hardware", "")).lower() in {"true", "是"}:
        rows.append(("硬件设备制造（采集设备）", {}))
    # B1_3／B1_4 与 B4_2 同为「是否运营某主体角色」的定性关：门控统一认「是/不确定」。
    # 「不确定」按 B 组全局「不确定（按最严口径）」保守出行（行＋待核同时出现＝列入待核
    # 范围、非推定成立；待核行见 pending_facts）。仅认「是」会让「不确定」路径在行集合
    # 与待核清单双双为空（V3-03 残留缺陷）。
    if str(answers.get("B1_3", "")).strip() in {"是", "不确定"}:
        rows.append(("生成式人工智能系统托管平台运营（下载站）", {}))
    if str(answers.get("B1_4", "")).strip() in {"是", "不确定"}:
        rows.append(("应用程序分发平台运营", {}))
    if str(answers.get("B4_2", "")).strip() in {"是", "不确定"}:
        rows.append(("内容传播平台运营", {}))
    if resolve_b12_companion_status(answers) in {"yes", "conditional"}:
        rows.append(("陪伴型聊天机器人平台运营", {}))
    b13 = answers.get("B13")
    if isinstance(b13, dict):
        role = b13.get("role")
        if role in {"creator", "both", "unknown"}:
            rows.append(("合成表演者广告制作与发布", {}))
        if role in {"advertising_medium", "both", "unknown"}:
            rows.append(("第三方广告传播媒介运营", {}))

    # 补占位：每行按在范围内的法域填占位（加州列若不在范围写「不适用（本次范围未含）」）
    filled: list[tuple[str, dict[str, str]]] = []
    for name, _ in rows:
        cells: dict[str, str] = {}
        for juris in JURIS_ORDER:
            if juris in jurisdictions:
                cells[juris] = PLACEHOLDER
            else:
                cells[juris] = "不适用（本次范围未含）"
        filled.append((name, cells))
    return filled


# ---------------------------------------------------------------------------
# 骨架渲染
# ---------------------------------------------------------------------------


def render(answers: dict, report_name: str) -> str:
    jurisdictions = normalise_jurisdictions(answers.get("A6"))
    if not jurisdictions:
        raise ValueError("A6（法域范围）为空或无法识别，至少需含一个法域")

    session_date = str(answers.get("session_date", "")).strip() or "{待填：日期}"
    lines: list[str] = []

    # agent2（2026-09-28）：交付偏好（A8）读取与默认标志。
    # 报告配置只能来自两条合法路径：A8 采集键，或 defaults_applied 标志＋批注留痕；
    # 不存在第三条路（阶段4 现场弹窗追问）。
    defaults_applied: list[str] = []
    lang_raw = str(answers.get("A8_report_language", "")).strip()
    if lang_raw in {"纯中文", "中英双语"}:
        report_language = lang_raw
    else:
        report_language = "纯中文"
        defaults_applied.append("report_language")
    foot_raw = str(answers.get("A8_footnote_original_text", "")).strip()
    if foot_raw in {"是", "否"}:
        footnote_pref = foot_raw
    else:
        footnote_pref = "否"
        defaults_applied.append("footnote_original_text")
    lines.append(
        f"<!-- agent2-report-config: language={report_language}; "
        f"footnote_original_text={footnote_pref}; "
        f"defaults_applied={','.join(defaults_applied) if defaults_applied else 'none'} -->"
    )

    lines.append(f"# {PLACEHOLDER}AI透明度合规义务清单（{'／'.join(jurisdictions)}）")
    lines.append("")
    lines.append("<!-- 本骨架由 scripts/build_skeleton.py 生成：只含表头、行主键与占位符，")
    lines.append(f"     不构成任何法律定性。来源答案：{report_name}。生成后请人工补齐 `{{待填：…}}`。 -->")
    lines.append("")
    lines.append(f"> 生成日期：{session_date} ｜ 效力核验日期：{{待填：日期}}")
    lines.append("")

    # 报头·临近节点提示（独立块形态）：仅当生成日距前瞻节点 ≤60 天时输出，
    # 否则整块不生成（对齐 references/validity-checklist.md「前瞻节点提醒」）。
    # 节点表同源于 lookups.py FORWARD_NODES，不另抄一份。
    upcoming = forward_nodes_within(session_date)
    if upcoming:
        lines.append("> **临近节点提示**：报告生成日距下列前瞻节点不足 60 天，请优先排期——")
        for node_date, item, target in upcoming:
            lines.append(f"> - {node_date}：{item}（影响对象：{target}）")
        lines.append("")

    # 一、画像摘要与角色判定
    lines.append("## 一、画像摘要与角色判定")
    lines.append("")
    lines.append(f"{{待填：用户画像一段话摘要；含各法域适用性结论（主动提供/被动可达的判定）}}")
    lines.append("")
    lines.append("**待核事实清单**")
    lines.append("")
    lines.append("| 待核事实 | 若成立则触发义务 | 待核人/材料 |")
    lines.append("|----------|------------------|-------------|")
    for fact, effect, owner in pending_facts(answers):
        lines.append(f"| {fact} | {effect} | {owner} |")
    lines.append("")
    lines.append("| 法域 | 判定角色 | 判定依据（双锚定：定义条款＋义务条款） |")
    lines.append("|------|----------|----------|")
    for juris in jurisdictions:
        lines.append(f"| {juris} | {PLACEHOLDER} | {PLACEHOLDER} |")
    lines.append("")

    # 现状盘点（B10）：A3 非空（生成型）时机械列示；纯分析型不生成该块（B10 未触发）。
    lines.extend(current_practices_block(answers))

    # 二、义务总览
    lines.append("## 二、义务总览（价值链环节×法域）")
    lines.append("")
    header = "| 价值链环节 | " + " | ".join(JURIS_ORDER) + " | 最迟履行节点 | 优先级 |"
    lines.append(header)
    lines.append("|" + "------------|" * (len(JURIS_ORDER) + 3))
    for name, cells in overview_rows(answers, jurisdictions):
        cells_line = " | ".join(cells[j] for j in JURIS_ORDER)
        lines.append(f"| {name} | {cells_line} | {PLACEHOLDER} | {PLACEHOLDER} |")
    lines.append("")

    # 三节结构占位（字段名取自模板，字段值一律 {待填：…}；不写任何法律定性）
    # 每项义务输出「**(n) 义务名称** ＋ 依据句 ＋ 字段块」；字段块使骨架态即满足 E-10/E-11
    # 的字段结构要求（字段值仍待填）。每个法域节末附「角色间义务关系说明」占位——承载
    # references/role-mapping.md「多环节叠加规则」中「多角色义务叠加/转致/联动」说明
    # （此前仅存于规则库、模板与骨架均无承载，属纸面门禁）。
    lines.append("## 三、分法域义务详述")
    lines.append("")
    for juris in jurisdictions:
        lines.append(f"### {juris}")
        lines.append("")

        layer_titles = [None]
        if juris == "加州":
            # 加州节四层中的第一层采用CAITA自身的来源披露与检测语境。
            # /(二)场景披露义务（多部单行法逐法独立判定）/(三)关联非透明度义务
            # /(四)本次评估范围外义务核验。与 README「两条并列路径」及 modeB 十三维对齐。
            layer_titles = [
                "（一）CAITA生成内容来源披露与检测义务",
                "（二）场景披露义务",
                "（三）关联非透明度义务",
            ]
        for layer_title in layer_titles:
            if layer_title:
                lines.append(f"#### {layer_title}")
                lines.append("")
            lines.append("**(1) {待填：义务名称}**")
            lines.append("")
            lines.append("根据{待填：法规名与条号}，{待填：义务内容}。")
            lines.append("")
            for label in DUTY_FIELD_LABELS:
                lines.append(f"- {label}：{PLACEHOLDER}")
            lines.append("")

        if juris == "欧盟":
            lines.append("**M{待填：Measure编号} {待填：措施名}**[^cop_s{待填}_c{待填}_m{待填}]")
            lines.append("")
            lines.append(f"- **层级**：{PLACEHOLDER}")
            lines.append(f"- **要求内容**：{PLACEHOLDER}")
            lines.append("- **技术与操作要点**：")
            lines.append(f"  1. {PLACEHOLDER}")
            lines.append(f"  2. {PLACEHOLDER}")
            lines.append("")
            lines.append("<!-- cop:item id={待填：注册表ID} points={待填：正文已覆盖的注册点} -->")
            lines.append("")
            lines.append(
                "[^cop_s{待填}_c{待填}_m{待填}]: 《AI生成内容透明度行为准则》"
                "Section {待填}，Commitment {待填}，Measure {待填}；对应AI Act Art. 50({待填})。"
            )
            lines.append("")

        if juris == "加州":
            lines.append("#### （四）本次评估范围外义务核验")
            lines.append("")
            lines.append("{待填：按out-of-scope-pointer.md列出需另行专项评估的相关维度}")
            lines.append("")
        lines.append(
            "**角色间义务关系说明**："
            "{待填：多角色时逐条说明义务叠加／转致／联动；仅单一角色时写「无角色间义务关系需说明」}"
        )
        lines.append("")

    # 四、罚则对比（行主键固定三地，但只列在范围内的法域）
    lines.append("## 四、三地罚则对比")
    lines.append("")
    lines.append("| 法域 | 罚则 | 执法主体 | 依据 |")
    lines.append("|------|------|----------|------|")
    for juris in jurisdictions:
        if juris == "加州":
            lines.append(f"| 加州CAITA | {PLACEHOLDER} | {PLACEHOLDER} | {PLACEHOLDER} |")
            lines.append(f"| 加州场景法规（实际引用时逐法分行） | {PLACEHOLDER} | {PLACEHOLDER} | {PLACEHOLDER} |")
        else:
            lines.append(f"| {juris} | {PLACEHOLDER} | {PLACEHOLDER} | {PLACEHOLDER} |")
    lines.append("")

    # 五、落地建议
    lines.append("## 五、落地建议（基于上文法定义务的跨法域落地措施）")
    lines.append("")
    lines.append(f"### 主题一：{PLACEHOLDER}")
    lines.append("")
    lines.append(f"- **覆盖义务**：{PLACEHOLDER}")
    lines.append(f"- **控制目标**：{PLACEHOLDER}")
    lines.append("- **实施动作**：")
    lines.append(f"  1. {PLACEHOLDER}")
    lines.append(f"  2. {PLACEHOLDER}")
    lines.append(f"- **责任分工**：主责：{PLACEHOLDER}；协同：{PLACEHOLDER}")
    lines.append(f"- **优先级与节点**：{PLACEHOLDER}")
    lines.append(f"- **验收证据**：{PLACEHOLDER}")
    lines.append(f"- **条件与依赖**：{PLACEHOLDER}（无条件或外部依赖时删除本行）")
    lines.append("<!-- cop:recommendation theme={待填：ASCII主题键} duties={待填：逗号分隔的义务ID} -->")
    lines.append("")

    # 六、效力核验记录（★强制）
    lines.append("## 六、效力核验记录（★强制节，任何报告不得省略）")
    lines.append("")
    lines.append("| 法规 | 效力状态 | 核验日期 | 核验来源 |")
    lines.append("|------|----------|----------|----------|")
    for juris in jurisdictions:
        for name, status in VERIFY_ROWS[juris]:
            lines.append(f"| {name} | {status} | {session_date} | {PLACEHOLDER} |")
    if "加州" in jurisdictions:
        chat_status = derive_b5b_chat_status(answers)
        if chat_status in {"yes", "unknown"}:
            lines.append(f"| B&P Code §§17940–17943（BOT Act） | 现行有效 | {session_date} | {PLACEHOLDER} |")
        if resolve_b12_companion_status(answers) in {"yes", "conditional"}:
            lines.append(f"| SB 243（B&P Code §§22601–22604） | 现行有效 | {session_date} | {PLACEHOLDER} |")
            lines.append(f"| SB 867（§22601定义修订） | 已制定；按报告日核验生效状态 | {session_date} | {PLACEHOLDER} |")
            lines.append(f"| SB 1119（B&P Code §§21810.5–21815及§22602修订） | 按条款级时间状态核验 | {session_date} | {PLACEHOLDER} |")
        b13 = answers.get("B13")
        if isinstance(b13, dict) and b13.get("role") in {
            "creator", "advertising_medium", "both", "unknown"
        }:
            lines.append(f"| SB 1050（合成表演者广告） | 已制定；2027-01-01生效 | {session_date} | {PLACEHOLDER} |")
        if answers.get("AB1609_status"):
            ab1609 = ab1609_baseline(str(answers["AB1609_status"]))
            lines.append(
                f"| AB 1609（客服机器人，监控项） | {ab1609['annotation']} | "
                f"{session_date} | {PLACEHOLDER} |"
            )
        # SB 1000 行由效力状态开关机械决定（同源于 lookups.py）
        status_raw = answers.get("SB1000_status", "不确定")
        baseline = sb1000_baseline(str(status_raw))
        lines.append(
            "| 加州 SB 1000（CAITA 修正案） | "
            f"{baseline['annotation']} | {session_date} | "
            "https://leginfo.legislature.ca.gov/faces/billHistoryClient.xhtml?bill_id=202520260SB1000 |"
        )
        if str(status_raw).strip() in {"", "不确定"}:
            lines.append("**待核事实**：SB 1000 签署/否决状态未采集，不能默认按待签署处理；应当联网核验后确定义务基准。")
        lines.append("")
        # 正文禁 blockquote（E-04）：改普通加粗段；且不写内部脚本名（属报告外实现细节）。
        # 措辞不得新引入「效力核验表未登记」的法规名/条号——否则本行会触发 W-14（覆盖率）。
        # B-5（2026-09-23）：渲染人类可读基准名，内部 token（SB942_AB853/SB1000）不进交付物
        baseline_readable = baseline.get("readable") or baseline["baseline"]
        lines.append(
            f"**义务基准**：{baseline_readable}"
            "（依加州 §22757 效力状态开关确定，随 SB 1000 签署状态切换）"
        )
    lines.append("")

    # 批注（推理承载区，交付 docx 时转 Word 批注）
    lines.append("---")
    lines.append("")
    lines.append("## 批注（判断过程、思路与假设）")
    lines.append("")
    lines.append("### 1. 角色判定推理（双锚定）")
    for juris in jurisdictions:
        lines.append(f"- {juris}：{PLACEHOLDER}")
    lines.append("")
    lines.append("### 2. 前置判断与适用性结论")
    lines.append(f"- {PLACEHOLDER}")
    lines.append("")
    lines.append("### 3. 假设与不确定项")
    lines.append("| 矛盾点/不确定项 | 拟采用结论（最严口径） | 后续动作 |")
    lines.append("|--------|-----------|----------|")
    lines.append(f"| {PLACEHOLDER} | {PLACEHOLDER} | {PLACEHOLDER} |")
    lines.append("")
    lines.append("### 4. 特定规则适用说明")
    # 回填确认记录为 W-19 的机器检查锚点（模式A 批注节须含该条目，模板 §4 同名条目）：
    # 具名占位使骨架态即满足条目存在性，缺项不再靠记忆。
    lines.append(f"- **回填确认记录**：{PLACEHOLDER}")
    if defaults_applied:
        # agent2（2026-09-28）：交付偏好缺键时的默认采用留痕（check_report 一致性检查锚点）。
        lines.append(
            f"- **交付偏好默认采用记录**：{('、'.join(defaults_applied))} 未采集（用户跳过），"
            "按默认规则执行（纯中文＋正文以条号援引）；如需调整请在报告定稿前告知。"
        )
    lines.append(f"- {PLACEHOLDER}")
    lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def load_answers(path: Path) -> dict:
    """读取结构化答案。

    读取逻辑统一在 `scripts/survey_io.py`（与 resolve_triggers 共用一处实现，
    避免两条维护线再次分叉）。本函数只是保留旧名以兼容既有调用。
    """
    return load_audit(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="由 survey_audit.json 生成报告骨架")
    parser.add_argument("survey", help="survey_audit.json（结构化问卷答案）")
    parser.add_argument("-o", "--out", help="输出文件；缺省打印到 stdout")
    parser.add_argument(
        "--force",
        action="store_true",
        help="双语义放行：①允许覆盖已存在的输出文件；②答案存在答案级校验问题时仍强行生成",
    )
    args = parser.parse_args(argv)

    path = Path(args.survey)
    try:
        answers = load_answers(path)
        text = render(answers, path.name)
    except (AuditFormatError, ValueError, KeyError) as exc:
        print(f"build_skeleton: 无法读取答案（未执行）：{exc}", file=sys.stderr)
        return 2

    # 答案级交叉校验（复用 resolve_triggers 的同源实现）：
    #   ①规模详情完整性（旧摘要不作跨字段硬性比较）；② B5a 高仿真能力×A3 输出模态（防过度勾选）。
    # 有矛盾（或校验未执行）时默认拒绝生成（exit=1，对齐 resolve_triggers「1=答案级问题」），
    # 须显式 --force 才放行——防矛盾答案静默进入骨架产物。
    try:
        problems = cross_check_scale(answers) + cross_check_capability_modality(answers)
        problems += cross_check_b13_gate(answers)
        problems += cross_check_b13_expressive_work_gate(answers)
        problems += cross_check_chat_confirmation(answers)
        derived_errors, derived_warnings = cross_check_derived_keys(answers)
    except Exception as exc:  # noqa: BLE001 - 校验失败视为「未执行」，同样不静默放行
        problems = [f"（答案级交叉校验未执行：{exc}）"]
        derived_warnings = []
    # B-11′：派生键「落盘更宽（少报）」属答案级矛盾，与上述问题同等拒绝；
    # 「落盘更严（多报，人工保守）」只留痕放行（骨架按较严值出行）。
    problems += derived_errors
    for w in derived_warnings:
        print(f"[~] {w}", file=sys.stderr)
    for p in problems:
        print(f"[!] {p}", file=sys.stderr)
    if problems and not args.force:
        print(
            "build_skeleton: 检测到答案级问题（统计详情不完整／值域无法识别／能力与模态矛盾／"
            "派生键落盘更宽／校验未执行），拒绝生成"
            "（须弹窗澄清并修订 answers；加 --force 可强行生成）",
            file=sys.stderr,
        )
        return 1

    if args.out:
        out = Path(args.out)
        if out.exists() and not args.force:
            print(
                f"build_skeleton: 输出已存在，拒绝覆盖（未执行，加 --force）：{out}",
                file=sys.stderr,
            )
            return 2
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"build_skeleton: 已写入 {out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
