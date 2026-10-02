#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resolve_triggers.py —— B 组触发引擎 与 问卷答案级交叉校验

定位
----
`assets/modeA-questionnaire.md` 的「B组触发总览表（11 行）」是纯布尔式，过去靠 agent 每轮
复述条件。本脚本把它落成可执行函数：agent 只需喂答案（结构化 JSON），不再复述条件。

三条元规则也被代码锁死
----------------------
1. **触发条件不得锚 A4**（modeA-questionnaire 顶部「触发条件锚定规则（防漂移）」）：A4 对三法域
   逐一采集事实、不设勾选跳过，故「A4含X」恒为真、不能作触发条件。见 `TRIGGER_TABLE`
   的 `depends_on` 字段与 `assert_conditions_not_anchored_on_a4()`。
   注：该规则约束的是「是否问某道 B 题」，不限制答案级校验对 A4 详情的完整性检查；不同统计口径不得直接比较。
2. **规模字段只有在统计对象、地域、周期和去重方法明确且一致时才可比较**；旧版摘要字段缺少这些信息时，不得把全球与法域档位直接比较。
3. **内部不变量**：`TRIGGER_TABLE` 中标注 `always=True` 的行（B2）必须解析为触发。
   该断言的作用是防「答案根本没读到」被当成「答案无矛盾」：案例16-18 轮发现，若输入
   结构不符（如按文档样例落盘而脚本未解包 answers），全部触发行会静默塌成 1 行。
4. **B5a 勾选的高仿真能力必须与 A3 输出模态相容**（2026-09-19 新增，单向防过度勾选）：
   纯文本产品误勾「数字人／人脸生成／沉浸式拟真场景」等客观不可能的组合即报警。
   反方向（A3 含模态而 B5a 未勾）不代码化——「风景图／无人脸视频」可合法不勾，
   属人工按 modeA-questionnaire「B5a判定备注」五条映射追问的范畴。

用法
----
    python resolve_triggers.py survey_audit.json
    python resolve_triggers.py --demo

输入契约见 `references/survey-audit-schema.md`，读取统一走 `scripts/survey_io.py`
（嵌套与扁平两种结构都收，读取失败硬失败、不静默降级）。

退出码
------
    0 = 通过
    1 = 答案级问题（档位交叉矛盾、能力与模态矛盾，或答案值无法识别——须弹窗澄清后修订 answers）
    2 = 未执行（输入缺失、结构不符、JSON 解析失败、内部不变量违反）
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import survey_io  # noqa: E402  （统一读取，见 survey_io 模块头）

# ---------------------------------------------------------------------------
# 档位序数（仅用于各自摘要字段的范围检查；不同统计口径不得直接比较）
# ---------------------------------------------------------------------------

SCALE_ORDINAL = {
    "0": 0,
    "趋零": 0,
    "0/趋零": 0,
    "<1万": 1,
    "1-10万": 2,
    "10-100万": 3,
    "100万-1000万": 4,
    "1000万+": 5,
}

# B3a 档位覆盖的序数区间
B3A_RANGE = {
    "≤100万": (0, 3),
    "<=100万": (0, 3),
    ">100万": (4, 5),
    "不确定": None,
}

# B4_2c（内容传播平台过去 12 个月独立月用户）档位序数
B4_2C_ORDINAL = {
    "≤100万": 3,
    "<=100万": 3,
    "100万-200万": 4,
    ">200万": 5,
}

# B3a 合法统计口径闭集（锚定 §22757.1(d) "monthly visitors or users"；V3-02 口径锁）
# 同义变体按落盘惯例放行；累计/非月度口径（downloads、registrations 等）一律闭集外。
B3A_METRIC_ALLOWED = {
    "mau",                # 月活跃用户
    "monthly_users",      # 月用户
    "monthly_visitors",   # 月访客
    "users",              # 月用户（落盘同义形态）
    "visitors",           # 月访客（落盘同义形态）
    "users/visitors",     # 月用户或月访客
}

NATIONAL = {"中国", "中国大陆", "CN", "欧盟", "EU", "加州", "CA", "美国加州"}


# ---------------------------------------------------------------------------
# 触发表（声明式；depends_on 用于「不得锚 A4」断言）
# ---------------------------------------------------------------------------


def _a6_has(answers: dict, name: str) -> bool:
    values = answers.get("A6", [])
    if isinstance(values, str):
        values = [values]
    return any(name in str(v) for v in values)


def _a3_modalities(answers: dict) -> list[str]:
    """读取拆分后的输出模态；旧 v1 答案回退到 A3。"""
    values = answers.get("A3_modalities")
    if values is None:
        values = answers.get("A3") or []
    if isinstance(values, str):
        values = [values]
    return [str(value).strip() for value in values if str(value).strip()]


def _a3_generates(answers: dict) -> bool:
    """只有功能明确含生成时才视为生成式产品；v1 A3 非空仍按旧语义迁移。"""
    functions = answers.get("A3_functions")
    if functions is None:
        return bool(_a3_modalities(answers))
    if isinstance(functions, str):
        functions = [functions]
    return any(any(token in str(item) for token in ("生成", "生成式", "生成内容")) for item in functions)


def _a3_any(answers: dict, keys: tuple[str, ...]) -> bool:
    return any(any(k in value for k in keys) for value in _a3_modalities(answers))


# B5b 交互布尔的显式值域（N-6，2026-09-19）：缺省 True（最严口径，与
# modeA-questionnaire-business「`B5b_interactive` 派生规则」一致：仅「无自然人直接交互界面」
# 为 false，其余含「不确定」皆为 true）。若该键被落盘为字符串（如「否」），裸 `bool("否")`
# 恒为 True 会静默误触发；故显式判值域，只有真·假值才判 False。
_B5B_FALSE_STRINGS = frozenset({"否", "false", "no", "n", "0", "无", "不"})


def _b5b_interactive(answers: dict) -> bool:
    value = answers.get("B5b_interactive")
    if value is None:
        return True  # 未采集 → 最严口径（触发），不得因缺键静默漏采
    if isinstance(value, str):
        return value.strip().lower() not in _B5B_FALSE_STRINGS
    return bool(value)


def derive_b5b_chat_status(answers: dict) -> str | None:
    """派生加州B12路由用的聊天状态；EU-only不落盘该派生键。"""
    if not _a6_has(answers, "加州"):
        return None
    raw = answers.get("B5b")
    if not isinstance(raw, list) or not raw:
        return "unknown"
    values = {str(item).strip() for item in raw if str(item).strip()}
    if any(any(token in value for token in ("聊天机器人", "智能助手", "客服机器人")) for value in values):
        return "yes"
    if any("不确定" in value for value in values):
        return "unknown"
    if any(value.startswith("其它") for value in values):
        confirmed = answers.get("B5b_other_chat_confirmed")
        if confirmed is True:
            return "yes"
        if confirmed is False:
            values.discard(next((value for value in values if value.startswith("其它")), ""))
        else:
            return "unknown"
    non_chat_tokens = ("提示词", "图形界面", "无自然人直接交互界面")
    if values and all(any(token in value for token in non_chat_tokens) for value in values):
        return "no"
    return "unknown"


def derive_b12_companion_status(answers: dict) -> str:
    """从B12客观事实派生陪伴型聊天机器人状态，不推定unknown成立。"""
    b12 = answers.get("B12")
    if not isinstance(b12, dict):
        return "conditional"
    core = [
        b12.get("natural_language_interface"),
        b12.get("adaptive_humanlike_responses"),
        b12.get("social_or_emotional_function"),
        b12.get("sustains_relationship"),
    ]
    if "no" in core:
        return "no"
    if any(value != "yes" for value in core):
        return "conditional"
    use_cases = set(b12.get("use_cases") or [])
    if not use_cases:
        return "conditional"
    excluded_only = {"客服", "企业运营", "基于源信息的生产力或分析", "内部研究", "技术支持"}
    if use_cases and use_cases <= excluded_only:
        return "no"
    if use_cases == {"游戏功能"}:
        status = b12.get("game_scope_limited")
        return "no" if status == "yes" else "conditional" if status != "no" else "yes"
    if use_cases == {"独立语音助手"}:
        device = b12.get("standalone_voice_device")
        emotional = b12.get("voice_emotional_output")
        if device == "yes" and emotional == "no":
            return "no"
        if device in {None, "unknown"} or emotional in {None, "unknown"}:
            return "conditional"
    return "yes"


def derive_b12_human_misidentification_status(answers: dict) -> str:
    """仅读B12身份事实；B10当前措施被刻意排除。"""
    b12 = answers.get("B12")
    if not isinstance(b12, dict):
        return "conditional"
    signals = {str(value).strip() for value in (b12.get("human_identity_signals") or [])}
    framing = b12.get("fictional_or_ai_framing")
    if "不确定" in signals or framing == "unknown" or framing is None:
        return "conditional"
    has_human_signal = bool(signals - {"以上皆无"})
    if has_human_signal and framing == "no":
        return "yes"
    if not has_human_signal and framing == "yes":
        return "no"
    return "conditional"


# ---------------------------------------------------------------------------
# B12 派生键的权威口径（B-11′，2026-09-23）
# ---------------------------------------------------------------------------
# 背景：三个派生键的消费情况原本不一致——`B5b_chat_status` 全仓零消费方（消费端一律
# 重算），而 `B12_companion_status` / `B12_human_misidentification_status` 被
# `build_skeleton` 直读落盘值（不重算）。一个派生键写错即可端到端静默改变交付物的
# 义务总览行集合，且 `overview_rows()` 的行集合无任何机器比对。
#
# 本节的统一口径：**权威值由代码重算**（确定性、可复现），落盘值仅作审计留痕；
# 但人工可基于代码不可捕获的产品语境作**更严**判定，故取「重算值」与「落盘值」中
# **较严**者作为权威值——以免机械重算覆盖真实业务状态（案例32：低龄儿童语境下
# 人工取 conditional，而重算为 no）。落盘值**更宽**（少报）方属可疑，由
# `cross_check_derived_keys()` 报答案级矛盾。

# 三态严格度序：no（不适用）＜ conditional（待核）＜ yes（义务成立）
_B12_STRICTNESS = {"no": 0, "conditional": 1, "yes": 2}

# B5b_chat_status 三态严格度序：no（无对话）＜ unknown（不确定）＜ yes（有对话）
_CHAT_STRICTNESS = {"no": 0, "unknown": 1, "yes": 2}


def b12_card_in_play(answers: dict) -> bool:
    """B12 卡是否进入判定范围。

    门控与 TRIGGER_TABLE 的 B12 行同源（``B5b_chat_status∈{yes,unknown}``），但**要求 B5b
    实际采集过**（存在且非空）：若整题未采集，则正确的诊断是「交互事实缺失」（更上游的
    缺口），此时报「B12 缺键」属误报——也会把仅含最小字段的合成审计全部噪声化。

    另加防御分支：卡未触发但已落 B12 对象（口径分裂态）按已进入判定处理，
    以免同一份骨架出现「效力核验行有、义务总览行无」。
    """
    b5b = answers.get("B5b")
    if isinstance(b5b, list) and b5b and derive_b5b_chat_status(answers) in {"yes", "unknown"}:
        return True
    return isinstance(answers.get("B12"), dict)


def _stricter(derived: str, recorded: object, order: dict[str, int]) -> str:
    """取重算值与落盘值中较严者；落盘值缺失/越界时以重算值为准。"""
    rec = str(recorded).strip().lower() if recorded is not None else ""
    if rec in order:
        return max((derived, rec), key=lambda v: order[v])
    return derived


def resolve_b12_companion_status(answers: dict) -> str:
    """B12-① 权威值：卡未进入判定 → ``"not_triggered"``；否则取较重算的较严者。"""
    if not b12_card_in_play(answers):
        return "not_triggered"
    return _stricter(
        derive_b12_companion_status(answers),
        answers.get("B12_companion_status"),
        _B12_STRICTNESS,
    )


def resolve_b12_human_misidentification_status(answers: dict) -> str:
    """B12-② 权威值，口径同 :func:`resolve_b12_companion_status`。"""
    if not b12_card_in_play(answers):
        return "not_triggered"
    return _stricter(
        derive_b12_human_misidentification_status(answers),
        answers.get("B12_human_misidentification_status"),
        _B12_STRICTNESS,
    )


TRIGGER_TABLE: list[dict] = [
    {
        "id": "B1",
        "depends_on": {"A2"},
        "cond": lambda a: a.get("A2") not in (None, "仅内部使用"),
        "desc": "A2≠仅内部使用",
    },
    {
        "id": "B2",
        "depends_on": set(),
        "cond": lambda a: True,
        "always": True,  # 内部不变量锚点：见 resolve_triggers() 的断言
        "desc": "恒触发（上游关系子问仅在 A1=否/部分时展开）",
    },
    {
        "id": "B3a",
        "depends_on": {"A6"},
        "cond": lambda a: _a6_has(a, "加州"),
        "desc": "A6含加州",
    },
    {
        "id": "B4",
        "depends_on": {"A2"},
        "cond": lambda a: a.get("A2") not in (None, "仅内部使用"),
        "desc": "A2≠仅内部使用",
    },
    {
        "id": "B5a",
        "depends_on": {"A6", "A3"},
        "cond": lambda a: _a6_has(a, "中国") and _a3_generates(a),
        "desc": "A6含中国 且 A3含任一生成模态",
    },
    {
        "id": "B5b",
        "depends_on": {"A6"},
        "cond": lambda a: (_a6_has(a, "欧盟") or _a6_has(a, "加州")) and _b5b_interactive(a),
        "desc": "A6含欧盟或加州 且产品可能与自然人交互",
    },
    {
        "id": "B6",
        "depends_on": {"A6", "A3"},
        "cond": lambda a: _a6_has(a, "欧盟") and _a3_any(a, ("文本",)),
        "desc": "A3含文本 且 A6含欧盟（①承担门控）",
    },
    {
        # B-7（2026-09-23）：Art. 50(4) 第 1-2 项（深度伪造：图像/音频/视频）此前无采集位——
        # 与 B6（第 3 项·公共利益文本）同属该款但对**不同模态**，故单列一行触发状态、
        # 独立落盘 `B6_deepfake`；呈现仍并入 B6 卡（一次采集，不增交互轮次）。
        "id": "B6-深伪",
        "depends_on": {"A6", "A3"},
        "cond": lambda a: _a6_has(a, "欧盟") and _a3_any(a, ("图像", "音频", "视频")),
        "desc": "A3含图像/音频/视频 且 A6含欧盟（Art. 50(4) 第1-2项深伪披露）",
    },
    {
        "id": "B7",
        "depends_on": {"B1_1"},
        "cond": lambda a: bool(a.get("B1_hardware")) or "硬件" in str(a.get("B1_1", [])),
        "desc": "B1①选硬件设备，或初始描述涉及硬件",
    },
    {
        "id": "B8-1~4",
        "depends_on": {"A6"},
        "cond": lambda a: _a6_has(a, "中国"),
        "desc": "A6含中国",
    },
    {
        "id": "B9",
        "depends_on": {"A6"},
        "cond": lambda a: _a6_has(a, "欧盟"),
        "desc": "A6含欧盟",
    },
    {
        "id": "B10",
        "depends_on": {"A3"},
        "cond": lambda a: _a3_generates(a),
        "desc": "A3功能含生成且有输出模态（纯分析/检测型不问）",
    },
    {
        "id": "B12",
        "depends_on": {"A6", "B5b"},
        "cond": lambda a: _a6_has(a, "加州") and derive_b5b_chat_status(a) in {"yes", "unknown"},
        "desc": "A6含加州 且 B5b_chat_status为yes/unknown",
    },
    {
        "id": "B13",
        "depends_on": {"A6"},
        "cond": lambda a: _a6_has(a, "加州"),
        "desc": "A6含加州（入口题恒呈现；卡内role=none时终止后续）",
    },
]


class AnchorViolation(AssertionError):
    pass


class InvariantViolation(AssertionError):
    """触发表内部不变量被破坏（多与「答案没读到」同源）。"""


def assert_conditions_not_anchored_on_a4() -> None:
    """元规则锁死：任何 B 组触发条件都不得引用 A4（modeA-questionnaire 防漂移规则）。"""
    offenders = [row["id"] for row in TRIGGER_TABLE if "A4" in row["depends_on"]]
    if offenders:
        raise AnchorViolation(
            f"触发条件锚定了 A4（违反 modeA-questionnaire「触发条件锚定规则」）：{', '.join(offenders)}"
        )


def assert_b10_isolation() -> None:
    """B10只能用于差距分析，不得进入触发或法律适用派生链。"""
    forbidden = {"B10", "B10_current_practices", "B10_status"}
    offenders = [
        row["id"] for row in TRIGGER_TABLE
        if forbidden & set(row.get("depends_on", set()))
    ]
    if offenders:
        raise AnchorViolation("B10进入触发链：" + ", ".join(offenders))


def always_true_ids() -> list[str]:
    """声明为恒触发的行（数据驱动，避免用「恰好返回 True 的 lambda」当不变量）。"""
    return [row["id"] for row in TRIGGER_TABLE if row.get("always")]


def resolve_triggers(answers: dict) -> list[str]:
    assert_conditions_not_anchored_on_a4()
    assert_b10_isolation()
    triggered = [row["id"] for row in TRIGGER_TABLE if row["cond"](answers)]
    missing = [tid for tid in always_true_ids() if tid not in triggered]
    if missing:
        raise InvariantViolation(
            "触发表内部不变量被破坏：恒触发行未解析为触发（"
            + ", ".join(missing)
            + "）。通常意味着答案未被正确读取，请检查 survey_audit.json 结构"
        )
    return triggered


def china_connection_points(answers: dict) -> dict[str, str]:
    """按义务连接点返回 true/false/unknown，不把中国法域当作单一总开关。"""
    a4b = answers.get("A4b") or {}
    cn_access = a4b.get("中国") if isinstance(a4b, dict) else None
    if cn_access == "不确定":
        domestic_application = "unknown"
    else:
        domestic_application = "true" if cn_access in {"主动提供", "被动可达"} else "unknown"
    public_service = "unknown" if answers.get("A2") in {None, "不确定"} else (
        "false" if answers.get("A2") == "仅内部使用" else domestic_application
    )
    content_public = str(answers.get("B8_1", "")).strip()
    if content_public not in {"是", "否"}:
        content_public = "unknown"
    filing = "unknown"
    security = "unknown"
    if public_service == "false":
        filing = security = "false"
    elif public_service == "true":
        if content_public == "否":
            filing = security = "false"
        elif content_public == "是":
            filing = security = "unknown" if any(
                str(answers.get(key, "")).strip() in {"不确定", ""} for key in ("B8_2", "B8_3")
            ) else "true"
    return {
        "domestic_deep_synthesis_application": domestic_application,
        "domestic_public_genai_service": public_service,
        "content_public_distribution": content_public,
        "algorithm_filing": filing,
        "security_assessment": security,
    }


# ---------------------------------------------------------------------------
# 答案级交叉校验
# ---------------------------------------------------------------------------


def _scale_ordinal_from_raw(value) -> int | None:
    """把 B3a_details.raw_value 的自由数值映射到 SCALE_ORDINAL 序数档；无法解析返回 None。

    支持 900000 / "900000" / "约90万" / "90万" / "0.9million" 等落盘形态；
    档位判断只作区间覆盖检查，不强制格式。
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        n = float(value)
    elif isinstance(value, str):
        s = value.strip().replace(",", "").replace("，", "")
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*万", s)
        if m:
            n = float(m.group(1)) * 10000
        else:
            m2 = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
            if not m2:
                return None
            n = float(m2.group(1))
            if ("million" in s.lower()) or ("百万" in s):
                n *= 1000000
    else:
        return None
    if n < 0:
        return None
    if n == 0:
        return 0
    if n < 10000:
        return 1
    if n < 100000:
        return 2
    if n < 1000000:
        return 3
    if n < 10000000:
        return 4
    return 5


def cross_check_scale(answers: dict) -> list[str]:
    """校验规模摘要和详情的内部完整性，不把不同法定口径强行比较。

    `covered provider` 的系统访问规模与 `large online platform` 的平台独立用户
    规模在法条中是两个不同指标。旧版答案只有档位时，保留值域检查和待核提示；
    只有详情字段明确同一统计对象、地域、周期和去重方法时，才允许作数值比较。
    """
    problems: list[str] = []
    b3a = str(answers.get("B3a", "")).strip()
    if b3a and b3a not in B3A_RANGE:
        if b3a == "不确定":
            return problems
        return [
            f"B3a 档位无法识别：「{b3a}」（允许值：≤100万 / >100万 / 不确定）",
            "提示：B3a 只保存门槛摘要；请补充 B3a_details 的统计对象、地域、周期和去重方法",
        ]
    if str(answers.get("B4_2", "")).strip() in {"是", "不确定"}:
        raw = str(answers.get("B4_2c", "")).strip()
        if raw and raw != "不确定" and raw not in B4_2C_ORDINAL:
            problems.append(
                f"B4_2c 档位无法识别：「{raw}」（允许值：≤100万 / 100万-200万 / >200万 / 不确定）"
            )
        # F-4（2026-09-23）：平台候选成立（B4_2=是/不确定）时门槛口径卡不得缺席——
        # 「接收分发内容用户」与「创作者·协作者用户」是 large online platform 三要件中
        # 200 万独立月用户量级关的**法定区分**（role-mapping 环节④规模关、ca-rules §2；
        # 问卷 B4②(c) 同源），agent 不得把平台总用户与二者混为一个数字。
        # 与同族规则（下方 monthly_values）**同层级**：答案级问题、退出码 1，不伪造历史数据。
        # 只钉「字段在位」，不要求数值非空（探数未果可落空数组＋阈值解释记待核）；
        # 摘要档位为「不确定」时不强求（无确定量级即无需该区分）。
        if raw and raw != "不确定":
            details = answers.get("B4_2c_details")
            if not isinstance(details, dict):
                problems.append(
                    "B4_2c 给出确定量级但缺 B4_2c_details 门槛口径卡：须记录此前12个月逐月独立用户、"
                    "接收分发内容用户、创作者/协作者用户（问卷 B4②(c)）；未采到者可落空数组并记待核"
                )
            else:
                missing_lop = [
                    f
                    for f in ("recipient_users", "creator_or_collaborator_users")
                    if f not in details
                ]
                if missing_lop:
                    problems.append(
                        "B4_2c_details 缺字段 " + "、".join(missing_lop)
                        + "（接收分发内容用户与创作者/协作者用户是 large online platform 门槛的法定区分，须分别记录）"
                    )

    # 新版平台详情要求逐月数据；旧版摘要没有详情时只列待核提示，不伪造历史数据。
    platform_details = answers.get("B4_2c_details")
    if isinstance(platform_details, dict):
        monthly = platform_details.get("monthly_values")
        if monthly is not None:
            if not isinstance(monthly, list) or len(monthly) != 12:
                problems.append("B4_2c_details.monthly_values 未提供完整的此前12个月逐月数据")
            elif any(not isinstance(item, (int, float, dict)) or isinstance(item, bool) for item in monthly):
                problems.append("B4_2c_details.monthly_values 含无法识别的月度数值")
        elif answers.get("B4_2c") not in (None, "", "不确定"):
            problems.append("B4_2c 只有门槛摘要，缺少 B4_2c_details.monthly_values；请核实此前12个月数据")

    # ---- B-1 同记录自洽校验（B3a 档位 × B3a_details.raw_value，2026-09-23 新增）----
    # 单记录内部自洽：raw_value 落入某档区间而勾选档位与之矛盾 → 答案级矛盾。
    # 零跨口径推理、不依赖 A4a；raw_value 缺失不报（详情允许后续补）；B3a=不确定跳过。
    if b3a and b3a != "不确定" and isinstance(answers.get("B3a_details"), dict):
        details = answers["B3a_details"]
        raw_ordinal = _scale_ordinal_from_raw(details.get("raw_value"))
        if raw_ordinal is not None:
            lo, hi = B3A_RANGE[b3a]
            if not (lo <= raw_ordinal <= hi):
                problems.append(
                    f"B3a 档位与详情矛盾：勾选「{b3a}」但 B3a_details.raw_value="
                    f"「{details.get('raw_value')}」应落更高档位——请回问归一（B-1）"
                )

    # ---- B-3 同口径 A4a×B3a 档位交叉（2026-09-23 新增；D-1 全球口径定稿后实施）----
    # 仅当 B3a_details 与某法域 A4a_details 的统计口径四要素（metric/scope/period/unique）
    # 完全一致（同口径）时才作档位比对；跨口径（如 B3a=global vs A4a=加州轮）维持
    # 「不同统计口径不得直接比较」的设计性 leniency，仅输出提示行。
    a4a_details = answers.get("A4a_details")
    if (
        b3a and b3a != "不确定"
        and isinstance(answers.get("B3a_details"), dict)
        and isinstance(a4a_details, dict)
    ):
        b3 = answers["B3a_details"]
        b3_keys = ("metric", "scope", "period", "unique")
        b3_sig = tuple(str(b3.get(k, "")).strip().lower() for k in b3_keys)
        for juris, det in a4a_details.items():
            if not isinstance(det, dict):
                continue
            a4_sig = tuple(str(det.get(k, "")).strip().lower() for k in b3_keys)
            if a4_sig != b3_sig:
                continue  # 跨口径：不硬性比较（设计性 leniency）
            raw_ord = _scale_ordinal_from_raw(det.get("raw_value"))
            if raw_ord is None:
                continue
            lo, hi = B3A_RANGE[b3a]
            if not (lo <= raw_ord <= hi):
                problems.append(
                    f"B3a 档位与 {juris} A4a_details 同口径矛盾：B3a=「{b3a}」但 "
                    f"A4a_details.{juris}.raw_value=「{det.get('raw_value')}」不落该档——"
                    "请回问归一（B-3）"
                )
                break  # 同口径矛盾报一次即够，避免多法域重复报

    # ---- B-2 metric 口径锁（V3-02 修复，2026-09-23 新增）----
    # B3a 锚定法条 "monthly visitors or users"（§22757.1(d)）；downloads/累计注册类
    # 口径冒充月活 → 答案级矛盾，要求回问归一。闭集外 metric 一律拦截。
    if b3a and b3a != "不确定" and isinstance(answers.get("B3a_details"), dict):
        metric_raw = str(answers["B3a_details"].get("metric", "")).strip()
        metric = metric_raw.lower()
        if metric and metric not in B3A_METRIC_ALLOWED:
            problems.append(
                f"B3a 口径锁：B3a_details.metric=「{metric_raw}」不在月度访客/用户闭集——"
                "B3a 须以 monthly visitors or users 口径作答，请回问归一（V3-02）"
            )

    return problems


def cross_check_derived_keys(answers: dict) -> tuple[list[str], list[str]]:
    """派生键一致性校验（B-11′）：返回 ``(errors, warnings)``。

    三态处置（缺键／值不等／一致）＋**方向敏感**：

    1. **缺键**——B12 双键仅在「卡应进入判定范围（``B5b_chat_status∈{yes,unknown}``）
       且未落 B12 对象、亦无派生键」时计为失配（卡未触发时不落键属正常，不得报）；
       ``B5b_chat_status`` 缺键不报（零消费方，消费端重算）。
    2. **值不等**——按方向敏感处置：落盘值**更宽**（少报）→ error（须回问归一）；
       落盘值**更严**（多报，如人工按产品语境取更严口径）→ warning 留痕、放行。
       若取「严格相等即报错」，会误伤保守判定，与本 skill「不确定按最严口径」冲突。
    3. **一致**——不报。
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ---- B5b_chat_status：值不等按方向报（缺键不报）----
    chat_derived = derive_b5b_chat_status(answers)
    chat_recorded = answers.get("B5b_chat_status")
    if chat_recorded is not None and chat_derived is not None:
        rec = str(chat_recorded).strip().lower()
        if rec in _CHAT_STRICTNESS and rec != chat_derived:
            detail = (
                f"B5b_chat_status 落盘「{rec}」≠ 源答案重算「{chat_derived}」"
            )
            if _CHAT_STRICTNESS[rec] < _CHAT_STRICTNESS[chat_derived]:
                errors.append(
                    detail + "——落盘更宽（少报交互形态），请回问归一并覆盖落盘值（B-11′）"
                )
            else:
                warnings.append(detail + "——落盘更严，按留痕放行（B-11′）")

    # ---- B12 双键：缺键带前置条件 + 值不等按方向报 ----
    card_in_play = b12_card_in_play(answers)
    has_b12_object = isinstance(answers.get("B12"), dict)
    for key, derive_fn in (
        ("B12_companion_status", derive_b12_companion_status),
        ("B12_human_misidentification_status", derive_b12_human_misidentification_status),
    ):
        recorded = answers.get(key)
        if recorded is None:
            # 前置条件（B-11′ 8.3③-(b)）：卡应进入判定范围却三者（B12 对象＋派生键）皆无
            if card_in_play and not has_b12_object:
                errors.append(
                    f"{key} 缺键：B5b_chat_status 表明 B12 卡应已采集"
                    f"（∈{{yes,unknown}}），但审计既未落 B12 对象、亦无派生键——"
                    "请补采集 B12 卡并重算派生键（B-11′）"
                )
            continue
        rec = str(recorded).strip().lower()
        if rec not in _B12_STRICTNESS:
            continue  # 值域由契约层（survey_io._ENUMS）把关，此处不重复
        derived = derive_fn(answers)
        if rec == derived:
            continue
        detail = f"{key} 落盘「{rec}」≠ 由 B12 客观事实重算「{derived}」"
        if _B12_STRICTNESS[rec] < _B12_STRICTNESS[derived]:
            errors.append(
                detail + "——落盘更宽（少报义务），请回问归一（B-11′）"
            )
        else:
            warnings.append(
                detail + "——落盘更严，按留痕放行（B-11′；骨架据此取较严值）"
            )
    return errors, warnings


# ---------------------------------------------------------------------------
# B5a 高仿真能力 × A3 输出模态 相容性（2026-09-19 用户裁定新增）
# ---------------------------------------------------------------------------
# 依据 `modeA-questionnaire.md` 「B5a判定备注（中国侧 A3 模态与高仿真能力核对，防止漏勾）」：
# A3 采集产品的**输出模态**，B5a 采集是否具备**深度合成规定第17条第1款所列高仿真能力**，
# 二者相关但不等同。该备注的落点是「防漏勾」（A3 含某模态而 B5a 未勾 → 不得直接采信
# 「以上皆无」），但「风景图／无人脸视频／音乐音效」等**可合法不勾**，机器无从裁断，
# 故漏勾方向**不代码化**、仍由人工按五条映射追问。
# 本函数只代码化**单向的「过度勾选」**：所勾能力依赖的输出模态在 A3 中**完全不存在**
# （如纯文本产品勾「人脸生成/替换/操控」「数字人」「沉浸式拟真场景」）——这是客观不可能，
# 可直接判为答案级矛盾。
# 新增能力选项时须同步本表（选项集见 modeA-questionnaire B5a；业务版皮肤继承母版同一选项集）。
B5A_REQUIRES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("智能对话", "智能写作"), ("文本",)),
    (("合成人声", "仿声", "语音合成", "语音克隆"), ("音频", "视频")),
    (("人脸生成", "人脸替换", "人脸操控", "换脸"), ("图像", "视频")),
    (("姿态操控",), ("图像", "视频")),
    (("沉浸式拟真场景",), ("虚拟场景", "3D", "视频")),
    (("数字人", "虚拟人"), ("数字人", "虚拟人", "图像", "视频", "虚拟场景")),
)

# B5a 中「不作肯定主张」的选项：未勾选任何能力，不参与过度勾选校验。
B5A_NON_CLAIM = ("以上皆无", "不确定")


def cross_check_capability_modality(answers: dict) -> list[str]:
    """B5a 勾选能力 × A3 输出模态 相容性（单向：防过度勾选）。

    只报「勾了能力、但产品根本不产出该能力所需模态」这一类客观不可能；
    漏勾与「以上皆无」是否可信属人工追问（见 modeA-questionnaire B5a判定备注），不在此报。
    """
    problems: list[str] = []
    ticks = [str(x).strip() for x in (answers.get("B5a") or []) if str(x).strip()]
    modalities = _a3_modalities(answers)
    if not ticks or not modalities:
        return problems
    for caps, mods in B5A_REQUIRES:
        hit = [t for t in ticks if any(c in t for c in caps)]
        if not hit:
            continue
        if any(m in mod for mod in modalities for m in mods):
            continue
        problems.append(
            f"能力与模态矛盾：B5a 勾选了「{'／'.join(hit)}」，"
            f"但 A3 输出模态为「{'、'.join(modalities)}」——"
            f"该能力需可生成「{'／'.join(mods)}」，产品既不产出该模态即不可能具备该能力。"
            "须即时弹窗核对（A3 漏勾模态？或 B5a 误勾？），并按 modeA-questionnaire"
            "「矛盾处理规则」以产品实际功能描述为准回退"
        )
    return problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

DEMO = {
    "A1": "部分自研",
    "A2": "B2C",
    "A3": ["文本", "音频"],
    "A4a": {"中国": "1000万+", "欧盟": "100万-1000万", "加州": "10-100万"},
    "A6": ["中国大陆", "欧盟", "加州"],
    "B1_1": ["App"],
    "B3a": "≤100万",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B 组触发引擎与答案级交叉校验")
    parser.add_argument("survey", nargs="?", help="survey_audit.json（结构化问卷答案）")
    parser.add_argument("--demo", action="store_true", help="用内置样例演示")
    args = parser.parse_args(argv)

    if args.demo:
        answers = DEMO
        print("（演示）B3a与A4(a)统计对象或地域未统一 → 仅提示补充详情，不报硬性规模矛盾")
    elif args.survey:
        try:
            answers = survey_io.load_audit(Path(args.survey))
        except survey_io.AuditFormatError as exc:
            print(f"resolve_triggers: 无法读取答案（未执行）：{exc}", file=sys.stderr)
            return 2
    else:
        parser.error("需要 survey_audit.json 或 --demo")

    try:
        triggered = resolve_triggers(answers)
    except (AnchorViolation, InvariantViolation) as exc:
        print(f"resolve_triggers: 内部不变量被破坏（未执行）：{exc}", file=sys.stderr)
        return 2

    problems = cross_check_scale(answers)
    problems += cross_check_capability_modality(answers)
    derived_errors, derived_warnings = cross_check_derived_keys(answers)
    problems += derived_errors

    keys = survey_io.recognised_keys(answers)
    print(f"已识别答案键：{len(keys)} 个（{', '.join(keys) if keys else '无'}）")
    print("触发状态：")
    for row in TRIGGER_TABLE:
        mark = "触发" if row["id"] in triggered else "不触发"
        print(f"  [{mark}] {row['id']:<8} <- {row['desc']}")
    if derived_warnings:
        print("派生键留痕（按方向敏感放行，不计入失败）：")
        for w in derived_warnings:
            print(f"  [~] {w}")
    if problems:
        print("交叉校验：")
        for p in problems:
            print(f"  [!] {p}")
        return 1
    print("交叉校验：通过（无答案级问题）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
